"""Capability-based permission system — every skill declares what it needs."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from pydantic import BaseModel

from nexus.core.errors import CapabilityDeniedError

logger = logging.getLogger(__name__)


class Capability(str, Enum):
    """All possible capabilities a skill can request."""

    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    NETWORK_HTTP = "network:http"
    NETWORK_WEBSOCKET = "network:websocket"
    SHELL_EXECUTE = "shell:execute"
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    LLM_INVOKE = "llm:invoke"
    SYSTEM_INFO = "system:info"


class CapabilityGrant(BaseModel):
    """A granted capability with optional constraints."""

    capability: Capability
    constraints: dict[str, Any] = {}
    # Examples:
    #   FILE_READ:  {"paths": ["/tmp/nexus/*", "~/documents/*"]}
    #   NETWORK_HTTP: {"domains": ["api.example.com"], "methods": ["GET"]}
    #   SHELL_EXECUTE: {"commands": ["ls", "cat", "grep"]}


class CapabilityEnforcer:
    """Checks and enforces capability grants at runtime."""

    def __init__(self) -> None:
        # skill_name -> list of granted capabilities
        self._grants: dict[str, list[CapabilityGrant]] = {}
        # Global default grants (applied to all skills)
        self._default_grants: list[CapabilityGrant] = [
            CapabilityGrant(capability=Capability.LLM_INVOKE),
            CapabilityGrant(capability=Capability.MEMORY_READ),
        ]

    def grant(self, skill_name: str, grants: list[CapabilityGrant]) -> None:
        """Grant capabilities to a skill."""
        self._grants[skill_name] = grants
        logger.info(
            "Granted %d capabilities to skill '%s'",
            len(grants),
            skill_name,
        )

    def check(
        self,
        skill_name: str,
        required: Capability,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Check if a skill has a capability. Raises CapabilityDeniedError if not."""
        grants = self._grants.get(skill_name, []) + self._default_grants

        for grant in grants:
            if grant.capability == required:
                if self._check_constraints(grant.constraints, context):
                    return True

        logger.warning(
            "Capability DENIED: skill=%s capability=%s",
            skill_name,
            required.value,
        )
        raise CapabilityDeniedError(
            f"Skill '{skill_name}' lacks capability '{required.value}'"
        )

    def _check_constraints(
        self, constraints: dict[str, Any], context: dict[str, Any] | None
    ) -> bool:
        """Verify that context satisfies capability constraints."""
        if not constraints:
            return True
        if not context:
            return True  # No context to check against

        # Check path constraints
        if "paths" in constraints and "path" in context:
            from fnmatch import fnmatch

            path = context["path"]
            if not any(fnmatch(path, pattern) for pattern in constraints["paths"]):
                return False

        # Check domain constraints
        if "domains" in constraints and "domain" in context:
            if context["domain"] not in constraints["domains"]:
                return False

        # Check command constraints
        if "commands" in constraints and "command" in context:
            if context["command"] not in constraints["commands"]:
                return False

        return True

    def get_grants(self, skill_name: str) -> list[CapabilityGrant]:
        """Return all capabilities granted to a skill."""
        return self._grants.get(skill_name, []) + self._default_grants
