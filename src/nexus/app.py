"""NEXUS application bootstrap."""

from __future__ import annotations

import asyncio
import logging
import sys

from nexus.core.config import NexusConfig
from nexus.core.lifecycle import shutdown, startup
from nexus.interfaces.cli.app import NexusCLI
from nexus.llm.router import ModelRouter
from nexus.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


async def run() -> None:
    """Main async entry point."""
    config = NexusConfig()  # type: ignore[call-arg]
    registry = await startup(config)

    try:
        router = registry.get(ModelRouter)
        memory = registry.get(MemoryManager)

        if not router.available_providers:
            print(
                "\nError: No LLM providers configured.\n"
                "Set NEXUS_ANTHROPIC_API_KEY or NEXUS_OPENAI_API_KEY in .env\n"
                "See .env.example for all options."
            )
            sys.exit(1)

        # Initialize swarm orchestrator
        swarm = None
        try:
            from nexus.agents.orchestrator import SwarmOrchestrator
            from nexus.core.event_bus import EventBus

            event_bus = registry.get(EventBus) if registry.has(EventBus) else None
            swarm = SwarmOrchestrator(
                llm=router,
                memory=memory,
                event_bus=event_bus,
                max_agents=config.swarm.max_concurrent_agents,
            )
            logger.info("Swarm orchestrator ready")
        except Exception as e:
            logger.warning("Swarm init failed (non-fatal): %s", e)

        # Initialize skills registry
        skills = None
        try:
            from pathlib import Path

            from nexus.security.audit import AuditLogger
            from nexus.security.capabilities import CapabilityEnforcer
            from nexus.skills.builtin import ALL_BUILTIN_SKILLS
            from nexus.skills.registry import SkillRegistry

            enforcer = CapabilityEnforcer()
            audit = AuditLogger(Path(config.security.audit_log_path))
            skills = SkillRegistry(enforcer=enforcer, audit=audit)

            for skill_cls in ALL_BUILTIN_SKILLS:
                skills.register(skill_cls())

            logger.info("Skills loaded: %s", skills.list_skills())
        except Exception as e:
            logger.warning("Skills init failed (non-fatal): %s", e)

        cli = NexusCLI(router=router, memory=memory, swarm=swarm, skills=skills)
        await cli.run()
    finally:
        await shutdown(registry)


def main() -> None:
    """Sync entry point for the CLI."""
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
