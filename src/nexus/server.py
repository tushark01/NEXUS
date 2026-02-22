"""NEXUS web server entry point — launches the FastAPI dashboard."""

from __future__ import annotations

import asyncio
import logging
import sys

from nexus.core.config import NexusConfig
from nexus.core.lifecycle import shutdown, startup
from nexus.llm.router import ModelRouter
from nexus.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


def main() -> None:
    """Launch the NEXUS web dashboard."""
    try:
        import uvicorn
    except ImportError:
        print("uvicorn not installed. Run: pip install nexus-agent[api]")
        sys.exit(1)

    asyncio.run(_setup_and_serve())


async def _setup_and_serve() -> None:
    config = NexusConfig()  # type: ignore[call-arg]
    registry = await startup(config)

    router = registry.get(ModelRouter)
    memory = registry.get(MemoryManager)

    if not router.available_providers:
        print("Error: No LLM providers configured.")
        sys.exit(1)

    # Initialize swarm
    swarm = None
    try:
        from nexus.agents.orchestrator import SwarmOrchestrator
        from nexus.core.event_bus import EventBus

        event_bus = registry.get(EventBus) if registry.has(EventBus) else None
        swarm = SwarmOrchestrator(
            llm=router, memory=memory, event_bus=event_bus,
            max_agents=config.swarm.max_concurrent_agents,
        )
    except Exception as e:
        logger.warning("Swarm init failed: %s", e)

    # Initialize skills
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
    except Exception as e:
        logger.warning("Skills init failed: %s", e)

    # Create and serve the FastAPI app
    from nexus.interfaces.api.app import create_api

    app = create_api(router=router, memory=memory, swarm=swarm, skills=skills)

    import uvicorn

    server_config = uvicorn.Config(
        app,
        host=config.interfaces.api_host,
        port=config.interfaces.api_port,
        log_level="info",
    )
    server = uvicorn.Server(server_config)

    logger.info(
        "NEXUS Dashboard: http://%s:%d",
        config.interfaces.api_host,
        config.interfaces.api_port,
    )

    try:
        await server.serve()
    finally:
        await shutdown(registry)


if __name__ == "__main__":
    main()
