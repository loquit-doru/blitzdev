"""
Fixer Agent for BlitzDev
Fixes issues identified by CriticAgent
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings, AGENT_PROMPTS, LLMProvider
from utils.llm_manager import get_llm_manager, LLMResponse
from agents.builder import BuildResult
from agents.critic import EvaluationResult


@dataclass
class FixResult:
    """Result of fix operation"""
    html: str
    css: Optional[str]
    js: Optional[str]
    fixes_applied: List[str]
    success: bool
    iterations: int
    error: Optional[str] = None


class FixerAgent:
    """
    Agent responsible for fixing issues in generated code
    """
    
    def __init__(self):
        self.llm = get_llm_manager()
        self.system_prompt = AGENT_PROMPTS["fixer"]
        self.fix_history: List[Dict[str, Any]] = []
        self.max_iterations = settings.MAX_RETRY_ATTEMPTS
    
    async def fix(
        self,
        build_result: BuildResult,
        evaluation: EvaluationResult
    ) -> FixResult:
        """
        Fix issues in the built application
        
        Args:
            build_result: Original build result
            evaluation: Evaluation with issues to fix
        
        Returns:
            FixResult with corrected code
        """
        if evaluation.passed:
            return FixResult(
                html=build_result.html,
                css=build_result.css,
                js=build_result.js,
                fixes_applied=["No fixes needed - evaluation passed"],
                success=True,
                iterations=0
            )
        
        html = build_result.html
        css = build_result.css
        js = build_result.js
        fixes_applied = []
        
        # Apply automated fixes first
        html, auto_fixes = self._apply_automated_fixes(html, evaluation)
        fixes_applied.extend(auto_fixes)
        
        # If issues remain, use LLM (Groq for speed — free tier, saves Claude credits)
        if evaluation.issues and len(evaluation.issues) > len(auto_fixes):
            for iteration in range(min(self.max_iterations, 1)):  # 1 LLM iteration per fix() call; outer loop in main.py does re-evaluation
                try:
                    fix_prompt = self._build_fix_prompt(
                        html, css, js, evaluation, iteration
                    )
                    
                    response = await self.llm.generate(
                        prompt=fix_prompt,
                        temperature=0.3,
                        system_prompt=self.system_prompt,
                        max_tokens=settings.MAX_TOKENS,
                        provider=LLMProvider.DEEPSEEK
                    )
                    
                    new_html, new_css, new_js = self._parse_fixed_code(response.content)
                    
                    if new_html:
                        html = new_html
                        css = new_css or css
                        js = new_js or js
                        fixes_applied.append(f"LLM fix iteration {iteration + 1}")
                    
                except Exception as e:
                    fixes_applied.append(f"Fix iteration {iteration + 1} failed: {e}")
                    break
        
        # Log fix
        self.fix_history.append({
            "original_score": evaluation.scores.overall,
            "fixes_applied": len(fixes_applied),
            "iterations": len(fixes_applied)
        })
        
        return FixResult(
            html=html,
            css=css,
            js=js,
            fixes_applied=fixes_applied,
            success=True,
            iterations=len(fixes_applied)
        )
    
    def _apply_automated_fixes(
        self,
        html: str,
        evaluation: EvaluationResult
    ) -> Tuple[str, List[str]]:
        """Apply automated fixes for common issues"""
        
        fixes = []
        
        # Fix 1: Add DOCTYPE if missing
        if "<!doctype" not in html.lower():
            html = "<!DOCTYPE html>\n" + html
            fixes.append("Added DOCTYPE declaration")
        
        # Fix 2: Add viewport meta if missing
        if "viewport" not in html.lower():
            viewport_meta = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
            if "<head" in html.lower():
                html = re.sub(
                    r'(<head[^>]*>)',
                    r'\1\n    ' + viewport_meta,
                    html,
                    flags=re.IGNORECASE
                )
                fixes.append("Added viewport meta tag")
        
        # Fix 3: Add lang attribute to html
        if '<html' in html.lower() and 'lang=' not in html.lower():
            html = re.sub(
                r'<html',
                '<html lang="en"',
                html,
                flags=re.IGNORECASE,
                count=1
            )
            fixes.append("Added lang attribute to html tag")
        
        # Fix 4: Add charset meta if missing
        if "charset" not in html.lower():
            charset_meta = '<meta charset="UTF-8">'
            if "<head" in html.lower():
                html = re.sub(
                    r'(<head[^>]*>)',
                    r'\1\n    ' + charset_meta,
                    html,
                    flags=re.IGNORECASE
                )
                fixes.append("Added charset meta tag")
        
        # Fix 5: Add title if missing
        if "<title" not in html.lower():
            if "<head" in html.lower():
                html = re.sub(
                    r'(</head>)',
                    r'    <title>BlitzDev App</title>\n\1',
                    html,
                    flags=re.IGNORECASE
                )
                fixes.append("Added title tag")
        
        # Fix 6: Ensure Tailwind CDN
        if "tailwind" not in html.lower() and "cdn.tailwindcss.com" not in html:
            tailwind_script = '<script src="https://cdn.tailwindcss.com"></script>'
            if "<head" in html.lower():
                html = re.sub(
                    r'(</head>)',
                    r'    ' + tailwind_script + '\n\1',
                    html,
                    flags=re.IGNORECASE
                )
                fixes.append("Added Tailwind CSS CDN")
        
        # Fix 7: Close unclosed tags (basic)
        # This is a simplified check - full HTML parsing would be better
        if html.count('<div') > html.count('</div>'):
            # Add closing divs at end of body
            unclosed = html.count('<div') - html.count('</div>')
            html = html.replace('</body>', '</div>' * unclosed + '\n</body>')
            fixes.append(f"Closed {unclosed} unclosed div tags")
        
        return html, fixes
    
    def _build_fix_prompt(
        self,
        html: str,
        css: Optional[str],
        js: Optional[str],
        evaluation: EvaluationResult,
        iteration: int
    ) -> str:
        """Build prompt for LLM fix"""
        
        issues_text = "\n".join([
            f"- [{i['category']}] {i['description']}"
            for i in evaluation.issues
        ])
        
        suggestions_text = "\n".join([
            f"- {s}" for s in evaluation.suggestions[:5]
        ])
        
        css_section = f"\n```css\n{css}\n```" if css else ""
        js_section = f"\n```javascript\n{js}\n```" if js else ""
        
        # Determine weakest dimension and prioritize
        scores = {
            "Functionality": evaluation.scores.functionality,
            "Design": evaluation.scores.design,
            "Speed": evaluation.scores.speed,
        }
        weakest = min(scores, key=scores.get)
        sorted_dims = sorted(scores.items(), key=lambda x: x[1])
        
        priority_instructions = ""
        if scores["Functionality"] < 70:
            priority_instructions += """
PRIORITY FIX — FUNCTIONALITY IS LOW:
- Every button, link, and form MUST have working JavaScript event handlers
- All interactive features (search, filter, sort, add, delete, calculate) must actually work
- Forms must validate input and show results
- No dead buttons, no placeholder onclick handlers
- Test every click path mentally — does it DO something?"""
        if scores["Design"] < 70:
            priority_instructions += """
PRIORITY FIX — DESIGN IS LOW:
- Add visual richness: gradients (bg-gradient-to-r), shadows (shadow-lg, shadow-xl), rounded corners
- Use proper spacing: sections need py-16+, cards need p-6+, gaps between elements
- Add hover effects on ALL interactive elements (hover:scale-105, hover:shadow-lg, hover:bg-opacity-80)
- Include 3+ inline SVG icons (real paths, not empty tags)
- Use the color palette consistently — primary for headers, accent for CTAs, surface for cards
- Add transitions: transition-all duration-300 on interactive elements"""
        if scores["Speed"] < 70:
            priority_instructions += """
PRIORITY FIX — SPEED IS LOW:
- Remove any unused CSS or JS
- Minimize DOM depth (flatten unnecessary nested divs)
- Use efficient selectors
- Lazy-load images if any
- Keep total HTML under 50KB"""
        
        return f"""You are fixing a web application to achieve a HIGHER quality score. Current score: {evaluation.scores.overall}/100. Target: 85+/100.

CURRENT SCORES (fix weakest first — {weakest} is lowest):
- {sorted_dims[0][0]}: {sorted_dims[0][1]}/100 ← WEAKEST, fix first
- {sorted_dims[1][0]}: {sorted_dims[1][1]}/100
- {sorted_dims[2][0]}: {sorted_dims[2][1]}/100
- Overall: {evaluation.scores.overall}/100
{priority_instructions}

ISSUES FOUND (fix ALL of them):
{issues_text}

IMPROVEMENT SUGGESTIONS:
{suggestions_text}

DETAILED FEEDBACK:
{evaluation.detailed_feedback}

CURRENT HTML:
```html
{html[:15000]}
```
{css_section}
{js_section}

INSTRUCTIONS:
1. Output the COMPLETE fixed HTML file — not snippets, not partial. Full <!DOCTYPE html> to </html>
2. Fix EVERY issue listed above, starting with the weakest dimension
3. Keep all existing working features — do NOT break what already works
4. If adding SVG icons, use real inline SVG paths (not empty <svg> tags)
5. If adding hover states, use real Tailwind hover: utilities  
6. If adding animations, use Tailwind transition-* or animate-* classes
7. If improving design, add gradients/shadows/rounded corners/proper spacing
8. Ensure responsive breakpoints (sm:/md:/lg:) are used
9. All JavaScript must be FUNCTIONAL — no empty function bodies or TODO comments

Output ONLY the complete HTML. No markdown fences, no explanations.
Fix iteration: {iteration + 1}"""
    
    def _parse_fixed_code(self, content: str) -> Tuple[str, Optional[str], Optional[str]]:
        """Parse fixed code from LLM response"""
        
        html = ""
        css = None
        js = None
        
        # Try to extract HTML from code fences first
        html_match = re.search(
            r'```html\s*\n(.*?)\n```',
            content,
            re.DOTALL | re.IGNORECASE
        )
        if html_match:
            html = html_match.group(1).strip()
        elif '<!DOCTYPE' in content or '<!doctype' in content or '<html' in content:
            # No fences — LLM returned raw HTML as instructed
            # Strip any leading/trailing non-HTML text
            start = content.find('<!DOCTYPE') if '<!DOCTYPE' in content else content.find('<!doctype') if '<!doctype' in content else content.find('<html')
            end = content.rfind('</html>')
            if start >= 0 and end > start:
                html = content[start:end + len('</html>')].strip()
            elif start >= 0:
                html = content[start:].strip()
        
        # Extract CSS (if present in fences)
        css_match = re.search(
            r'```css\s*\n(.*?)\n```',
            content,
            re.DOTALL | re.IGNORECASE
        )
        if css_match:
            css = css_match.group(1).strip()
        
        # Extract JS (if present in fences)
        js_match = re.search(
            r'```(?:javascript|js)\s*\n(.*?)\n```',
            content,
            re.DOTALL | re.IGNORECASE
        )
        if js_match:
            js = js_match.group(1).strip()
        
        return html, css, js
    
    async def quick_fix(
        self,
        html: str,
        issue_description: str
    ) -> str:
        """
        Quick fix for specific issue
        
        Args:
            html: HTML to fix
            issue_description: Description of the issue
        
        Returns:
            Fixed HTML
        """
        fix_prompt = f"""Fix this specific issue in the HTML:

ISSUE: {issue_description}

HTML:
```html
{html[:3000]}
```

Provide only the fixed HTML:"""
        
        try:
            response = await self.llm.generate(
                prompt=fix_prompt,
                temperature=0.3,
                provider=LLMProvider.DEEPSEEK
            )
            
            # Extract HTML
            match = re.search(
                r'```html\s*\n(.*?)\n```',
                response.content,
                re.DOTALL | re.IGNORECASE
            )
            if match:
                return match.group(1).strip()
            
            return response.content
            
        except Exception:
            return html
    
    def get_fix_history(self) -> List[Dict[str, Any]]:
        """Get fix history"""
        return self.fix_history
    
    def get_stats(self) -> Dict[str, Any]:
        """Get fixer statistics"""
        if not self.fix_history:
            return {"total_fixes": 0}
        
        total = len(self.fix_history)
        avg_fixes = sum(f["fixes_applied"] for f in self.fix_history) / total
        
        return {
            "total_fixes": total,
            "average_fixes_per_build": avg_fixes
        }
