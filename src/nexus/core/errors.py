"""NEXUS exception hierarchy."""


class NexusError(Exception):
    """Base exception for all NEXUS errors."""


class ConfigError(NexusError):
    """Configuration is invalid or missing."""


class LLMError(NexusError):
    """Error communicating with an LLM provider."""


class LLMProviderNotFoundError(LLMError):
    """Requested LLM provider is not configured."""


class LLMRateLimitError(LLMError):
    """LLM provider rate limit exceeded."""


class MemoryError(NexusError):
    """Error in the memory subsystem."""


class SecurityError(NexusError):
    """Security violation detected."""


class CapabilityDeniedError(SecurityError):
    """A skill attempted an action it lacks the capability for."""


class SandboxError(SecurityError):
    """Skill sandbox execution failed."""


class SandboxTimeoutError(SandboxError):
    """Skill exceeded its sandbox time limit."""


class SkillError(NexusError):
    """Error in the skill subsystem."""


class SkillNotFoundError(SkillError):
    """Requested skill does not exist."""


class AgentError(NexusError):
    """Error in the agent subsystem."""


class TaskError(AgentError):
    """Error in task execution."""


class TaskTimeoutError(TaskError):
    """Task exceeded its time limit."""


class ConsensusError(AgentError):
    """Agents could not reach consensus."""
