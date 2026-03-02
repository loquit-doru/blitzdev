"""
Tests for Seedstr API client (unit tests with mocked HTTP)
"""

import pytest
import asyncio
import json
import base64
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seedstr_client import (
    SeedstrClient, SeedstrError, SeedstrAuthError,
    Job, JobType, JobStatus, ResponseType,
    FileAttachment, SubmitResponseResult, AcceptJobResult, AgentInfo
)


# ==================== Data Models ====================

def test_job_from_api():
    """Test Job.from_api with standard job data"""
    data = {
        "id": "job-123",
        "prompt": "Build a calculator",
        "budget": 5.0,
        "status": "OPEN",
        "expiresAt": "2026-12-31T23:59:59Z",
        "createdAt": "2026-01-01T00:00:00Z",
        "responseCount": 2,
        "jobType": "STANDARD",
    }
    job = Job.from_api(data)
    assert job.id == "job-123"
    assert job.prompt == "Build a calculator"
    assert job.budget == 5.0
    assert job.status == JobStatus.OPEN
    assert job.job_type == JobType.STANDARD
    assert job.is_open()
    assert not job.is_swarm()


def test_job_from_api_swarm():
    """Test Job.from_api with SWARM job data"""
    data = {
        "id": "swarm-456",
        "prompt": "Create a landing page",
        "budget": 20.0,
        "status": "OPEN",
        "expiresAt": "2026-12-31T23:59:59Z",
        "createdAt": "2026-01-01T00:00:00Z",
        "responseCount": 0,
        "jobType": "SWARM",
        "maxAgents": 5,
        "budgetPerAgent": 4.0,
        "requiredSkills": ["web-development", "html"],
        "minReputation": 0.5,
    }
    job = Job.from_api(data)
    assert job.is_swarm()
    assert job.max_agents == 5
    assert job.budget_per_agent == 4.0
    assert job.required_skills == ["web-development", "html"]


def test_job_from_api_defaults():
    """Test Job.from_api with minimal data (defaults)"""
    data = {}
    job = Job.from_api(data)
    assert job.id == ""
    assert job.prompt == ""
    assert job.budget == 0.0
    assert job.job_type == JobType.STANDARD


def test_file_attachment():
    """Test FileAttachment dataclass"""
    fa = FileAttachment(
        url="https://cdn.seedstr.io/files/abc.zip",
        name="project.zip",
        size=12345,
        type="application/zip"
    )
    assert fa.name == "project.zip"
    assert fa.size == 12345


def test_agent_info():
    """Test AgentInfo dataclass"""
    info = AgentInfo(
        id="agent-1",
        name="BlitzDev",
        bio="AI web builder",
        wallet_address="So1Ana...",
        reputation=4.5,
        jobs_completed=10,
        total_earnings=50.0,
        is_verified=True,
        skills=["web-development"]
    )
    assert info.is_verified
    assert info.reputation == 4.5


# ==================== Client construction ====================

def test_client_defaults():
    """Test SeedstrClient initializes with config defaults"""
    client = SeedstrClient()
    assert "seedstr.io" in client.api_url
    assert client.poll_interval > 0
    assert client.timeout > 0


def test_client_custom_params():
    """Test SeedstrClient with custom parameters"""
    client = SeedstrClient(
        api_url="https://custom.api/v1",
        api_url_v2="https://custom.api/v2",
        api_key="test-key",
        poll_interval=10,
        timeout=60
    )
    assert client.api_url == "https://custom.api/v1"
    assert client.api_url_v2 == "https://custom.api/v2"
    assert client.api_key == "test-key"
    assert client.poll_interval == 10


def test_client_stats_initial():
    """Test initial stats are zeroed"""
    client = SeedstrClient()
    stats = client.get_stats()
    assert stats["polls"] == 0
    assert stats["jobs_received"] == 0
    assert stats["errors"] == 0


# ==================== Mocked API calls ====================

class MockResponse:
    """Mock aiohttp response"""
    def __init__(self, data, status=200):
        self._data = data
        self.status = status
        self.ok = 200 <= status < 300

    async def json(self):
        return self._data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.mark.asyncio
async def test_list_jobs():
    """Test listing jobs via mocked API"""
    client = SeedstrClient(api_key="test")
    mock_session = AsyncMock()
    mock_session.closed = False

    mock_resp = MockResponse({
        "jobs": [
            {
                "id": "j1",
                "prompt": "Build something",
                "budget": 10,
                "status": "OPEN",
                "expiresAt": "",
                "createdAt": "",
                "responseCount": 0,
            }
        ]
    })
    mock_session.request = MagicMock(return_value=mock_resp)
    client.session = mock_session

    jobs = await client.list_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "j1"
    assert jobs[0].budget == 10


@pytest.mark.asyncio
async def test_accept_job():
    """Test accepting a SWARM job"""
    client = SeedstrClient(api_key="test")
    mock_session = AsyncMock()
    mock_session.closed = False

    mock_resp = MockResponse({
        "acceptance": {
            "id": "acc-1",
            "responseDeadline": "2026-03-10T00:00:00Z",
            "budgetPerAgent": 5.0
        }
    })
    mock_session.request = MagicMock(return_value=mock_resp)
    client.session = mock_session

    result = await client.accept_job("swarm-1")
    assert result.success
    assert result.acceptance_id == "acc-1"
    assert result.budget_per_agent == 5.0


@pytest.mark.asyncio
async def test_submit_response():
    """Test submitting a response"""
    client = SeedstrClient(api_key="test")
    mock_session = AsyncMock()
    mock_session.closed = False

    mock_resp = MockResponse({
        "responseId": "resp-42",
        "message": "Response submitted"
    })
    mock_session.request = MagicMock(return_value=mock_resp)
    client.session = mock_session

    files = [FileAttachment(url="https://cdn/f.zip", name="f.zip", size=100, type="application/zip")]
    result = await client.submit_response(
        job_id="j1",
        content="Here is my solution",
        response_type=ResponseType.FILE,
        files=files
    )
    assert result.success
    assert result.response_id == "resp-42"


@pytest.mark.asyncio
async def test_upload_bytes():
    """Test uploading bytes"""
    client = SeedstrClient(api_key="test")
    mock_session = AsyncMock()
    mock_session.closed = False

    mock_resp = MockResponse({
        "success": True,
        "files": [{
            "url": "https://cdn.seedstr.io/files/abc.zip",
            "name": "test.zip",
            "size": 256,
            "type": "application/zip"
        }]
    })
    mock_session.request = MagicMock(return_value=mock_resp)
    client.session = mock_session

    attachment = await client.upload_bytes("test.zip", b"PK\x03\x04fake-zip-content")
    assert attachment.url == "https://cdn.seedstr.io/files/abc.zip"
    assert attachment.name == "test.zip"


@pytest.mark.asyncio
async def test_upload_file(tmp_path):
    """Test uploading a file from disk"""
    # Create temp file
    zip_path = tmp_path / "project.zip"
    zip_path.write_bytes(b"PK\x03\x04fake")

    client = SeedstrClient(api_key="test")
    mock_session = AsyncMock()
    mock_session.closed = False

    mock_resp = MockResponse({
        "success": True,
        "files": [{
            "url": "https://cdn.seedstr.io/files/proj.zip",
            "name": "project.zip",
            "size": 100,
            "type": "application/zip"
        }]
    })
    mock_session.request = MagicMock(return_value=mock_resp)
    client.session = mock_session

    attachment = await client.upload_file(zip_path)
    assert attachment.name == "project.zip"

    # Verify base64 encoding was used
    call_args = mock_session.request.call_args
    body = call_args.kwargs.get("json") or call_args[1].get("json")
    assert body is not None
    content_b64 = body["files"][0]["content"]
    # Should decode without error
    decoded = base64.b64decode(content_b64)
    assert decoded == b"PK\x03\x04fake"


@pytest.mark.asyncio
async def test_api_error_handling():
    """Test API error raises SeedstrError"""
    client = SeedstrClient(api_key="test")
    mock_session = AsyncMock()
    mock_session.closed = False

    mock_resp = MockResponse({"message": "Unauthorized"}, status=401)
    mock_session.request = MagicMock(return_value=mock_resp)
    client.session = mock_session

    with pytest.raises(SeedstrError, match="Unauthorized"):
        await client.list_jobs()


@pytest.mark.asyncio
async def test_get_me():
    """Test getting agent info"""
    client = SeedstrClient(api_key="test")
    mock_session = AsyncMock()
    mock_session.closed = False

    mock_resp = MockResponse({
        "id": "agent-99",
        "name": "TestAgent",
        "bio": "A test agent",
        "walletAddress": "So1...",
        "reputation": 3.7,
        "jobsCompleted": 5,
        "totalEarnings": 25.0,
        "isVerified": True,
        "skills": ["python"]
    })
    mock_session.request = MagicMock(return_value=mock_resp)
    client.session = mock_session

    info = await client.get_me()
    assert info.name == "TestAgent"
    assert info.is_verified
    assert info.skills == ["python"]


@pytest.mark.asyncio
async def test_close_session():
    """Test session cleanup"""
    client = SeedstrClient(api_key="test")
    mock_session = AsyncMock()
    mock_session.closed = False
    client.session = mock_session

    await client.close()
    mock_session.close.assert_called_once()
