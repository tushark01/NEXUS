"""NEXUS configuration — loaded from environment, .env, and YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProviderConfig(BaseModel):
    provider: Literal["anthropic", "openai", "ollama"] = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    api_key: SecretStr | None = None
    base_url: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.7


class MemoryConfig(BaseModel):
    chroma_persist_dir: Path = Path("./data/chroma")
    embedding_model: str = "all-MiniLM-L6-v2"
    consolidation_interval_hours: int = 24
    max_working_memory_tokens: int = 8000


class SecurityConfig(BaseModel):
    sandbox_enabled: bool = True
    sandbox_timeout_seconds: int = 30
    require_skill_signatures: bool = False
    rate_limit_requests_per_minute: int = 60
    audit_log_path: Path = Path("./data/audit.jsonl")


class SwarmConfig(BaseModel):
    max_concurrent_agents: int = 5
    default_consensus_method: Literal["majority", "weighted", "coordinator"] = "coordinator"
    task_timeout_seconds: int = 300


class InterfacesConfig(BaseModel):
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    telegram_token: str | None = None
    discord_token: str | None = None


class NexusConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEXUS_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM provider configs — built from flat env vars in validator
    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-sonnet-4-20250514"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    default_provider: str = "anthropic"

    memory: MemoryConfig = MemoryConfig()
    security: SecurityConfig = SecurityConfig()
    swarm: SwarmConfig = SwarmConfig()
    interfaces: InterfacesConfig = InterfacesConfig()

    def get_provider_configs(self) -> list[LLMProviderConfig]:
        """Build provider configs from flat env vars."""
        configs: list[LLMProviderConfig] = []
        if self.anthropic_api_key:
            configs.append(
                LLMProviderConfig(
                    provider="anthropic",
                    model=self.anthropic_model,
                    api_key=self.anthropic_api_key,
                )
            )
        if self.openai_api_key:
            configs.append(
                LLMProviderConfig(
                    provider="openai",
                    model=self.openai_model,
                    api_key=self.openai_api_key,
                )
            )
        # Ollama is always available (local, no key needed)
        configs.append(
            LLMProviderConfig(
                provider="ollama",
                model=self.ollama_model,
                base_url=self.ollama_base_url,
            )
        )
        return configs
