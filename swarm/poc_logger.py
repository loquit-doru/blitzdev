"""
Proof of Coordination (PoC) Logger for the FlashForge Agent Swarm.

Each PoC entry is HMAC-SHA256 signed so that:
  1. Events are tamper-evident — any modification breaks the chain.
  2. Any verifier with the shared secret can re-verify all signatures.
  3. A rolling chain-hash links each entry to the previous one (like a mini-blockchain).
  4. Multi-stage coordination is provable: who did what, when, in what order.

Log format: newline-delimited JSON (JSONL), one entry per event.
File location: poc_logs/poc_{job_id}.jsonl

Use verify_poc_log() to independently verify a completed log.
"""
import hashlib
import hmac as _hmac_mod
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class PoCLogger:
    """
    Append-only, HMAC-chained Proof of Coordination log.

    Every entry contains:
      seq          — monotonically increasing sequence number
      job_id       — which job this belongs to
      event        — event name (e.g. PLAN_READY, BUILD_COMPLETE, EVAL_PASS)
      actor        — node_id or role that produced this event
      timestamp_ms — unix millisecond timestamp
      prev_chain   — HMAC of the previous entry (empty string for first)
      data         — arbitrary event-specific data
      hmac         — HMAC-SHA256 of all of the above (sorted canonical JSON)
    """

    def __init__(
        self,
        job_id: str,
        secret: str = "swarm-secret-change-in-prod",
        log_dir: str = "./poc_logs",
    ):
        self.job_id = job_id
        self._secret = secret.encode()
        self._log_path = Path(log_dir) / f"poc_{job_id}.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._seq = 0
        self._chain_hash = ""   # HMAC of last entry (empty for genesis)
        self._resume_from_file()  # continue chain if file already has entries

    # ── Public API ─────────────────────────────────────────────────────────────

    def _resume_from_file(self) -> None:
        """If the log file already exists, fast-forward seq + chain_hash to its last entry."""
        if not self._log_path.exists():
            return
        last_entry = None
        with open(self._log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        last_entry = json.loads(line)
                    except json.JSONDecodeError:
                        pass
        if last_entry is not None:
            self._seq = last_entry.get("seq", 0) + 1
            self._chain_hash = last_entry.get("hmac", "")

    # ── Public API ─────────────────────────────────────────────────────────────

    def record(
        self,
        event: str,
        actor: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Append a signed event to the PoC log. Returns the signed entry."""
        entry: Dict[str, Any] = {
            "seq": self._seq,
            "job_id": self.job_id,
            "event": event,
            "actor": actor,
            "timestamp_ms": int(time.time() * 1000),
            "prev_chain": self._chain_hash,
            "data": data or {},
        }
        entry["hmac"] = self._sign(entry)
        self._chain_hash = entry["hmac"]
        self._seq += 1

        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")

        return entry

    def finalize(self, signers: List[str]) -> Dict[str, Any]:
        """
        Append a COORDINATION_COMPLETE summary entry and return it.

        signers: list of node_ids or roles that contributed to this job.
        """
        return self.record(
            "COORDINATION_COMPLETE",
            actor="swarm",
            data={
                "signers": signers,
                "total_events": self._seq,
                "chain_root": self._chain_hash,
            },
        )

    @property
    def log_path(self) -> Path:
        return self._log_path

    @property
    def chain_hash(self) -> str:
        """Current chain tip (HMAC of last written entry)."""
        return self._chain_hash

    # ── HMAC helper ────────────────────────────────────────────────────────────

    def _sign(self, entry: Dict[str, Any]) -> str:
        body = {k: v for k, v in entry.items() if k != "hmac"}
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        return _hmac_mod.new(self._secret, canonical, hashlib.sha256).hexdigest()


# ── Standalone verifier ────────────────────────────────────────────────────────

def verify_poc_log(log_path: str, secret: str) -> bool:
    """
    Re-compute and verify every HMAC + chain link in a PoC log file.

    Returns True if the log is intact, False if any tampering is detected.
    Prints a human-readable report for each entry.
    """
    secret_bytes = secret.encode()
    prev_chain = ""
    ok = True

    print(f"\n🔍 Verifying PoC log: {log_path}")
    print("─" * 60)

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            seq = entry.get("seq", "?")
            event = entry.get("event", "?")

            # 1. Chain link
            if entry.get("prev_chain") != prev_chain:
                print(f"  ✗ seq {seq} [{event}] CHAIN BREAK")
                ok = False
            else:
                # 2. HMAC
                stored_hmac = entry.get("hmac", "")
                body = {k: v for k, v in entry.items() if k != "hmac"}
                canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
                computed = _hmac_mod.new(secret_bytes, canonical, hashlib.sha256).hexdigest()
                if _hmac_mod.compare_digest(stored_hmac, computed):
                    print(f"  ✓ seq {seq:>3} [{event}]  actor={entry.get('actor')}")
                    prev_chain = stored_hmac
                else:
                    print(f"  ✗ seq {seq} [{event}] HMAC MISMATCH — TAMPERED")
                    ok = False

    print("─" * 60)
    print(f"  {'✅ Log VALID — coordination proof intact.' if ok else '❌ Log INVALID — tampering detected.'}")
    return ok
