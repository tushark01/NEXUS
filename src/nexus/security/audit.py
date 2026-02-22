"""Structured audit logging — append-only JSONL for all security events."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AuditEvent(BaseModel):
    """A single audit log entry."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str  # "skill_invoked", "capability_checked", "rate_limited", etc.
    actor: str  # agent_id or "user"
    action: str
    resource: str
    result: Literal["allowed", "denied", "error"]
    details: dict[str, Any] = {}


class AuditLogger:
    """Append-only structured audit log for all security-relevant events."""

    def __init__(self, log_path: Path) -> None:
        self._log_path = log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Audit log: %s", log_path)

    async def log(self, event: AuditEvent) -> None:
        """Append a JSON-lines entry to the audit log."""
        line = event.model_dump_json() + "\n"
        with open(self._log_path, "a") as f:
            f.write(line)

    async def log_action(
        self,
        event_type: str,
        actor: str,
        action: str,
        resource: str,
        result: Literal["allowed", "denied", "error"],
        details: dict[str, Any] | None = None,
    ) -> None:
        """Convenience method to log an action."""
        await self.log(
            AuditEvent(
                event_type=event_type,
                actor=actor,
                action=action,
                resource=resource,
                result=result,
                details=details or {},
            )
        )

    async def query(
        self,
        event_type: str | None = None,
        actor: str | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Search the audit log (for dashboard display)."""
        if not self._log_path.exists():
            return []

        entries: list[AuditEvent] = []
        with open(self._log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = AuditEvent.model_validate_json(line)
                if event_type and entry.event_type != event_type:
                    continue
                if actor and entry.actor != actor:
                    continue
                entries.append(entry)

        return entries[-limit:]
