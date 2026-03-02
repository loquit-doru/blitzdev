"""
Integration test — full BlitzDev pipeline with mocked LLM + Seedstr API
Verifies the Agent processes a job through Plan → Build → Evaluate → Fix → Package → Upload → Submit
"""

import pytest
import asyncio
import json
import zipfile
import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import LLMProvider
from seedstr_client import (
    SeedstrClient, Job, JobType, JobStatus,
    ResponseType, FileAttachment, SubmitResponseResult
)
from agents.planner import PlannerAgent, ImplementationPlan, AppType, Complexity
from agents.builder import BuilderAgent, BuildResult
from agents.critic import CriticAgent, EvaluationResult, EvaluationScores, ScoreLevel
from agents.fixer import FixerAgent, FixResult
from utils.packer import Packer, PackResult
from main import BlitzDevAgent, PipelineResult


# ==================== Helpers ====================

SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Coffee Shop</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-white min-h-screen">
    <header class="bg-amber-800 text-white p-6">
        <h1 class="text-3xl font-bold">Bean Dreams</h1>
        <nav class="mt-2"><a href="#menu" class="mr-4">Menu</a><a href="#contact">Contact</a></nav>
    </header>
    <section id="hero" class="py-20 text-center">
        <h2 class="text-4xl font-bold text-amber-900">Welcome to Bean Dreams</h2>
        <p class="text-lg mt-4">The finest coffee in town.</p>
        <button onclick="scrollToMenu()" class="mt-6 px-6 py-3 bg-amber-600 text-white rounded-lg">View Menu</button>
    </section>
    <section id="menu" class="p-8 bg-amber-50">
        <h3 class="text-2xl font-bold mb-4">Our Menu</h3>
        <div class="grid md:grid-cols-3 gap-4">
            <div class="p-4 bg-white rounded shadow"><h4>Espresso</h4><p>$3.50</p></div>
            <div class="p-4 bg-white rounded shadow"><h4>Latte</h4><p>$4.50</p></div>
            <div class="p-4 bg-white rounded shadow"><h4>Cappuccino</h4><p>$4.00</p></div>
        </div>
    </section>
    <section id="contact" class="p-8">
        <h3 class="text-2xl font-bold mb-4">Contact Us</h3>
        <form class="max-w-md">
            <input type="text" placeholder="Name" class="block w-full p-2 border mb-2 rounded" />
            <input type="email" placeholder="Email" class="block w-full p-2 border mb-2 rounded" />
            <textarea placeholder="Message" class="block w-full p-2 border mb-2 rounded"></textarea>
            <button type="submit" class="px-6 py-2 bg-amber-700 text-white rounded">Send</button>
        </form>
    </section>
    <footer class="bg-amber-900 text-white p-4 text-center">&copy; 2026 Bean Dreams</footer>
    <script>
        function scrollToMenu() { document.getElementById('menu').scrollIntoView({behavior:'smooth'}); }
    </script>
</body>
</html>"""

SAMPLE_PLAN_JSON = json.dumps({
    "app_type": "landing_page",
    "design_preset": "warm_organic",
    "components": ["header", "hero", "menu", "contact_form", "footer"],
    "features": ["responsive_design", "smooth_scrolling", "contact_form"],
    "pages": ["index"],
    "complexity": "medium",
    "estimated_time": 45
})

SAMPLE_EVAL_JSON = json.dumps({
    "scores": {"functionality": 85, "design": 80, "speed": 90},
    "suggestions": ["Add hover effects on menu cards"],
    "feedback": "Good implementation with responsive layout."
})


def _make_llm_response(content: str, provider=LLMProvider.GROQ):
    """Create a mock LLMResponse-like object"""
    from utils.llm_manager import LLMResponse
    return LLMResponse(
        content=content,
        provider=provider,
        model="mock-model",
        tokens_used=500,
        generation_time=1.0,
        success=True
    )


def _make_mock_job():
    """Create a test Job"""
    return Job(
        id="test-hackathon-001",
        prompt="Create a beautiful landing page for a coffee shop called Bean Dreams with hero, menu, and contact form",
        budget=10.0,
        status=JobStatus.OPEN,
        expires_at="2026-12-31T23:59:59Z",
        created_at="2026-03-01T00:00:00Z",
        response_count=0,
        job_type=JobType.STANDARD
    )


# ==================== Unit: ImplementationPlan round-trip ====================

def test_plan_roundtrip():
    """Test plan serialization and deserialization"""
    plan = ImplementationPlan(
        app_type=AppType.LANDING_PAGE,
        design_preset="warm_organic",
        components=["header", "hero", "footer"],
        features=["responsive"],
        pages=["index"],
        complexity=Complexity.MEDIUM,
        estimated_time=45,
        requirements_analysis={"core_functionality": "information_display"},
        tech_stack={"frontend": ["HTML5"]},
        layout_structure={"header": "sticky"}
    )
    d = plan.to_dict()
    plan2 = ImplementationPlan.from_dict(d)
    assert plan2.app_type == AppType.LANDING_PAGE
    assert plan2.complexity == Complexity.MEDIUM
    assert plan2.design_preset == "warm_organic"


# ==================== Unit: Critic automated eval ====================

def test_critic_automated_evaluation():
    """Test CriticAgent._automated_evaluation with real HTML"""
    critic = CriticAgent()
    build = BuildResult(
        html=SAMPLE_HTML,
        css=None,
        js=None,
        success=True,
        build_time=2.0
    )
    scores = critic._automated_evaluation(build)

    assert scores["functionality"]["code_validity"] == 100
    assert scores["functionality"]["interactivity"] >= 60   # no addEventListener in sample
    assert scores["functionality"]["responsiveness"] >= 70   # sample has md: + viewport, no sm:/lg:
    assert scores["design"]["typography"] >= 70


def test_critic_extract_issues_low_score():
    """Test issue extraction for low-scoring builds"""
    critic = CriticAgent()
    build = BuildResult(html="<div>No doctype</div>", css=None, js=None, success=True, build_time=1.0)
    scores = EvaluationScores(
        functionality=50, design=40, speed=70, overall=50,
        functionality_breakdown={}, design_breakdown={}, speed_breakdown={}
    )
    issues = critic._extract_issues(build, scores)
    categories = [i["category"] for i in issues]
    assert "functionality" in categories
    assert "design" in categories
    assert "structure" in categories  # missing doctype (category renamed)


# ==================== Unit: Fixer automated fixes ====================

def test_fixer_adds_missing_elements():
    """Test that automated fixer adds DOCTYPE, viewport, charset, lang, title, Tailwind"""
    fixer = FixerAgent()
    html = "<html><head></head><body><p>Hello</p></body></html>"
    scores = EvaluationScores(
        functionality=50, design=50, speed=50, overall=50,
        functionality_breakdown={}, design_breakdown={}, speed_breakdown={}
    )
    evaluation = EvaluationResult(
        scores=scores, suggestions=[], issues=[], passed=False,
        level=ScoreLevel.POOR, detailed_feedback=""
    )
    fixed_html, fixes = fixer._apply_automated_fixes(html, evaluation)

    assert "<!DOCTYPE html>" in fixed_html
    assert 'viewport' in fixed_html
    assert 'charset="UTF-8"' in fixed_html
    assert 'lang="en"' in fixed_html
    assert "<title" in fixed_html.lower()
    assert "tailwindcss.com" in fixed_html
    assert len(fixes) >= 5


# ==================== Unit: Builder code parsing ====================

def test_builder_parse_multiblock():
    """Test parsing a response with HTML + CSS + JS blocks"""
    builder = BuilderAgent()
    content = f"""Here is your app:

```html
{SAMPLE_HTML}
```

```css
body {{ font-family: sans-serif; }}
```

```javascript
console.log('loaded');
```
"""
    html, css, js = builder._parse_generated_code(content)
    assert "Bean Dreams" in html
    assert "font-family" in css
    assert "console.log" in js


def test_builder_parse_no_blocks():
    """Test parsing when LLM returns raw HTML without code blocks"""
    builder = BuilderAgent()
    raw = "<html><body>Raw output</body></html>"
    html, css, js = builder._parse_generated_code(raw)
    assert "Raw output" in html
    assert css is None
    assert js is None


# ==================== Unit: Planner helpers ====================

def test_planner_data_needs():
    """Test _identify_data_needs"""
    planner = PlannerAgent()
    needs = planner._identify_data_needs("Import your files and save them")
    assert needs["local_storage"] is True
    assert needs["file_upload"] is True
    assert needs["api_integration"] is False

    # keyword 'api' triggers api_integration
    needs2 = planner._identify_data_needs("Fetch data from an api")
    assert needs2["api_integration"] is True


def test_planner_recommend_tech_stack():
    """Test _recommend_tech_stack for different app types"""
    planner = PlannerAgent()
    stack = planner._recommend_tech_stack({"app_type": "game", "complexity": "complex"})
    assert "Canvas API" in stack["javascript"]

    stack2 = planner._recommend_tech_stack({"app_type": "dashboard", "complexity": "medium"})
    assert any("Chart" in s for s in stack2["javascript"])


def test_planner_suggest_layout():
    """Test layout suggestions for different app types"""
    planner = PlannerAgent()
    layout = planner._suggest_layout({"app_type": "dashboard"})
    assert "sidebar" in layout

    layout2 = planner._suggest_layout({"app_type": "portfolio"})
    assert "hero" in layout2


def test_planner_parse_plan_json():
    """Test _parse_plan_response with valid JSON"""
    planner = PlannerAgent()
    from utils.llm_manager import LLMResponse
    resp = LLMResponse(
        content=f"```json\n{SAMPLE_PLAN_JSON}\n```",
        provider=LLMProvider.GROQ,
        model="test",
        success=True
    )
    plan_data = planner._parse_plan_response(resp)
    assert plan_data["app_type"] == "landing_page"
    assert plan_data["complexity"] == "medium"
    assert len(plan_data["components"]) == 5


def test_planner_parse_plan_malformed():
    """Test _parse_plan_response with invalid JSON falls back to default"""
    planner = PlannerAgent()
    from utils.llm_manager import LLMResponse
    resp = LLMResponse(
        content="This is not JSON at all",
        provider=LLMProvider.GROQ,
        model="test",
        success=True
    )
    plan_data = planner._parse_plan_response(resp)
    assert plan_data["app_type"] == "interactive_app"  # default


# ==================== Unit: Packer create_webapp_package ====================

def test_webapp_package_contents():
    """Test that create_webapp_package includes all expected files"""
    packer = Packer(max_size_mb=10)
    result = packer.create_webapp_package(
        html_content=SAMPLE_HTML,
        css_content="body { color: brown; }",
        js_content="console.log('init');",
        additional_files={"README.md": "# Test"},
        app_name="bean-dreams"
    )
    assert result.success

    zf = zipfile.ZipFile(io.BytesIO(result.zip_bytes))
    names = zf.namelist()
    assert "index.html" in names
    assert "styles.css" in names
    assert "app.js" in names
    assert "README.md" in names
    assert "manifest.json" in names
    assert "blitzdev-meta.json" in names

    # Verify HTML content
    assert "Bean Dreams" in zf.read("index.html").decode()


# ==================== Integration: Pipeline mock ====================

@pytest.mark.asyncio
async def test_pipeline_process_job():
    """
    Integration test: mock LLM + Seedstr and run _process_job
    Verify the full Plan → Build → Evaluate → Package → Upload → Submit chain
    """
    agent = BlitzDevAgent()

    # ---- Mock LLM manager ----
    # Track call order so planner gets JSON and builder gets HTML
    _call_count = {"planner": 0, "builder": 0}

    async def mock_planner_generate(prompt, **kwargs):
        _call_count["planner"] += 1
        return _make_llm_response(f"```json\n{SAMPLE_PLAN_JSON}\n```")

    async def mock_builder_generate(prompt, **kwargs):
        _call_count["builder"] += 1
        return _make_llm_response(
            f"```html\n{SAMPLE_HTML}\n```\n\n```css\nbody {{ margin: 0; }}\n```\n\n```javascript\nconsole.log('ok');\n```"
        )

    async def mock_critic_generate(prompt, **kwargs):
        return _make_llm_response(f"```json\n{SAMPLE_EVAL_JSON}\n```")

    async def mock_default_generate(prompt, **kwargs):
        return _make_llm_response("OK")

    # LLM manager is a singleton — all agents share one instance.
    # Replace each agent's .llm with a SEPARATE MagicMock so mocks don't collide.
    for attr, gen_fn in [
        ("planner", mock_planner_generate),
        ("builder", mock_builder_generate),
        ("critic",  mock_critic_generate),
        ("fixer",   mock_default_generate),
    ]:
        mock_llm = MagicMock()
        mock_llm.generate = gen_fn
        mock_llm.generate_with_quality = gen_fn
        setattr(getattr(agent, attr), "llm", mock_llm)

    default_llm = MagicMock()
    default_llm.generate = mock_default_generate
    default_llm.generate_with_quality = mock_default_generate
    agent.llm = default_llm

    # ---- Mock Seedstr client (upload + submit) ----
    agent.client.upload_file = AsyncMock(return_value=FileAttachment(
        url="https://cdn.seedstr.io/files/test.zip",
        name="test.zip",
        size=5000,
        type="application/zip"
    ))
    agent.client.upload_bytes = AsyncMock(return_value=FileAttachment(
        url="https://cdn.seedstr.io/files/test.zip",
        name="test.zip",
        size=5000,
        type="application/zip"
    ))
    agent.client.submit_response = AsyncMock(return_value=SubmitResponseResult(
        success=True,
        response_id="resp-test-001",
        message="Submitted"
    ))

    # ---- Run pipeline on test job ----
    job = _make_mock_job()
    result = await agent._process_job(job)

    # ---- Assertions ----
    assert result.success, f"Pipeline failed: {result.error}"
    assert result.job_id == "test-hackathon-001"

    # Plan
    assert result.plan is not None
    assert result.plan.app_type == AppType.LANDING_PAGE

    # Build
    assert result.build is not None
    assert result.build.success
    assert "Bean Dreams" in result.build.html

    # Evaluation
    assert result.evaluation is not None
    assert result.evaluation.scores.overall > 0

    # Package
    assert result.package is not None
    assert result.package.success
    assert result.package.size_bytes > 0

    # Submission
    assert result.submission is not None
    assert result.submission.success
    assert result.submission.response_id == "resp-test-001"

    # Total time tracked
    assert result.total_time > 0


@pytest.mark.asyncio
async def test_pipeline_result_serialization():
    """Test PipelineResult.to_dict()"""
    plan = ImplementationPlan(
        app_type=AppType.DASHBOARD,
        design_preset="dark_cyberpunk",
        components=["nav", "widgets"],
        features=["charts"],
        pages=["index"],
        complexity=Complexity.COMPLEX,
        estimated_time=90,
        requirements_analysis={},
        tech_stack={},
        layout_structure={}
    )
    build = BuildResult(html="<html></html>", css=None, js=None, success=True, build_time=3.0)
    result = PipelineResult(
        job_id="j-99",
        success=True,
        plan=plan,
        build=build,
        total_time=5.0
    )
    d = result.to_dict()
    assert d["job_id"] == "j-99"
    assert d["success"] is True
    assert d["plan"]["app_type"] == "dashboard"
    assert d["build"]["build_time"] == 3.0
