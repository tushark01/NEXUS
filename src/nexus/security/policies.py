"""Default security policies."""

from __future__ import annotations

from nexus.security.capabilities import Capability, CapabilityGrant

# Default grants for built-in skills
BUILTIN_SKILL_GRANTS: dict[str, list[CapabilityGrant]] = {
    "web_search": [
        CapabilityGrant(capability=Capability.NETWORK_HTTP),
    ],
    "file_ops": [
        CapabilityGrant(
            capability=Capability.FILE_READ,
            constraints={"paths": ["*"]},  # configurable
        ),
        CapabilityGrant(
            capability=Capability.FILE_WRITE,
            constraints={"paths": ["./data/*", "/tmp/nexus/*"]},
        ),
    ],
    "code_exec": [
        CapabilityGrant(capability=Capability.SHELL_EXECUTE),
    ],
    "notes": [
        CapabilityGrant(capability=Capability.MEMORY_READ),
        CapabilityGrant(capability=Capability.MEMORY_WRITE),
    ],
    "shell": [
        CapabilityGrant(
            capability=Capability.SHELL_EXECUTE,
            constraints={"commands": ["ls", "cat", "grep", "find", "wc", "date", "echo", "pwd"]},
        ),
    ],
}
