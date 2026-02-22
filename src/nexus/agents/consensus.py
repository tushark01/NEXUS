"""Consensus engine — agents vote and reach agreement on decisions."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class VoteType(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


class Vote(BaseModel):
    """A single agent's vote on a proposal."""

    agent_id: str
    vote: VoteType
    reasoning: str = ""
    confidence: float = 0.5  # 0.0 - 1.0


class Proposal(BaseModel):
    """A proposal submitted for consensus."""

    proposal_id: str
    title: str
    content: Any
    submitted_by: str
    votes: list[Vote] = []
    resolved: bool = False
    accepted: bool = False

    @property
    def vote_counts(self) -> dict[str, int]:
        counts = {"approve": 0, "reject": 0, "abstain": 0}
        for v in self.votes:
            counts[v.vote.value] += 1
        return counts


class ConsensusStrategy(str, Enum):
    MAJORITY = "majority"  # >50% approve
    SUPERMAJORITY = "supermajority"  # >=2/3 approve
    UNANIMOUS = "unanimous"  # all approve
    WEIGHTED = "weighted"  # confidence-weighted voting


class ConsensusEngine:
    """Manages voting and agreement between agents.

    Supports multiple consensus strategies:
    - Majority: >50% approve votes
    - Supermajority: >=66.7% approve votes
    - Unanimous: all voters must approve
    - Weighted: confidence-weighted scoring
    """

    def __init__(self, strategy: ConsensusStrategy = ConsensusStrategy.MAJORITY) -> None:
        self._strategy = strategy
        self._proposals: dict[str, Proposal] = {}

    def create_proposal(
        self,
        proposal_id: str,
        title: str,
        content: Any,
        submitted_by: str,
    ) -> Proposal:
        """Create a new proposal for voting."""
        proposal = Proposal(
            proposal_id=proposal_id,
            title=title,
            content=content,
            submitted_by=submitted_by,
        )
        self._proposals[proposal_id] = proposal
        logger.info("Proposal created: %s by %s", proposal_id, submitted_by)
        return proposal

    def cast_vote(
        self,
        proposal_id: str,
        agent_id: str,
        vote: VoteType,
        reasoning: str = "",
        confidence: float = 0.5,
    ) -> Vote | None:
        """Cast a vote on a proposal. Returns the Vote or None if proposal not found."""
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.resolved:
            return None

        # Prevent double-voting
        for existing in proposal.votes:
            if existing.agent_id == agent_id:
                logger.warning("Agent %s already voted on %s", agent_id, proposal_id)
                return existing

        v = Vote(
            agent_id=agent_id,
            vote=vote,
            reasoning=reasoning,
            confidence=confidence,
        )
        proposal.votes.append(v)
        logger.info("Vote cast: %s -> %s on %s", agent_id, vote.value, proposal_id)
        return v

    def resolve(self, proposal_id: str, min_voters: int = 1) -> bool | None:
        """Resolve a proposal based on the consensus strategy.

        Returns:
            True if accepted, False if rejected, None if not enough votes.
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return None

        non_abstain = [v for v in proposal.votes if v.vote != VoteType.ABSTAIN]
        if len(non_abstain) < min_voters:
            return None

        accepted = self._evaluate(proposal)
        proposal.resolved = True
        proposal.accepted = accepted

        logger.info(
            "Proposal %s resolved: %s (votes: %s)",
            proposal_id,
            "ACCEPTED" if accepted else "REJECTED",
            proposal.vote_counts,
        )
        return accepted

    def _evaluate(self, proposal: Proposal) -> bool:
        """Evaluate votes according to the current strategy."""
        counts = proposal.vote_counts
        total_cast = counts["approve"] + counts["reject"]

        if total_cast == 0:
            return False

        if self._strategy == ConsensusStrategy.MAJORITY:
            return counts["approve"] > total_cast / 2

        elif self._strategy == ConsensusStrategy.SUPERMAJORITY:
            return counts["approve"] >= total_cast * 2 / 3

        elif self._strategy == ConsensusStrategy.UNANIMOUS:
            return counts["reject"] == 0 and counts["approve"] > 0

        elif self._strategy == ConsensusStrategy.WEIGHTED:
            weighted_approve = sum(
                v.confidence for v in proposal.votes if v.vote == VoteType.APPROVE
            )
            weighted_reject = sum(
                v.confidence for v in proposal.votes if v.vote == VoteType.REJECT
            )
            return weighted_approve > weighted_reject

        return False

    def get_proposal(self, proposal_id: str) -> Proposal | None:
        return self._proposals.get(proposal_id)

    @property
    def pending_proposals(self) -> list[Proposal]:
        return [p for p in self._proposals.values() if not p.resolved]

    def summary(self) -> str:
        total = len(self._proposals)
        resolved = sum(1 for p in self._proposals.values() if p.resolved)
        accepted = sum(1 for p in self._proposals.values() if p.accepted)
        return (
            f"Strategy: {self._strategy.value}\n"
            f"Proposals: {total} total, {resolved} resolved, {accepted} accepted"
        )
