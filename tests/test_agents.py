"""
Tests for agent modules
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.planner import PlannerAgent, ImplementationPlan, AppType, Complexity
from agents.builder import BuilderAgent, BuildResult
from agents.critic import CriticAgent, EvaluationResult, EvaluationScores
from agents.fixer import FixerAgent, FixResult


# Planner Tests
@pytest.fixture
def planner():
    return PlannerAgent()


def test_planner_create_default_plan(planner):
    """Test default plan creation"""
    plan = planner._create_default_plan()
    
    assert "app_type" in plan
    assert "design_preset" in plan
    assert "components" in plan


def test_planner_extract_core_functionality(planner):
    """Test functionality extraction"""
    assert planner._extract_core_functionality("Create a calculator app") == "calculation_tool"
    assert planner._extract_core_functionality("Build a dashboard") == "data_visualization"
    assert planner._extract_core_functionality("Make a game") == "interactive_game"


def test_planner_infer_audience(planner):
    """Test audience inference"""
    assert planner._infer_audience("Business website") == "business_professionals"
    assert planner._infer_audience("Kids game") == "children"
    assert planner._infer_audience("Developer tool") == "developers"


def test_planner_identify_interactions(planner):
    """Test interaction identification"""
    interactions = planner._identify_interactions("Form with button click")
    assert "button_clicks" in interactions
    assert "form_submission" in interactions


# Builder Tests
@pytest.fixture
def builder():
    return BuilderAgent()


def test_builder_parse_generated_code(builder):
    """Test code parsing from LLM response"""
    response = """
```html
<html><body>Test</body></html>
```
```css
body { color: red; }
```
```javascript
console.log('test');
```
"""
    html, css, js = builder._parse_generated_code(response)
    
    assert "<html>" in html
    assert "color: red" in css
    assert "console.log" in js


def test_builder_validate_output(builder):
    """Test output validation"""
    # _validate_output requires: len > 100, <html or <!doctype, <body, tailwind or class=
    valid_html = (
        '<!DOCTYPE html><html lang="en"><head>'
        '<script src="https://cdn.tailwindcss.com"></script></head>'
        '<body class="min-h-screen bg-white">'
        '<div class="container mx-auto p-4"><h1>Hello World</h1></div>'
        '</body></html>'
    )
    assert builder._validate_output(valid_html)
    
    invalid_html = "just text"
    assert not builder._validate_output(invalid_html)
    
    # Too short
    short_html = "<html><body class='x'>a</body></html>"
    assert not builder._validate_output(short_html)


def test_builder_inject_styling(builder):
    """Test Tailwind injection"""
    html = "<html><head></head><body></body></html>"
    design_preset = {
        "tailwind_config": {"colors": {"primary": "#000"}},
        "cdn": ["https://fonts.googleapis.com"]
    }
    
    result = builder._inject_styling(html, design_preset)
    
    assert "tailwind.config" in result
    assert "fonts.googleapis.com" in result


# Critic Tests
@pytest.fixture
def critic():
    return CriticAgent()


def test_critic_get_score_level(critic):
    """Test score level determination"""
    from agents.critic import ScoreLevel
    
    assert critic._get_score_level(95) == ScoreLevel.EXCELLENT
    assert critic._get_score_level(80) == ScoreLevel.GOOD
    assert critic._get_score_level(65) == ScoreLevel.ACCEPTABLE
    assert critic._get_score_level(45) == ScoreLevel.POOR
    assert critic._get_score_level(30) == ScoreLevel.FAIL


def test_critic_combine_scores(critic):
    """Test score combination"""
    auto_scores = {
        "functionality": {"code_validity": 100, "interactivity": 80},
        "design": {"visual_appeal": 90, "consistency": 85},
        "speed": {"render_efficiency": 85, "code_optimization": 80}
    }
    
    llm_eval = {
        "scores": {"functionality": 85, "design": 90, "speed": 80}
    }
    
    scores = critic._combine_scores(auto_scores, llm_eval, 45.0)
    
    assert scores.functionality > 0
    assert scores.design > 0
    assert scores.speed > 0
    assert scores.overall > 0


def test_evaluation_scores_to_dict():
    """Test EvaluationScores serialization"""
    scores = EvaluationScores(
        functionality=80,
        design=75,
        speed=90,
        overall=81.5,
        functionality_breakdown={},
        design_breakdown={},
        speed_breakdown={}
    )
    
    data = scores.to_dict()
    assert data["functionality"] == 80
    assert data["overall"] == 81.5


# Fixer Tests
@pytest.fixture
def fixer():
    return FixerAgent()


def test_fixer_apply_automated_fixes(fixer):
    """Test automated fixes"""
    from agents.critic import EvaluationResult, EvaluationScores, ScoreLevel
    
    html = "<html><head></head><body></body></html>"
    
    scores = EvaluationScores(
        functionality=60, design=70, speed=80, overall=68,
        functionality_breakdown={}, design_breakdown={}, speed_breakdown={}
    )
    
    evaluation = EvaluationResult(
        scores=scores,
        suggestions=[],
        issues=[{"category": "code", "severity": "high", "description": "Missing DOCTYPE"}],
        passed=False,
        level=ScoreLevel.ACCEPTABLE,
        detailed_feedback=""
    )
    
    fixed_html, fixes = fixer._apply_automated_fixes(html, evaluation)
    
    assert "<!DOCTYPE html>" in fixed_html
    assert "viewport" in fixed_html
    assert len(fixes) > 0


def test_fixer_no_fixes_needed(fixer):
    """Test when no fixes needed"""
    from agents.critic import EvaluationResult, EvaluationScores, ScoreLevel
    
    scores = EvaluationScores(
        functionality=90, design=85, speed=80, overall=86,
        functionality_breakdown={}, design_breakdown={}, speed_breakdown={}
    )
    
    evaluation = EvaluationResult(
        scores=scores,
        suggestions=[],
        issues=[],
        passed=True,
        level=ScoreLevel.GOOD,
        detailed_feedback=""
    )
    
    build_result = BuildResult(
        html="<html></html>",
        css=None,
        js=None,
        success=True,
        build_time=1.0
    )
    
    # Should return without fixes
    result = asyncio.run(fixer.fix(build_result, evaluation))
    assert any("No fixes needed" in fix for fix in result.fixes_applied)
# Integration Test
def test_full_pipeline_mock():
    """Test full pipeline with mocked LLM"""
    
    # This would require mocking the LLM manager
    # For now, just verify the pipeline structure
    
    planner = PlannerAgent()
    builder = BuilderAgent()
    critic = CriticAgent()
    fixer = FixerAgent()
    
    # Verify agents are initialized
    assert planner is not None
    assert builder is not None
    assert critic is not None
    assert fixer is not None
