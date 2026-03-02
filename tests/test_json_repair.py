"""Tests for JSON Repair Engine"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.json_repair import repair_json, safe_parse_llm_json, _strip_code_fences, _fix_common_issues


class TestRepairJson:
    def test_valid_json_passthrough(self):
        result = repair_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_in_code_fences(self):
        text = '```json\n{"scores": {"functionality": 85}}\n```'
        result = repair_json(text)
        assert result["scores"]["functionality"] == 85

    def test_json_in_generic_fences(self):
        text = '```\n{"key": "val"}\n```'
        result = repair_json(text)
        assert result == {"key": "val"}

    def test_json_with_preamble_text(self):
        text = 'Here is my evaluation:\n{"scores": {"speed": 90}, "feedback": "good"}'
        result = repair_json(text)
        assert result["scores"]["speed"] == 90

    def test_trailing_commas(self):
        text = '{"a": 1, "b": 2, }'
        result = repair_json(text)
        assert result == {"a": 1, "b": 2}

    def test_trailing_comma_in_array(self):
        text = '{"items": [1, 2, 3, ]}'
        result = repair_json(text)
        assert result["items"] == [1, 2, 3]

    def test_empty_input(self):
        assert repair_json("") is None
        assert repair_json("   ") is None

    def test_no_json_at_all(self):
        assert repair_json("This is just plain text with no JSON") is None

    def test_nested_json_in_text(self):
        text = 'The plan is: {"app_type": "dashboard", "components": ["header", "chart"]} end.'
        result = repair_json(text)
        assert result["app_type"] == "dashboard"
        assert "header" in result["components"]

    def test_multiline_json_in_fences(self):
        text = """```json
{
    "scores": {
        "functionality": 80,
        "design": 75,
        "speed": 90
    },
    "suggestions": ["add hover effects"],
    "feedback": "Good work"
}
```"""
        result = repair_json(text)
        assert result["scores"]["functionality"] == 80
        assert len(result["suggestions"]) == 1


class TestSafeParseJson:
    def test_returns_parsed_on_success(self):
        result = safe_parse_llm_json('{"ok": true}')
        assert result == {"ok": True}

    def test_returns_fallback_on_failure(self):
        fallback = {"default": True}
        result = safe_parse_llm_json("not json", fallback)
        assert result == fallback

    def test_returns_empty_dict_no_fallback(self):
        result = safe_parse_llm_json("not json")
        assert result == {}


class TestHelpers:
    def test_strip_code_fences_json(self):
        assert _strip_code_fences('```json\n{"a":1}\n```') == '{"a":1}'

    def test_strip_code_fences_plain(self):
        assert _strip_code_fences('```\n{"a":1}\n```') == '{"a":1}'

    def test_strip_code_fences_no_fences(self):
        assert _strip_code_fences('{"a":1}') == '{"a":1}'

    def test_fix_trailing_comma(self):
        assert '"b": 2}' in _fix_common_issues('{"a": 1, "b": 2,}')
