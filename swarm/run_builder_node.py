"""
Builder Node — FlashForge Swarm participant.

Listens for TASK_AVAILABLE{capability="building"}, bids, and if it wins:
  1. Calls BuilderAgent.build(plan, prompt) to generate HTML/CSS/JS.
  2. Records the event in the PoC log.
  3. Announces TASK_AVAILABLE{capability="evaluation"} for the critic.

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

NODE_ID = os.getenv("NODE_ID", f"builder-{uuid.uuid4().hex[:8]}")
FOXMQ_HOST = os.getenv("FOXMQ_HOST", "127.0.0.1")
FOXMQ_PORT = int(os.getenv("FOXMQ_PORT", "1883"))
SWARM_SECRET = os.getenv("SWARM_SECRET", "swarm-secret-change-in-prod")
POC_LOG_DIR = os.getenv("POC_LOG_DIR", "./poc_logs")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./swarm_output")


async def main() -> None:
    from agents.planner import ImplementationPlan
    from agents.builder import BuilderAgent

    node = FoxMQNode(NODE_ID, "builder", FOXMQ_HOST, FOXMQ_PORT, SWARM_SECRET)
    bidder = BidProtocol(node, capability="building")
    builder = BuilderAgent()

    # job_id of build task → original job_id (for PoC log continuity)
    build_to_root: dict[str, str] = {}

    async def on_commit(job_id: str, won: bool, task_payload: dict | None) -> None:
        if not won or task_payload is None:
            return

        prompt: str = task_payload.get("prompt", "Build a web app")
        ctx: dict = task_payload.get("context", {})
        plan_dict: dict = ctx.get("plan", {})
        root_job_id = job_id.split(":")[0]

        print(f"[builder] 🏆 Won build job {job_id[:10]} — building…")

        poc = PoCLogger(root_job_id, SWARM_SECRET, POC_LOG_DIR)
        poc.record("BUILD_STARTED", NODE_ID, {"job_id": job_id})

        try:
            plan = ImplementationPlan.from_dict(plan_dict) if plan_dict else None
            if plan is None:
                raise ValueError("No plan provided in task context")

            result = await builder.build(plan, prompt)
            if not result.success or not result.html:
                raise RuntimeError(result.error or "Builder returned empty HTML")

            # Save output
            out_dir = Path(OUTPUT_DIR) / root_job_id
            out_dir.mkdir(parents=True, exist_ok=True)
            html_path = out_dir / "index.html"
            html_path.write_text(result.html, encoding="utf-8")

            poc.record("BUILD_COMPLETE", NODE_ID, {
                "html_bytes": len(result.html),
                "build_time_s": round(result.build_time, 2),
                "output": str(html_path),
            })

            # Hand off to critic
            await bidder.announce_task(
                prompt=prompt,
                capability="evaluation",
                context={
                    "plan": plan_dict,
                    "html": result.html,
                    "output_path": str(html_path),
                },
                job_id=f"{root_job_id}:eval",
            )
            print(f"[builder] ✓ Build done ({len(result.html):,} chars) — announced eval task")

        except Exception as exc:
            print(f"[builder] ✗ Build failed: {exc}")
            poc.record("BUILD_FAILED", NODE_ID, {"error": str(exc)})

    bidder.on_commit(on_commit)
    await node.start()

    print(f"[builder] Listening — FoxMQ {FOXMQ_HOST}:{FOXMQ_PORT}")
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("[builder] Shutting down…")
        await node.stop()


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
