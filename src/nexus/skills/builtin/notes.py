"""Notes skill — persistent note-taking using the memory system."""

from __future__ import annotations

from typing import Any

from nexus.security.capabilities import Capability
from nexus.skills.base import BaseSkill, ParameterDef, SkillManifest, SkillResult


class NotesSkill(BaseSkill):
    """Take, search, and retrieve persistent notes."""

    manifest = SkillManifest(
        name="notes",
        description="Save and search persistent notes. Notes are stored in long-term memory and can be retrieved by semantic search.",
        capabilities_required=[Capability.MEMORY_READ, Capability.MEMORY_WRITE],
        parameters={
            "action": ParameterDef(
                type="string",
                description="Action to perform",
                enum=["save", "search"],
                required=True,
            ),
            "content": ParameterDef(
                type="string",
                description="Note content (for save) or search query (for search)",
                required=True,
            ),
            "tags": ParameterDef(
                type="string",
                description="Comma-separated tags for the note",
                required=False,
            ),
        },
    )

    def __init__(self, memory_manager: Any = None) -> None:
        self._memory = memory_manager

    async def execute(self, params: dict[str, Any]) -> SkillResult:
        action = params.get("action", "")
        content = params.get("content", "")

        if not content:
            return SkillResult(success=False, error="Content is required")

        if not self._memory:
            return SkillResult(success=False, error="Memory system not available")

        if action == "save":
            tags = params.get("tags", "")
            metadata = {"type": "note"}
            if tags:
                metadata["tags"] = tags

            doc_id = await self._memory.store_episodic(content, metadata=metadata)
            return SkillResult(
                success=True,
                output=f"Note saved (id: {doc_id})",
                metadata={"id": doc_id},
            )

        elif action == "search":
            entries = await self._memory.recall(content, limit=5)
            if entries:
                results = "\n\n".join(
                    f"[{e.id[:8]}] {e.text}" for e in entries
                )
                return SkillResult(
                    success=True,
                    output=results,
                    metadata={"count": len(entries)},
                )
            return SkillResult(success=True, output="No matching notes found.")

        else:
            return SkillResult(success=False, error=f"Unknown action: {action}")
