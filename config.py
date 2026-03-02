"""
BlitzDev Configuration Module
Pydantic settings, design presets, and constants for Seedstr Hackathon Agent
"""

from typing import Dict, List, Optional, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum
from pathlib import Path


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    GROQ = "groq"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"


class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Application settings with Pydantic validation"""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
    
    # App Info
    APP_NAME: str = "BlitzDev"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: LogLevel = Field(default=LogLevel.INFO)
    
    # Seedstr API Configuration
    SEEDSTR_API_URL: str = Field(
        default="https://www.seedstr.io/api/v1",
        description="Seedstr API base URL (use www.seedstr.io to avoid redirect issues)"
    )
    SEEDSTR_API_URL_V2: str = Field(
        default="https://www.seedstr.io/api/v2",
        description="Seedstr API v2 base URL (for SWARM jobs)"
    )
    SEEDSTR_API_KEY: str = Field(
        default="",
        description="Seedstr API key for authentication"
    )
    SEEDSTR_POLL_INTERVAL: int = Field(
        default=3,
        description="Polling interval in seconds (3s for maximum speed)"
    )
    SEEDSTR_TIMEOUT: int = Field(
        default=300,
        description="Request timeout in seconds"
    )
    
    # LLM API Keys
    GROQ_API_KEY: str = Field(default="", description="Groq API key")
    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic API key")
    DEEPSEEK_API_KEY: str = Field(default="", description="DeepSeek API key")
    GOOGLE_API_KEY: str = Field(default="", description="Google AI (Gemini) API key")
    
    # LLM Configuration
    PRIMARY_LLM: LLMProvider = Field(default=LLMProvider.GROQ)
    FALLBACK_LLM: LLMProvider = Field(default=LLMProvider.DEEPSEEK)  # cheap fallback ($0.002)
    QUALITY_LLM: LLMProvider = Field(default=LLMProvider.GEMINI)  # FREE — fast, compact output, great at HTML/JS
    
    # Model Selection
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")
    ANTHROPIC_MODEL: str = Field(default="claude-sonnet-4-20250514")
    DEEPSEEK_MODEL: str = Field(default="deepseek-chat")
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash")
    
    # Generation Parameters
    MAX_TOKENS: int = Field(default=32768)
    TEMPERATURE_PLANNER: float = Field(default=0.7)
    TEMPERATURE_BUILDER: float = Field(default=0.5)
    TEMPERATURE_CRITIC: float = Field(default=0.3)
    
    # Output Configuration
    OUTPUT_DIR: Path = Field(default=Path("./output"))
    TEMP_DIR: Path = Field(default=Path("./temp"))
    MAX_ZIP_SIZE_MB: int = Field(default=10)
    
    # Evaluation Weights
    WEIGHT_FUNCTIONALITY: float = Field(default=0.50)
    WEIGHT_DESIGN: float = Field(default=0.30)
    WEIGHT_SPEED: float = Field(default=0.20)
    
    # Quality Thresholds
    MIN_QUALITY_SCORE: float = Field(default=80.0)
    MAX_RETRY_ATTEMPTS: int = Field(default=5)
    
    @field_validator("OUTPUT_DIR", "TEMP_DIR", mode="before")
    @classmethod
    def validate_path(cls, v: Any) -> Path:
        """Ensure paths are Path objects"""
        if isinstance(v, str):
            return Path(v)
        return v


# Design Presets for Web Applications
DESIGN_PRESETS: Dict[str, Dict[str, Any]] = {
    "modern_minimal": {
        "name": "Modern Minimal",
        "description": "Clean, minimalist design with focus on content",
        "tailwind_config": {
            "colors": {
                "primary": "#0f172a",
                "secondary": "#64748b",
                "accent": "#3b82f6",
                "background": "#ffffff",
                "surface": "#f8fafc"
            },
            "fontFamily": {
                "sans": ["Inter", "system-ui", "sans-serif"]
            }
        },
        "cdn": [
            "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
        ]
    },
    "dark_cyberpunk": {
        "name": "Dark Cyberpunk",
        "description": "Neon-accented dark theme with futuristic vibes",
        "tailwind_config": {
            "colors": {
                "primary": "#00ff9f",
                "secondary": "#00b8ff",
                "accent": "#ff00ff",
                "background": "#0a0a0f",
                "surface": "#12121a"
            },
            "fontFamily": {
                "sans": ["Orbitron", "Rajdhani", "system-ui", "sans-serif"]
            }
        },
        "cdn": [
            "https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700&family=Rajdhani:wght@300;400;500;600;700&display=swap"
        ]
    },
    "warm_organic": {
        "name": "Warm Organic",
        "description": "Warm, approachable design with earth tones",
        "tailwind_config": {
            "colors": {
                "primary": "#92400e",
                "secondary": "#d97706",
                "accent": "#f59e0b",
                "background": "#fffbeb",
                "surface": "#fef3c7"
            },
            "fontFamily": {
                "sans": ["Nunito", "system-ui", "sans-serif"]
            }
        },
        "cdn": [
            "https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;500;600;700&display=swap"
        ]
    },
    "corporate_pro": {
        "name": "Corporate Pro",
        "description": "Professional, business-oriented design",
        "tailwind_config": {
            "colors": {
                "primary": "#1e40af",
                "secondary": "#3b82f6",
                "accent": "#60a5fa",
                "background": "#ffffff",
                "surface": "#eff6ff"
            },
            "fontFamily": {
                "sans": ["Roboto", "system-ui", "sans-serif"]
            }
        },
        "cdn": [
            "https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap"
        ]
    },
    "playful_colorful": {
        "name": "Playful Colorful",
        "description": "Vibrant, playful design for creative projects",
        "tailwind_config": {
            "colors": {
                "primary": "#7c3aed",
                "secondary": "#ec4899",
                "accent": "#fbbf24",
                "background": "#faf5ff",
                "surface": "#f3e8ff"
            },
            "fontFamily": {
                "sans": ["Poppins", "system-ui", "sans-serif"]
            }
        },
        "cdn": [
            "https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap"
        ]
    }
}

# HTML Templates
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{ tailwind_config | safe }}
    </script>
    {% for cdn in cdns %}
    <link rel="stylesheet" href="{{ cdn }}">
    {% endfor %}
    <style>
        {{ custom_css | safe }}
    </style>
</head>
<body class="bg-background text-primary min-h-screen">
    {{ content | safe }}
    <script>
        {{ custom_js | safe }}
    </script>
</body>
</html>"""

# Evaluation Criteria
EVALUATION_CRITERIA = {
    "functionality": {
        "weight": 0.50,
        "subcriteria": {
            "code_validity": 0.30,  # HTML/CSS/JS valid
            "interactivity": 0.25,   # Interactive elements work
            "responsiveness": 0.25,  # Mobile-friendly
            "completeness": 0.20     # All features implemented
        }
    },
    "design": {
        "weight": 0.30,
        "subcriteria": {
            "visual_appeal": 0.35,
            "consistency": 0.25,
            "typography": 0.20,
            "color_harmony": 0.20
        }
    },
    "speed": {
        "weight": 0.20,
        "subcriteria": {
            "generation_time": 0.50,
            "render_efficiency": 0.30,
            "code_optimization": 0.20
        }
    }
}

# Agent System Prompts
AGENT_PROMPTS = {
    "planner": """You are the Planner Agent for BlitzDev — an AI agent competing in a hackathon.
Your job: analyze ANY user request and produce a DETAILED implementation plan that maximizes scores on Functionality, Design, and Speed.

CRITICAL: The output is ALWAYS a single self-contained HTML file. Even if the user asks for text, code, analysis, or other non-visual content, you MUST plan it as a beautiful HTML presentation. Examples:
- "Write a poem about nature" → plan a gorgeous typographic HTML page with the poem, decorative elements, dark/light mode
- "Generate a sorting algorithm" → plan an HTML page with syntax-highlighted code, copy button, explanation, and interactive demo
- "Analyze the pros and cons of X" → plan a dashboard-style HTML page with comparison cards, charts, and interactive tabs
- "Create a tutorial about Y" → plan a step-by-step interactive HTML guide with progress tracking

Think like a senior frontend architect. The plan must enable a builder agent to generate EXCELLENT code in one shot.

CRITICAL RULES:
- For ANY request: decide the best HTML presentation format to maximize Functionality + Design + Speed scores
- For complex requests (games, dashboards, calculators): specify EVERY feature and interaction in detail
- For text content (poems, essays, stories): specify typography, layout, interactive features (dark mode, font controls)
- For code requests: specify syntax highlighting library, copy buttons, interactive demos
- For analysis/reports: specify chart types, data layout, comparison cards
- tech_stack.javascript: list specific CDN libraries needed (e.g. ["chart.js", "marked.js", "prism.js", "highlight.js"])
- quality_notes: list 5+ specific design tricks (gradients, glassmorphism, animated counters, particle effects, etc.)

Output a JSON object with:
- "app_type": Type (landing_page, dashboard, portfolio, e_commerce, game, calculator, interactive_app, text_content, code_showcase, tutorial, article, utility, data_visualization, creative, form_wizard, blog, documentation)
- "design_preset": One of: modern_minimal, dark_cyberpunk, warm_organic, corporate_pro, playful_colorful
- "layout": Detailed layout description — what goes where. Be SPECIFIC.
- "components": List of specific UI components
- "features": List of ALL interactive features (ALWAYS include at least 3: dark mode, responsive nav, copy buttons, etc.)
- "tech_stack": { "css": "Tailwind CDN", "javascript": ["library1", "library2"], "icons": "inline SVG", "animations": "Tailwind + CSS keyframes" }
- "layout_structure": { "header": "...", "main": "...", "sidebar": "...", "footer": "..." }
- "pages": List of pages/sections
- "color_scheme": { primary, secondary, accent, background }
- "complexity": "simple", "medium", or "complex"
- "estimated_time": Estimated generation time in seconds
- "quality_notes": List of 5+ specific design/UX details for high scores

Be SPECIFIC and OPINIONATED — vague plans produce vague code. Every feature the user mentions must appear in the plan.""",

    "builder": """You are the Builder Agent for BlitzDev — competing in a hackathon judged by AI on Functionality, Design, and Speed.
Your goal: generate a SINGLE self-contained HTML file that scores 90+/100 on all three criteria.

YOU ARE BEING SCORED. Missing requirements = low score = FAILURE.

UNIVERSAL RULE: No matter what the user asks for (web app, text, code, analysis, game, art), your output is ALWAYS a beautiful, interactive HTML page. If the request is for text/code/analysis, create a stunning HTML presentation of that content.

MANDATORY HTML STRUCTURE:
1. <!DOCTYPE html> with lang="en"
2. <meta charset="UTF-8"> and viewport meta tag
3. Tailwind CSS via CDN: <script src="https://cdn.tailwindcss.com"></script>
4. Custom Tailwind config: <script>tailwind.config = { theme: { extend: { ... } } }</script>
5. Semantic HTML5: <header>, <nav>, <main>, <section>, <article>, <footer>
6. Google Fonts import for professional typography

MANDATORY FUNCTIONALITY:
7. ALL requested features must ACTUALLY WORK — no placeholder buttons, no TODO comments
8. Interactive JavaScript with addEventListener (NOT inline onclick attributes)
9. At least 3 interactive features (dark mode toggle, copy buttons, responsive nav, filters, modals, etc.)
10. State management: track user interactions, save to localStorage where appropriate
11. Error handling: graceful degradation, user-friendly messages

MANDATORY DESIGN:
12. Responsive: sm:, md:, lg:, xl: breakpoints used throughout
13. 3+ real inline SVG icons (with actual path data, NOT empty tags)
14. Hover states on ALL clickable elements: hover:scale-105, hover:shadow-lg, hover:bg-opacity-*
15. Smooth transitions: transition-all duration-300 on every interactive element
16. Visual depth: shadows (shadow-md, shadow-lg), gradients (bg-gradient-to-r), rounded corners
17. Color: consistent design system palette, accent color for CTAs
18. Spacing: sections need py-16+, cards need p-6+, proper gap utilities
19. ARIA labels on all interactive elements

Output ONLY the complete HTML. No markdown fences. No explanations. Start with <!DOCTYPE html>.""",

    "critic": """You are the Critic Agent for BlitzDev — a STRICT quality judge.
You evaluate generated HTML applications on exactly the criteria used by hackathon AI judges.
The output is always an HTML page — even if the original prompt asked for text, code, or analysis.

Scoring dimensions (be PRECISE — each sub-score matters):
1. FUNCTIONALITY (50%):
   - Does it implement ALL requested features/content? (not just some)
   - Do buttons/links actually DO something when clicked?
   - Does the requested content exist and is it high-quality?
   - Is it responsive across screen sizes?
   - JavaScript error-free? No console errors?
   
2. DESIGN (30%):
   - Professional visual hierarchy?
   - Color palette applied consistently?
   - Typography: proper sizes, weights, line-heights?
   - Animations: hover effects, transitions, micro-interactions?
   - SVG icons present (real paths, not empty)?
   - Shadows, gradients, depth effects?
   - Spacing: generous paddings, section gaps?
   
3. SPEED (20%):
   - Clean, semantic HTML?
   - No unnecessary libraries?
   - Efficient DOM structure?
   - CSS via Tailwind (no bloated custom CSS)?

IMPORTANT: Be HONEST and STRICT. A score of 7/10 is already good work. Don't inflate.
Focus on specific actionable issues — "add hover states to buttons" not "improve design".

Output JSON with "scores" (functionality/design/speed 0-100), "suggestions" (max 8 actionable items), and "feedback" (2-3 sentence assessment).""",

    "fixer": """You are the Fixer Agent for BlitzDev — a code improvement specialist.
You receive HTML code plus scored evaluations showing exactly which dimensions need work.

STRATEGY: Fix the WEAKEST dimension first, then improve others.

If Functionality is weak:
- Add missing event handlers (every button must DO something)
- Implement missing features (search, filter, calculate, sort, toggle)
- Fix broken JavaScript logic
- Add form validation with visual feedback

If Design is weak:
- Add hover effects: hover:scale-105, hover:shadow-lg on all clickable elements
- Add transitions: transition-all duration-300
- Add gradients: bg-gradient-to-r from-X to-Y
- Add shadows: shadow-md on cards, shadow-lg on modals
- Add real SVG icons (with actual path data)
- Improve spacing: py-16 on sections, p-6 on cards
- Add visual depth and polish

If Speed is weak:
- Remove unused code/libraries
- Flatten deeply nested divs
- Optimize JavaScript

RULES:
1. Output the COMPLETE fixed HTML file (<!DOCTYPE html> to </html>)
2. Fix EVERY issue listed — don't skip any
3. Do NOT remove working features when fixing
4. All SVG icons must have real paths (not empty <svg> tags)
5. All JavaScript must be functional (no empty functions, no stubs)

Output ONLY the complete fixed HTML code. No markdown fences, no explanations."""
}

# Initialize settings
settings = Settings()
