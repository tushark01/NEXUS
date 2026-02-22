"""Memory consolidation loop — promotes episodic patterns into semantic knowledge."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

CONSOLIDATION_PROMPT = """\
You are the NEXUS Memory Consolidation System. Analyze these episodic memories \
and extract durable knowledge.

Episodic memories:
{episodes}

For each meaningful pattern, preference, or fact you identify, output a JSON array:
[
  {{
    "content": "The extracted knowledge or pattern",
    "category": "general|preference|pattern|fact|procedure",
    "confidence": 0.0-1.0
  }}
]

Rules:
- Only extract knowledge that appears across multiple episodes or is clearly significant.
- Don't just restate individual episodes — find the underlying pattern.
- Assign higher confidence to patterns with more evidence.
- Return an empty array [] if no meaningful patterns emerge.

Return ONLY the JSON array."""


class ConsolidationLoop:
    """Background task that periodically consolidates episodic -> semantic memory.

    The loop:
    1. Fetches high-importance recent episodic memories
    2. Uses an LLM to identify patterns and knowledge
    3. Stores extracted knowledge in semantic memory
    4. Optionally prunes old low-importance episodes
    """

    def __init__(
        self,
        episodic: Any,  # EpisodicMemory
        semantic: Any,  # SemanticMemory
        llm: Any,  # ModelRouter
        interval_hours: int = 24,
        min_episodes: int = 5,
    ) -> None:
        self._episodic = episodic
        self._semantic = semantic
        self._llm = llm
        self._interval = interval_hours * 3600
        self._min_episodes = min_episodes
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._consolidation_count = 0

    async def start(self) -> None:
        """Start the consolidation loop as a background task."""
        if self._task is not None:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Consolidation loop started (interval: %dh)", self._interval // 3600)

    async def stop(self) -> None:
        """Stop the consolidation loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        """Main consolidation loop."""
        while self._running:
            try:
                await asyncio.sleep(self._interval)
                await self.consolidate()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Consolidation error")

    async def consolidate(self) -> int:
        """Run one consolidation cycle. Returns number of knowledge entries created."""
        episodes = await self._episodic.get_high_importance(threshold=0.6, limit=20)
        if len(episodes) < self._min_episodes:
            logger.debug("Not enough episodes for consolidation (%d < %d)", len(episodes), self._min_episodes)
            return 0

        # Build episodes text for the LLM
        episodes_text = ""
        episode_ids = []
        for i, ep in enumerate(episodes, 1):
            episodes_text += f"\n{i}. [{ep.metadata.get('episode_type', 'unknown')}] {ep.text}\n"
            episode_ids.append(ep.id)

        # Use LLM to extract knowledge
        from nexus.llm.schemas import LLMRequest, Message, TaskComplexity

        request = LLMRequest(
            messages=[
                Message(role="system", content="You are a knowledge extraction system."),
                Message(role="user", content=CONSOLIDATION_PROMPT.format(episodes=episodes_text)),
            ]
        )

        try:
            response = await self._llm.complete(request, hint=TaskComplexity.COMPLEX)
        except Exception as e:
            logger.error("LLM call failed during consolidation: %s", e)
            return 0

        # Parse extracted knowledge
        import json

        created = 0
        try:
            json_str = response.content.strip()
            if "```" in json_str:
                start = json_str.find("[")
                end = json_str.rfind("]") + 1
                if start >= 0 and end > start:
                    json_str = json_str[start:end]

            knowledge_items = json.loads(json_str)

            for item in knowledge_items:
                await self._semantic.store_knowledge(
                    content=item["content"],
                    category=item.get("category", "general"),
                    confidence=item.get("confidence", 0.5),
                    source_episodes=episode_ids,
                )
                created += 1

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to parse consolidation output: %s", e)

        self._consolidation_count += 1
        logger.info("Consolidation complete: %d knowledge entries created", created)
        return created

    async def consolidate_now(self) -> int:
        """Trigger immediate consolidation (for manual use / CLI command)."""
        return await self.consolidate()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def consolidation_count(self) -> int:
        return self._consolidation_count
