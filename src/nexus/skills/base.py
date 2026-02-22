"""Base skill protocol and decorators."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from nexus.llm.schemas import ToolDefinition
from nexus.security.capabilities import Capability


class ParameterDef(BaseModel):
    """Definition of a skill parameter."""

    type: str = "string"
    description: str = ""
    required: bool = True
    default: Any = None
    enum: list[str] | None = None


class SkillManifest(BaseModel):
    """Declarative manifest for a skill — what it does and what it needs."""

    name: str
    version: str = "0.1.0"
    description: str
    author: str = "nexus-builtin"
    capabilities_required: list[Capability] = []
    parameters: dict[str, ParameterDef] = {}
    returns: str = "string"


class SkillResult(BaseModel):
    """Result of a skill execution."""

    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = {}


class BaseSkill(ABC):
    """Abstract base for all NEXUS skills."""

    manifest: SkillManifest

    @abstractmethod
    async def execute(self, params: dict[str, Any]) -> SkillResult:
        """Execute the skill with the given parameters."""

    def to_tool_definition(self) -> ToolDefinition:
        """Convert this skill's manifest to an LLM tool definition."""
        properties: dict[str, Any] = {}
        required: list[str] = []

        for name, param in self.manifest.parameters.items():
            prop: dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[name] = prop

            if param.required and param.default is None:
                required.append(name)

        return ToolDefinition(
            name=self.manifest.name,
            description=self.manifest.description,
            parameters={
                "type": "object",
                "properties": properties,
                "required": required,
            },
        )
