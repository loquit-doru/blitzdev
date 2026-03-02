"""
Critic Agent for BlitzDev
Evaluates web applications on functionality, design, and speed
"""

import json
import time
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from bs4 import BeautifulSoup

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings, EVALUATION_CRITERIA, AGENT_PROMPTS, LLMProvider
from utils.llm_manager import get_llm_manager, LLMResponse
from utils.json_repair import safe_parse_llm_json
from agents.builder import BuildResult


class ScoreLevel(str, Enum):
    """Quality score levels"""
    EXCELLENT = "excellent"  # 90-100
    GOOD = "good"            # 75-89
    ACCEPTABLE = "acceptable" # 60-74
    POOR = "poor"            # 40-59
    FAIL = "fail"            # 0-39


@dataclass
class EvaluationScores:
    """Detailed evaluation scores"""
    functionality: float
    design: float
    speed: float
    overall: float
    
    functionality_breakdown: Dict[str, float]
    design_breakdown: Dict[str, float]
    speed_breakdown: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "functionality": round(self.functionality, 2),
            "design": round(self.design, 2),
            "speed": round(self.speed, 2),
            "overall": round(self.overall, 2),
            "breakdown": {
                "functionality": self.functionality_breakdown,
                "design": self.design_breakdown,
                "speed": self.speed_breakdown
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvaluationScores":
        return cls(
            functionality=data.get("functionality", 0),
            design=data.get("design", 0),
            speed=data.get("speed", 0),
            overall=data.get("overall", 0),
            functionality_breakdown=data.get("breakdown", {}).get("functionality", {}),
            design_breakdown=data.get("breakdown", {}).get("design", {}),
            speed_breakdown=data.get("breakdown", {}).get("speed", {})
        )


@dataclass
class EvaluationResult:
    """Complete evaluation result"""
    scores: EvaluationScores
    suggestions: List[str]
    issues: List[Dict[str, Any]]
    passed: bool
    level: ScoreLevel
    detailed_feedback: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scores": self.scores.to_dict(),
            "suggestions": self.suggestions,
            "issues": self.issues,
            "passed": self.passed,
            "level": self.level.value,
            "detailed_feedback": self.detailed_feedback
        }


class CriticAgent:
    """
    Agent responsible for evaluating web application quality
    Weights: Functionality 50%, Design 30%, Speed 20%
    """
    
    def __init__(self):
        self.llm = get_llm_manager()
        self.system_prompt = AGENT_PROMPTS["critic"]
        self.evaluation_history: List[Dict[str, Any]] = []
        
        # Weights from config
        self.weights = {
            "functionality": settings.WEIGHT_FUNCTIONALITY,
            "design": settings.WEIGHT_DESIGN,
            "speed": settings.WEIGHT_SPEED
        }
        self.min_score = settings.MIN_QUALITY_SCORE
    
    async def evaluate(
        self,
        build_result: BuildResult,
        original_prompt: str,
        generation_time: Optional[float] = None
    ) -> EvaluationResult:
        """
        Evaluate a built web application
        
        Args:
            build_result: Result from BuilderAgent
            original_prompt: Original user prompt
            generation_time: Time taken to generate
        
        Returns:
            EvaluationResult with scores and feedback
        """
        start_time = time.time()
        
        # Run automated checks
        auto_scores = self._automated_evaluation(build_result)
        
        # Get LLM evaluation
        llm_evaluation = await self._llm_evaluation(
            build_result,
            original_prompt
        )
        
        # Combine scores
        scores = self._combine_scores(auto_scores, llm_evaluation, generation_time)
        
        # Determine if passed
        passed = scores.overall >= self.min_score
        level = self._get_score_level(scores.overall)
        
        # Extract suggestions and issues
        suggestions = llm_evaluation.get("suggestions", [])
        issues = self._extract_issues(build_result, scores)
        
        evaluation_time = time.time() - start_time
        
        result = EvaluationResult(
            scores=scores,
            suggestions=suggestions,
            issues=issues,
            passed=passed,
            level=level,
            detailed_feedback=llm_evaluation.get("feedback", "")
        )
        
        # Log evaluation
        self.evaluation_history.append({
            "overall_score": scores.overall,
            "passed": passed,
            "evaluation_time": evaluation_time
        })
        
        return result
    
    def _automated_evaluation(self, build_result: BuildResult) -> Dict[str, Any]:
        """Run automated code analysis"""
        
        scores = {
            "functionality": {},
            "design": {},
            "speed": {}
        }
        
        html = build_result.html
        css = build_result.css or ""
        js = build_result.js or ""
        
        # Parse HTML
        try:
            soup = BeautifulSoup(html, 'html.parser')
        except Exception:
            soup = None
        
        # ===== Functionality checks =====
        # Code validity
        has_doctype = "<!doctype" in html.lower() or "<!DOCTYPE" in html
        has_html = "<html" in html.lower()
        has_head = "<head" in html.lower()
        has_body = "<body" in html.lower()
        has_lang = 'lang=' in html.lower()
        has_charset = "charset" in html.lower()
        validity_score = sum([has_doctype, has_html, has_head, has_body, has_lang, has_charset]) / 6 * 100
        scores["functionality"]["code_validity"] = round(validity_score)
        
        # Interactivity — count real interactive features
        interactive_features = 0
        if "onclick" in html.lower(): interactive_features += 1
        if "addEventListener" in html or "addEventListener" in js: interactive_features += 2
        if "querySelector" in html or "querySelector" in js: interactive_features += 1
        if "getElementById" in html or "getElementById" in js: interactive_features += 1
        if "<form" in html.lower(): interactive_features += 1
        if "<button" in html.lower(): interactive_features += 1
        if "<input" in html.lower(): interactive_features += 1
        if "function " in html or "function " in js: interactive_features += 1
        if "=>" in html or "=>" in js: interactive_features += 1
        scores["functionality"]["interactivity"] = min(100, 30 + interactive_features * 8)
        
        # Responsiveness — check for actual breakpoints
        responsive_features = 0
        if "viewport" in html.lower(): responsive_features += 2
        for bp in ["sm:", "md:", "lg:", "xl:", "2xl:"]:
            if bp in html:
                responsive_features += 2
        if "tailwind" in html.lower(): responsive_features += 1
        if "max-w-" in html: responsive_features += 1
        if "grid" in html and "cols" in html: responsive_features += 1
        scores["functionality"]["responsiveness"] = min(100, 30 + responsive_features * 7)
        
        # Completeness — semantic HTML + proper structure
        completeness_score = 0
        for tag in ["<title", "<meta", "<header", "<nav", "<main", "<section", "<footer", "<h1", "<h2", "<p"]:
            if tag in html.lower():
                completeness_score += 10
        scores["functionality"]["completeness"] = min(100, completeness_score)
        
        # ===== Design checks =====
        if soup:
            # Visual appeal — SVGs, gradients, shadows, images, color usage
            appeal_score = 50
            if soup.find_all('svg'): appeal_score += 15
            if soup.find_all('img'): appeal_score += 10
            if 'gradient' in html.lower(): appeal_score += 10
            if 'shadow' in html: appeal_score += 5
            if 'rounded' in html: appeal_score += 5
            if 'hover:' in html: appeal_score += 10
            scores["design"]["visual_appeal"] = min(100, appeal_score)
            
            # Consistency — variety of Tailwind classes
            elements_with_class = soup.find_all(class_=True)
            unique_class_patterns = set()
            for el in elements_with_class:
                classes = ' '.join(sorted(el.get('class', [])))
                unique_class_patterns.add(classes)
            class_count = len(unique_class_patterns)
            scores["design"]["consistency"] = min(100, 40 + class_count * 3)
            
            # Typography — headings, paragraphs, font utilities
            typography_score = 50
            headings = len(soup.find_all(['h1', 'h2', 'h3', 'h4']))
            paragraphs = len(soup.find_all(['p', 'span']))
            if headings >= 2: typography_score += 15
            if paragraphs >= 3: typography_score += 10
            if 'font-bold' in html or 'font-semibold' in html: typography_score += 10
            if 'text-lg' in html or 'text-xl' in html or 'text-2xl' in html: typography_score += 10
            if 'leading-' in html or 'tracking-' in html: typography_score += 5
            scores["design"]["typography"] = min(100, typography_score)
            
            # Color harmony — check for systematic color usage
            color_score = 50
            if bool(re.search(r'#[0-9a-fA-F]{3,6}', html)): color_score += 10
            for c in ['primary', 'secondary', 'accent', 'bg-', 'text-']:
                if c in html: color_score += 8
            scores["design"]["color_harmony"] = min(100, color_score)
        else:
            scores["design"] = {
                "visual_appeal": 40,
                "consistency": 40,
                "typography": 40,
                "color_harmony": 40
            }
        
        # ===== Speed checks =====
        html_size = len(html) + len(css) + len(js)
        scores["speed"]["render_efficiency"] = 95 if html_size < 30000 else (85 if html_size < 50000 else 75)
        scores["speed"]["code_optimization"] = 90 if html_size < 20000 else (80 if html_size < 50000 else 70)
        
        return scores
    
    async def _llm_evaluation(
        self,
        build_result: BuildResult,
        original_prompt: str
    ) -> Dict[str, Any]:
        """Get LLM-based evaluation"""
        
        # Larger sample for better evaluation
        html_sample = build_result.html[:6000] + "\n<!-- ... truncated ... -->" if len(build_result.html) > 6000 else build_result.html
        
        eval_prompt = f"""You are a STRICT web application quality judge for a hackathon.
Score HONESTLY — do NOT inflate scores. A "7" is already good.

ORIGINAL REQUEST: {original_prompt}

GENERATED HTML:
```html
{html_sample}
```

Score each dimension 0-100 using this rubric:

## FUNCTIONALITY (50% weight)
- 90-100: All requested features work perfectly, form validation, error states, smooth interactions
- 70-89: Core features work but missing polish (e.g. no loading states, basic validation only)
- 50-69: Some features work, others broken or missing
- <50: Major features missing or broken

Check specifically:
- Does it actually implement what was requested?
- Do buttons/forms/interactions work via JavaScript?
- Is there proper error handling?
- Are edge cases considered?

## DESIGN (30% weight)
- 90-100: Professional-grade visual design — beautiful color palette, excellent typography hierarchy, smooth animations, modern layout, SVG icons, gradient accents
- 70-89: Good design but missing some polish (e.g. no animations, basic icons, inconsistent spacing)
- 50-69: Generic/template look, poor color choices, no visual hierarchy
- <50: Broken layout, no styling, ugly

Check specifically:
- Color harmony (is there a cohesive palette or random colors?)
- Typography hierarchy (headings vs body, font weights, line height)
- Spacing and alignment consistency
- Visual polish (rounded corners, shadows, hover states, transitions)
- Does it look like a professional made it?

## SPEED (20% weight)
- 90-100: Minimal DOM, efficient CSS (Tailwind utility), no render-blocking, optimized images
- 70-89: Clean but could be more optimized
- <70: Bloated, unnecessary code

Respond with ONLY valid JSON (no markdown):
{{
    "scores": {{
        "functionality": <number>,
        "design": <number>,
        "speed": <number>
    }},
    "suggestions": [
        "specific actionable improvement 1",
        "specific actionable improvement 2",
        "specific actionable improvement 3"
    ],
    "feedback": "2-3 sentence overall assessment"
}}"""
        
        try:
            response = await self.llm.generate(
                prompt=eval_prompt,
                temperature=0.3,
                provider=LLMProvider.DEEPSEEK
            )
            
            content = response.content
            
            # Use JSON repair engine for robust parsing
            fallback = {
                "scores": {"functionality": 70, "design": 70, "speed": 70},
                "suggestions": ["Could not parse LLM evaluation"],
                "feedback": "Evaluation parsing failed — using defaults"
            }
            return safe_parse_llm_json(content, fallback)
            
        except Exception as e:
            return {
                "scores": {"functionality": 70, "design": 70, "speed": 70},
                "suggestions": ["Could not complete LLM evaluation"],
                "feedback": f"Evaluation error: {e}"
            }
    
    def _combine_scores(
        self,
        auto_scores: Dict[str, Any],
        llm_evaluation: Dict[str, Any],
        generation_time: Optional[float]
    ) -> EvaluationScores:
        """Combine automated and LLM scores"""
        
        llm_scores = llm_evaluation.get("scores", {})
        
        # Functionality (50%)
        func_auto = sum(auto_scores["functionality"].values()) / len(auto_scores["functionality"])
        func_llm = llm_scores.get("functionality", func_auto)
        functionality = (func_auto * 0.4 + func_llm * 0.6)  # Weight LLM slightly more
        
        # Design (30%)
        design_auto = sum(auto_scores["design"].values()) / len(auto_scores["design"])
        design_llm = llm_scores.get("design", design_auto)
        design = (design_auto * 0.3 + design_llm * 0.7)  # Weight LLM more for design
        
        # Speed (20%)
        speed_auto = sum(auto_scores["speed"].values()) / len(auto_scores["speed"])
        speed_llm = llm_scores.get("speed", speed_auto)
        
        # Adjust for generation time
        if generation_time:
            if generation_time < 30:
                time_score = 100
            elif generation_time < 60:
                time_score = 90
            elif generation_time < 120:
                time_score = 80
            else:
                time_score = 70
            speed = (speed_auto * 0.3 + speed_llm * 0.4 + time_score * 0.3)
        else:
            speed = (speed_auto * 0.5 + speed_llm * 0.5)
        
        # Calculate weighted overall
        overall = (
            functionality * self.weights["functionality"] +
            design * self.weights["design"] +
            speed * self.weights["speed"]
        )
        
        return EvaluationScores(
            functionality=round(functionality, 1),
            design=round(design, 1),
            speed=round(speed, 1),
            overall=round(overall, 1),
            functionality_breakdown=auto_scores["functionality"],
            design_breakdown=auto_scores["design"],
            speed_breakdown={
                **auto_scores["speed"],
                "generation_time_factor": generation_time
            }
        )
    
    def _get_score_level(self, score: float) -> ScoreLevel:
        """Get score level from numeric score"""
        if score >= 90:
            return ScoreLevel.EXCELLENT
        elif score >= 75:
            return ScoreLevel.GOOD
        elif score >= 60:
            return ScoreLevel.ACCEPTABLE
        elif score >= 40:
            return ScoreLevel.POOR
        else:
            return ScoreLevel.FAIL
    
    def _extract_issues(
        self,
        build_result: BuildResult,
        scores: EvaluationScores
    ) -> List[Dict[str, Any]]:
        """Extract specific, actionable issues for the fixer"""
        
        issues = []
        html = build_result.html
        html_lower = html.lower()
        
        # Parse HTML for DOM analysis
        try:
            soup = BeautifulSoup(html, 'html.parser')
        except Exception:
            soup = None
        
        # --- Structure issues ---
        if "<!doctype" not in html_lower:
            issues.append({"category": "structure", "severity": "high", "description": "Missing DOCTYPE declaration"})
        if 'lang=' not in html_lower:
            issues.append({"category": "structure", "severity": "medium", "description": "Missing lang attribute on <html>"})
        if 'charset' not in html_lower:
            issues.append({"category": "structure", "severity": "medium", "description": "Missing charset meta tag"})
        if '<title' not in html_lower:
            issues.append({"category": "structure", "severity": "medium", "description": "Missing <title> element"})
        
        # --- Responsiveness issues ---
        if 'viewport' not in html_lower:
            issues.append({"category": "responsiveness", "severity": "high", "description": "Missing viewport meta tag — will not be responsive on mobile"})
        if 'tailwind' not in html_lower:
            issues.append({"category": "responsiveness", "severity": "high", "description": "Missing Tailwind CDN — no utility classes available"})
        has_breakpoints = any(bp in html for bp in ["sm:", "md:", "lg:", "xl:"])
        if not has_breakpoints:
            issues.append({"category": "responsiveness", "severity": "medium", "description": "No responsive breakpoints (sm:/md:/lg:) — layout won't adapt to screen sizes"})
        
        # --- Interactivity issues ---
        has_script = '<script' in html_lower
        has_events = 'onclick' in html_lower or 'addEventListener' in html or '=>' in html
        if not has_script and not has_events:
            issues.append({"category": "functionality", "severity": "high", "description": "No JavaScript — page is completely static with no interactivity"})
        elif has_script and 'addEventListener' not in html and 'onclick' not in html_lower:
            issues.append({"category": "functionality", "severity": "medium", "description": "Script present but no event listeners — interactivity may not work"})
        
        # --- Button/modal wiring issues ---
        if soup:
            buttons = soup.find_all('button')
            button_count = len(buttons)
            # Check if modals exist but might lack close handlers
            modals = soup.find_all(id=lambda x: x and ('modal' in x.lower() or 'settings' in x.lower() or 'dialog' in x.lower()))
            if modals and 'close' not in html_lower and 'cancel' not in html_lower and 'hide' not in html_lower:
                issues.append({"category": "functionality", "severity": "high", "description": "Modal/dialog found but no close/cancel handler — users will get stuck"})
            # Check buttons vs event handlers ratio
            event_handler_count = html.count('addEventListener') + html_lower.count('onclick')
            if button_count > 3 and event_handler_count < button_count // 2:
                issues.append({"category": "functionality", "severity": "medium", "description": f"{button_count} buttons but only ~{event_handler_count} event handlers — some buttons likely do nothing"})
        
        # --- Toast/notification overlap ---
        if 'fixed' in html and ('toast' in html_lower or 'notification' in html_lower or 'snackbar' in html_lower):
            if 'translateY' not in html and 'top:' not in html and 'offset' not in html_lower:
                issues.append({"category": "design", "severity": "medium", "description": "Toast notifications use fixed positioning but no vertical offset — they will overlap each other"})
        
        # --- Design issues ---
        if '<svg' not in html_lower and 'lucide' not in html_lower and 'heroicon' not in html_lower:
            issues.append({"category": "design", "severity": "medium", "description": "No SVG icons found — add inline SVG icons for visual polish"})
        if 'gradient' not in html_lower:
            issues.append({"category": "design", "severity": "low", "description": "No gradients — consider adding gradient backgrounds for visual depth"})
        if 'shadow' not in html:
            issues.append({"category": "design", "severity": "low", "description": "No shadows — add shadow utilities for card depth and elevation"})
        if 'hover:' not in html:
            issues.append({"category": "design", "severity": "medium", "description": "No hover states — add hover: utilities for interactive feedback"})
        if 'transition' not in html and 'animate' not in html:
            issues.append({"category": "design", "severity": "low", "description": "No animations/transitions — add transition-all or animate-* for polish"})
        
        # --- Semantic issues ---
        semantic_tags = ['<header', '<nav', '<main', '<section', '<article', '<footer']
        found_semantic = sum(1 for tag in semantic_tags if tag in html_lower)
        if found_semantic < 3:
            issues.append({"category": "semantics", "severity": "medium",
                          "description": f"Only {found_semantic}/6 semantic HTML tags used — add <header>, <main>, <section>, <footer> for structure"})
        
        # --- Score-based issues ---
        if scores.functionality < 70:
            issues.append({"category": "functionality", "severity": "high",
                          "description": f"Functionality score is {scores.functionality}/100 — core features may be missing or broken"})
        if scores.design < 70:
            issues.append({"category": "design", "severity": "high",
                          "description": f"Design score is {scores.design}/100 — visual quality needs significant improvement"})
        
        return issues
    
    def get_evaluation_history(self) -> List[Dict[str, Any]]:
        """Get evaluation history"""
        return self.evaluation_history
    
    def get_stats(self) -> Dict[str, Any]:
        """Get critic statistics"""
        if not self.evaluation_history:
            return {"total_evaluations": 0}
        
        total = len(self.evaluation_history)
        passed = sum(1 for e in self.evaluation_history if e["passed"])
        avg_score = sum(e["overall_score"] for e in self.evaluation_history) / total
        
        return {
            "total_evaluations": total,
            "passed": passed,
            "pass_rate": passed / total,
            "average_score": avg_score
        }
