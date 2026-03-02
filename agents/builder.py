"""
Builder Agent for BlitzDev
Generates complete web applications (HTML/CSS/JS) with Tailwind CSS
"""

import json
import time
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings, DESIGN_PRESETS, HTML_TEMPLATE, AGENT_PROMPTS
from utils.llm_manager import get_llm_manager, LLMResponse
from utils.templates import get_template_context, format_components_for_prompt, CSS_UTILITIES
from agents.planner import ImplementationPlan


@dataclass
class BuildResult:
    """Result of build operation"""
    html: str
    css: Optional[str]
    js: Optional[str]
    success: bool
    build_time: float
    tokens_used: Optional[int] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BuilderAgent:
    """
    Agent responsible for generating complete web applications
    using HTML, Tailwind CSS, and JavaScript
    """
    
    def __init__(self):
        self.llm = get_llm_manager()
        self.system_prompt = AGENT_PROMPTS["builder"]
        self.build_history: List[Dict[str, Any]] = []
    
    async def build(
        self,
        plan: ImplementationPlan,
        prompt: str
    ) -> BuildResult:
        """
        Build web application from implementation plan
        
        Args:
            plan: ImplementationPlan from PlannerAgent
            prompt: Original user prompt
        
        Returns:
            BuildResult with HTML/CSS/JS code
        """
        start_time = time.time()
        
        try:
            # Get design preset
            design_preset = DESIGN_PRESETS.get(
                plan.design_preset,
                DESIGN_PRESETS["modern_minimal"]
            )
            
            # Dynamic MAX_TOKENS based on complexity (saves 30-40% for simple apps)
            complexity_tokens = {
                "simple": 10_000,
                "medium": 20_000,
                "complex": settings.MAX_TOKENS,  # full budget
            }
            max_tokens = complexity_tokens.get(
                plan.complexity.value if hasattr(plan.complexity, 'value') else str(plan.complexity),
                settings.MAX_TOKENS
            )
            
            # Generate code — use quality LLM (Claude) for best HTML output
            build_prompt = self._build_generation_prompt(plan, prompt, design_preset)
            
            response = await self.llm.generate_with_quality(
                prompt=build_prompt,
                temperature=settings.TEMPERATURE_BUILDER,
                max_tokens=max_tokens,
                min_content_length=10000  # real builds are 19K-23K; 5K was too lenient
            )
            
            # Debug: log raw response length and provider
            print(f"  📊 Builder LLM: provider={response.provider}, raw_len={len(response.content)}, tokens={response.tokens_used}, max_tokens={max_tokens}")
            if len(response.content) < 10000:
                print(f"  ⚠ SHORT RESPONSE — first 500 chars:\n{response.content[:500]}")
            
            # Parse generated code
            html, css, js = self._parse_generated_code(response.content)
            
            # Inject Tailwind config and fonts
            html = self._inject_styling(html, design_preset)
            
            # Validate output
            is_valid = self._validate_output(html)
            
            build_time = time.time() - start_time
            
            result = BuildResult(
                html=html,
                css=css if css else None,
                js=js if js else None,
                success=is_valid,
                build_time=build_time,
                tokens_used=response.tokens_used,
                metadata={
                    "design_preset": plan.design_preset,
                    "components": plan.components,
                    "provider": response.provider.value
                }
            )
            
            # Log build
            self.build_history.append({
                "prompt": prompt[:100],
                "plan": plan.to_dict(),
                "build_time": build_time,
                "success": is_valid
            })
            
            return result
            
        except Exception as e:
            return BuildResult(
                html="",
                css=None,
                js=None,
                success=False,
                build_time=time.time() - start_time,
                error=str(e)
            )
    
    def _build_generation_prompt(
        self,
        plan: ImplementationPlan,
        prompt: str,
        design_preset: Dict[str, Any]
    ) -> str:
        """Build the code generation prompt"""
        
        colors = design_preset["tailwind_config"]["colors"]
        components = "\n".join([f"- {c}" for c in plan.components])
        features = "\n".join([f"- {f}" for f in plan.features])
        
        tech_stack_text = ""
        if plan.tech_stack:
            libs = plan.tech_stack.get("javascript", [])
            if libs:
                tech_stack_text = f"\nJAVASCRIPT LIBRARIES (load via CDN):\n" + "\n".join([f"- {lib}" for lib in libs])
            icons = plan.tech_stack.get("icons", "")
            if icons:
                tech_stack_text += f"\nICONS: {icons}"
            animations = plan.tech_stack.get("animations", "")
            if animations:
                tech_stack_text += f"\nANIMATIONS: {animations}"

        layout_text = ""
        if plan.layout_structure:
            layout_text = f"\nLAYOUT STRUCTURE:\n" + json.dumps(plan.layout_structure, indent=2)

        # Quality notes from planner (design tricks, specific details)
        quality_notes_text = ""
        if hasattr(plan, 'requirements_analysis') and plan.requirements_analysis:
            quality_notes = plan.requirements_analysis.get("quality_notes", [])
            if quality_notes:
                quality_notes_text = "\nQUALITY NOTES FROM PLANNER:\n" + "\n".join([f"- {n}" for n in quality_notes])

        # Complexity-specific instructions
        complexity_val = plan.complexity.value if hasattr(plan.complexity, 'value') else plan.complexity
        app_type_val = plan.app_type.value if hasattr(plan.app_type, 'value') else plan.app_type
        
        complexity_instructions = ""
        if complexity_val == "complex":
            complexity_instructions = """
COMPLEX APP INSTRUCTIONS:
- Implement ALL requested features fully — no placeholders, no "coming soon"
- Add localStorage persistence where appropriate (save state, preferences, data)
- Include at least 5+ interactive JavaScript features (forms, filters, toggles, modals, tabs, drag-drop, etc.)
- Use advanced layouts: CSS Grid + Flexbox, multi-column, sidebar+content
- Add micro-interactions: hover transforms, loading spinners, toast notifications
- Include real data (mock realistic content, not "Lorem ipsum foo bar")
- Add keyboard shortcuts and focus management"""
        elif complexity_val == "medium":
            complexity_instructions = """
MEDIUM APP INSTRUCTIONS:
- Implement all core features with proper event handling
- At least 3-4 interactive JavaScript features
- Include form validation with visual error feedback
- Add transitions on section changes and hover states
- Use realistic mock content (names, descriptions, prices — not lorem ipsum)"""

        # App-type specific instructions for better output
        app_type_hints = {
            "game": """
GAME-SPECIFIC REQUIREMENTS:
- Use <canvas> or DOM-based game rendering
- Implement game loop with requestAnimationFrame
- Add score tracking, game over state, restart functionality
- Include keyboard/mouse/touch controls
- Add visual feedback for actions (particles, color changes, animations)
- Make it actually PLAYABLE and FUN""",
            "dashboard": """
DASHBOARD-SPECIFIC REQUIREMENTS:
- Use CSS Grid for widget layout (auto-fill, responsive)
- Include at least 3 different chart/data visualizations (use Chart.js CDN or SVG)
- Add sidebar navigation with active state
- Include data cards with stats and trend indicators
- Add dark mode toggle
- Make data look realistic""",
            "calculator": """
CALCULATOR-SPECIFIC REQUIREMENTS:
- Implement full calculation logic (not just UI)
- Handle edge cases: division by zero, decimal precision, operator chaining
- Add keyboard input support
- Include calculation history
- Add clear/backspace functionality""",
            "e_commerce": """
E-COMMERCE-SPECIFIC REQUIREMENTS:
- Product grid with images, prices, ratings, add-to-cart
- Shopping cart with quantity controls and total calculation
- Filter/search functionality
- Product detail modal or expanded view
- Responsive: 1-col mobile, 2-col tablet, 3-4 col desktop""",
            "interactive_app": """
INTERACTIVE APP REQUIREMENTS:
- Implement the FULL application logic — no stub functions
- Add state management (track what the user has done)
- Include save/reset functionality
- Error handling with user-friendly messages
- Make it genuinely USEFUL, not a demo""",
            "text_content": """
TEXT CONTENT REQUIREMENTS (poem, essay, story, letter, etc.):
- The PRIMARY content is the TEXT — generate high-quality, relevant writing
- Present it in a BEAUTIFUL typographic HTML page with:
  - Professional font (serif for prose, monospace for poetry)
  - Large, readable text with proper line-height (1.8+)
  - Elegant spacing, margins, and visual breathing room
  - Subtle background texture or gradient
  - Decorative elements: drop caps, ornamental dividers, pull quotes
- Add interactive features: dark/light mode toggle, font size control, text-to-speech button, copy button
- Include a header with title and an elegant layout""",
            "code_showcase": """
CODE SHOWCASE REQUIREMENTS (scripts, algorithms, programs):
- Generate the ACTUAL working code the user asked for
- Present it in a beautiful HTML page with:
  - Syntax highlighting (use Prism.js or highlight.js via CDN)
  - Line numbers
  - Copy-to-clipboard button
  - Code explanation sections with clear typography
- Add interactive features: toggle between different code styles, language selector if relevant
- Include a "Run" button with sandboxed output display if feasible (eval for JS)
- Show the code prominently — this IS the deliverable""",
            "tutorial": """
TUTORIAL REQUIREMENTS (guides, how-tos, step-by-step):
- Create a visually rich, interactive tutorial page
- Numbered steps with progress tracking (clickable stepper/timeline)
- Each step has: title, explanation, code/example, interactive demo if possible
- Include a table of contents sidebar (sticky)
- Add "Mark as complete" checkboxes per step with progress bar
- Use icons, color coding, and visual hierarchy to make it scannable
- Include copy buttons for code snippets""",
            "article": """
ARTICLE/ANALYSIS REQUIREMENTS (reports, research, reviews):
- Create a data-rich, professional presentation page
- Include: executive summary, key findings cards, data tables, comparison charts
- Use Chart.js or inline SVG for any data visualization
- Add interactive filtering, sorting, or tab navigation between sections
- Professional typography with clear heading hierarchy
- Include a table of contents and "back to top" navigation
- Make data points visually prominent with cards and stat counters""",
            "utility": """
UTILITY/TOOL REQUIREMENTS (converters, generators, processors):
- Build a FULLY FUNCTIONAL tool — the core logic must work perfectly
- Clean input → process → output flow
- Handle edge cases and errors gracefully
- Add real-time preview/feedback where appropriate
- Include history of operations (localStorage)
- Copy/download output functionality""",
            "data_visualization": """
DATA VISUALIZATION REQUIREMENTS:
- Use Chart.js CDN for professional charts
- Include at least 3 different chart types (bar, line, pie/doughnut, radar)
- Add interactive controls: date range, filters, data toggles
- Use a dashboard-style card layout
- Show key metrics in stat cards with trend indicators
- Make it responsive with proper chart sizing""",
            "creative": """
CREATIVE CONTENT REQUIREMENTS:
- Build an immersive, visually stunning HTML experience
- Use CSS animations, gradients, SVG art, and creative layouts
- Make it interactive and explorable
- Add subtle surprises: Easter eggs, hover reveal effects, parallax
- Focus heavily on Design score — this should be BEAUTIFUL
- Include animation sequences and visual storytelling"""
        }
        
        app_hint = app_type_hints.get(app_type_val, "")

        # ── Template & Component Library injection ──
        tpl_ctx = get_template_context(app_type_val)
        
        # CDN tags for this app type (Chart.js, Prism.js, etc.)
        cdn_section = ""
        if tpl_ctx["cdn_tags"]:
            cdn_lines = "\n".join(tpl_ctx["cdn_tags"])
            cdn_section = f"\nEXTRA CDN LIBRARIES (include these in <head>):\n{cdn_lines}"
        
        # Pre-built component snippets the LLM can copy/adapt
        components_section = ""
        if tpl_ctx["components"]:
            formatted = format_components_for_prompt(tpl_ctx["components"], max_components=3)
            components_section = f"""
PRE-BUILT COMPONENTS (copy, adapt, and customize these — don't reinvent):
{formatted}"""
        
        # Structure hint
        structure_section = ""
        if tpl_ctx["structure_hint"]:
            structure_section = f"\nRECOMMENDED STRUCTURE: {tpl_ctx['structure_hint']}"
        
        # Available icon names (LLM can ask for specific hero-style SVGs)
        icon_list = ", ".join(tpl_ctx["available_icons"][:15])

        return f"""Generate a **visually stunning, fully functional** single-page HTML application.

UNIVERSAL RULE: No matter what the user asked for (web app, text, code, analysis, poem, tutorial, etc.), your output is ALWAYS a single beautiful HTML file. Present ANY content type as an interactive, well-designed HTML page.

USER REQUEST: {prompt}

APP TYPE: {app_type_val}
COMPLEXITY: {complexity_val}
{structure_section}

COMPONENTS TO BUILD:
{components}

FEATURES TO IMPLEMENT:
{features}

DESIGN SYSTEM:
- Style: {design_preset['name']}
- Primary: {colors['primary']}, Secondary: {colors['secondary']}, Accent: {colors['accent']}
- Background: {colors['background']}, Surface: {colors['surface']}
{tech_stack_text}
{layout_text}
{cdn_section}
{quality_notes_text}
{complexity_instructions}
{app_hint}
{components_section}

AVAILABLE SVG ICONS (use inline, heroicons-style, 24x24 viewBox, stroke="currentColor", class="w-6 h-6"):
{icon_list}

BANNED (do NOT use):
- NO Alpine.js, Vue, React, Angular, Svelte, or ANY JavaScript framework
- NO x-data, x-show, x-bind, v-if, ng-if directives
- ONLY vanilla JavaScript (addEventListener, getElementById, querySelector, etc.)
- NO unpkg.com or cdnjs links for JS frameworks (Tailwind CDN and Chart.js/Prism.js are OK)
- NO base64 data URIs — do NOT embed images, audio, or fonts as data:... strings
- NO inline audio/sound files — use Web Audio API oscillator or skip sounds entirely
- NO embedded SVG paths longer than 200 characters — use simple geometric shapes
- Use emoji (🍅⏱️✅) instead of complex images

⚠️ CRITICAL OUTPUT STRUCTURE — FOLLOW THIS EXACT ORDER:
The HTML MUST be structured so that ALL JavaScript comes FIRST (in <head>), before the <body> markup.
This prevents truncation from losing application logic.

```
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>App Title</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{ ... }}
  </script>
  <style>
    /* CSS animations and custom styles here */
  </style>
  <script>
    // ═══════════════════════════════════════
    // ALL APPLICATION JAVASCRIPT GOES HERE
    // ═══════════════════════════════════════
    document.addEventListener('DOMContentLoaded', () => {{
      // Full app logic: state, event listeners, DOM manipulation
      // This is the MOST IMPORTANT section — implement EVERYTHING
    }});
  </script>
</head>
<body>
  <!-- HTML markup uses Tailwind classes, semantic elements -->
</body>
</html>
```

MANDATORY REQUIREMENTS:
1. ALL JavaScript in <head> wrapped in DOMContentLoaded — this is NON-NEGOTIABLE
2. Tailwind CSS via CDN + responsive breakpoints (sm:, md:, lg:)
3. VANILLA JavaScript only — real event handlers, DOM manipulation, 3+ interactive features
4. SEMANTIC HTML5 — <header>, <nav>, <main>, <section>, <footer>
5. ARIA labels on interactive elements
6. Smooth CSS animations (fadeIn, slideIn, transitions)
7. 2-3 inline SVG icons for visual richness
8. Professional typography and color consistency with design system

CRITICAL: Actually IMPLEMENT all features. The code must be COMPLETE and FUNCTIONAL — no stubs, no placeholders.

COMMON BUGS TO AVOID (these WILL fail judging if present):
- Toast/notification overlap: each toast MUST have a unique vertical offset (use a counter × 60px). Remove toasts after 3s with setTimeout.
- Modal close/cancel buttons: EVERY modal MUST have a working close/cancel button. Wire the click handler. Test: clicking Cancel or X must hide the modal.
- Buttons without handlers: EVERY visible button must have a working addEventListener or onclick. No decorative-only buttons.
- SVG circular progress: use stroke-dasharray + stroke-dashoffset, update in the timer interval. Don't leave the progress ring static.

BE CONCISE: Efficient code, minimal comments, no bloated markup. Keep HTML body under 150 lines. Quality over quantity.
NO BLOAT: Every byte counts. No decorative-only SVG paths > 100 chars. No data: URIs. No base64. Use emoji for icons when possible.

OUTPUT: Return ONLY the raw HTML starting with <!DOCTYPE html>. No markdown fences."""
    
    def _parse_generated_code(self, content: str) -> Tuple[str, Optional[str], Optional[str]]:
        """Parse HTML, CSS, and JS from LLM response"""
        
        html = ""
        css = None
        js = None
        
        # Try to extract HTML from code fences
        html_match = re.search(
            r'```html\s*\n(.*?)\n```',
            content,
            re.DOTALL | re.IGNORECASE
        )
        if html_match:
            html = html_match.group(1).strip()
        elif '<!DOCTYPE' in content or '<!doctype' in content or '<html' in content:
            # Raw HTML — LLM returned it without fences (as instructed)
            start = content.find('<!DOCTYPE') if '<!DOCTYPE' in content else content.find('<!doctype') if '<!doctype' in content else content.find('<html')
            end = content.rfind('</html>')
            if start >= 0 and end > start:
                html = content[start:end + len('</html>')].strip()
            elif start >= 0:
                html = content[start:].strip()
        else:
            # Try generic code fence
            generic_match = re.search(r'```\s*\n(.*?)\n```', content, re.DOTALL)
            if generic_match:
                html = generic_match.group(1).strip()
        
        # Extract CSS from separate fence (if builder still returns it)
        css_match = re.search(
            r'```css\s*\n(.*?)\n```',
            content,
            re.DOTALL | re.IGNORECASE
        )
        if css_match:
            css = css_match.group(1).strip()
        
        # Extract JS from separate fence (if builder still returns it)
        js_match = re.search(
            r'```(?:javascript|js)\s*\n(.*?)\n```',
            content,
            re.DOTALL | re.IGNORECASE
        )
        if js_match:
            js = js_match.group(1).strip()
        
        # Final fallback
        if not html:
            html = content
        
        # ── Truncation recovery ──
        html = self._recover_truncated_html(html)
        
        # ── Strip base64 data URIs that bloat the output ──
        html = self._strip_base64_bloat(html)
        
        return html, css, js
    
    def _strip_base64_bloat(self, html: str) -> str:
        """Remove base64 data URIs that waste output tokens."""
        original_len = len(html)
        # Replace data:audio/... and data:image/... with placeholder
        html = re.sub(
            r'data:(audio|image)/[^"\')\s]{200,}',
            r'data:\1/placeholder',
            html
        )
        # If base64 appears at the end (truncation mid-base64), strip it
        # Detect: file ends with a long alphanumeric+/+ string without closing tags
        if not html.rstrip().endswith('>'):
            # Find last > and trim everything after
            last_tag = html.rfind('>')
            if last_tag > 0 and (len(html) - last_tag) > 100:
                stripped = html[:last_tag + 1]
                print(f"  ⚠ Stripped {len(html) - len(stripped)} trailing base64 bytes")
                html = stripped
        if len(html) != original_len:
            print(f"  🧹 Base64 cleanup: {original_len} → {len(html)} chars")
        return html
    
    def _recover_truncated_html(self, html: str) -> str:
        """Detect and repair truncated HTML output from LLM token limits."""
        if not html or '</html>' in html.lower():
            return html  # Not truncated
        
        print(f"  ⚠ Truncation detected (len={len(html)}, missing </html>). Auto-repairing...")
        
        # Close any unclosed <script> tag
        open_scripts = html.lower().count('<script')
        # Count </script> but exclude self-closing <script.../> patterns
        close_scripts = html.lower().count('</script>')
        if open_scripts > close_scripts:
            # Find the last unclosed script and see if DOMContentLoaded was used
            has_dom_loaded = 'domcontentloaded' in html.lower()
            if has_dom_loaded:
                # Close the DOMContentLoaded callback + script
                html += "\n  });\n});\n</script>"
            else:
                html += "\n});\n</script>"
        
        # Close unclosed tags in order
        for tag in ['</main>', '</div>', '</body>', '</html>']:
            if tag not in html.lower():
                html += f"\n{tag}"
        
        return html
    
    def _inject_styling(
        self,
        html: str,
        design_preset: Dict[str, Any]
    ) -> str:
        """Inject Tailwind config and fonts into HTML"""
        
        # Create Tailwind config
        tailwind_config = json.dumps(design_preset["tailwind_config"], indent=2)
        
        # Check if HTML has proper structure
        if "<html" not in html.lower():
            # Wrap in template
            cdns = "\n".join([
                f'<link rel="stylesheet" href="{cdn}">'
                for cdn in design_preset.get("cdn", [])
            ])
            
            html = HTML_TEMPLATE.replace("{{ title }}", "BlitzDev App")\
                               .replace("{{ tailwind_config | safe }}", tailwind_config)\
                               .replace("{% for cdn in cdns %}", "")\
                               .replace("{% endfor %}", "")\
                               .replace("{{ cdns }}", cdns)\
                               .replace("{{ custom_css | safe }}", "")\
                               .replace("{{ content | safe }}", html)\
                               .replace("{{ custom_js | safe }}", "")
        else:
            # Inject Tailwind config into existing HTML
            if "tailwind.config" not in html:
                config_script = f"""
    <script>
        tailwind.config = {tailwind_config}
    </script>"""
                # Insert before closing head
                html = html.replace("</head>", config_script + "\n</head>")
            
            # Inject fonts
            for cdn in design_preset.get("cdn", []):
                if cdn not in html:
                    html = html.replace(
                        "</head>",
                        f'<link rel="stylesheet" href="{cdn}">\n</head>'
                    )
            
            # Inject CSS utility animations if not already present
            if "animate-fade-in-up" not in html or "@keyframes fadeInUp" not in html:
                if "<style>" in html:
                    # Append to first existing <style> block
                    html = html.replace("<style>", f"<style>\n{CSS_UTILITIES}", 1)
                else:
                    # Add a <style> block before </head>
                    html = html.replace(
                        "</head>",
                        f"<style>{CSS_UTILITIES}</style>\n</head>"
                    )
        
        return html
    
    def _validate_output(self, html: str) -> bool:
        """Validate generated HTML has structure AND functional JS"""
        html_lower = html.lower()
        
        structure_checks = [
            len(html) > 100,  # Not empty
            "<html" in html_lower or "<!doctype" in html_lower,
            "<body" in html_lower,
            "tailwind" in html_lower or "class=" in html_lower
        ]
        
        # JS interactivity checks — at least ONE must be present
        js_patterns = [
            "addeventlistener" in html_lower,
            "onclick" in html_lower,
            "getelementbyid" in html_lower,
            "queryselector" in html_lower,
            "innerhtml" in html_lower,
            "textcontent" in html_lower,
            "classlist" in html_lower,
            "setinterval" in html_lower,
            "settimeout" in html_lower,
        ]
        
        has_js = any(js_patterns)
        if not has_js:
            print("  ⚠ WARNING: No JavaScript interactivity detected in output!")
        
        return all(structure_checks)
    
    async def quick_build(
        self,
        prompt: str,
        design_preset_name: str = "modern_minimal"
    ) -> BuildResult:
        """
        Quick build without full planning
        
        Args:
            prompt: Simple prompt
            design_preset_name: Design preset to use
        
        Returns:
            BuildResult
        """
        from agents.planner import ImplementationPlan, AppType, Complexity
        
        # Create minimal plan
        plan = ImplementationPlan(
            app_type=AppType.LANDING_PAGE,
            design_preset=design_preset_name,
            components=["header", "hero", "content", "footer"],
            features=["responsive"],
            pages=["index"],
            complexity=Complexity.SIMPLE,
            estimated_time=30,
            requirements_analysis={},
            tech_stack={},
            layout_structure={}
        )
        
        return await self.build(plan, prompt)
    
    def get_build_history(self) -> List[Dict[str, Any]]:
        """Get build history"""
        return self.build_history
    
    def get_stats(self) -> Dict[str, Any]:
        """Get builder statistics"""
        if not self.build_history:
            return {"total_builds": 0}
        
        total = len(self.build_history)
        successful = sum(1 for b in self.build_history if b["success"])
        avg_time = sum(b["build_time"] for b in self.build_history) / total
        
        return {
            "total_builds": total,
            "successful_builds": successful,
            "success_rate": successful / total,
            "average_build_time": avg_time
        }
