# ⚡ BlitzDev

**Autonomous AI Agent for the Seedstr Blind Hackathon**

BlitzDev is a speed-first, multi-agent system built for the [Seedstr](https://seedstr.io) platform. It polls for jobs, classifies them intelligently (text vs. project), generates solutions using a 4-LLM fallback chain, and submits responses — all autonomously with zero human intervention.

- **ERC-8004 Registered** on Base chain
- **Verified** on Seedstr
- Production-grade codebase with full test coverage

## Architecture

```
flashforge/
├── main.py               # Autonomous agent: polling, classification, routing
├── config.py             # Pydantic settings (env-driven)
├── seedstr_client.py     # Seedstr API v1/v2 client
├── demo.py               # Standalone demo (no API keys)
├── agents/
│   ├── planner.py        # Prompt analysis → structured plan
│   ├── builder.py        # HTML/CSS/JS generation + content gate
│   ├── critic.py         # Quality evaluation
│   └── fixer.py          # Automatic issue repair
├── utils/
│   ├── llm_manager.py    # Multi-LLM orchestration + fallback chain
│   ├── packer.py         # ZIP packaging with manifest
│   ├── html_enhancer.py  # Post-build HTML polishing
│   └── templates.py      # Template library for fast scaffolding
```

## Key Features

### Intelligent Job Classification
- **40+ keyword patterns** for text detection (questions, lists, explanations, comparisons)
- **Regex-based question detection** (`_QUESTION_RE`) with contraction normalization
- **3 routing paths**: Text Fast Path (~10-20s), Project Path (~45-90s), Hybrid → Text
- Cheap jobs (≤$1) skip eval/fix cycle for maximum speed

### Multi-LLM Fallback Chain
| Provider | Role | Cost | Model |
|----------|------|------|-------|
| **Groq** | Planner | FREE | `llama-3.3-70b-versatile` |
| **Google Gemini** | Builder / Quality | FREE | `gemini-2.5-flash` |
| **DeepSeek** | Fallback | ~$0.002/build | `deepseek-chat` |
| **Anthropic** | Last resort | ~$0.05/build | `claude-sonnet-4-20250514` |

Tagged provider selection with automatic failover. Cooldowns (60s/300s/30s) prevent retry storms. 180s request timeout with warm-path caching.

### Content Validation Gate
Builder enforces `min_content_length=10000` — rejects shallow outputs and regenerates automatically. Ensures every submission has substantial, production-quality content.

### HTML Enhancer
Post-build processing pipeline:
- Injects Tailwind CSS CDN + responsive viewport meta
- Adds smooth scroll, transitions, hover effects
- Ensures proper `<html>`, `<head>`, `<body>` structure
- Minifies output for smaller uploads

### Resilience
- **Cooldown system**: Per-provider cooldowns prevent cascading failures
- **Retry with backoff**: Automatic retry on transient errors
- **409 Conflict handling**: Treated as success (duplicate submission)
- **Graceful degradation**: Missing optional services → skip, don't crash

## Quick Start

### 1. Install

```bash
cd flashforge
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your API keys
```

| Variable | Required | Description |
|----------|----------|-------------|
| `SEEDSTR_API_KEY` | Yes | Your agent API key |
| `GROQ_API_KEY` | Yes | [console.groq.com](https://console.groq.com) (FREE) |
| `GOOGLE_API_KEY` | Yes | [aistudio.google.com](https://aistudio.google.com/apikey) (FREE) |
| `DEEPSEEK_API_KEY` | No | [platform.deepseek.com](https://platform.deepseek.com) (cheap fallback) |
| `ANTHROPIC_API_KEY` | No | [console.anthropic.com](https://console.anthropic.com) (last resort) |
| `SEEDSTR_POLL_INTERVAL` | No | Polling interval in seconds (default: 3) |

### 3. Run

```bash
# Demo mode (no API keys needed)
python demo.py

# Continuous autonomous polling
python main.py

# Single cycle (for testing)
python main.py --test
```



## How It Works

```
Poll (3s) → New Job? → Classify (text/project/hybrid)
                          │
                    ┌──────┴──────┐
                    ▼             ▼
              TEXT PATH      PROJECT PATH
              (10-20s)       (45-90s)
                │               │
            LLM Generate    Plan → Build → Enhance
                │               │
                │           Eval + Fix (if budget > $1)
                │               │
                │           ZIP + Upload
                │               │
                ▼               ▼
              Submit TEXT    Submit FILE
```

1. **Poll** — Checks Seedstr API every 3 seconds for new jobs
2. **Classify** — Routes to optimal path based on job content
3. **Generate** — Uses multi-agent pipeline with LLM fallback chain
4. **Quality Gate** — Content validation ensures minimum quality bar
5. **Submit** — Automatically submits response (text or file attachment)

## Seedstr Integration

- Seedstr API v1 + v2 support
- SWARM job acceptance
- File upload via base64 → CDN
- Job type detection (STANDARD vs SWARM)
- Profile and skills management
- Agent verification flow

## Hackathon Details

- **Platform**: [Seedstr Blind Hackathon](https://seedstr.io)
- **Agent Name**: BlitzDev
- **Skills**: Content Writing, Copywriting, Code Review, Technical Writing, Research, Data Analysis, API Integration

## License

MIT License — See [LICENSE](LICENSE) for details.

---

**Built for the Seedstr Blind Hackathon** — speed wins.
