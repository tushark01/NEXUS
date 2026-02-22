"""Skill registry — stores and manages available skills with capability checking."""

from __future__ import annotations

import logging
from typing import Any

from nexus.core.errors import CapabilityDeniedError, SkillNotFoundError
from nexus.llm.schemas import ToolDefinition
from nexus.security.audit import AuditLogger
from nexus.security.capabilities import CapabilityEnforcer
from nexus.skills.base import BaseSkill, SkillResult

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Registry of available skills with security enforcement."""

    def __init__(
        self,
        enforcer: CapabilityEnforcer,
        audit: AuditLogger,
    ) -> None:
        self._skills: dict[str, BaseSkill] = {}
        self._enforcer = enforcer
        self._audit = audit

    def register(self, skill: BaseSkill) -> None:
        """Register a skill, granting its declared capabilities."""
        name = skill.manifest.name
        self._skills[name] = skill

        # Auto-grant the capabilities the skill declares
        from nexus.security.capabilities import CapabilityGrant

        grants = [
            CapabilityGrant(capability=cap)
            for cap in skill.manifest.capabilities_required
        ]
        self._enforcer.grant(name, grants)

        logger.info(
            "Registered skill: %s (v%s) — capabilities: %s",
            name,
            skill.manifest.version,
            [c.value for c in skill.manifest.capabilities_required],
        )

    def get(self, name: str) -> BaseSkill:
        """Get a skill by name."""
        skill = self._skills.get(name)
        if not skill:
            raise SkillNotFoundError(f"Skill '{name}' not found")
        return skill

    async def invoke(
        self,
        name: str,
        params: dict[str, Any],
        actor: str = "user",
    ) -> SkillResult:
        """Invoke a skill with security checks and audit logging."""
        skill = self.get(name)

        # Check capabilities
        for cap in skill.manifest.capabilities_required:
            try:
                self._enforcer.check(name, cap)
            except CapabilityDeniedError:
                await self._audit.log_action(
                    event_type="skill_invocation",
                    actor=actor,
                    action=f"invoke:{name}",
                    resource=name,
                    result="denied",
                    details={"capability": cap.value, "params": params},
                )
                raise

        # Execute the skill
        await self._audit.log_action(
            event_type="skill_invocation",
            actor=actor,
            action=f"invoke:{name}",
            resource=name,
            result="allowed",
            details={"params": params},
        )

        try:
            result = await skill.execute(params)
            return result
        except Exception as e:
            await self._audit.log_action(
                event_type="skill_error",
                actor=actor,
                action=f"invoke:{name}",
                resource=name,
                result="error",
                details={"error": str(e)},
            )
            return SkillResult(success=False, error=str(e))

    def list_skills(self) -> list[str]:
        """Return names of all registered skills."""
        return list(self._skills.keys())

    def get_tool_definitions(self) -> list[ToolDefinition]:
        """Return tool definitions for all skills (for LLM tool calling)."""
        return [skill.to_tool_definition() for skill in self._skills.values()]
