"""Tests for NexusConfig."""

import pytest

from nexus.core.config import NexusConfig, SecurityConfig, SwarmConfig, MemoryConfig


class TestConfig:
    def test_default_config(self):
        # NexusConfig should work with all defaults
        config = NexusConfig()  # type: ignore[call-arg]
        assert config.default_provider == "anthropic"
        assert config.anthropic_model == "claude-sonnet-4-20250514"
        assert config.openai_model == "gpt-4o"

    def test_security_defaults(self):
        sec = SecurityConfig()
        assert sec.sandbox_enabled is True
        assert sec.rate_limit_requests_per_minute == 60

    def test_swarm_defaults(self):
        swarm = SwarmConfig()
        assert swarm.max_concurrent_agents == 5
        assert swarm.default_consensus_method == "coordinator"

    def test_memory_defaults(self):
        mem = MemoryConfig()
        assert mem.embedding_model == "all-MiniLM-L6-v2"
        assert mem.max_working_memory_tokens == 8000

    def test_get_provider_configs(self):
        config = NexusConfig()  # type: ignore[call-arg]
        providers = config.get_provider_configs()
        # Should always have ollama at minimum
        provider_names = [p.provider for p in providers]
        assert "ollama" in provider_names
