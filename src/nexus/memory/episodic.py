"""Episodic memory — stores and retrieves specific interactions and experiences."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from nexus.memory.store import MemoryEntry, VectorStore

logger = logging.getLogger(__name__)

COLLECTION_NAME = "episodic"


class Episode(BaseModel):
    """A single episodic memory — a recorded interaction or event."""

    id: str = ""
    content: str
    episode_type: str = "interaction"  # interaction, task_result, observation, insight
    session_id: str | None = None
    agent_id: str | None = None
    importance: float = 0.5  # 0.0 - 1.0, affects consolidation priority
    access_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime | None = None


class EpisodicMemory:
    """Manages episodic memories — specific interactions, events, and experiences.

    Episodic memories are individual recorded events that can be recalled
    by semantic similarity. High-importance episodes are candidates for
    consolidation into semantic memory (long-term knowledge).
    """

    def __init__(
        self,
        store: VectorStore,
        embedder: Any,  # EmbeddingProvider
    ) -> None:
        self._store = store
        self._embedder = embedder

    async def record(
        self,
        content: str,
        episode_type: str = "interaction",
        session_id: str | None = None,
        agent_id: str | None = None,
        importance: float = 0.5,
    ) -> str:
        """Record a new episode. Returns the episode ID."""
        now = datetime.now(timezone.utc)
        metadata = {
            "episode_type": episode_type,
            "importance": importance,
            "created_at": now.isoformat(),
            "access_count": 0,
        }
        if session_id:
            metadata["session_id"] = session_id
        if agent_id:
            metadata["agent_id"] = agent_id

        embedding = await self._embedder.embed(content)
        doc_id = await self._store.add(
            COLLECTION_NAME, content, embedding, metadata=metadata
        )
        logger.debug("Recorded episode: %s (type=%s, importance=%.2f)", doc_id[:8], episode_type, importance)
        return doc_id

    async def recall(
        self,
        query: str,
        limit: int = 5,
        episode_type: str | None = None,
        min_importance: float = 0.0,
    ) -> list[MemoryEntry]:
        """Recall episodes similar to a query.

        Args:
            query: Text to search for
            limit: Max results
            episode_type: Filter by type (interaction, task_result, etc.)
            min_importance: Minimum importance threshold
        """
        embedding = await self._embedder.embed(query)

        where = {}
        if episode_type:
            where["episode_type"] = episode_type

        results = await self._store.query(
            COLLECTION_NAME, embedding, n_results=limit, where=where or None
        )

        # Post-filter by importance
        if min_importance > 0:
            results = [
                r for r in results
                if r.metadata.get("importance", 0) >= min_importance
            ]

        return results

    async def get_recent(self, limit: int = 10) -> list[MemoryEntry]:
        """Get the most recently stored episodes."""
        # ChromaDB doesn't support ORDER BY, so we query with a generic embedding
        # and rely on insertion order as approximation
        dummy_embedding = await self._embedder.embed("recent interactions")
        return await self._store.query(COLLECTION_NAME, dummy_embedding, n_results=limit)

    async def get_high_importance(self, threshold: float = 0.7, limit: int = 20) -> list[MemoryEntry]:
        """Get high-importance episodes (candidates for consolidation)."""
        dummy_embedding = await self._embedder.embed("important interactions patterns")
        results = await self._store.query(COLLECTION_NAME, dummy_embedding, n_results=limit * 2)
        return [
            r for r in results
            if r.metadata.get("importance", 0) >= threshold
        ][:limit]

    async def count(self) -> int:
        """Count total episodic memories."""
        return await self._store.count(COLLECTION_NAME)
