# ⚡ FlashForge Agent Swarm

**Autonomous, leaderless multi-agent swarm for AI-powered web app generation.**

Built for the **Vertex Swarm Challenge 2026 — Track 3: Agent Economy**.

FlashForge runs 4 AI agents as independent P2P processes (FoxMQ nodes). They self-organize via leaderless bidding, execute a complete build pipeline, and produce a cryptographically verifiable **Proof of Coordination** log — with no central controller.

- **ERC-8004 Registered** on Base chain
- **4 autonomous nodes**: Planner → Builder → Critic → Fixer
- **Leaderless** — any node can announce a task; agents bid for ownership
- **Proof of Coordination** — HMAC-chained audit log for every job
- **Multi-LLM** — Groq → Gemini → DeepSeek → Anthropic fallback chain

---

## Architecture

Each node is a **paho-mqtt client** connecting to the **FoxMQ broker** (MQTT 5.0 + Tashi Vertex BFT consensus):
- All agents connect to a single FoxMQ broker on `localhost:1883`.
- Vertex BFT consensus inside FoxMQ **orders messages** before delivery — every agent sees the exact same sequence.
- Messages are **HMAC-SHA256 signed** — tampering or replay → dropped.
- **Heartbeats** every 2s detect stale peers automatically.

### Leaderless Bid Protocol

```
TASK_AVAILABLE announced
       │
       ├── any capable node sees it
       ├── each sends BID{load_score, timestamp_ms, node_id}
       └── after 500ms: winner = min(load_score, timestamp_ms, node_id)
                         winner broadcasts COMMIT; others stand down
```

### Build Pipeline

```
job_injector → [BID: planning]  → planner_node  → analyze_prompt()
            → [BID: building]   → builder_node  → build(plan, prompt)  → index.html
            → [BID: evaluation] → critic_node   → evaluate(html)       → score
            → [BID: fixing]     → fixer_node    → fix(html, issues)    → index_fixed.html
            → COORDINATION_COMPLETE + PoC log finalized
```

### Proof of Coordination

Every job produces a HMAC-chained `.jsonl` log:

```json
{"seq":0,"event":"TASK_COMMITTED","actor":"planner-001","prev_chain":"","hmac":"a1b2..."}
{"seq":1,"event":"PLAN_READY","actor":"planner-001","prev_chain":"a1b2...","hmac":"c3d4..."}
{"seq":2,"event":"BUILD_COMPLETE","actor":"builder-001","prev_chain":"c3d4...","hmac":"e5f6..."}
{"seq":3,"event":"EVAL_COMPLETE","actor":"critic-001","data":{"overall":88.5},"hmac":"g7h8..."}
{"seq":4,"event":"COORDINATION_COMPLETE","actor":"swarm","data":{"signers":["planner","builder","critic"]},"hmac":"i9j0..."}
```

Verify: `python swarm/verify_poc.py poc_logs/poc_<job_id>.jsonl`

---

## Project Structure

```
flashforge/
├── swarm/
│   ├── foxmq_node.py          # paho-mqtt client over FoxMQ broker (heartbeat, HMAC, replay prevention)
│   ├── bid_protocol.py        # Leaderless task bidding (500ms window, deterministic winner)
│   ├── poc_logger.py          # HMAC-chained Proof of Coordination + standalone verifier
│   ├── run_planner_node.py    # Planner as independent FoxMQ node
│   ├── run_builder_node.py    # Builder as independent FoxMQ node
│   ├── run_critic_node.py     # Critic as independent FoxMQ node
│   ├── run_fixer_node.py      # Fixer as independent FoxMQ node
│   ├── job_injector.py        # Injects tasks, waits for completion, verifies PoC
│   └── verify_poc.py          # CLI verifier
├── agents/
│   ├── planner.py             # Prompt → ImplementationPlan
│   ├── builder.py             # Plan → HTML/CSS/JS (Tailwind)
│   ├── critic.py              # Quality evaluation (0-100)
│   └── fixer.py               # Automatic issue repair
├── utils/
│   ├── llm_manager.py         # Multi-LLM fallback chain
│   └── ...
├── config.py                  # Pydantic settings (SWARM_SECRET, POC_LOG_DIR, ...)
├── docker-compose.yml         # 5 services: 4 nodes + injector
└── Dockerfile.swarm
```

---

## Quick Start

### Requirements

- Python 3.11+ with pip
- Groq API key (free): https://console.groq.com

### Install

```bash
cd flashforge
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Set GROQ_API_KEY (required, free)
# Set GEMINI_API_KEY (recommended, free)
```

### Run (5 terminals)

```bash
# Terminal 1 — FoxMQ broker (Vertex BFT MQTT, must start first)
.\swarm\setup_foxmq.ps1           # Windows PowerShell
# Linux/macOS: ./foxmq run --secret-key-file=foxmq.d/key_0.pem --allow-anonymous-login

# Terminal 2
python swarm/run_planner_node.py

# Terminal 3
python swarm/run_builder_node.py

# Terminal 4
python swarm/run_critic_node.py

# Terminal 5
python swarm/run_fixer_node.py

# Terminal 6 — inject a job and watch coordination happen
python swarm/job_injector.py "Build a landing page for a coffee shop"
```

### Run with Docker Compose

```bash
cp .env.example .env   # add GROQ_API_KEY
docker compose up --build

# Custom prompt:
PROMPT="Build a portfolio for a photographer" docker compose run --rm injector
```

---

## LLM Fallback Chain

| Priority | Provider | Model | Cost |
|----------|----------|-------|------|
| 1 | Groq | llama-3.3-70b-versatile | FREE |
| 2 | Google Gemini | gemini-2.5-flash | FREE |
| 3 | DeepSeek | deepseek-chat | ~$0.002/call |
| 4 | Anthropic | claude-sonnet-4-20250514 | ~$0.05/call |

---

## Track 3 Alignment

| Requirement | Implementation |
|-------------|----------------|
| Decentralized agents | 4 independent processes, no central controller |
| FoxMQ transport | paho-mqtt over real FoxMQ broker (MQTT 5.0 + Vertex BFT ordering) |
| Leaderless consensus | min(load_score, timestamp_ms, node_id) deterministic selection |
| Agent specialization | planner / builder / critic / fixer roles |
| Proof of coordination | HMAC-SHA256 chained JSONL audit log, independently verifiable |
| ERC-8004 identity | Registered on Base chain |

---

## Security

- HMAC-SHA256 on every swarm message (tampering → drop)
- Nonce replay prevention (bounded ring buffer, 1024 entries)
- Chain hash linkage in PoC log (edit any entry → chain breaks)
- Idempotency on job commits (duplicate COMMITs → ignored)
- FoxMQ Vertex BFT consensus — fair message ordering, no front-running

---

## License

MIT
