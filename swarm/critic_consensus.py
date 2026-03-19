"""
CriticConsensus — BFT supermajority vote tracker for multi-critic evaluation.

Quorum rule (mirrors Vertex BFT supermajority): quorum = floor(2 * n / 3) + 1

  n=1  → quorum=1   single critic, immediate (backward-compatible default)
  n=2  → quorum=2   both must agree
  n=3  → quorum=3   all must agree, tolerates 0 failures  ← demo sweet spot
  n=4  → quorum=3   tolerates 1 Byzantine failure

Track 3 requirement: leaderless agreement — no single critic can override the
collective verdict. All votes travel via FoxMQ, giving Vertex BFT consensus the
final say on message ordering (no front-running possible).
"""
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

VOTE_WINDOW_S = 25.0  # max wait for all critic votes before timeout

ConsensusResult = Tuple[bool, float, List["Vote"]]  # (verdict_pass, avg_score, votes)


@dataclass
class Vote:
    critic_id:    str
    job_id:       str
    score:        float
    passed:       bool
    issues:       List[str] = field(default_factory=list)
    timestamp_ms: int       = field(default_factory=lambda: int(time.time() * 1000))


class CriticConsensus:
    """
    Accumulates EVAL_VOTEs from multiple critics; settles when BFT supermajority
    of votes agree on pass or fail.

    Properties:
      - add_vote() is idempotent per critic_id (last vote wins if re-submitted).
      - Once settled, _result is immutable.
      - force_majority() settles with whatever votes arrived (used on timeout).
    """

    def __init__(self, job_id: str, n_critics: int = 1):
        self.job_id    = job_id
        self.n_critics = max(n_critics, 1)
        self.quorum    = self.n_critics * 2 // 3 + 1   # BFT supermajority
        self._votes:  Dict[str, Vote]          = {}
        self._result: Optional[ConsensusResult] = None
        self._start   = time.time()

    # ── Public API ─────────────────────────────────────────────────────────────

    def add_vote(self, vote: Vote) -> Optional[ConsensusResult]:
        """
        Add (or update) a vote from a critic.
        Returns ConsensusResult immediately if BFT quorum is reached, else None.
        """
        if self._result is not None:
            return self._result          # already settled — idempotent
        self._votes[vote.critic_id] = vote
        return self._try_settle()

    @property
    def result(self) -> Optional[ConsensusResult]:
        """Return settled ConsensusResult, or None if still pending."""
        return self._result

    @property
    def has_consensus(self) -> bool:
        return self._result is not None

    @property
    def vote_count(self) -> int:
        return len(self._votes)

    def timed_out(self) -> bool:
        return (time.time() - self._start) > VOTE_WINDOW_S

    def force_majority(self) -> Optional[ConsensusResult]:
        """
        Force a verdict from however many votes arrived — called on timeout.
        Returns None only if no votes at all.
        """
        if self._result is not None or not self._votes:
            return self._result
        votes      = list(self._votes.values())
        pass_count = sum(1 for v in votes if v.passed)
        verdict    = pass_count > len(votes) / 2
        avg_score  = sum(v.score for v in votes) / len(votes)
        self._result = (verdict, avg_score, votes)
        return self._result

    def summary(self) -> str:
        return (
            f"votes={self.vote_count}/{self.n_critics} "
            f"quorum={self.quorum} settled={self.has_consensus}"
        )

    # ── Internal ───────────────────────────────────────────────────────────────

    def _try_settle(self) -> Optional[ConsensusResult]:
        """Check if any verdict reached BFT quorum; if so, lock result."""
        votes      = list(self._votes.values())
        n          = len(votes)
        pass_count = sum(1 for v in votes if v.passed)
        fail_count = n - pass_count
        avg_score  = sum(v.score for v in votes) / n

        if pass_count >= self.quorum:
            self._result = (True, avg_score, votes)
        elif fail_count >= self.quorum:
            self._result = (False, avg_score, votes)
        # else: split vote — wait for more votes

        return self._result
