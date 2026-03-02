"""
Tests for LLM Manager utility
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm_manager import LLMManager, LLMResponse, LLMError
from config import LLMProvider


# ==================== LLMResponse ====================

def test_llm_response_defaults():
    """Test LLMResponse default fields"""
    resp = LLMResponse(content="Hello", provider=LLMProvider.GROQ, model="mixtral")
    assert resp.content == "Hello"
    assert resp.success is True
    assert resp.tokens_used is None
    assert resp.generation_time == 0.0


def test_llm_response_error():
    """Test LLMResponse in error state"""
    resp = LLMResponse(
        content="",
        provider=LLMProvider.GROQ,
        model="",
        success=False,
        error="Rate limit exceeded"
    )
    assert not resp.success
    assert resp.error == "Rate limit exceeded"


# ==================== LLMManager ====================

def test_manager_init_no_keys():
    """Manager should create with no clients when no API keys are set"""
    # Patch settings to have empty keys
    with patch("utils.llm_manager.settings") as mock_settings:
        mock_settings.GROQ_API_KEY = ""
        mock_settings.ANTHROPIC_API_KEY = ""
        mock_settings.DEEPSEEK_API_KEY = ""
        mock_settings.GOOGLE_API_KEY = ""
        mock_settings.PRIMARY_LLM = LLMProvider.GROQ
        mock_settings.FALLBACK_LLM = LLMProvider.DEEPSEEK
        mock_settings.QUALITY_LLM = LLMProvider.ANTHROPIC
        mock_settings.TEMPERATURE_BUILDER = 0.5
        mock_settings.MAX_TOKENS = 4096
        mock_settings.DEBUG = False

        manager = LLMManager()
        assert len(manager.clients) == 0


@pytest.mark.asyncio
async def test_generate_all_providers_fail():
    """When no providers are available, generate returns error response"""
    with patch("utils.llm_manager.settings") as mock_settings:
        mock_settings.GROQ_API_KEY = ""
        mock_settings.ANTHROPIC_API_KEY = ""
        mock_settings.DEEPSEEK_API_KEY = ""
        mock_settings.GOOGLE_API_KEY = ""
        mock_settings.PRIMARY_LLM = LLMProvider.GROQ
        mock_settings.FALLBACK_LLM = LLMProvider.DEEPSEEK
        mock_settings.QUALITY_LLM = LLMProvider.ANTHROPIC
        mock_settings.TEMPERATURE_BUILDER = 0.5
        mock_settings.MAX_TOKENS = 4096
        mock_settings.DEBUG = False

        manager = LLMManager()
        response = await manager.generate("Hello world")

        assert not response.success
        assert "failed" in response.error.lower() or response.error


def test_manager_stats_empty():
    """Test stats with no requests"""
    with patch("utils.llm_manager.settings") as mock_settings:
        mock_settings.GROQ_API_KEY = ""
        mock_settings.ANTHROPIC_API_KEY = ""
        mock_settings.DEEPSEEK_API_KEY = ""
        mock_settings.GOOGLE_API_KEY = ""
        mock_settings.PRIMARY_LLM = LLMProvider.GROQ
        mock_settings.FALLBACK_LLM = LLMProvider.DEEPSEEK
        mock_settings.QUALITY_LLM = LLMProvider.ANTHROPIC
        mock_settings.TEMPERATURE_BUILDER = 0.5
        mock_settings.MAX_TOKENS = 4096
        mock_settings.DEBUG = False

        manager = LLMManager()
        stats = manager.get_stats()
        assert stats["total_requests"] == 0


def test_manager_log_request():
    """Test request logging"""
    with patch("utils.llm_manager.settings") as mock_settings:
        mock_settings.GROQ_API_KEY = ""
        mock_settings.ANTHROPIC_API_KEY = ""
        mock_settings.DEEPSEEK_API_KEY = ""
        mock_settings.GOOGLE_API_KEY = ""
        mock_settings.PRIMARY_LLM = LLMProvider.GROQ
        mock_settings.FALLBACK_LLM = LLMProvider.DEEPSEEK
        mock_settings.QUALITY_LLM = LLMProvider.ANTHROPIC
        mock_settings.TEMPERATURE_BUILDER = 0.5
        mock_settings.MAX_TOKENS = 4096
        mock_settings.DEBUG = False

        manager = LLMManager()
        resp = LLMResponse(
            content="test output",
            provider=LLMProvider.GROQ,
            model="test-model",
            tokens_used=100,
            generation_time=1.5,
            success=True
        )
        manager._log_request(LLMProvider.GROQ, "test prompt", resp)

        stats = manager.get_stats()
        assert stats["total_requests"] == 1
        assert stats["successful_requests"] == 1
        assert stats["total_tokens"] == 100
        assert stats["provider_breakdown"]["groq"]["count"] == 1


@pytest.mark.asyncio
async def test_generate_with_mock_groq():
    """Test generate with a mocked Groq client"""
    with patch("utils.llm_manager.settings") as mock_settings:
        mock_settings.GROQ_API_KEY = "fake-key"
        mock_settings.ANTHROPIC_API_KEY = ""
        mock_settings.DEEPSEEK_API_KEY = ""
        mock_settings.GOOGLE_API_KEY = ""
        mock_settings.PRIMARY_LLM = LLMProvider.GROQ
        mock_settings.FALLBACK_LLM = LLMProvider.DEEPSEEK
        mock_settings.QUALITY_LLM = LLMProvider.ANTHROPIC
        mock_settings.TEMPERATURE_BUILDER = 0.5
        mock_settings.MAX_TOKENS = 4096
        mock_settings.GROQ_MODEL = "mixtral-8x7b-32768"
        mock_settings.DEBUG = False

        manager = LLMManager()

        # Mock the Groq client's chat completion
        mock_choice = MagicMock()
        mock_choice.message.content = "Generated HTML content"
        mock_usage = MagicMock()
        mock_usage.total_tokens = 150

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = mock_usage

        mock_groq = AsyncMock()
        mock_groq.chat.completions.create = AsyncMock(return_value=mock_completion)
        manager.clients[LLMProvider.GROQ] = mock_groq

        response = await manager.generate("Build a landing page")

        assert response.success
        assert response.content == "Generated HTML content"
        assert response.tokens_used == 150
        assert response.provider == LLMProvider.GROQ


@pytest.mark.asyncio
async def test_generate_fallback_on_error():
    """Test that fallback provider is used when primary fails"""
    with patch("utils.llm_manager.settings") as mock_settings:
        mock_settings.GROQ_API_KEY = "fake"
        mock_settings.ANTHROPIC_API_KEY = ""
        mock_settings.DEEPSEEK_API_KEY = "fake"
        mock_settings.GOOGLE_API_KEY = ""
        mock_settings.PRIMARY_LLM = LLMProvider.GROQ
        mock_settings.FALLBACK_LLM = LLMProvider.DEEPSEEK
        mock_settings.QUALITY_LLM = LLMProvider.ANTHROPIC
        mock_settings.TEMPERATURE_BUILDER = 0.5
        mock_settings.MAX_TOKENS = 4096
        mock_settings.GROQ_MODEL = "mixtral"
        mock_settings.DEEPSEEK_MODEL = "deepseek-chat"
        mock_settings.DEBUG = False

        manager = LLMManager()

        # Mock Groq to fail
        mock_groq = AsyncMock()
        mock_groq.chat.completions.create = AsyncMock(side_effect=Exception("Groq down"))
        manager.clients[LLMProvider.GROQ] = mock_groq

        # Mock DeepSeek to succeed
        mock_choice = MagicMock()
        mock_choice.message.content = "Fallback content"
        mock_usage = MagicMock()
        mock_usage.total_tokens = 200

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = mock_usage

        mock_deepseek = AsyncMock()
        mock_deepseek.chat.completions.create = AsyncMock(return_value=mock_completion)
        manager.clients[LLMProvider.DEEPSEEK] = mock_deepseek

        response = await manager.generate("Hello")

        assert response.success
        assert response.content == "Fallback content"
        assert response.provider == LLMProvider.DEEPSEEK


@pytest.mark.asyncio
async def test_health_check():
    """Test health check with mocked providers"""
    with patch("utils.llm_manager.settings") as mock_settings:
        mock_settings.GROQ_API_KEY = "fake"
        mock_settings.ANTHROPIC_API_KEY = ""
        mock_settings.DEEPSEEK_API_KEY = ""
        mock_settings.GOOGLE_API_KEY = ""
        mock_settings.PRIMARY_LLM = LLMProvider.GROQ
        mock_settings.FALLBACK_LLM = LLMProvider.DEEPSEEK
        mock_settings.QUALITY_LLM = LLMProvider.ANTHROPIC
        mock_settings.TEMPERATURE_BUILDER = 0.5
        mock_settings.MAX_TOKENS = 4096
        mock_settings.GROQ_MODEL = "mixtral"
        mock_settings.DEBUG = False

        manager = LLMManager()

        # Mock Groq to succeed
        mock_choice = MagicMock()
        mock_choice.message.content = "OK"
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = None

        mock_groq = AsyncMock()
        mock_groq.chat.completions.create = AsyncMock(return_value=mock_completion)
        manager.clients[LLMProvider.GROQ] = mock_groq

        results = await manager.health_check()
        assert results["groq"] is True
        assert results["anthropic"] is False
        assert results["deepseek"] is False
        assert results["gemini"] is False
