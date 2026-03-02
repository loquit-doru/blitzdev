"""
Planner Agent for BlitzDev
Analyzes prompts and creates implementation plans
"""

import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings, DESIGN_PRESETS, AGENT_PROMPTS
from utils.llm_manager import get_llm_manager, LLMResponse


class AppType(str, Enum):
    """Types of applications — covers ANY prompt type"""
    LANDING_PAGE = "landing_page"
    DASHBOARD = "dashboard"
    PORTFOLIO = "portfolio"
    E_COMMERCE = "e_commerce"
    BLOG = "blog"
    DOCUMENTATION = "documentation"
    INTERACTIVE_APP = "interactive_app"
    GAME = "game"
    CALCULATOR = "calculator"
    FORM_WIZARD = "form_wizard"
    # Universal types for non-web prompts
    TEXT_CONTENT = "text_content"        # poems, essays, stories, letters
    CODE_SHOWCASE = "code_showcase"      # code generation, algorithms, scripts
    TUTORIAL = "tutorial"                # how-to guides, step-by-step
    ARTICLE = "article"                  # analysis, reports, research
    UTILITY = "utility"                  # tools, converters, generators
    DATA_VISUALIZATION = "data_visualization"  # charts, graphs, infographics
    CREATIVE = "creative"                # art, design concepts, brainstorming


class Complexity(str, Enum):
    """Complexity levels"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class ImplementationPlan:
    """Complete implementation plan"""
    app_type: AppType
    design_preset: str
    components: List[str]
    features: List[str]
    pages: List[str]
    complexity: Complexity
    estimated_time: int
    requirements_analysis: Dict[str, Any]
    tech_stack: Dict[str, Any]
    layout_structure: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "app_type": self.app_type.value if isinstance(self.app_type, Enum) else self.app_type,
            "design_preset": self.design_preset,
            "components": self.components,
            "features": self.features,
            "pages": self.pages,
            "complexity": self.complexity.value if isinstance(self.complexity, Enum) else self.complexity,
            "estimated_time": self.estimated_time,
            "requirements_analysis": self.requirements_analysis,
            "tech_stack": self.tech_stack,
            "layout_structure": self.layout_structure
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImplementationPlan":
        """Create from dictionary"""
        # Gracefully handle unknown app_type values from LLM
        try:
            app_type = AppType(data.get("app_type", "interactive_app"))
        except ValueError:
            app_type = AppType.INTERACTIVE_APP
        
        try:
            complexity = Complexity(data.get("complexity", "medium"))
        except ValueError:
            complexity = Complexity.MEDIUM
        
        return cls(
            app_type=app_type,
            design_preset=data.get("design_preset", "modern_minimal"),
            components=data.get("components", []),
            features=data.get("features", []),
            pages=data.get("pages", ["index"]),
            complexity=complexity,
            estimated_time=data.get("estimated_time", 60),
            requirements_analysis=data.get("requirements_analysis", {}),
            tech_stack=data.get("tech_stack", {}),
            layout_structure=data.get("layout_structure", {})
        )


class PlannerAgent:
    """
    Agent responsible for analyzing prompts and creating
    detailed implementation plans
    """
    
    def __init__(self):
        self.llm = get_llm_manager()
        self.system_prompt = AGENT_PROMPTS["planner"]
        self.plan_history: List[Dict[str, Any]] = []
    
    async def analyze_prompt(
        self,
        prompt: str,
        requirements: Optional[Dict[str, Any]] = None
    ) -> ImplementationPlan:
        """
        Analyze user prompt and create implementation plan
        
        Args:
            prompt: User's mystery prompt
            requirements: Additional requirements
        
        Returns:
            ImplementationPlan with complete strategy
        """
        start_time = time.time()
        
        # Build analysis prompt
        analysis_prompt = self._build_analysis_prompt(prompt, requirements)
        
        # Get LLM response
        response = await self.llm.generate(
            prompt=analysis_prompt,
            temperature=settings.TEMPERATURE_PLANNER,
            system_prompt=self.system_prompt
        )
        
        # Parse response
        plan_data = self._parse_plan_response(response)
        
        # Enhance with additional analysis
        plan_data = await self._enhance_plan(plan_data, prompt)
        
        plan = ImplementationPlan.from_dict(plan_data)
        
        # Log plan
        self.plan_history.append({
            "prompt": prompt[:100],
            "plan": plan.to_dict(),
            "generation_time": time.time() - start_time
        })
        
        return plan
    
    def _build_analysis_prompt(
        self,
        prompt: str,
        requirements: Optional[Dict[str, Any]]
    ) -> str:
        """Build the analysis prompt for LLM"""
        
        design_presets_list = "\n".join([
            f"- {k}: {v['description']}"
            for k, v in DESIGN_PRESETS.items()
        ])
        
        req_text = ""
        if requirements:
            req_text = f"\nAdditional Requirements:\n{json.dumps(requirements, indent=2)}"
        
        return f"""Analyze this prompt and create a DETAILED implementation plan that will maximize quality scores.
Think like a senior frontend architect planning a hackathon-winning entry.

IMPORTANT: The output is ALWAYS a single self-contained HTML file. Even if the prompt asks for text, code, analysis, or other non-visual content, you MUST plan it as a beautiful HTML presentation. For example:
- "Write a poem" → plan a gorgeous typographic HTML page displaying the poem with animations
- "Generate a Python script" → plan an HTML page with syntax-highlighted code, copy button, and explanation
- "Analyze market trends" → plan an HTML dashboard with charts, cards, and data visualization
- "Create a tutorial" → plan a step-by-step HTML guide with interactive sections

PROMPT: {prompt}{req_text}

Available Design Presets:
{design_presets_list}

Respond with a JSON object (no markdown fences, just raw JSON):
{{
    "app_type": "One of: landing_page, dashboard, portfolio, e_commerce, blog, documentation, interactive_app, game, calculator, form_wizard, text_content, code_showcase, tutorial, article, utility, data_visualization, creative",
    "design_preset": "Name of the most suitable design preset from the list above",
    "layout_structure": {{
        "header": "description of header/nav",
        "hero": "description of hero section",
        "sections": ["list of main content sections with descriptions"],
        "footer": "description of footer"
    }},
    "components": ["List of specific UI components (e.g. 'animated hero with gradient text', 'pricing card grid with hover effects')"],
    "features": ["List of interactive features (e.g. 'dark mode toggle', 'form validation with error messages', 'smooth scroll navigation')"],
    "tech_stack": {{
        "css": "Tailwind CSS via CDN",
        "icons": "inline SVG",
        "animations": "Tailwind transitions + CSS keyframes",
        "javascript": ["any CDN libraries if needed like chart.js, alpine.js"]
    }},
    "pages": ["List of pages/sections"],
    "complexity": "simple, medium, or complex",
    "estimated_time": 30,
    "quality_notes": ["specific design tricks to score high: gradients, micro-interactions, SVG icons, professional typography"]
}}

CRITICAL: The output is ALWAYS an HTML page. If the prompt doesn't obviously map to a web app, choose the most fitting app_type (text_content, code_showcase, tutorial, article, etc.) and plan a visually stunning HTML presentation of that content.

Be SPECIFIC and OPINIONATED. Vague plans produce vague code."""
    
    def _parse_plan_response(self, response: LLMResponse) -> Dict[str, Any]:
        """Parse LLM response into plan dictionary"""
        try:
            content = response.content
            
            # Use JSON repair engine for robust parsing
            from utils.json_repair import safe_parse_llm_json
            plan_data = safe_parse_llm_json(content)
            if not plan_data:
                return self._create_default_plan()
            
            # Validate required fields
            required = ["app_type", "design_preset", "components", "features"]
            for field in required:
                if field not in plan_data:
                    plan_data[field] = self._get_default_value(field)
            
            return plan_data
            
        except Exception as e:
            # Fallback to default plan
            return self._create_default_plan()
    
    async def _enhance_plan(
        self,
        plan_data: Dict[str, Any],
        original_prompt: str
    ) -> Dict[str, Any]:
        """Enhance plan with additional analysis — PRESERVE LLM-generated data"""
        
        # Add requirements analysis (always useful)
        plan_data["requirements_analysis"] = {
            "core_functionality": self._extract_core_functionality(original_prompt),
            "target_audience": self._infer_audience(original_prompt),
            "key_interactions": self._identify_interactions(original_prompt),
            "data_requirements": self._identify_data_needs(original_prompt),
            "quality_notes": plan_data.get("quality_notes", [])  # Preserve LLM quality_notes
        }
        
        # Only fill tech_stack/layout if LLM didn't provide them
        if not plan_data.get("tech_stack") or not isinstance(plan_data["tech_stack"], dict):
            plan_data["tech_stack"] = self._recommend_tech_stack(plan_data)
        
        if not plan_data.get("layout_structure") or not isinstance(plan_data["layout_structure"], dict):
            plan_data["layout_structure"] = self._suggest_layout(plan_data)
        
        return plan_data
    
    def _extract_core_functionality(self, prompt: str) -> str:
        """Extract core functionality from prompt"""
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ["calculator", "compute", "calculate"]):
            return "calculation_tool"
        elif any(word in prompt_lower for word in ["dashboard", "analytics", "chart", "visualization"]):
            return "data_visualization"
        elif any(word in prompt_lower for word in ["game", "play", "score", "puzzle"]):
            return "interactive_game"
        elif any(word in prompt_lower for word in ["form", "input", "submit", "survey"]):
            return "form_handler"
        elif any(word in prompt_lower for word in ["portfolio", "showcase", "gallery"]):
            return "content_showcase"
        elif any(word in prompt_lower for word in ["write", "poem", "essay", "story", "letter", "text"]):
            return "text_generation"
        elif any(word in prompt_lower for word in ["code", "script", "algorithm", "function", "program"]):
            return "code_generation"
        elif any(word in prompt_lower for word in ["tutorial", "guide", "how to", "steps", "learn"]):
            return "tutorial_guide"
        elif any(word in prompt_lower for word in ["analyze", "report", "research", "compare", "review"]):
            return "analysis_report"
        elif any(word in prompt_lower for word in ["convert", "transform", "generate", "tool", "utility"]):
            return "utility_tool"
        else:
            return "information_display"
    
    def _infer_audience(self, prompt: str) -> str:
        """Infer target audience"""
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ["business", "corporate", "professional", "enterprise"]):
            return "business_professionals"
        elif any(word in prompt_lower for word in ["kids", "children", "fun", "game", "play"]):
            return "children"
        elif any(word in prompt_lower for word in ["developer", "tech", "code", "api", "algorithm"]):
            return "developers"
        elif any(word in prompt_lower for word in ["student", "learn", "tutorial", "education"]):
            return "students"
        elif any(word in prompt_lower for word in ["creative", "art", "design", "writer"]):
            return "creatives"
        else:
            return "general_audience"
    
    def _identify_interactions(self, prompt: str) -> List[str]:
        """Identify key user interactions"""
        interactions = []
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ["click", "button", "press"]):
            interactions.append("button_clicks")
        if any(word in prompt_lower for word in ["input", "type", "enter"]):
            interactions.append("text_input")
        if any(word in prompt_lower for word in ["drag", "drop", "move"]):
            interactions.append("drag_drop")
        if any(word in prompt_lower for word in ["scroll", "navigate"]):
            interactions.append("scrolling")
        if any(word in prompt_lower for word in ["form", "submit"]):
            interactions.append("form_submission")
        
        return interactions if interactions else ["basic_navigation"]
    
    def _identify_data_needs(self, prompt: str) -> Dict[str, Any]:
        """Identify data/storage requirements"""
        prompt_lower = prompt.lower()
        
        needs = {
            "local_storage": any(word in prompt_lower for word in ["save", "store", "remember"]),
            "api_integration": any(word in prompt_lower for word in ["fetch", "api", "data", "load"]),
            "file_upload": any(word in prompt_lower for word in ["upload", "import", "file"]),
            "export": any(word in prompt_lower for word in ["export", "download", "save as"])
        }
        
        return needs
    
    def _recommend_tech_stack(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend technology stack"""
        app_type = plan_data.get("app_type", "interactive_app")
        complexity = plan_data.get("complexity", "medium")
        
        stack = {
            "frontend": ["HTML5", "Tailwind CSS"],
            "javascript": ["Vanilla JS"],
            "icons": "Lucide or Heroicons (via CDN)",
            "fonts": "Google Fonts"
        }
        
        # Add based on complexity
        if complexity in ["medium", "complex"]:
            stack["javascript"].append("GSAP (for animations)")
        
        if app_type in ["dashboard", "interactive_app", "data_visualization", "article"]:
            stack["javascript"].append("Chart.js (if charts needed)")
        
        if app_type == "game":
            stack["javascript"].append("Canvas API")
        
        if app_type in ["code_showcase", "tutorial"]:
            stack["javascript"].append("Prism.js (syntax highlighting)")
        
        if app_type in ["text_content", "article", "tutorial"]:
            stack["javascript"].append("marked.js (markdown rendering)")
        
        return stack
    
    def _suggest_layout(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest layout structure"""
        app_type = plan_data.get("app_type", "interactive_app")
        
        layouts = {
            "landing_page": {
                "header": "sticky navigation",
                "hero": "full-width with CTA",
                "sections": ["features", "testimonials", "cta"],
                "footer": "standard"
            },
            "dashboard": {
                "sidebar": "collapsible navigation",
                "header": "top bar with user info",
                "main": "widget grid layout",
                "footer": "minimal"
            },
            "portfolio": {
                "header": "minimal navigation",
                "hero": "intro with photo",
                "sections": ["projects", "skills", "contact"],
                "footer": "social links"
            },
            "text_content": {
                "header": "minimal with title",
                "main": "centered prose with max-width",
                "controls": "dark mode, font size, copy",
                "footer": "subtle attribution"
            },
            "code_showcase": {
                "header": "title and language badge",
                "main": "syntax-highlighted code block",
                "sidebar": "explanation and notes",
                "footer": "copy button and meta info"
            },
            "tutorial": {
                "header": "title and progress bar",
                "sidebar": "table of contents (sticky)",
                "main": "step-by-step content sections",
                "footer": "navigation (prev/next)"
            },
            "article": {
                "header": "title and key metrics cards",
                "main": "content sections with charts",
                "sidebar": "table of contents",
                "footer": "sources and references"
            },
            "data_visualization": {
                "header": "dashboard title and filters",
                "main": "chart grid with stat cards",
                "controls": "date range, data toggles",
                "footer": "data source attribution"
            }
        }
        
        return layouts.get(app_type, layouts.get("landing_page", {
            "header": "navigation",
            "main": "content area",
            "footer": "standard footer"
        }))
    
    def _get_default_value(self, field: str) -> Any:
        """Get default value for missing fields"""
        defaults = {
            "app_type": "interactive_app",
            "design_preset": "modern_minimal",
            "components": ["header", "main_content", "footer"],
            "features": ["responsive_design", "interactive_elements"],
            "pages": ["index"],
            "complexity": "medium",
            "estimated_time": 60
        }
        return defaults.get(field)
    
    def _create_default_plan(self) -> Dict[str, Any]:
        """Create default plan on parsing failure"""
        return {
            "app_type": "interactive_app",
            "design_preset": "modern_minimal",
            "components": ["header", "main_content", "features", "footer"],
            "features": ["responsive_design", "interactive_elements", "dark_mode_toggle"],
            "pages": ["index"],
            "complexity": "medium",
            "estimated_time": 60,
            "requirements_analysis": {},
            "tech_stack": {},
            "layout_structure": {}
        }
    
    def get_plan_history(self) -> List[Dict[str, Any]]:
        """Get history of created plans"""
        return self.plan_history
