# FlashForge — Judging Criteria → Code Mapping

> Track 3 | Agent Economy | Vertex Swarm Challenge 2026
> Minimum requirement: ≥3 agents completing **negotiate → commit → execute → verify** loop ✅ (4 agents + multi-critic consensus)

---

## 1. Coordination Correctness
> *No double assignments, deterministic resolution under contention.*

| What | Where |
|------|-------|
| Leaderless task bidding (load score → timestamp → ID tiebreak) | [`swarm/bid_protocol.py`](swarm/bid_protocol.py) — `_evaluate_bids()` |
| Idempotency key prevents double assignment | [`swarm/bid_protocol.py`](swarm/bid_protocol.py) — `_committed_jobs: Set[str]` |
| BFT fair ordering via FoxMQ/Vertex — no front-running possible | [`swarm/foxmq_node.py`](swarm/foxmq_node.py) — MQTT QoS 1 + Vertex BFT |
| Multi-critic BFT quorum (`floor(2n/3)+1`) prevents single critic override | [`swarm/critic_consensus.py`](swarm/critic_consensus.py) — `CriticConsensus` |
| All critics vote independently (voter role) | [`swarm/run_critic_node.py`](swarm/run_critic_node.py) — `evaluate_and_vote()` |
| Leader publishes `EVAL_CONSENSUS` only after quorum | [`swarm/run_critic_node.py`](swarm/run_critic_node.py) — `_publish_consensus()` |

---

## 2. Resilience
> *Swarm continues when nodes drop or messages are delayed.*

| What | Where |
|------|-------|
| Heartbeat every 2s per node | [`swarm/foxmq_node.py`](swarm/foxmq_node.py) — `_heartbeat_loop()` |
| Stale detection after 10s silence (threshold env-configurable) | [`swarm/foxmq_node.py`](swarm/foxmq_node.py) — `PEER_STALE_AFTER` |
| Automatic revival when peer reconnects | [`swarm/foxmq_node.py`](swarm/foxmq_node.py) — `_heartbeat_loop()` revival branch |
| Quorum timeout → force majority from available votes | [`swarm/run_critic_node.py`](swarm/run_critic_node.py) — `on_commit()` timeout path |
| Live demo of stale → revive cycle | [`swarm/warmup_demo.py`](swarm/warmup_demo.py) — Phase 4 + 5 |

---

## 3. Auditability
> *Clear, complete, verifiable Proof of Coordination.*

| What | Where |
|------|-------|
| HMAC-SHA256 chained PoC log (mini-blockchain) | [`swarm/poc_logger.py`](swarm/poc_logger.py) — `PoCLogger` |
| Every event: `seq`, `actor`, `timestamp_ms`, `prev_chain`, `hmac` | [`swarm/poc_logger.py`](swarm/poc_logger.py) — `record()` |
| `EVAL_CONSENSUS` with full vote summary recorded in PoC | [`swarm/run_critic_node.py`](swarm/run_critic_node.py) — `_publish_consensus()` |
| `COORDINATION_COMPLETE` with signer list finalizes log | [`swarm/poc_logger.py`](swarm/poc_logger.py) — `finalize()` |
| Standalone verifier re-computes every HMAC + chain link | [`swarm/verify_poc.py`](swarm/verify_poc.py) |

**To verify a PoC log:**
```bash
python swarm/verify_poc.py poc_logs/poc_<job_id>.jsonl
```

---

## 4. Security Posture
> *Message integrity + resistance to replay attacks.*

| What | Where |
|------|-------|
| Every MQTT message HMAC-SHA256 signed before publish | [`swarm/foxmq_node.py`](swarm/foxmq_node.py) — `_sign()` / `publish()` |
| HMAC verified on every received message | [`swarm/foxmq_node.py`](swarm/foxmq_node.py) — `_verify()` in `_dispatch()` |
| Nonce ring-buffer (1024 entries) prevents replay attacks | [`swarm/foxmq_node.py`](swarm/foxmq_node.py) — `_seen_nonces` |
| FoxMQ Vertex BFT consensus — mathematically fair message ordering | [FoxMQ docs](https://github.com/tashigit/foxmq-legacy) |
| Canonical JSON (sorted keys) for deterministic HMAC | [`swarm/foxmq_node.py`](swarm/foxmq_node.py) — `_sign()` |

---

## 5. Developer Clarity
> *Runnable repo, clear demo flow, observability.*

### Quick Start (local, 6 terminals)
```bash
# Terminal 1 — FoxMQ broker
.\foxmq.exe run --secret-key-file=foxmq.d/key_0.pem --allow-anonymous-login

# Terminal 2 — Planner
python swarm/run_planner_node.py

# Terminal 3 — Builder
python swarm/run_builder_node.py

# Terminal 4 — Critic 1 (CRITICS_EXPECTED=2 for BFT demo)
CRITICS_EXPECTED=2 python swarm/run_critic_node.py

# Terminal 5 — Critic 2 (second vote for quorum)
CRITICS_EXPECTED=2 NODE_ID=critic-002 python swarm/run_critic_node.py

# Terminal 6 — Inject job
python swarm/job_injector.py "Build a portfolio website for a blockchain developer"
```

### Warm-Up Proof (single command)
```bash
python swarm/warmup_demo.py
# → 5/5 acceptance criteria in ~75 seconds
```

### Live Dashboard
```bash
python swarm/dashboard_server.py
# → open http://localhost:5050
```

### Docker (everything in one command)
```bash
cp .env.example .env   # add GROQ_API_KEY
docker compose up      # foxmq + planner + builder + critic + critic2 + fixer + dashboard
# Dashboard: http://localhost:5050
```

---

## Architecture Diagram

```
User Prompt
     │
     ▼
[job_injector] ──TASK_AVAILABLE(planning)──► [planner] ──TASK_AVAILABLE(building)──► [builder]
                                                                                          │
                                                         TASK_AVAILABLE(evaluation)◄──────┘
                                                                   │
                                            ┌──────────────────────┼──────────────────────┐
                                            ▼                      ▼                      │
                                       [critic-001]          [critic-002]          (n critics)
                                       evaluates              evaluates
                                       independently         independently
                                            │                      │
                                            └──── EVAL_VOTE ───────┘
                                                        │
                                              FoxMQ Vertex BFT
                                           (fair ordering, all nodes
                                            see votes in same seq)
                                                        │
                                            quorum = floor(2n/3)+1
                                                        │
                                              EVAL_CONSENSUS
                                           (PASS → finalize PoC)
                                           (FAIL → [fixer] → DONE)
                                                        │
                                              PoC Log (HMAC chain)
                                           verifiable by any third party
```

## File Index

| File | Role |
|------|------|
| `swarm/foxmq_node.py` | MQTT wrapper, HMAC signing, heartbeat, stale detection |
| `swarm/bid_protocol.py` | Leaderless task bidding (no orchestrator) |
| `swarm/critic_consensus.py` | BFT supermajority vote tracker |
| `swarm/poc_logger.py` | HMAC-chained Proof of Coordination log |
| `swarm/verify_poc.py` | Standalone PoC verifier |
| `swarm/warmup_demo.py` | Warm-Up proof (discovery + heartbeat + stale + recovery) |
| `swarm/dashboard_server.py` | Real-time observability dashboard (FastAPI SSE) |
| `swarm/run_planner_node.py` | Planner agent node |
| `swarm/run_builder_node.py` | Builder agent node |
| `swarm/run_critic_node.py` | Critic agent node (multi-critic BFT) |
| `swarm/run_fixer_node.py` | Fixer agent node |
| `swarm/job_injector.py` | Job submission CLI |
| `Dockerfile.foxmq` | Linux FoxMQ broker container |
| `Dockerfile.swarm` | Python agent container |
| `docker-compose.yml` | Full stack (8 services) |
