"""
Job Injector — FlashForge Swarm entry point.

Injects a build task into the swarm and waits for the coordination to complete.
This replaces the old Seedstr API polling loop.

Usage:
  python swarm/job_injector.py "Build a landing page for a coffee shop"
  python swarm/job_injector.py "Create a portfolio site for a photographer"
  python swarm/job_injector.py --prompt "Build an expense tracker dashboard" --timeout 300

The injector also participates in the peer mesh so nodes can discover it.
It prints a live summary of swarm activity and exits when done (or on timeout).

Environment variables:
  FOXMQ_HOST      default "127.0.0.1"
  FOXMQ_PORT      default 1883
  SWARM_SECRET    default "swarm-secret-change-in-prod"
  POC_LOG_DIR     default "./poc_logs"
"""
import argparse
import asyncio
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swarm.foxmq_node import FoxMQNode
from swarm.bid_protocol import BidProtocol
from swarm.poc_logger import verify_poc_log

FOXMQ_HOST = os.getenv("FOXMQ_HOST", "127.0.0.1")
FOXMQ_PORT = int(os.getenv("FOXMQ_PORT", "1883"))
SWARM_SECRET = os.getenv("SWARM_SECRET", "swarm-secret-change-in-prod")
POC_LOG_DIR = os.getenv("POC_LOG_DIR", "./poc_logs")


async def main(prompt: str, timeout_s: int) -> None:
    node_id = f"injector-{uuid.uuid4().hex[:8]}"
    job_id = str(uuid.uuid4())

    node = FoxMQNode(node_id, "injector", FOXMQ_HOST, FOXMQ_PORT, SWARM_SECRET)
    bidder = BidProtocol(node, capability="none")   # injector doesn't bid on tasks

    done_event = asyncio.Event()

    # Track coordination progress
    seen_events: list[tuple[str, str]] = []

    @node.on("COMMIT")
    async def _on_commit(msg: dict) -> None:
        payload = msg["payload"]
        cap = payload.get("capability", "?")
        winner = payload.get("winner_role", "?")
        seen_events.append((cap, winner))
        ts = time.strftime("%H:%M:%S")
        print(f"  [{ts}] COMMIT  {cap:12s}  → winner: {winner}")

    @node.on("TASK_AVAILABLE")
    async def _on_task(msg: dict) -> None:
        payload = msg["payload"]
        cap = payload.get("capability", "?")
        jid = payload.get("job_id", "")
        root = jid.split(":")[0]
        ts = time.strftime("%H:%M:%S")
        if root == job_id or jid == job_id:
            print(f"  [{ts}] TASK    {cap:12s}  announced")

    @node.on("HEARTBEAT")
    async def _on_heartbeat(msg: dict) -> None:
        pass   # suppress heartbeat noise

    await node.start()

    # Wait briefly for peer discovery
    print(f"\n🌐 FlashForge Swarm — Job Injector")
    print(f"   job_id : {job_id}")
    print(f"   prompt : {prompt[:80]!r}")
    print(f"   broker : FoxMQ {FOXMQ_HOST}:{FOXMQ_PORT}")
    print(f"\n⏳ Waiting 2s for peer discovery…")
    await asyncio.sleep(2)
    print(f"   Mesh   : {node.peer_summary()}")

    online = len(node.online_peers)
    if online == 0:
        print("\n⚠ No peers online. Start the 4 node processes first:")
        print("  python swarm/run_planner_node.py")
        print("  python swarm/run_builder_node.py")
        print("  python swarm/run_critic_node.py")
        print("  python swarm/run_fixer_node.py")
        await node.stop()
        return

    print(f"\n🚀 Injecting task ({online} peers online)…\n")
    start_ts = time.time()

    # Inject the planning task
    await bidder.announce_task(
        prompt=prompt,
        capability="planning",
        job_id=job_id,
    )

    # Wait for completion (detected by COORDINATION_COMPLETE in PoC log)
    poc_path = f"{POC_LOG_DIR}/poc_{job_id}.jsonl"
    deadline = start_ts + timeout_s

    while time.time() < deadline:
        await asyncio.sleep(3)
        # Check if PoC log has been finalized
        try:
            if os.path.exists(poc_path):
                with open(poc_path, encoding="utf-8") as f:
                    lines = [l for l in f if "COORDINATION_COMPLETE" in l]
                if lines:
                    elapsed = time.time() - start_ts
                    print(f"\n✅ Coordination complete in {elapsed:.1f}s")
                    print(f"   PoC log : {poc_path}")
                    print(f"\n🔍 Verifying Proof of Coordination…")
                    verify_poc_log(poc_path, SWARM_SECRET)
                    done_event.set()
                    break
        except Exception:
            pass

    if not done_event.is_set():
        elapsed = time.time() - start_ts
        print(f"\n⏱ Timeout after {elapsed:.0f}s — partial results may exist in {POC_LOG_DIR}/")

    await node.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject a build task into the FlashForge swarm")
    parser.add_argument("prompt", nargs="?", default="Build a landing page for a coffee shop")
    parser.add_argument("--timeout", type=int, default=300, help="Max seconds to wait (default 300)")
    args = parser.parse_args()

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(args.prompt, args.timeout))
