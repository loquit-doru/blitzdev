"""
Fixer Node — FlashForge Swarm participant.

Listens for TASK_AVAILABLE{capability="fixing"}, bids, and if it wins:
  1. Calls FixerAgent.fix(build_result, evaluation) to correct issues.
  2. Saves the fixed HTML output.
  3. Finalizes the PoC log with COORDINATION_COMPLETE (all 4 signers).

This is the terminal stage of the build pipeline. If the fixer is not needed
(critic score ≥ threshold), this node stays idle.

Environment variables:
  NODE_ID         (optional, auto-generated)
  FOXMQ_HOST      default "127.0.0.1"
  FOXMQ_PORT      default 1883
  SWARM_SECRET    default "swarm-secret-change-in-prod"
  POC_LOG_DIR     default "./poc_logs"
  OUTPUT_DIR      default "./swarm_output"
"""
import asyncio
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swarm.foxmq_node import FoxMQNode
from swarm.bid_protocol import BidProtocol
from swarm.poc_logger import PoCLogger

NODE_ID = os.getenv("NODE_ID", f"fixer-{uuid.uuid4().hex[:8]}")
FOXMQ_HOST = os.getenv("FOXMQ_HOST", "127.0.0.1")
FOXMQ_PORT = int(os.getenv("FOXMQ_PORT", "1883"))
SWARM_SECRET = os.getenv("SWARM_SECRET", "swarm-secret-change-in-prod")
POC_LOG_DIR = os.getenv("POC_LOG_DIR", "./poc_logs")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./swarm_output")


async def main() -> None:
    from agents.builder import BuildResult
    from agents.critic import EvaluationResult, EvaluationScores
    from agents.fixer import FixerAgent

    node = FoxMQNode(NODE_ID, "fixer", FOXMQ_HOST, FOXMQ_PORT, SWARM_SECRET)
    bidder = BidProtocol(node, capability="fixing")
    fixer = FixerAgent()

    async def on_commit(job_id: str, won: bool, task_payload: dict | None) -> None:
        if not won or task_payload is None:
            return

        prompt: str = task_payload.get("prompt", "")
        ctx: dict = task_payload.get("context", {})
        html: str = ctx.get("html", "")
        issues_raw: list = ctx.get("issues", [])
        score: float = ctx.get("score", 0.0)
        root_job_id = job_id.split(":")[0]

        print(f"[fixer]   🏆 Won fix job {job_id[:10]} — fixing score={score:.1f}…")

        poc = PoCLogger(root_job_id, SWARM_SECRET, POC_LOG_DIR)
        poc.record("FIX_STARTED", NODE_ID, {"issues_count": len(issues_raw), "score_before": score})

        try:
            build_result = BuildResult(
                html=html, css=None, js=None,
                success=bool(html), build_time=0.0,
            )
            # Build a minimal EvaluationResult from context data
            fake_scores = EvaluationScores(
                functionality=score,
                design=score,
                speed=score,
                overall=score,
                functionality_breakdown={},
                design_breakdown={},
                speed_breakdown={},
            )
            from agents.critic import ScoreLevel
            level = ScoreLevel.POOR if score < 60 else ScoreLevel.ACCEPTABLE
            from dataclasses import dataclass

            evaluation = EvaluationResult(
                scores=fake_scores,
                suggestions=issues_raw,
                issues=[{"description": i, "severity": "medium"} for i in issues_raw],
                passed=False,
                level=level,
                detailed_feedback=f"Score {score:.1f}/100 — needs improvement",
            )

            fix_result = await fixer.fix(build_result, evaluation)

            if fix_result.success and fix_result.html:
                out_dir = Path(OUTPUT_DIR) / root_job_id
                out_dir.mkdir(parents=True, exist_ok=True)
                fixed_path = out_dir / "index_fixed.html"
                fixed_path.write_text(fix_result.html, encoding="utf-8")

                poc.record("FIX_COMPLETE", NODE_ID, {
                    "fixes_applied": fix_result.fixes_applied,
                    "iterations": fix_result.iterations,
                    "output": str(fixed_path),
                })
                print(f"[fixer]   ✓ Fixed — {len(fix_result.fixes_applied)} fixes applied → {fixed_path}")
            else:
                poc.record("FIX_PARTIAL", NODE_ID, {"error": fix_result.error})
                print(f"[fixer]   ⚠ Partial fix — {fix_result.error}")

            # Finalize PoC — this is the end of the coordination chain
            poc.finalize(signers=["planner", "builder", "critic", "fixer"])
            print(f"[fixer]   🎉 Job {root_job_id[:8]} DONE — PoC log: {poc.log_path}")

        except Exception as exc:
            print(f"[fixer]   ✗ Fix failed: {exc}")
            poc.record("FIX_FAILED", NODE_ID, {"error": str(exc)})

    bidder.on_commit(on_commit)
    await node.start()

    print(f"[fixer]   Listening — FoxMQ {FOXMQ_HOST}:{FOXMQ_PORT}")
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("[fixer]   Shutting down…")
        await node.stop()


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
