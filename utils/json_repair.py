"""
JSON Repair Engine for BlitzDev
Self-healing parser that fixes malformed LLM outputs:
- Strips markdown code fences
- Fixes trailing commas
- Extracts deep JSON from mixed text
- Escapes problematic characters
"""

import json
import re
from typing import Any, Optional, Dict


def repair_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to parse JSON from potentially malformed LLM output.
    Tries multiple strategies in order of aggressiveness.
    
    Returns parsed dict or None if all strategies fail.
    """
    if not text or not text.strip():
        return None
    
    # Strategy 1: Direct parse (fast path)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Strip markdown code fences
    cleaned = _strip_code_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    # Strategy 3: Extract JSON object from mixed text
    extracted = _extract_json_object(text)
    if extracted:
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            pass
    
    # Strategy 4: Fix common issues (trailing commas, single quotes, etc.)
    fixed = _fix_common_issues(cleaned)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    
    # Strategy 5: Deep extraction — find outermost { ... } even across newlines
    deep = _deep_extract(text)
    if deep:
        fixed_deep = _fix_common_issues(deep)
        try:
            return json.loads(fixed_deep)
        except json.JSONDecodeError:
            pass
    
    return None


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences: ```json ... ``` or ``` ... ```"""
    # Try ```json first
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _extract_json_object(text: str) -> Optional[str]:
    """Extract the first complete JSON object { ... } from text"""
    start = text.find('{')
    if start == -1:
        return None
    
    # Find matching closing brace
    depth = 0
    in_string = False
    escape_next = False
    
    for i in range(start, len(text)):
        ch = text[i]
        
        if escape_next:
            escape_next = False
            continue
        
        if ch == '\\':
            escape_next = True
            continue
        
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if in_string:
            continue
        
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    
    # If we got here, no matching brace found — try with what we have
    return None


def _deep_extract(text: str) -> Optional[str]:
    """Find the LAST complete JSON object (LLMs sometimes have preamble)"""
    # Find all { positions
    starts = [i for i, ch in enumerate(text) if ch == '{']
    
    for start in starts:
        depth = 0
        in_string = False
        escape_next = False
        
        for i in range(start, len(text)):
            ch = text[i]
            
            if escape_next:
                escape_next = False
                continue
            if ch == '\\':
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    candidate = text[start:i + 1]
                    # Verify it has the typical keys we expect
                    if '"scores"' in candidate or '"functionality"' in candidate or '"app_type"' in candidate:
                        return candidate
                    break
    
    return None


def _fix_common_issues(text: str) -> str:
    """Fix common JSON issues from LLM output"""
    result = text
    
    # Fix trailing commas before } or ]
    result = re.sub(r',\s*([}\]])', r'\1', result)
    
    # Fix single quotes used as string delimiters (risky, only if no double quotes in value)
    # Only do this if no valid JSON detected
    if "'" in result and '"' not in result:
        result = result.replace("'", '"')
    
    # Fix unquoted keys: { key: "value" } → { "key": "value" }
    # Use two passes instead of variable-width lookbehind (Python 3.10 compat)
    result = re.sub(r'(?<=\{)\s*(\w+)\s*:', r' "\1":', result)
    result = re.sub(r'(?<=,)\s*(\w+)\s*:', r' "\1":', result)
    
    # Newline escaping inside strings is too risky with regex — skip it
    
    return result


def safe_parse_llm_json(text: str, fallback: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Parse JSON from LLM output with repair, returning fallback on failure.
    
    Args:
        text: Raw LLM output  
        fallback: Default dict to return if all parsing fails
    
    Returns:
        Parsed dict or fallback
    """
    result = repair_json(text)
    if result is not None:
        return result
    return fallback or {}
