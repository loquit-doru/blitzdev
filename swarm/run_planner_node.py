"""
Planner Node — FlashForge Swarm participant.

Listens for TASK_AVAILABLE{capability="planning"}, bids, and if it wins:
  1. Calls PlannerAgent.analyze_prompt(prompt) to create an ImplementationPlan.
  2. Records the event in the PoC log.
  3. Announces TASK_AVAILABLE{capability="building"} for the next stage.

Environment variables:
  NODE_ID         (optional, auto-generated)
  FOXMQ_HOST      default "127.0.0.1"
  FOXMQ_PORT      default 1883
  SWARM_SECRET    default "swarm-secret-change-in-prod"
  POC_LOG_DIR     default "./poc_logs"
"""
import asyncio
import os
import sys
import uuid

# Allow running as `python swarm/run_planner_node.py` from the flashforge/ dir
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swarm.foxmq_node import FoxMQNode
from swarm.bid_protocol import BidProtocol
from swarm.poc_logger import PoCLogger

NODE_ID = os.getenv("NODE_ID", f"planner-{uuid.uuid4().hex[:8]}")
FOXMQ_HOST = os.getenv("FOXMQ_HOST", "127.0.0.1")
FOXMQ_PORT = int(os.getenv("FOXMQ_PORT", "1883"))
SWARM_SECRET = os.getenv("SWARM_SECRET", "swarm-secret-change-in-prod")
POC_LOG_DIR = os.getenv("POC_LOG_DIR", "./poc_logs")


async def main() -> None:
    from agents.planner import PlannerAgent

    node = FoxMQNode(NODE_ID, "planner", FOXMQ_HOST, FOXMQ_PORT, SWARM_SECRET)
    bidder = BidProtocol(node, capability="planning")
    planner = PlannerAgent()

    async def on_commit(job_id: str, won: bool, task_payload: dict | None) -> None:
        if not won or task_payload is None:
            return

        prompt: str = task_payload.get("prompt", "Build a web app")
        print(f"[planner] 🏆 Won job {job_id[:8]} — analysing: {prompt[:60]!r}")

        poc = PoCLogger(job_id, SWARM_SECRET, POC_LOG_DIR)
        poc.record("TASK_COMMITTED", NODE_ID, {"stage": "planning", "prompt": prompt[:120]})

        try:
            plan = await planner.analyze_prompt(prompt)
            plan_dict = plan.to_dict()
            poc.record("PLAN_READY", NODE_ID, {
                "app_type": plan_dict.get("app_type"),
                "complexity": plan_dict.get("complexity"),
                "components": plan_dict.get("components", [])[:5],
            })

            # Hand off to builder via the swarm
            await bidder.announce_task(
                prompt=prompt,
                capability="building",
                context={"plan": plan_dict},
                job_id=f"{job_id}:build",
            )
            print(f"[planner] ✓ Plan ready — announced building task for job {job_id[:8]}")

        except Exception as exc:
            print(f"[planner] ✗ Planning failed: {exc}")
            poc.record("PLAN_FAILED", NODE_ID, {"error": str(exc)})

    bidder.on_commit(on_commit)
    await node.start()

    print(f"[planner] Listening — FoxMQ {FOXMQ_HOST}:{FOXMQ_PORT}")
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("[planner] Shutting down…")
        await node.stop()


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
