"""NEXUS lifecycle — ordered startup and shutdown of all components."""

from __future__ import annotations

import logging
from pathlib import Path

from nexus.core.config import NexusConfig
from nexus.core.event_bus import EventBus
from nexus.core.registry import Registry
from nexus.llm.router import ModelRouter
from nexus.memory.embeddings import SentenceTransformerEmbedder
from nexus.memory.manager import MemoryManager
from nexus.memory.store import ChromaDBStore
from nexus.memory.working import WorkingMemory

logger = logging.getLogger(__name__)


async def startup(config: NexusConfig) -> Registry:
    """Initialize all NEXUS components and return the service registry.

    Startup order:
    1. Structured logging
    2. Event bus
    3. LLM providers + router
    4. Memory system
    5. Registry wiring
    """
    registry = Registry()

    # 1. Logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Starting NEXUS v0.1.0")

    # 2. Event bus
    bus = EventBus()
    await bus.start()
    registry.register(EventBus, bus)
    logger.info("Event bus started")

    # 3. LLM providers + router
    router = ModelRouter(default_provider=config.default_provider)

    for pc in config.get_provider_configs():
        try:
            if pc.provider == "anthropic" and pc.api_key:
                from nexus.llm.providers.anthropic import AnthropicProvider

                router.register_provider(AnthropicProvider(pc))
            elif pc.provider == "openai" and pc.api_key:
                from nexus.llm.providers.openai import OpenAIProvider

                router.register_provider(OpenAIProvider(pc))
            elif pc.provider == "ollama":
                # Ollama is optional — only register if reachable
                pass  # Phase 4: OllamaProvider
        except Exception as e:
            logger.warning("Failed to init provider %s: %s", pc.provider, e)

    if not router.available_providers:
        logger.error(
            "No LLM providers available! Set NEXUS_ANTHROPIC_API_KEY or NEXUS_OPENAI_API_KEY"
        )

    # Set up fallback chains
    if "anthropic" in router.available_providers and "openai" in router.available_providers:
        router.add_fallback_chain("anthropic", ["openai"])
        router.add_fallback_chain("openai", ["anthropic"])

    registry.register(ModelRouter, router)
    logger.info("LLM router ready: %s", router.available_providers)

    # 4. Memory system
    chroma_dir = Path(config.memory.chroma_persist_dir)
    vector_store = ChromaDBStore(chroma_dir)
    embedder = SentenceTransformerEmbedder(config.memory.embedding_model)
    working = WorkingMemory()

    memory = MemoryManager(
        working=working,
        vector_store=vector_store,
        embedder=embedder,
    )
    registry.register(MemoryManager, memory)
    logger.info("Memory system ready")

    # Store config for later
    registry.register(NexusConfig, config)

    logger.info("NEXUS startup complete")
    return registry


async def shutdown(registry: Registry) -> None:
    """Graceful shutdown — reverse order teardown."""
    logger.info("Shutting down NEXUS...")

    if registry.has(EventBus):
        bus = registry.get(EventBus)
        await bus.stop()

    logger.info("NEXUS shutdown complete")
