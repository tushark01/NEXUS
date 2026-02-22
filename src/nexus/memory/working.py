"""Working memory — current conversation context with sliding window."""

from __future__ import annotations

import logging

from nexus.llm.schemas import Message

logger = logging.getLogger(__name__)


class WorkingMemory:
    """Manages per-session conversation context with a token budget."""

    def __init__(self, max_messages: int = 50) -> None:
        self._sessions: dict[str, list[Message]] = {}
        self._max_messages = max_messages

    def add_message(self, session_id: str, message: Message) -> None:
        """Add a message to a session, evicting oldest if over budget."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        self._sessions[session_id].append(message)

        # Keep system messages + trim oldest non-system messages
        messages = self._sessions[session_id]
        if len(messages) > self._max_messages:
            system_msgs = [m for m in messages if m.role == "system"]
            non_system = [m for m in messages if m.role != "system"]
            # Keep the most recent messages
            trimmed = non_system[-(self._max_messages - len(system_msgs)) :]
            self._sessions[session_id] = system_msgs + trimmed

    def get_messages(self, session_id: str) -> list[Message]:
        """Return current conversation for a session."""
        return self._sessions.get(session_id, [])

    def clear_session(self, session_id: str) -> None:
        """Clear all messages for a session."""
        self._sessions.pop(session_id, None)

    def has_session(self, session_id: str) -> bool:
        return session_id in self._sessions

    @property
    def active_sessions(self) -> list[str]:
        return list(self._sessions.keys())
