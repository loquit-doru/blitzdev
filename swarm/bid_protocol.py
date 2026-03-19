"""
Leaderless Bid Protocol for the FlashForge Agent Swarm.

Design (Track 3 — Agent Economy):
  - No central orchestrator. Any node can announce a TASK_AVAILABLE.
  - Capable agents self-select and send a BID within COMMIT_WINDOW_MS.
  - After the window, every bidder evaluates all received bids using the
    same deterministic rule: min(load_score, timestamp_ms, bidder_id).
  - The winner broadcasts COMMIT; others stand down.
  - Race conditions → first valid COMMIT wins (idempotency key on job_id).
  - All bid/commit events feed directly into PoCLogger for audit trail.

Message schema (all via FoxMQNode.publish):
  TASK_AVAILABLE  { job_id, capability, prompt, context }
  BID             { job_id, bidder_id, bidder_role, load_score, capability, timestamp_ms }
  COMMIT          { job_id, winner_id, winner_role, capability, committed_at_ms }
"""
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

COMMIT_WINDOW_MS = 500   # ms to collect bids before evaluating winner


@dataclass
class Bid:
    job_id: str
    bidder_id: str
    bidder_role: str
    load_score: float          # 0.0 = idle, 1.0 = saturated
    capability: str
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass
class Commit:
    job_id: str
    winner_id: str
    winner_role: str
    capability: str
    committed_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))


CommitCallback = Callable[[str, bool, Optional[Dict[str, Any]]], None]
# Called with (job_id, won: bool, task_payload: dict|None)


class BidProtocol:
    """
    Plugs into a FoxMQNode to add leaderless task-bidding.

    Usage:
        node = FoxMQNode(...)
        bp = BidProtocol(node, capability="planning")
        bp.on_commit(my_handler)   # my_handler(job_id, won, task_payload)
        await node.start()
    """

    def __init__(
        self,
        node,                          # FoxMQNode
        capability: str,
        load_fn: Optional[Callable[[], float]] = None,
    ):
        self.node = node
        self.capability = capability
        self._load_fn = load_fn or (lambda: 0.0)

        # job_id → list of Bid objects (from all bidders including self)
        self._pending_bids: Dict[str, List[Bid]] = {}
        # job_id → full TASK_AVAILABLE payload (for winner to use)
        self._task_payloads: Dict[str, Dict[str, Any]] = {}
        # committed job IDs (idempotency key)
        self._committed_jobs: Set[str] = set()

        self._commit_callbacks: List[CommitCallback] = []

        # Wire up handlers on the node
        node.on("TASK_AVAILABLE", self._handle_task)
        node.on("BID", self._handle_bid)
        node.on("COMMIT", self._handle_commit)

    # ── Public API ─────────────────────────────────────────────────────────────

    def on_commit(self, callback: CommitCallback) -> None:
        """Register callback: called when any job's winner is determined."""
        self._commit_callbacks.append(callback)

    async def announce_task(
        self,
        prompt: str,
        capability: str = "planning",
        context: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None,
    ) -> str:
        """Announce a new task to the swarm. Returns job_id."""
        job_id = job_id or str(uuid.uuid4())
        payload = {
            "job_id": job_id,
            "capability": capability,
            "prompt": prompt,
            "context": context or {},
            "announced_at_ms": int(time.time() * 1000),
        }
        self._task_payloads[job_id] = payload
        await self.node.publish("TASK_AVAILABLE", payload)
        return job_id

    # ── Handlers ───────────────────────────────────────────────────────────────

    async def _handle_task(self, msg: Dict[str, Any]) -> None:
        payload = msg["payload"]
        job_id: str = payload["job_id"]
        required_cap: str = payload.get("capability", "any")

        if job_id in self._committed_jobs:
            return
        if required_cap != "any" and required_cap != self.capability:
            return

        # Store task payload for winner to use
        self._task_payloads[job_id] = payload

        # Create our bid
        our_bid = Bid(
            job_id=job_id,
            bidder_id=self.node.node_id,
            bidder_role=self.node.role,
            load_score=self._load_fn(),
            capability=self.capability,
        )
        self._pending_bids.setdefault(job_id, []).append(our_bid)

        # Broadcast our bid
        await self.node.publish("BID", {
            "job_id": job_id,
            "bidder_id": our_bid.bidder_id,
            "bidder_role": our_bid.bidder_role,
            "load_score": our_bid.load_score,
            "capability": our_bid.capability,
            "timestamp_ms": our_bid.timestamp_ms,
        })

        # Schedule evaluation after commit window
        loop = asyncio.get_event_loop()
        loop.call_later(
            COMMIT_WINDOW_MS / 1000,
            lambda: asyncio.create_task(self._evaluate_bids(job_id))
        )

    async def _handle_bid(self, msg: Dict[str, Any]) -> None:
        payload = msg["payload"]
        job_id: str = payload["job_id"]
        if job_id in self._committed_jobs:
            return
        bid = Bid(
            job_id=job_id,
            bidder_id=payload["bidder_id"],
            bidder_role=payload["bidder_role"],
            load_score=payload["load_score"],
            capability=payload["capability"],
            timestamp_ms=payload["timestamp_ms"],
        )
        self._pending_bids.setdefault(job_id, []).append(bid)

    async def _handle_commit(self, msg: Dict[str, Any]) -> None:
        payload = msg["payload"]
        job_id: str = payload["job_id"]
        winner_id: str = payload["winner_id"]

        if job_id in self._committed_jobs:
            return
        self._committed_jobs.add(job_id)

        won = (winner_id == self.node.node_id)
        task_payload = self._task_payloads.get(job_id)
        for cb in self._commit_callbacks:
            asyncio.create_task(cb(job_id, won, task_payload))

    async def _evaluate_bids(self, job_id: str) -> None:
        """After commit window: pick winner deterministically and broadcast COMMIT if we win."""
        if job_id in self._committed_jobs:
            return
        bids = self._pending_bids.get(job_id, [])
        if not bids:
            return

        # Deterministic winner: min load → earliest timestamp → lexicographically smallest ID
        winner = min(bids, key=lambda b: (b.load_score, b.timestamp_ms, b.bidder_id))

        if winner.bidder_id != self.node.node_id:
            # We lost — wait for COMMIT from winner
            return

        # We won — broadcast COMMIT
        self._committed_jobs.add(job_id)
        await self.node.publish("COMMIT", {
            "job_id": job_id,
            "winner_id": self.node.node_id,
            "winner_role": self.node.role,
            "capability": self.capability,
            "committed_at_ms": int(time.time() * 1000),
        })

        task_payload = self._task_payloads.get(job_id)
        for cb in self._commit_callbacks:
            asyncio.create_task(cb(job_id, True, task_payload))
