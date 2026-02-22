"""Skill discovery and loading."""

from __future__ import annotations

import logging

from nexus.security.audit import AuditLogger
from nexus.security.capabilities import CapabilityEnforcer
from nexus.security.sandbox import SkillSandbox
from nexus.skills.builtin import ALL_BUILTIN_SKILLS
from nexus.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


def load_builtin_skills(
    registry: SkillRegistry,
    sandbox: SkillSandbox | None = None,
    memory_manager: object | None = None,
) -> None:
    """Discover and register all built-in skills."""
    from nexus.skills.builtin.code_exec import CodeExecSkill
    from nexus.skills.builtin.notes import NotesSkill

    for skill_cls in ALL_BUILTIN_SKILLS:
        try:
            if skill_cls is CodeExecSkill:
                skill = skill_cls(sandbox=sandbox)
            elif skill_cls is NotesSkill:
                skill = skill_cls(memory_manager=memory_manager)
            else:
                skill = skill_cls()
            registry.register(skill)
        except Exception as e:
            logger.warning("Failed to load skill %s: %s", skill_cls.__name__, e)

    logger.info("Loaded %d built-in skills", len(registry.list_skills()))


def create_skill_registry(
    enforcer: CapabilityEnforcer | None = None,
    audit: AuditLogger | None = None,
) -> SkillRegistry:
    """Create a skill registry with default security components."""
    from pathlib import Path

    enforcer = enforcer or CapabilityEnforcer()
    audit = audit or AuditLogger(Path("./data/audit.jsonl"))
    return SkillRegistry(enforcer=enforcer, audit=audit)
