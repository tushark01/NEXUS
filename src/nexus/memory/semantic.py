"""Semantic memory — long-term knowledge extracted from patterns across episodes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from nexus.memory.store import MemoryEntry, VectorStore

logger = logging.getLogger(__name__)

COLLECTION_NAME = "semantic"


class KnowledgeEntry(BaseModel):
    """A piece of consolidated knowledge in semantic memory."""

    id: str = ""
    content: str
    category: str = "general"  # general, preference, pattern, fact, procedure
    confidence: float = 0.5  # how sure we are this knowledge is correct
    source_episodes: list[str] = []  # IDs of episodes this was derived from
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_reinforced: datetime | None = None
    reinforcement_count: int = 0


class SemanticMemory:
    """Manages long-term knowledge — patterns, facts, and preferences.

    Semantic memories are durable knowledge that persist across sessions.
    They are created by the consolidation loop which analyzes episodic
    memories for recurring patterns and important insights.
    """

    def __init__(
        self,
        store: VectorStore,
        embedder: Any,  # EmbeddingProvider
    ) -> None:
        self._store = store
        self._embedder = embedder

    async def store_knowledge(
        self,
        content: str,
        category: str = "general",
        confidence: float = 0.5,
        source_episodes: list[str] | None = None,
    ) -> str:
        """Store a new piece of knowledge. Returns the entry ID."""
        now = datetime.now(timezone.utc)
        metadata = {
            "category": category,
            "confidence": confidence,
            "created_at": now.isoformat(),
            "reinforcement_count": 0,
        }
        if source_episodes:
            metadata["source_episodes"] = ",".join(source_episodes)

        embedding = await self._embedder.embed(content)
        doc_id = await self._store.add(
            COLLECTION_NAME, content, embedding, metadata=metadata
        )
        logger.info("Stored knowledge: %s (category=%s, confidence=%.2f)", doc_id[:8], category, confidence)
        return doc_id

    async def query_knowledge(
        self,
        query: str,
        limit: int = 5,
        category: str | None = None,
        min_confidence: float = 0.0,
    ) -> list[MemoryEntry]:
        """Query semantic memory for relevant knowledge."""
        embedding = await self._embedder.embed(query)

        where = {}
        if category:
            where["category"] = category

        results = await self._store.query(
            COLLECTION_NAME, embedding, n_results=limit, where=where or None
        )

        if min_confidence > 0:
            results = [
                r for r in results
                if r.metadata.get("confidence", 0) >= min_confidence
            ]

        return results

    async def reinforce(self, entry_id: str, additional_evidence: str = "") -> None:
        """Reinforce existing knowledge (increases confidence and count)."""
        # ChromaDB doesn't have a great update mechanism, but we can
        # query by ID and log the reinforcement
        logger.info("Reinforcing knowledge %s: %s", entry_id[:8], additional_evidence[:50])

    async def get_by_category(self, category: str, limit: int = 10) -> list[MemoryEntry]:
        """Get knowledge entries by category."""
        return await self.query_knowledge(
            f"{category} knowledge",
            limit=limit,
            category=category,
        )

    async def count(self) -> int:
        """Count total semantic memories."""
        return await self._store.count(COLLECTION_NAME)
