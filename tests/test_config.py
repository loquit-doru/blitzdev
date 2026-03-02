"""
Tests for configuration module
"""

import pytest
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Settings, DESIGN_PRESETS, EVALUATION_CRITERIA, LLMProvider


def test_settings_defaults():
    """Test default settings"""
    settings = Settings()
    
    assert settings.APP_NAME == "BlitzDev"
    assert settings.APP_VERSION == "1.0.0"
    assert settings.PRIMARY_LLM == LLMProvider.GROQ
    assert settings.FALLBACK_LLM == LLMProvider.DEEPSEEK
    assert settings.QUALITY_LLM == LLMProvider.GEMINI


def test_design_presets():
    """Test design presets are loaded"""
    assert len(DESIGN_PRESETS) > 0
    
    # Check required presets exist
    required = ["modern_minimal", "dark_cyberpunk"]
    for preset in required:
        assert preset in DESIGN_PRESETS
    
    # Check preset structure
    for name, preset in DESIGN_PRESETS.items():
        assert "name" in preset
        assert "description" in preset
        assert "tailwind_config" in preset
        assert "colors" in preset["tailwind_config"]


def test_evaluation_criteria():
    """Test evaluation criteria weights"""
    criteria = EVALUATION_CRITERIA
    
    # Check main categories
    assert "functionality" in criteria
    assert "design" in criteria
    assert "speed" in criteria
    
    # Check weights sum to 1.0
    total_weight = sum(c["weight"] for c in criteria.values())
    assert abs(total_weight - 1.0) < 0.001


def test_settings_validation():
    """Test settings validation"""
    settings = Settings()
    
    # Check paths are Path objects
    assert isinstance(settings.OUTPUT_DIR, Path)
    assert isinstance(settings.TEMP_DIR, Path)
    
    # Check weights are valid
    assert 0 <= settings.WEIGHT_FUNCTIONALITY <= 1
    assert 0 <= settings.WEIGHT_DESIGN <= 1
    assert 0 <= settings.WEIGHT_SPEED <= 1
