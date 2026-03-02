"""
Multi-LLM Manager for BlitzDev
Handles Groq (primary), DeepSeek/Gemini (fallback), and Anthropic (quality)
with automatic fallback across ALL configured providers.

Resilience features (inspired by defi-agent):
  - Per-provider cooldown: skip provider for 60s after failure/429
  - Request timeout: 45s hard limit per API call
  - Last-successful-provider caching (warm path)
  - DeepSeek max_tokens cap (8192 API limit)
  - Content Validation Gate for short-response detection
"""

import asyncio
import time
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum
import json

import aiohttp
from groq import AsyncGroq
from openai import AsyncOpenAI  # used for DeepSeek (OpenAI-compatible API)
from anthropic import AsyncAnthropic
from google import genai
from google.genai import types as genai_types

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings, LLMProvider, LogLevel

# ── Resilience constants ─────────────────────────────────────────────
PROVIDER_COOLDOWN_SEC = 60        # skip provider for 60s after failure
REQUEST_TIMEOUT_SEC = 180         # hard timeout per API call (Gemini~65s, DeepSeek~110s, Anthropic~180s)
DEEPSEEK_MAX_TOKENS = 8192       # DeepSeek API hard limit


class LLMError(Exception):
    """Base exception for LLM errors"""
    pass


class LLMRateLimitError(LLMError):
    """Rate limit exceeded"""
    pass


class LLMTimeoutError(LLMError):
    """Request timeout"""
    pass


@dataclass
class LLMResponse:
    """Standardized LLM response"""
    content: str
    provider: LLMProvider
    model: str
    tokens_used: Optional[int] = None
    generation_time: float = 0.0
    success: bool = True
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMManager:
    """Manages multiple LLM providers with fallback logic"""
    
    def __init__(self):
        self.clients: Dict[LLMProvider, Any] = {}
        self._init_clients()
        self.request_history: List[Dict[str, Any]] = []
        # Resilience state (borrowed from defi-agent)
        self._cooldowns: Dict[LLMProvider, float] = {}  # provider → cooldown-until timestamp
        self._last_successful: Dict[str, LLMProvider] = {}  # role → last provider that worked
        
    def _init_clients(self):
        """Initialize LLM clients"""
        # Groq Client (planner — FREE, ultra-fast)
        if settings.GROQ_API_KEY:
            self.clients[LLMProvider.GROQ] = AsyncGroq(
                api_key=settings.GROQ_API_KEY
            )
        
        # DeepSeek Client (OpenAI-compatible API — cheap fallback)
        if settings.DEEPSEEK_API_KEY:
            self.clients[LLMProvider.DEEPSEEK] = AsyncOpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com"
            )
        
        # Google Gemini Client (native SDK — FREE builder)
        if settings.GOOGLE_API_KEY:
            self.clients[LLMProvider.GEMINI] = genai.Client(
                api_key=settings.GOOGLE_API_KEY
            )
        
        # Anthropic Client (quality last resort — $$)
        if settings.ANTHROPIC_API_KEY:
            self.clients[LLMProvider.ANTHROPIC] = AsyncAnthropic(
                api_key=settings.ANTHROPIC_API_KEY
            )
    
    def _is_cooling_down(self, provider: LLMProvider) -> bool:
        """Check if provider is on cooldown (recently failed/429'd)."""
        until = self._cooldowns.get(provider)
        if not until:
            return False
        if time.time() > until:
            del self._cooldowns[provider]
            return False
        remaining = until - time.time()
        print(f"  ⏳ {provider.value} on cooldown ({remaining:.0f}s left) — skipping")
        return True

    def _set_cooldown(self, provider: LLMProvider, seconds: float = PROVIDER_COOLDOWN_SEC):
        """Put provider on cooldown after failure."""
        self._cooldowns[provider] = time.time() + seconds
        print(f"  🧊 {provider.value} → cooldown for {seconds:.0f}s")

    async def generate(
        self,
        prompt: str,
        provider: Optional[LLMProvider] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        fallback: bool = True,
        min_content_length: int = 0
    ) -> LLMResponse:
        """
        Generate text using specified or primary provider with optional fallback.
        
        Content Validation Gate: if min_content_length > 0, a response shorter
        than that threshold is treated as a failure (triggers retry / fallback)
        even when the API call itself succeeded.  This catches Gemini's
        intermittent "degenerate short response" pattern.
        
        Args:
            prompt: User prompt
            provider: Specific provider to use (defaults to PRIMARY_LLM)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt
            fallback: Whether to try fallback providers on failure
            min_content_length: Minimum acceptable response length (0 = disabled)
        
        Returns:
            LLMResponse with generated content and metadata
        """
        provider = provider or settings.PRIMARY_LLM
        temperature = temperature or settings.TEMPERATURE_BUILDER
        max_tokens = max_tokens or settings.MAX_TOKENS
        
        # ── Build smart fallback chain ────────────────────────
        # Use tagged entries to allow Gemini to appear twice (Flash then Pro)
        # Each entry is (provider, tag) where tag differentiates duplicates
        tagged_chain: List[tuple] = [(provider, "primary")]
        if fallback:
            smart_order: List[tuple] = []
            # If primary is Gemini, add Gemini Pro as immediate fallback
            if provider == LLMProvider.GEMINI:
                smart_order.append((LLMProvider.GEMINI, "alt"))  # alt = Pro model
            smart_order.extend([
                (settings.FALLBACK_LLM, "primary"),
                (LLMProvider.DEEPSEEK, "primary"),
            ])
            # Add remaining configured providers (except quality LLM)
            for p in LLMProvider:
                if p != provider and p != settings.QUALITY_LLM:
                    entry = (p, "primary")
                    if entry not in smart_order:
                        smart_order.append(entry)
            # Quality LLM last (most expensive)
            smart_order.append((settings.QUALITY_LLM, "primary"))
            for entry in smart_order:
                if entry not in tagged_chain:
                    tagged_chain.append(entry)
        
        # Warm path: if we know a provider that worked recently for this role,
        # move it to the front (after the requested provider).
        role_key = f"{provider.value}:{temperature}"
        warm = self._last_successful.get(role_key)
        if warm:
            warm_entry = (warm, "primary")
            if warm_entry in tagged_chain and warm_entry != tagged_chain[0]:
                tagged_chain.remove(warm_entry)
                tagged_chain.insert(1, warm_entry)
        
        last_error = None
        
        for prov, tag in tagged_chain:
            if prov not in self.clients:
                continue
            
            # Skip providers on cooldown — but allow "alt" tag (Gemini Pro)
            # to bypass cooldowns set by content-gate (not infra errors)
            if tag != "alt" and self._is_cooling_down(prov):
                continue
            
            use_alt_gemini = (prov == LLMProvider.GEMINI and tag == "alt")
            
            # Retry same provider once on short content (targeted at Gemini
            # transient truncation).  Other providers get a single attempt.
            max_attempts = 2 if (min_content_length and prov == provider and tag == "primary") else 1
            
            # DeepSeek has a hard 8192 max_tokens API limit
            effective_max_tokens = min(max_tokens, DEEPSEEK_MAX_TOKENS) if prov == LLMProvider.DEEPSEEK else max_tokens
            
            for attempt in range(1, max_attempts + 1):
                try:
                    start_time = time.time()
                    
                    # ── Wrap call with timeout ───────────────────────
                    coro = self._dispatch_provider(
                        prov, prompt, temperature, effective_max_tokens,
                        system_prompt, use_alt_gemini=use_alt_gemini
                    )
                    try:
                        response = await asyncio.wait_for(coro, timeout=REQUEST_TIMEOUT_SEC)
                    except asyncio.TimeoutError:
                        elapsed = time.time() - start_time
                        print(f"  ⏰ {prov.value} timed out after {elapsed:.0f}s")
                        self._set_cooldown(prov, 30)  # shorter cooldown for timeout
                        last_error = LLMTimeoutError(f"{prov.value} timed out after {elapsed:.0f}s")
                        break  # move to next provider
                    # ────────────────────────────────────────────────
                    
                    response.generation_time = time.time() - start_time
                    
                    # ── Content Validation Gate ──────────────────────
                    content_len = len(response.content or "")
                    if min_content_length and content_len < min_content_length:
                        print(
                            f"  ⚠ Content gate: {prov.value} returned {content_len} chars "
                            f"(need {min_content_length}) — attempt {attempt}/{max_attempts}"
                        )
                        if attempt < max_attempts:
                            await asyncio.sleep(1)   # brief backoff before retry
                            continue
                        # Exhausted retries → NO cooldown (content gate is not
                        # an infra failure; Gemini Pro alt can still work).
                        last_error = ValueError(
                            f"{prov.value}: content too short ({content_len} < {min_content_length})"
                        )
                        break  # move to next provider
                    # ────────────────────────────────────────────────
                    
                    # Success! Cache warm path.
                    self._last_successful[role_key] = prov
                    self._log_request(prov, prompt, response)
                    return response
                    
                except asyncio.TimeoutError:
                    raise  # already handled above
                except Exception as e:
                    last_error = e
                    err_str = str(e).lower()
                    # Rate limit → longer cooldown
                    if '429' in err_str or 'rate' in err_str:
                        self._set_cooldown(prov, PROVIDER_COOLDOWN_SEC)
                    elif '401' in err_str or 'auth' in err_str:
                        self._set_cooldown(prov, 300)  # 5min for auth errors
                    else:
                        self._set_cooldown(prov, 30)
                    if settings.DEBUG:
                        print(f"Provider {prov.value} failed: {e}")
                    break  # move to next provider
        
        # All providers failed
        return LLMResponse(
            content="",
            provider=LLMProvider.GROQ,
            model="",
            success=False,
            error=str(last_error) if last_error else "All providers failed",
            generation_time=0.0
        )
    
    async def _dispatch_provider(
        self,
        provider: LLMProvider,
        prompt: str,
        temperature: float,
        max_tokens: int,
        system_prompt: Optional[str],
        use_alt_gemini: bool = False
    ) -> LLMResponse:
        """Dispatch to the correct provider generator."""
        if provider == LLMProvider.GROQ:
            return await self._generate_groq(prompt, temperature, max_tokens, system_prompt)
        elif provider == LLMProvider.DEEPSEEK:
            return await self._generate_deepseek(prompt, temperature, max_tokens, system_prompt)
        elif provider == LLMProvider.GEMINI:
            return await self._generate_gemini(prompt, temperature, max_tokens, system_prompt, use_alt_model=use_alt_gemini)
        elif provider == LLMProvider.ANTHROPIC:
            return await self._generate_anthropic(prompt, temperature, max_tokens, system_prompt)
        else:
            raise LLMError(f"Unknown provider: {provider}")

    async def _generate_groq(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        system_prompt: Optional[str]
    ) -> LLMResponse:
        """Generate using Groq"""
        client = self.clients[LLMProvider.GROQ]
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            provider=LLMProvider.GROQ,
            model=settings.GROQ_MODEL,
            tokens_used=response.usage.total_tokens if response.usage else None
        )
    
    async def _generate_deepseek(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        system_prompt: Optional[str]
    ) -> LLMResponse:
        """Generate using DeepSeek (OpenAI-compatible API)"""
        client = self.clients[LLMProvider.DEEPSEEK]
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            provider=LLMProvider.DEEPSEEK,
            model=settings.DEEPSEEK_MODEL,
            tokens_used=response.usage.total_tokens if response.usage else None
        )
    
    async def _generate_gemini(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        system_prompt: Optional[str],
        use_alt_model: bool = False
    ) -> LLMResponse:
        """Generate using Google Gemini (native SDK).
        
        When use_alt_model=True, switches to gemini-2.5-pro for diversity
        (e.g. when Flash already failed with short content).
        """
        client = self.clients[LLMProvider.GEMINI]
        model_id = "gemini-2.5-pro" if use_alt_model else settings.GEMINI_MODEL
        
        if use_alt_model:
            print(f"  🔄 Gemini alt-model: using {model_id} instead of {settings.GEMINI_MODEL}")
        
        config = genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_prompt or None,
        )
        
        # Run sync client in thread to avoid blocking event loop
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model_id,
            contents=prompt,
            config=config,
        )
        
        tokens_used = None
        if response.usage_metadata:
            tokens_used = (response.usage_metadata.prompt_token_count or 0) + (response.usage_metadata.candidates_token_count or 0)
        
        return LLMResponse(
            content=response.text or "",
            provider=LLMProvider.GEMINI,
            model=model_id,
            tokens_used=tokens_used
        )
    
    async def _generate_anthropic(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        system_prompt: Optional[str]
    ) -> LLMResponse:
        """Generate using Anthropic"""
        client = self.clients[LLMProvider.ANTHROPIC]
        
        response = await client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return LLMResponse(
            content=response.content[0].text,
            provider=LLMProvider.ANTHROPIC,
            model=settings.ANTHROPIC_MODEL,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens
        )
    
    async def generate_with_quality(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        min_content_length: int = 0
    ) -> LLMResponse:
        """Generate using quality-focused LLM with content validation gate."""
        return await self.generate(
            prompt=prompt,
            provider=settings.QUALITY_LLM,
            temperature=temperature,
            max_tokens=max_tokens,
            fallback=True,
            min_content_length=min_content_length
        )
    
    async def generate_parallel(
        self,
        prompt: str,
        providers: Optional[List[LLMProvider]] = None,
        temperature: Optional[float] = None
    ) -> List[LLMResponse]:
        """Generate with multiple providers in parallel"""
        providers = providers or [settings.PRIMARY_LLM, settings.FALLBACK_LLM]
        
        tasks = [
            self.generate(
                prompt=prompt,
                provider=prov,
                temperature=temperature,
                fallback=False
            )
            for prov in providers if prov in self.clients
        ]
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def _log_request(
        self,
        provider: LLMProvider,
        prompt: str,
        response: LLMResponse
    ):
        """Log request for analytics"""
        self.request_history.append({
            "provider": provider.value,
            "prompt_length": len(prompt),
            "response_length": len(response.content),
            "tokens_used": response.tokens_used,
            "generation_time": response.generation_time,
            "success": response.success
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        if not self.request_history:
            return {"total_requests": 0}
        
        total = len(self.request_history)
        successful = sum(1 for r in self.request_history if r["success"])
        avg_time = sum(r["generation_time"] for r in self.request_history) / total
        total_tokens = sum(r["tokens_used"] or 0 for r in self.request_history)
        
        provider_stats = {}
        for r in self.request_history:
            prov = r["provider"]
            if prov not in provider_stats:
                provider_stats[prov] = {"count": 0, "success": 0}
            provider_stats[prov]["count"] += 1
            if r["success"]:
                provider_stats[prov]["success"] += 1
        
        return {
            "total_requests": total,
            "successful_requests": successful,
            "success_rate": successful / total,
            "average_generation_time": avg_time,
            "total_tokens": total_tokens,
            "provider_breakdown": provider_stats
        }
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all configured providers.
        
        NOTE: Uses a snapshot of cooldowns and restores after, so health
        checks don't pollute the cooldown state for real builds.
        """
        saved_cooldowns = dict(self._cooldowns)
        results = {}
        
        for provider in LLMProvider:
            if provider not in self.clients:
                results[provider.value] = False
                continue
            
            try:
                response = await self.generate(
                    prompt="Say 'OK'",
                    provider=provider,
                    max_tokens=10,
                    fallback=False
                )
                results[provider.value] = response.success
            except Exception:
                results[provider.value] = False
        
        # Restore cooldowns — health check failures shouldn't block real builds
        self._cooldowns = saved_cooldowns
        return results


# Singleton instance
_llm_manager: Optional[LLMManager] = None


def get_llm_manager() -> LLMManager:
    """Get or create LLM manager singleton"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager


async def generate_text(
    prompt: str,
    provider: Optional[LLMProvider] = None,
    temperature: Optional[float] = None,
    system_prompt: Optional[str] = None
) -> str:
    """Convenience function for text generation"""
    manager = get_llm_manager()
    response = await manager.generate(
        prompt=prompt,
        provider=provider,
        temperature=temperature,
        system_prompt=system_prompt
    )
    return response.content if response.success else ""
