"""Memory manager — unified interface to the tri-layer memory system."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from nexus.llm.schemas import Message
from nexus.memory.store import MemoryEntry
from nexus.memory.working import WorkingMemory

if TYPE_CHECKING:
    from nexus.memory.consolidation import ConsolidationLoop
    from nexus.memory.embeddings import EmbeddingProvider
    from nexus.memory.episodic import EpisodicMemory
    from nexus.memory.semantic import SemanticMemory
    from nexus.memory.store import VectorStore

logger = logging.getLogger(__name__)


class MemoryManager:
    """Unified facade for the NEXUS tri-layer memory system.

    Layers:
    - Working: Current conversation context (per-session message buffer)
    - Episodic: Specific interactions and events (vector-indexed)
    - Semantic: Long-term knowledge extracted from patterns

    The consolidation loop periodically promotes episodic -> semantic.
    """

    def __init__(
        self,
        working: WorkingMemory,
        vector_store: VectorStore | None = None,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        self.working = working
        self._store = vector_store
        self._embedder = embedder
        self._episodic: EpisodicMemory | None = None
        self._semantic: SemanticMemory | None = None
        self._consolidation: ConsolidationLoop | None = None

        # Initialize episodic + semantic if vector store is available
        if vector_store and embedder:
            from nexus.memory.episodic import EpisodicMemory
            from nexus.memory.semantic import SemanticMemory

            self._episodic = EpisodicMemory(store=vector_store, embedder=embedder)
            self._semantic = SemanticMemory(store=vector_store, embedder=embedder)

    # --- Working memory shortcuts ---

    def add_message(self, session_id: str, message: Message) -> None:
        self.working.add_message(session_id, message)

    def get_messages(self, session_id: str) -> list[Message]:
        return self.working.get_messages(session_id)

    def clear_session(self, session_id: str) -> None:
        self.working.clear_session(session_id)

    # --- Episodic memory ---

    async def store_episodic(
        self, text: str, metadata: dict[str, Any] | None = None
    ) -> str | None:
        """Store an interaction in episodic memory."""
        if not self._episodic:
            return None
        episode_type = (metadata or {}).pop("episode_type", "interaction")
        session_id = (metadata or {}).get("session_id")
        importance = (metadata or {}).pop("importance", 0.5)
        return await self._episodic.record(
            content=text,
            episode_type=episode_type,
            session_id=session_id,
            importance=importance,
        )

    async def recall(
        self, query: str, limit: int = 5
    ) -> list[MemoryEntry]:
        """Search across episodic memory for relevant content."""
        if not self._episodic:
            return []
        return await self._episodic.recall(query, limit=limit)

    # --- Semantic memory ---

    async def store_knowledge(
        self,
        content: str,
        category: str = "general",
        confidence: float = 0.5,
    ) -> str | None:
        """Store knowledge in semantic memory."""
        if not self._semantic:
            return None
        return await self._semantic.store_knowledge(
            content=content,
            category=category,
            confidence=confidence,
        )

    async def query_knowledge(
        self, query: str, limit: int = 3
    ) -> list[MemoryEntry]:
        """Query semantic memory for relevant knowledge."""
        if not self._semantic:
            return []
        return await self._semantic.query_knowledge(query, limit=limit)

    # --- Unified context building ---

    async def get_context_for_prompt(self, query: str, max_entries: int = 3) -> str:
        """Build a context string from relevant memories for LLM prompt injection.

        Combines results from both episodic and semantic memory layers.
        """
        parts: list[str] = []

        # Query semantic memory (long-term knowledge)
        knowledge = await self.query_knowledge(query, limit=max_entries)
        if knowledge:
            parts.append("[Long-term knowledge]")
            for entry in knowledge:
                parts.append(f"- {entry.text}")

        # Query episodic memory (specific past interactions)
        episodes = await self.recall(query, limit=max_entries)
        if episodes:
            parts.append("[Relevant past interactions]")
            for entry in episodes:
                parts.append(f"- {entry.text}")

        return "\n".join(parts) if parts else ""

    # --- Consolidation ---

    def init_consolidation(self, llm: Any, interval_hours: int = 24) -> None:
        """Initialize the consolidation loop (call after LLM router is ready)."""
        if self._episodic and self._semantic:
            from nexus.memory.consolidation import ConsolidationLoop

            self._consolidation = ConsolidationLoop(
                episodic=self._episodic,
                semantic=self._semantic,
                llm=llm,
                interval_hours=interval_hours,
            )

    async def start_consolidation(self) -> None:
        """Start the background consolidation loop."""
        if self._consolidation:
            await self._consolidation.start()

    async def stop_consolidation(self) -> None:
        """Stop the consolidation loop."""
        if self._consolidation:
            await self._consolidation.stop()

    async def consolidate_now(self) -> int:
        """Trigger immediate consolidation. Returns knowledge entries created."""
        if self._consolidation:
            return await self._consolidation.consolidate_now()
        return 0

    # --- Stats ---

    async def stats(self) -> dict[str, Any]:
        """Return memory statistics across all layers."""
        stats: dict[str, Any] = {
            "working_sessions": len(self.working.active_sessions),
        }
        if self._episodic:
            stats["episodic_count"] = await self._episodic.count()
        if self._semantic:
            stats["semantic_count"] = await self._semantic.count()
        if self._consolidation:
            stats["consolidation_running"] = self._consolidation.is_running
            stats["consolidation_cycles"] = self._consolidation.consolidation_count
        return stats
