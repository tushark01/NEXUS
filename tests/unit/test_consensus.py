"""Tests for the ConsensusEngine."""

import pytest

from nexus.agents.consensus import ConsensusEngine, ConsensusStrategy, VoteType


class TestConsensusEngine:
    def test_create_proposal(self):
        engine = ConsensusEngine()
        p = engine.create_proposal("p1", "Test", "content", "agent_a")
        assert p.proposal_id == "p1"
        assert not p.resolved

    def test_cast_vote(self):
        engine = ConsensusEngine()
        engine.create_proposal("p1", "Test", "content", "agent_a")
        v = engine.cast_vote("p1", "agent_b", VoteType.APPROVE, "looks good")
        assert v is not None
        assert v.vote == VoteType.APPROVE

    def test_no_double_vote(self):
        engine = ConsensusEngine()
        engine.create_proposal("p1", "Test", "content", "agent_a")
        engine.cast_vote("p1", "agent_b", VoteType.APPROVE)
        v2 = engine.cast_vote("p1", "agent_b", VoteType.REJECT)
        # Should return original vote, not cast a new one
        assert v2.vote == VoteType.APPROVE

    def test_majority_accept(self):
        engine = ConsensusEngine(ConsensusStrategy.MAJORITY)
        engine.create_proposal("p1", "Test", "content", "agent_a")
        engine.cast_vote("p1", "agent_b", VoteType.APPROVE)
        engine.cast_vote("p1", "agent_c", VoteType.APPROVE)
        engine.cast_vote("p1", "agent_d", VoteType.REJECT)
        result = engine.resolve("p1")
        assert result is True

    def test_majority_reject(self):
        engine = ConsensusEngine(ConsensusStrategy.MAJORITY)
        engine.create_proposal("p1", "Test", "content", "agent_a")
        engine.cast_vote("p1", "agent_b", VoteType.REJECT)
        engine.cast_vote("p1", "agent_c", VoteType.REJECT)
        engine.cast_vote("p1", "agent_d", VoteType.APPROVE)
        result = engine.resolve("p1")
        assert result is False

    def test_unanimous_accept(self):
        engine = ConsensusEngine(ConsensusStrategy.UNANIMOUS)
        engine.create_proposal("p1", "Test", "content", "agent_a")
        engine.cast_vote("p1", "agent_b", VoteType.APPROVE)
        engine.cast_vote("p1", "agent_c", VoteType.APPROVE)
        result = engine.resolve("p1")
        assert result is True

    def test_unanimous_reject_on_any_reject(self):
        engine = ConsensusEngine(ConsensusStrategy.UNANIMOUS)
        engine.create_proposal("p1", "Test", "content", "agent_a")
        engine.cast_vote("p1", "agent_b", VoteType.APPROVE)
        engine.cast_vote("p1", "agent_c", VoteType.REJECT)
        result = engine.resolve("p1")
        assert result is False

    def test_supermajority(self):
        engine = ConsensusEngine(ConsensusStrategy.SUPERMAJORITY)
        engine.create_proposal("p1", "Test", "content", "agent_a")
        engine.cast_vote("p1", "a1", VoteType.APPROVE, confidence=0.9)
        engine.cast_vote("p1", "a2", VoteType.APPROVE, confidence=0.8)
        engine.cast_vote("p1", "a3", VoteType.REJECT, confidence=0.3)
        result = engine.resolve("p1")
        assert result is True  # 2/3 >= 66.7%

    def test_weighted_voting(self):
        engine = ConsensusEngine(ConsensusStrategy.WEIGHTED)
        engine.create_proposal("p1", "Test", "content", "agent_a")
        engine.cast_vote("p1", "a1", VoteType.APPROVE, confidence=0.9)
        engine.cast_vote("p1", "a2", VoteType.REJECT, confidence=0.3)
        result = engine.resolve("p1")
        assert result is True  # 0.9 > 0.3

    def test_not_enough_votes(self):
        engine = ConsensusEngine()
        engine.create_proposal("p1", "Test", "content", "agent_a")
        result = engine.resolve("p1", min_voters=2)
        assert result is None

    def test_abstain_ignored(self):
        engine = ConsensusEngine(ConsensusStrategy.MAJORITY)
        engine.create_proposal("p1", "Test", "content", "agent_a")
        engine.cast_vote("p1", "a1", VoteType.APPROVE)
        engine.cast_vote("p1", "a2", VoteType.ABSTAIN)
        result = engine.resolve("p1")
        assert result is True  # 1 approve, 0 reject (abstain not counted)

    def test_pending_proposals(self):
        engine = ConsensusEngine()
        engine.create_proposal("p1", "Test1", "c", "a")
        engine.create_proposal("p2", "Test2", "c", "a")
        assert len(engine.pending_proposals) == 2
        engine.cast_vote("p1", "b", VoteType.APPROVE)
        engine.resolve("p1")
        assert len(engine.pending_proposals) == 1

    def test_summary(self):
        engine = ConsensusEngine()
        s = engine.summary()
        assert "majority" in s.lower()
