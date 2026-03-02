"""
Tests for job classification and text-fast-path in main.py
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import classify_job, BlitzDevAgent


# ── classify_job ──────────────────────────────────────────────────

class TestClassifyJob:
    """Tests for the classify_job() function"""

    # ---- Text-only prompts ----

    @pytest.mark.parametrize("prompt", [
        "Write a tweet about AI agents",
        "write a twitter thread about crypto",
        "write an email to my boss about a raise",
        "write a poem about the moon",
        "Summarize the latest news on Bitcoin",
        "Translate this to Spanish: Hello world",
        "Explain how transformers work in machine learning",
        "Tell me about the history of the internet",
        "What happened in 1969?",
        "Answer the question: what is gravity?",
        "Give me a list of top 10 programming languages",
        "Write a blog post about web3",
        "Write a cover letter for a software engineer position",
        "Proofread this paragraph: Their are many reasons...",
        "Rewrite this sentence to be more professional",
    ])
    def test_text_prompts(self, prompt):
        assert classify_job(prompt) == "text"

    # ---- Project prompts ----

    @pytest.mark.parametrize("prompt", [
        "Build a todo app",
        "Create a website for my portfolio",
        "Create a landing page for my SaaS product",
        "Build a calculator with dark mode",
        "Create a dashboard for analytics",
        "Build a game like snake in JavaScript",
        "Create a web app for tracking expenses",
        "Make a website for a coffee shop",
        "Generate a website for a personal blog",
        "Build an e-commerce product page",
        "Create an HTML page with a form",
    ])
    def test_project_prompts(self, prompt):
        assert classify_job(prompt) == "project"

    # ---- Hybrid / default (short questions → text) ----

    def test_short_question_classified_as_text(self):
        assert classify_job("What is Python?") == "text"

    def test_how_question_classified_as_text(self):
        assert classify_job("How does DNS work?") == "text"

    def test_why_question_classified_as_text(self):
        assert classify_job("Why is the sky blue?") == "text"

    def test_who_question_classified_as_text(self):
        assert classify_job("Who invented the internet?") == "text"

    # ---- Hybrid / default (long ambiguous prompts → hybrid) ----

    def test_long_ambiguous_prompt_is_hybrid(self):
        prompt = (
            "I need you to help me with a comprehensive analysis of the "
            "current machine learning landscape including recent advances "
            "and practical applications in various industries around the world"
        )
        assert classify_job(prompt) == "hybrid"

    # ---- Project keywords override text keywords ----

    def test_project_beats_text_keyword_when_both_present(self):
        """If prompt has both 'explain' and 'build', project wins."""
        prompt = "Explain and build a calculator app"
        assert classify_job(prompt) == "project"

    # ---- Case insensitivity ----

    def test_case_insensitive(self):
        assert classify_job("WRITE A TWEET about cats") == "text"
        assert classify_job("BUILD A LANDING PAGE for dogs") == "project"


# ── _wrap_text_as_html ────────────────────────────────────────────

class TestWrapTextAsHtml:
    def test_returns_valid_html(self):
        html = BlitzDevAgent._wrap_text_as_html("Test prompt", "Test answer")
        assert "<!DOCTYPE html>" in html
        assert "Test prompt" in html
        assert "Test answer" in html
        assert "BlitzDev" in html

    def test_escapes_html_entities(self):
        html = BlitzDevAgent._wrap_text_as_html("<script>alert(1)</script>", "a & b < c")
        # The XSS attempt in the prompt must be escaped
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
        # The answer entities must also be escaped
        assert "a &amp; b &lt; c" in html
        # The raw malicious script must NOT appear unescaped
        assert "<script>alert(1)</script>" not in html

    def test_preserves_line_breaks(self):
        html = BlitzDevAgent._wrap_text_as_html("Q", "line1\nline2\nline3")
        assert html.count("<p class=") >= 3
