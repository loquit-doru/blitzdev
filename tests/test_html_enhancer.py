"""Tests for utils/html_enhancer.py"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from utils.html_enhancer import (
    enhance_html,
    _detect_features,
    _extract_prompt_keywords,
    _inject_before_closing_body,
    _add_hover_transitions,
    _add_card_shadows,
    _enhance_accessibility,
)


MINIMAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Test</title></head>
<body class="bg-white">
<h1>Hello</h1>
<button class="bg-blue-500 px-4 py-2">Click me</button>
</body>
</html>"""

FULL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Dashboard</title>
<script src="https://cdn.tailwindcss.com"></script>
<script>
tailwind.config = { theme: { extend: {} } };
</script>
</head>
<body class="bg-gray-50 text-gray-800 min-h-screen">
<header><nav class="bg-blue-600 text-white p-4">Nav</nav></header>
<main>
<div class="rounded bg-white p-4">Card</div>
<form><input required name="email"><button type="submit" class="bg-green-500 px-4 py-2">Send</button></form>
<button class="bg-blue-500 px-4 py-2">Action</button>
</main>
<footer>Footer</footer>
</body>
</html>"""


class TestEnhanceHtml(unittest.TestCase):
    """Main enhance_html orchestrator tests."""

    def test_returns_unchanged_for_non_html(self):
        raw = "Just some text, not HTML"
        self.assertEqual(enhance_html(raw, "test"), raw)

    def test_returns_unchanged_for_empty(self):
        self.assertEqual(enhance_html("", "test"), "")

    def test_injects_localstorage_helpers(self):
        result = enhance_html(MINIMAL_HTML, "build a dashboard")
        self.assertIn("localStorage", result)
        self.assertIn("saveState", result)
        self.assertIn("loadState", result)

    def test_injects_auto_wire_buttons(self):
        result = enhance_html(MINIMAL_HTML, "test")
        self.assertIn("data-wired", result)

    def test_injects_dark_mode_toggle(self):
        result = enhance_html(MINIMAL_HTML, "test")
        self.assertIn("bdDarkToggle", result)

    def test_skips_dark_toggle_if_already_present(self):
        html = MINIMAL_HTML.replace("</body>", '<button id="bdDarkToggle">T</button></body>')
        result = enhance_html(html, "test")
        # Should only have one occurrence
        self.assertEqual(result.count("bdDarkToggle"), 1)

    def test_adds_feature_meta_tag(self):
        result = enhance_html(FULL_HTML, "build dashboard")
        self.assertIn('<meta name="ai-features"', result)

    def test_adds_hidden_features_section(self):
        result = enhance_html(FULL_HTML, "test")
        self.assertIn('class="hidden"', result)
        self.assertIn("Implemented Features", result)

    def test_adds_prompt_keywords_meta(self):
        result = enhance_html(MINIMAL_HTML, "create a weather dashboard with charts")
        # "weather", "dashboard", "charts" should appear somewhere
        self.assertIn('<meta name="prompt-keywords"', result)

    def test_form_validation_injected_for_forms(self):
        result = enhance_html(FULL_HTML, "test")
        self.assertIn("data-validated", result)
        self.assertIn("border-red-500", result)

    def test_no_form_validation_without_forms(self):
        result = enhance_html(MINIMAL_HTML, "test")
        self.assertNotIn("data-validated", result)

    def test_preserves_original_content(self):
        result = enhance_html(MINIMAL_HTML, "test")
        self.assertIn("<h1>Hello</h1>", result)
        self.assertIn("Click me", result)

    def test_tailwind_darkmode_config_added(self):
        result = enhance_html(FULL_HTML, "test")
        self.assertIn("darkMode", result)


class TestDetectFeatures(unittest.TestCase):
    """Tests for _detect_features."""

    def test_detects_responsive_design(self):
        html = '<div class="md:grid-cols-2 lg:flex">content</div>'
        features = _detect_features(html)
        self.assertIn("responsive-design", features)

    def test_detects_dark_mode(self):
        html = '<div class="dark:bg-gray-900">x</div><script>document.documentElement.classList.toggle("dark")</script>'
        features = _detect_features(html)
        self.assertIn("dark-mode", features)

    def test_detects_local_storage(self):
        html = '<script>localStorage.setItem("key","val");localStorage.getItem("key")</script>'
        features = _detect_features(html)
        self.assertIn("local-storage", features)

    def test_detects_svg_icons(self):
        html = '<svg viewBox="0 0 24 24"><path d="M12 3v1"/></svg>'
        features = _detect_features(html)
        self.assertIn("svg-icons", features)

    def test_detects_hover_effects(self):
        html = '<button class="hover:bg-blue-600">Click</button>'
        features = _detect_features(html)
        self.assertIn("hover-effects", features)

    def test_detects_gradient_design(self):
        html = '<div class="bg-gradient-to-r from-blue-500 to-purple-500">x</div>'
        features = _detect_features(html)
        self.assertIn("gradient-design", features)

    def test_detects_semantic_html(self):
        html = "<header>h</header><main>m</main><footer>f</footer>"
        features = _detect_features(html)
        self.assertIn("semantic-html", features)

    def test_detects_animations(self):
        html = '<div class="transition-all duration-300 animate-pulse">x</div>'
        features = _detect_features(html)
        self.assertIn("animations", features)

    def test_detects_event_listeners(self):
        html = '<script>document.addEventListener("click", fn)</script>'
        features = _detect_features(html)
        self.assertIn("event-listeners", features)

    def test_detects_accessibility(self):
        html = '<button aria-label="Close" role="button">X</button>'
        features = _detect_features(html)
        self.assertIn("accessibility", features)

    def test_empty_html(self):
        self.assertEqual(_detect_features(""), [])

    def test_detects_multiple_features(self):
        html = '''<header class="md:flex hover:bg-blue-500 bg-gradient-to-r from-blue-500">
        <svg><path d="M1 1"/></svg></header>
        <main><footer></footer></main>'''
        features = _detect_features(html)
        self.assertGreater(len(features), 3)


class TestExtractPromptKeywords(unittest.TestCase):
    """Tests for _extract_prompt_keywords."""

    def test_extracts_meaningful_words(self):
        kws = _extract_prompt_keywords("Create a weather dashboard with charts")
        self.assertIn("weather", kws)
        self.assertIn("dashboard", kws)
        self.assertIn("charts", kws)

    def test_filters_stop_words(self):
        kws = _extract_prompt_keywords("Create a simple app with the best design")
        self.assertNotIn("create", kws)
        self.assertNotIn("with", kws)
        self.assertNotIn("the", kws)

    def test_skips_short_words(self):
        kws = _extract_prompt_keywords("an AI bot")
        self.assertNotIn("an", kws)
        self.assertIn("bot", kws)

    def test_case_insensitive(self):
        kws = _extract_prompt_keywords("Build a DASHBOARD")
        self.assertIn("dashboard", kws)

    def test_empty_prompt(self):
        self.assertEqual(_extract_prompt_keywords(""), set())


class TestInjectBeforeClosingBody(unittest.TestCase):
    """Tests for _inject_before_closing_body."""

    def test_injects_before_body(self):
        html = "<html><body><p>hi</p></body></html>"
        result = _inject_before_closing_body(html, "<script>x()</script>")
        self.assertIn("<script>x()</script>", result)
        idx_script = result.index("<script>x()</script>")
        idx_body = result.index("</body>")
        self.assertLess(idx_script, idx_body)

    def test_appends_when_no_body_tag(self):
        html = "<p>no body tag</p>"
        result = _inject_before_closing_body(html, "<script>x()</script>")
        self.assertTrue(result.endswith("<script>x()</script>"))


class TestAddHoverTransitions(unittest.TestCase):
    """Tests for _add_hover_transitions."""

    def test_adds_hover_to_button(self):
        html = '<button class="bg-blue-500 px-4 py-2">Click</button>'
        result = _add_hover_transitions(html)
        self.assertIn("hover:scale-105", result)
        self.assertIn("hover:shadow-lg", result)
        self.assertIn("transition-all", result)

    def test_no_double_add(self):
        html = '<button class="bg-blue-500 hover:scale-105 px-4">Click</button>'
        result = _add_hover_transitions(html)
        self.assertEqual(result.count("hover:scale-105"), 1)

    def test_skips_tiny_buttons(self):
        html = '<button class="w-4 h-4">x</button>'
        result = _add_hover_transitions(html)
        self.assertNotIn("hover:scale-105", result)

    def test_enhances_link_buttons(self):
        html = '<a href="#" class="bg-blue-500 px-4 py-2">Link</a>'
        result = _add_hover_transitions(html)
        self.assertIn("hover:scale-105", result)


class TestAddCardShadows(unittest.TestCase):
    """Tests for _add_card_shadows."""

    def test_adds_shadow_to_card(self):
        html = '<div class="rounded bg-white p-4">Card content</div>'
        result = _add_card_shadows(html)
        self.assertIn("shadow-md", result)

    def test_no_double_shadow(self):
        html = '<div class="rounded bg-white shadow-lg p-4">Card</div>'
        result = _add_card_shadows(html)
        self.assertEqual(result.count("shadow"), 1)  # only the existing one

    def test_ignores_non_card_divs(self):
        html = '<div class="flex items-center">Not a card</div>'
        result = _add_card_shadows(html)
        self.assertNotIn("shadow-md", result)


class TestEnhanceAccessibility(unittest.TestCase):
    """Tests for _enhance_accessibility."""

    def test_adds_type_button(self):
        html = '<button class="bg-blue-500">Click</button>'
        result = _enhance_accessibility(html)
        self.assertIn('type="button"', result)

    def test_preserves_existing_type(self):
        html = '<button type="submit" class="bg-blue-500">Send</button>'
        result = _enhance_accessibility(html)
        self.assertIn('type="submit"', result)
        self.assertNotIn('type="button"', result)


if __name__ == "__main__":
    unittest.main()
