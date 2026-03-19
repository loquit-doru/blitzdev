"""
FlashForge Task Client
Generic task polling, file upload, and response submission.
Supports any HTTP-based job queue with the same interface.
"""

import asyncio
import base64
import json
import time
from collections import OrderedDict
from typing import Optional, Dict, Any, Callable, AsyncGenerator, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import aiohttp

import sys
import os

_parent = os.path.dirname(os.path.abspath(__file__))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from config import settings, LogLevel


class AgentTaskError(Exception):
    """Base exception for agent task errors"""
    pass


class AgentAuthError(AgentTaskError):
    """Authentication error"""
    pass


class AgentTimeoutError(AgentTaskError):
    """Request timeout"""
    pass


class JobType(str, Enum):
    """Job types"""
    STANDARD = "STANDARD"
    SWARM = "SWARM"


class JobStatus(str, Enum):
    """Job status values"""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class ResponseType(str, Enum):
    """Response types"""
    TEXT = "TEXT"
    FILE = "FILE"


@dataclass
class FileAttachment:
    """File attachment for responses"""
    url: str
    name: str
    size: int
    type: str


@dataclass
class Job:
    """Agent task job structure"""
    id: str
    prompt: str
    budget: float
    status: JobStatus
    expires_at: str
    created_at: str
    response_count: int
    
    # V2 fields
    job_type: JobType = JobType.STANDARD
    max_agents: Optional[int] = None
    budget_per_agent: Optional[float] = None
    required_skills: List[str] = field(default_factory=list)
    min_reputation: Optional[float] = None
    accepted_count: int = 0
    accepted_id: Optional[str] = None
    router_version: Optional[int] = None
    
    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "Job":
        """Create from API response"""
        return cls(
            id=data.get("id", ""),
            prompt=data.get("prompt", ""),
            budget=float(data.get("budget", 0)),
            status=JobStatus(data.get("status", "OPEN")),
            expires_at=data.get("expiresAt", ""),
            created_at=data.get("createdAt", ""),
            response_count=data.get("responseCount", 0),
            job_type=JobType(data.get("jobType", "STANDARD")),
            max_agents=data.get("maxAgents"),
            budget_per_agent=data.get("budgetPerAgent"),
            required_skills=data.get("requiredSkills", []),
            min_reputation=data.get("minReputation"),
            accepted_count=data.get("acceptedCount", 0),
            accepted_id=data.get("acceptedId"),
            router_version=data.get("routerVersion")
        )
    
    def is_swarm(self) -> bool:
        """Check if this is a SWARM job"""
        return self.job_type == JobType.SWARM
    
    def is_open(self) -> bool:
        """Check if job is still open"""
        return self.status == JobStatus.OPEN


@dataclass
class AcceptJobResult:
    """Result of accepting a job"""
    success: bool
    acceptance_id: Optional[str] = None
    response_deadline: Optional[str] = None
    budget_per_agent: Optional[float] = None
    error: Optional[str] = None


@dataclass
class SubmitResponseResult:
    """Result of submitting a response"""
    success: bool
    response_id: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


@dataclass
class AgentInfo:
    """Agent information"""
    id: str
    name: str
    bio: str
    wallet_address: str
    reputation: float
    jobs_completed: int
    total_earnings: float
    is_verified: bool
    skills: List[str] = field(default_factory=list)


class AgentTaskClient:
    """
    Client for agent task HTTP API
    
    API Endpoints:
    - GET /jobs - List available jobs
    - GET /jobs/:id - Get specific job
    - POST /jobs/:id/accept - Accept a SWARM job
    - POST /jobs/:id/decline - Decline a job
    - POST /jobs/:id/respond - Submit response
    - POST /upload - Upload files (base64 encoded)
    """
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_url_v2: Optional[str] = None,
        api_key: Optional[str] = None,
        poll_interval: Optional[int] = None,
        timeout: Optional[int] = None
    ):
        self.api_url = (api_url or "https://task-api.local/v1").rstrip('/')
        self.api_url_v2 = (api_url_v2 or "https://task-api.local/v2" or self.api_url).rstrip('/')
        self.api_key = api_key or ""
        self.poll_interval = poll_interval or 3
        self.timeout = timeout or 300
        
        self.session: Optional[aiohttp.ClientSession] = None
        self._stop_polling = False
        self._last_job_id: Optional[str] = None
        self._processed_job_ids: OrderedDict = OrderedDict()  # FIFO dedup — insertion order preserved
        self._MAX_PROCESSED_IDS = 10_000  # Cap to prevent memory leak on long runs
        self._stats = {
            "polls": 0,
            "jobs_received": 0,
            "jobs_accepted": 0,
            "responses_submitted": 0,
            "files_uploaded": 0,
            "errors": 0
        }
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": f"FlashForge/{settings.APP_VERSION}"
            }
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self.session
    
    async def _request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        use_v2: bool = False
    ) -> Dict[str, Any]:
        """Make API request"""
        session = await self._get_session()
        base_url = self.api_url_v2 if use_v2 else self.api_url
        url = f"{base_url}{endpoint}"
        
        async with session.request(method, url, json=data) as resp:
            response_data = await resp.json()
            
            if not resp.ok:
                error_msg = response_data.get("message", f"API error: {resp.status}")
                raise AgentTaskError(error_msg)
            
            return response_data
    
    async def health_check(self) -> bool:
        """Check API health"""
        try:
            await self._request("/health", use_v2=True)
            return True
        except Exception as e:
            if settings.DEBUG:
                print(f"Health check failed: {e}")
            return False
    
    # ==================== Agent Management ====================
    
    async def register(
        self,
        wallet_address: str,
        owner_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Register a new agent"""
        data = {"walletAddress": wallet_address}
        if owner_url:
            data["ownerUrl"] = owner_url
        
        result = await self._request("/register", "POST", data, use_v2=True)
        
        # Update API key if returned
        if "apiKey" in result:
            self.api_key = result["apiKey"]
        
        return result
    
    async def get_me(self) -> AgentInfo:
        """Get current agent information"""
        data = await self._request("/me", use_v2=True)
        
        return AgentInfo(
            id=data.get("id", ""),
            name=data.get("name", ""),
            bio=data.get("bio", ""),
            wallet_address=data.get("walletAddress", ""),
            reputation=float(data.get("reputation", 0)),
            jobs_completed=data.get("jobsCompleted", 0),
            total_earnings=float(data.get("totalEarnings", 0)),
            is_verified=data.get("isVerified", False),
            skills=data.get("skills", [])
        )
    
    async def update_profile(
        self,
        name: Optional[str] = None,
        bio: Optional[str] = None,
        profile_picture: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update agent profile"""
        data = {}
        if name:
            data["name"] = name
        if bio:
            data["bio"] = bio
        if profile_picture:
            data["profilePicture"] = profile_picture
        
        return await self._request("/me", "PATCH", data, use_v2=True)
    
    async def update_skills(self, skills: List[str]) -> Dict[str, Any]:
        """Update agent skills"""
        return await self._request("/me", "PATCH", {"skills": skills}, use_v2=True)
    
    async def verify(self) -> Dict[str, Any]:
        """Trigger verification check"""
        return await self._request("/verify", "POST", use_v2=True)
    
    # ==================== Job Management ====================
    
    async def list_jobs(
        self,
        limit: int = 20,
        offset: int = 0,
        use_v2: bool = True
    ) -> List[Job]:
        """List available jobs"""
        data = await self._request(
            f"/jobs?limit={limit}&offset={offset}",
            use_v2=use_v2
        )
        
        jobs = data.get("jobs", [])
        return [Job.from_api(job) for job in jobs]
    
    async def get_job(self, job_id: str, use_v2: bool = True) -> Job:
        """Get a specific job by ID"""
        data = await self._request(f"/jobs/{job_id}", use_v2=use_v2)
        return Job.from_api(data)
    
    async def accept_job(self, job_id: str) -> AcceptJobResult:
        """
        Accept a SWARM job (first-come-first-served)
        Must be called before submitting response for SWARM jobs
        """
        try:
            data = await self._request(
                f"/jobs/{job_id}/accept",
                "POST",
                use_v2=True
            )
            
            acceptance = data.get("acceptance", {})
            self._stats["jobs_accepted"] += 1
            
            return AcceptJobResult(
                success=True,
                acceptance_id=acceptance.get("id"),
                response_deadline=acceptance.get("responseDeadline"),
                budget_per_agent=acceptance.get("budgetPerAgent")
            )
        except Exception as e:
            return AcceptJobResult(success=False, error=str(e))
    
    async def decline_job(self, job_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Decline a job (optional, for analytics)"""
        data = {"reason": reason} if reason else {}
        return await self._request(
            f"/jobs/{job_id}/decline",
            "POST",
            data,
            use_v2=True
        )
    
    # ==================== Polling ====================
    
    async def poll_for_jobs(
        self,
        callback: Optional[Callable[[Job], None]] = None,
        stop_event: Optional[asyncio.Event] = None,
        use_v2: bool = True
    ) -> AsyncGenerator[Job, None]:
        """
        Poll for available jobs continuously
        
        Args:
            callback: Optional callback when job received
            stop_event: Event to stop polling
            use_v2: Use v2 API (includes SWARM jobs)
        
        Yields:
            Job when available
        """
        self._stop_polling = False
        poll_count = 0
        
        while not self._stop_polling:
            try:
                jobs = await self.list_jobs(use_v2=use_v2)
                poll_count += 1
                
                # Heartbeat every 20 polls (~60s at 3s interval)
                if poll_count % 20 == 0:
                    from datetime import datetime
                    now = datetime.now().strftime("%H:%M:%S")
                    print(f"  💓 [{now}] Poll #{poll_count} | {len(self._processed_job_ids)} jobs seen | {self._stats['responses_submitted']} submitted")
                
                for job in jobs:
                    # Skip already processed jobs (FIFO dedup via OrderedDict)
                    if job.id in self._processed_job_ids:
                        continue
                    
                    # Only process open jobs
                    if job.is_open():
                        self._processed_job_ids[job.id] = True
                        # FIFO eviction: remove OLDEST entries when cap exceeded
                        while len(self._processed_job_ids) > self._MAX_PROCESSED_IDS:
                            self._processed_job_ids.popitem(last=False)  # pop oldest
                        self._last_job_id = job.id
                        self._stats["jobs_received"] += 1
                        
                        if callback:
                            callback(job)
                        yield job
                
                # Check stop event
                if stop_event and stop_event.is_set():
                    break
                
                # Wait before next poll
                await asyncio.sleep(self.poll_interval)
                
            except AgentAuthError:
                raise
            except Exception as e:
                self._stats["errors"] += 1
                if settings.DEBUG:
                    print(f"Poll error: {e}")
                await asyncio.sleep(self.poll_interval)
    
    def stop_polling(self):
        """Stop polling loop"""
        self._stop_polling = True
    
    # ==================== Response Submission ====================
    
    async def submit_response(
        self,
        job_id: str,
        content: str,
        response_type: ResponseType = ResponseType.TEXT,
        files: Optional[List[FileAttachment]] = None,
        use_v2: bool = True,
        max_retries: int = 3
    ) -> SubmitResponseResult:
        """
        Submit a response to a job, with exponential backoff retry on transient errors.
        
        Args:
            job_id: Job ID
            content: Response content
            response_type: TEXT or FILE
            files: Optional file attachments (from upload_file)
            use_v2: Use v2 API
            max_retries: Max retry attempts on transient errors (5xx, network)
        
        Returns:
            SubmitResponseResult
        """
        data = {
            "content": content,
            "responseType": response_type.value
        }
        
        if files:
            data["files"] = [
                {
                    "url": f.url,
                    "name": f.name,
                    "size": f.size,
                    "type": f.type
                }
                for f in files
            ]
        
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                session = await self._get_session()
                base_url = self.api_url_v2 if use_v2 else self.api_url
                url = f"{base_url}/jobs/{job_id}/respond"
                
                async with session.request("POST", url, json=data) as resp:
                    response_data = await resp.json()
                    
                    if resp.status == 409:
                        # Already submitted — treat as success (idempotent)
                        self._stats["responses_submitted"] += 1
                        return SubmitResponseResult(
                            success=True,
                            message="Already submitted (409)",
                        )
                    
                    if resp.ok:
                        self._stats["responses_submitted"] += 1
                        return SubmitResponseResult(
                            success=True,
                            response_id=response_data.get("responseId"),
                            message=response_data.get("message")
                        )
                    
                    # Transient server errors (5xx) — retry with backoff
                    if resp.status >= 500 and attempt < max_retries:
                        wait = 2 ** attempt  # 2s, 4s, 8s
                        if settings.LOG_LEVEL == LogLevel.DEBUG:
                            print(f"Submit attempt {attempt} got {resp.status}, retrying in {wait}s...")
                        await asyncio.sleep(wait)
                        last_error = f"API error: {resp.status}"
                        continue
                    
                    # Client error (4xx) or final attempt — fail immediately
                    error_msg = response_data.get("message", f"API error: {resp.status}")
                    self._stats["errors"] += 1
                    return SubmitResponseResult(success=False, error=error_msg)
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = str(e)
                if attempt < max_retries:
                    wait = 2 ** attempt
                    if settings.LOG_LEVEL == LogLevel.DEBUG:
                        print(f"Submit attempt {attempt} failed ({e}), retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    continue
            except Exception as e:
                self._stats["errors"] += 1
                return SubmitResponseResult(success=False, error=str(e))
        
        # All retries exhausted
        self._stats["errors"] += 1
        return SubmitResponseResult(success=False, error=f"Failed after {max_retries} attempts: {last_error}")
    
    # ==================== File Upload ====================
    
    async def upload_file(self, file_path: Path) -> FileAttachment:
        """
        Upload a file (base64 encoded)
        
        Args:
            file_path: Path to file
        
        Returns:
            FileAttachment with URL
        """
        if not file_path.exists():
            raise AgentTaskError(f"File not found: {file_path}")
        
        # Get file info
        stats = file_path.stat()
        file_name = file_path.name
        
        # Determine MIME type
        ext = file_path.suffix.lower()
        mime_types = {
            ".zip": "application/zip",
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".json": "application/json",
            ".html": "text/html",
            ".css": "text/css",
            ".js": "text/javascript",
            ".ts": "text/typescript",
            ".md": "text/markdown",
            ".txt": "text/plain",
            ".tar": "application/x-tar",
            ".gz": "application/gzip",
        }
        mime_type = mime_types.get(ext, "application/octet-stream")
        
        # Read and encode file
        file_content = file_path.read_bytes()
        base64_content = base64.b64encode(file_content).decode("utf-8")
        
        # Upload
        data = {
            "files": [{
                "name": file_name,
                "content": base64_content,
                "type": mime_type
            }]
        }
        
        result = await self._request("/upload", "POST", data, use_v2=True)
        
        if not result.get("success"):
            raise AgentTaskError("Upload failed: No success flag")
        
        files = result.get("files", [])
        if not files:
            raise AgentTaskError("Upload failed: No files returned")
        
        file_result = files[0]
        self._stats["files_uploaded"] += 1
        
        return FileAttachment(
            url=file_result["url"],
            name=file_result["name"],
            size=file_result["size"],
            type=file_result["type"]
        )
    
    async def upload_bytes(
        self,
        file_name: str,
        file_bytes: bytes,
        mime_type: str = "application/zip"
    ) -> FileAttachment:
        """
        Upload file from bytes
        
        Args:
            file_name: File name
            file_bytes: File content as bytes
            mime_type: MIME type
        
        Returns:
            FileAttachment with URL
        """
        base64_content = base64.b64encode(file_bytes).decode("utf-8")
        
        data = {
            "files": [{
                "name": file_name,
                "content": base64_content,
                "type": mime_type
            }]
        }
        
        result = await self._request("/upload", "POST", data, use_v2=True)
        
        if not result.get("success"):
            raise AgentTaskError("Upload failed: No success flag")
        
        files = result.get("files", [])
        if not files:
            raise AgentTaskError("Upload failed: No files returned")
        
        file_result = files[0]
        self._stats["files_uploaded"] += 1
        
        return FileAttachment(
            url=file_result["url"],
            name=file_result["name"],
            size=file_result["size"],
            type=file_result["type"]
        )
    
    async def upload_multiple(self, file_paths: List[Path]) -> List[FileAttachment]:
        """Upload multiple files"""
        attachments = []
        for path in file_paths:
            attachment = await self.upload_file(path)
            attachments.append(attachment)
        return attachments
    
    # ==================== Statistics ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            **self._stats,
            "api_url": self.api_url,
            "api_url_v2": self.api_url_v2,
            "poll_interval": self.poll_interval
        }
    
    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None


# Singleton instance
_client: Optional[AgentTaskClient] = None


def get_task_client() -> AgentTaskClient:
    """Get or create task client singleton"""
    global _client
    if _client is None:
        _client = AgentTaskClient()
    return _client


