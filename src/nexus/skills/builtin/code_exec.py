"""Code execution skill — runs Python code in a sandboxed environment."""

from __future__ import annotations

from typing import Any

from nexus.security.capabilities import Capability
from nexus.security.sandbox import SkillSandbox
from nexus.skills.base import BaseSkill, ParameterDef, SkillManifest, SkillResult


class CodeExecSkill(BaseSkill):
    """Execute Python code in a sandboxed subprocess."""

    manifest = SkillManifest(
        name="code_exec",
        description="Execute Python code safely in an isolated sandbox. The code runs in a restricted environment with limited imports. Set a 'result' variable to return output.",
        capabilities_required=[Capability.SHELL_EXECUTE],
        parameters={
            "code": ParameterDef(
                type="string",
                description="Python code to execute. Assign to 'result' variable for output.",
                required=True,
            ),
        },
    )

    def __init__(self, sandbox: SkillSandbox | None = None) -> None:
        self._sandbox = sandbox or SkillSandbox()

    async def execute(self, params: dict[str, Any]) -> SkillResult:
        code = params.get("code", "")
        if not code:
            return SkillResult(success=False, error="Code is required")

        result = await self._sandbox.execute(code)

        return SkillResult(
            success=result.get("success", False),
            output=result.get("result"),
            error=result.get("error"),
        )
