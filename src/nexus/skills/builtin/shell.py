"""Shell skill — execute restricted shell commands."""

from __future__ import annotations

import asyncio
from typing import Any

from nexus.security.capabilities import Capability
from nexus.skills.base import BaseSkill, ParameterDef, SkillManifest, SkillResult

# Whitelist of safe commands
ALLOWED_COMMANDS = {"ls", "cat", "grep", "find", "wc", "date", "echo", "pwd", "head", "tail", "sort", "uniq"}


class ShellSkill(BaseSkill):
    """Execute restricted shell commands."""

    manifest = SkillManifest(
        name="shell",
        description=f"Execute shell commands. Only these commands are allowed: {', '.join(sorted(ALLOWED_COMMANDS))}",
        capabilities_required=[Capability.SHELL_EXECUTE],
        parameters={
            "command": ParameterDef(
                type="string",
                description="Shell command to execute",
                required=True,
            ),
        },
    )

    async def execute(self, params: dict[str, Any]) -> SkillResult:
        command = params.get("command", "").strip()
        if not command:
            return SkillResult(success=False, error="Command is required")

        # Security: check the base command is in the whitelist
        base_cmd = command.split()[0] if command.split() else ""
        if base_cmd not in ALLOWED_COMMANDS:
            return SkillResult(
                success=False,
                error=f"Command '{base_cmd}' is not allowed. Allowed: {', '.join(sorted(ALLOWED_COMMANDS))}",
            )

        # Security: block dangerous patterns
        dangerous = [";", "&&", "||", "|", "`", "$(", ">>", ">"]
        for pattern in dangerous:
            if pattern in command:
                return SkillResult(
                    success=False,
                    error=f"Command contains disallowed pattern: '{pattern}'",
                )

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=10.0
            )

            output = stdout.decode(errors="replace")
            errors = stderr.decode(errors="replace")

            if proc.returncode != 0:
                return SkillResult(
                    success=False,
                    output=output,
                    error=errors or f"Command exited with code {proc.returncode}",
                )

            # Truncate large output
            if len(output) > 20_000:
                output = output[:20_000] + "\n... (truncated)"

            return SkillResult(success=True, output=output)

        except asyncio.TimeoutError:
            return SkillResult(success=False, error="Command timed out (10s limit)")
        except Exception as e:
            return SkillResult(success=False, error=f"Shell execution failed: {e}")
