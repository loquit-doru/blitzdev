# BlitzDev — AI Improvement Brief
## Context for AI Collaborators

> **Goal**: Help us win the [Seedstr Blind Hackathon](https://seedstr.io/hackathon) ($10K prize).
> **Critical fact**: The winner is chosen by **Seedstr's AI judge agent** — not humans. We need to optimize for what an AI evaluator scores highest.

---

## What BlitzDev Does

BlitzDev is an autonomous AI agent on the Seedstr platform. It receives job prompts (e.g., "Build a Pomodoro timer app") and delivers a self-contained HTML/CSS/JS web application as a `.zip` file.

**Pipeline**: Prompt → Plan (Groq) → Build (Gemini) → Evaluate (DeepSeek) → Fix → Re-Evaluate → Package ZIP → Upload → Submit

**Key constraint**: Output is always a **single `index.html` file** with inline CSS/JS (Tailwind via CDN). No backend, no multi-page, no build step.

---

## How the AI Judge Scores (what we MUST optimize for)

The AI judge evaluates responses on **3 dimensions**:

### 1. FUNCTIONALITY (50% weight) — Most Important
| Sub-criterion | What the judge checks |
|---|---|
| Feature completeness | Does it implement **ALL** requested features? Every feature mentioned in the prompt must work. |
| Interactivity | Do buttons, forms, toggles, filters actually DO something? Uses `addEventListener`, not empty `onclick=""`. |
| State management | Does it persist data (`localStorage`), track user state, handle edge cases? |
| Error handling | Graceful degradation, form validation with visual feedback, user-friendly messages. |
| Responsiveness | Works on mobile/tablet/desktop — uses `sm:`, `md:`, `lg:`, `xl:` Tailwind breakpoints. |

**Scoring**: 90-100 = all features work perfectly with polish. 70-89 = core features work, missing polish. <70 = features missing/broken.

### 2. DESIGN (30% weight)
| Sub-criterion | What the judge checks |
|---|---|
| Visual appeal | SVG icons (real `<path>` data), gradients, shadows, rounded corners, consistent color palette. |
| Typography | Font hierarchy (h1>h2>h3>p), proper `font-bold`/`font-semibold`, `leading-`/`tracking-` utilities. |
| Hover/transitions | Every clickable element has `hover:scale-105`, `hover:shadow-lg`, `transition-all duration-300`. |
| Color harmony | Cohesive palette, accent color for CTAs, dark mode toggle. |
| Spacing | Sections use `py-16+`, cards use `p-6+`, proper `gap` utilities. |
| Semantic HTML | `<header>`, `<nav>`, `<main>`, `<section>`, `<footer>`, `<article>` — at least 4-5 of these. |

**Scoring**: 90-100 = professional-grade, beautiful. 70-89 = good but missing polish. <70 = generic/ugly.

### 3. SPEED (20% weight)
| Sub-criterion | What the judge checks |
|---|---|
| Code efficiency | Total HTML < 30KB ideal, < 50KB acceptable. No bloat. |
| Clean DOM | Minimal nesting, semantic elements, no redundant wrappers. |
| No heavy dependencies | Tailwind CDN + Google Fonts + maybe Chart.js. No React, no giant frameworks. |
| Generation time | < 30s = 100, < 60s = 90, < 120s = 80 (we currently average 88-130s). |

---

## Current Architecture

```
main.py (orchestrator)
├── classify_job(prompt) → 'text' | 'project' | 'hybrid'
│   ├── text → _process_text_job() → LLM answer + HTML showcase ZIP
│   └── project/hybrid → _process_project_job() → full pipeline
│
├── agents/planner.py  → Groq (Llama 3.3 70B, FREE)
│   └── Analyzes prompt → app_type, complexity, components, features, layout, tech_stack
│
├── agents/builder.py  → Gemini 2.5 Flash (FREE)
│   └── Generates single HTML file with inline Tailwind + JS
│   └── Uses DESIGN_PRESETS (color palettes, font configs)
│   └── Has app-type-specific instructions (game, dashboard, e-commerce, etc.)
│
├── agents/critic.py   → DeepSeek ($2 budget)
│   └── Automated checks: HTML structure, interactivity count, SVG presence, breakpoints
│   └── LLM evaluation: scores 0-100 on functionality/design/speed
│   └── Combined score = 40% auto + 60% LLM (functionality), 30/70 (design)
│
├── agents/fixer.py    → DeepSeek
│   └── Takes scored evaluation → fixes weakest dimension
│   └── Regression revert: if fix makes score worse, revert to best version
│
├── utils/packer.py    → Creates ZIP with index.html + metadata
├── utils/templates.py → Template library (game, dashboard, form, etc.)
└── seedstr_client.py  → Seedstr API v2 client (poll, upload, submit)
```

**LLM Budget**: Groq = FREE, Gemini = FREE, Kimi = FREE, DeepSeek = ~$2, Claude = ~$3 (reserved), OpenAI = disabled.

---

## What We Need Help With

### A) Functionality Improvements
Our builder sometimes produces HTML where:
- Buttons exist but have no event handlers (dead buttons)
- Forms render but don't validate or submit
- Features mentioned in the prompt are partially implemented (placeholder text, TODO comments)
- `localStorage` is referenced but not actually used

**Question**: What patterns/techniques can we add to the builder prompt or post-processing to ensure 100% of requested features are functional? Should we add a post-build JavaScript injection step that auto-wires orphan buttons?

### B) Design Score Boosters
The AI judge specifically looks for these Tailwind patterns. Which of these can we auto-inject without breaking layout?:
- `hover:scale-105 hover:shadow-lg transition-all duration-300` on all `<button>` and `<a>` elements
- `bg-gradient-to-r from-{primary} to-{accent}` on hero sections
- Real inline SVG icons (we need a library of 20-30 common icons as `<svg><path d="..."/></svg>`)
- `shadow-md` on all cards, `shadow-lg` on modals
- `rounded-xl` on containers, `rounded-full` on avatars
- Dark mode: `dark:bg-gray-900 dark:text-gray-100` with toggle

**Question**: Can you generate a reusable "design polish" post-processor that injects these patterns into any HTML output? Also, a library of 20+ inline SVG icons (home, search, settings, user, heart, star, arrow, menu, close, check, plus, trash, edit, calendar, clock, chart, download, upload, mail, bell)?

### C) Speed Optimization
Our generation time is 88-130 seconds for the full pipeline. The seed-agent (competitor) does 10-30 seconds but with lower quality. We already:
- Skip fix loop when score >= 85
- Use Gemini Flash (fast) as builder

**Question**: What else can we do? Should we:
1. Pre-cache common templates and only LLM the unique parts?
2. Run planner + builder in parallel (plan provides structure, builder fills content)?
3. Reduce MAX_TOKENS from 32768 to something smaller for simple apps?
4. Cache the Tailwind CDN + common SVGs as a static prefix to reduce LLM token generation?

### D) Beating the AI Judge Specifically
Since the judge is an AI (likely GPT-4 or similar), it probably:
- Parses the HTML and checks for specific patterns (like our automated evaluator does)
- Counts interactive elements, event listeners, breakpoints
- Looks for semantic HTML tags
- Checks if the output matches the prompt requirements keyword-by-keyword

**Question**: How should we reverse-engineer AI judging to maximize score? Should we:
1. Add invisible HTML comments like `<!-- Feature: dark mode toggle - IMPLEMENTED -->` that an AI parser would identify?
2. Add a `<meta name="features" content="dark-mode,responsive,form-validation,...">` tag?
3. Include a `manifest.json` or `README.md` that explicitly maps prompt requirements → implemented features?
4. Ensure every prompt keyword appears somewhere in the HTML (as heading text, aria-label, or data attribute)?

### E) Text-Only Jobs
We added a fast path for non-code prompts (tweets, emails, essays). The text goes through Gemini, gets wrapped in a beautiful HTML page, and submitted as ZIP.

**Question**: How can we make the HTML wrapper for text content score highest on design? What makes an AI judge think "this is beautifully presented text"?

---

## Sample Builder Output (for reference)

A typical output looks like this (simplified):
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pomodoro Timer</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: { extend: { colors: { primary: '#0f172a', accent: '#3b82f6' } } },
            darkMode: 'class'
        }
    </script>
</head>
<body class="bg-gray-50 dark:bg-gray-900 min-h-screen font-[Inter]">
    <header class="bg-white dark:bg-gray-800 shadow-sm">...</header>
    <main class="max-w-4xl mx-auto px-4 py-16">
        <section>...</section>
    </main>
    <footer class="text-center py-8 text-gray-400">...</footer>
    <script>
        // Interactive JavaScript here
        document.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', () => { /* logic */ });
        });
    </script>
</body>
</html>
```

---

## Competition Landscape

| Agent | Position | Strategy | Our Advantage |
|-------|----------|----------|--------------|
| **Lexis** (#1) | 52 jobs, $205 earned | Unknown (closed source) | — |
| **seedstr.io** (#2) | 17 jobs, $26 earned | Single LLM, tool-calling, no quality control | Our multi-agent pipeline + critic + fixer |
| **SentraAgent** (#3) | 4 jobs, $15 earned | Unknown | — |
| **BlitzDev** (us, #18) | 0 jobs counted | Multi-agent, 6 LLMs, critic+fixer, templates | Quality advantage, need speed |

Most competitors use a single LLM call with no evaluation or fixing. Our pipeline produces higher quality but takes longer.

---

## How to Help

Please provide:
1. **Concrete code snippets** — not just ideas. We need implementable Python/JS.
2. **Focus on AI-judge-visible improvements** — things that a code-parsing AI would score higher.
3. **Prioritize by impact**: Functionality (50%) > Design (30%) > Speed (20%).
4. **Stay within constraints**: Single HTML file, Tailwind CDN, no backend, inline JS.

The prize is $10,000. Every point of score matters.
