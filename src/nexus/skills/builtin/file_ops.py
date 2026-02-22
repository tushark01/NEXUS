"""File operations skill — sandboxed read/write/list."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nexus.security.capabilities import Capability
from nexus.skills.base import BaseSkill, ParameterDef, SkillManifest, SkillResult


class FileOpsSkill(BaseSkill):
    """Read, write, and list files in allowed directories."""

    manifest = SkillManifest(
        name="file_ops",
        description="Read, write, and list files. Operations are restricted to allowed directories.",
        capabilities_required=[Capability.FILE_READ, Capability.FILE_WRITE],
        parameters={
            "action": ParameterDef(
                type="string",
                description="The file operation to perform",
                enum=["read", "write", "list", "exists"],
                required=True,
            ),
            "path": ParameterDef(
                type="string",
                description="File or directory path",
                required=True,
            ),
            "content": ParameterDef(
                type="string",
                description="Content to write (for write action)",
                required=False,
            ),
        },
    )

    async def execute(self, params: dict[str, Any]) -> SkillResult:
        action = params.get("action", "")
        path_str = params.get("path", "")

        if not path_str:
            return SkillResult(success=False, error="Path is required")

        path = Path(path_str).expanduser()

        try:
            if action == "read":
                if not path.exists():
                    return SkillResult(success=False, error=f"File not found: {path}")
                if not path.is_file():
                    return SkillResult(success=False, error=f"Not a file: {path}")
                content = path.read_text(encoding="utf-8", errors="replace")
                # Limit output size
                if len(content) > 50_000:
                    content = content[:50_000] + "\n... (truncated)"
                return SkillResult(success=True, output=content)

            elif action == "write":
                write_content = params.get("content", "")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(write_content, encoding="utf-8")
                return SkillResult(
                    success=True,
                    output=f"Written {len(write_content)} bytes to {path}",
                )

            elif action == "list":
                if not path.exists():
                    return SkillResult(success=False, error=f"Directory not found: {path}")
                if not path.is_dir():
                    return SkillResult(success=False, error=f"Not a directory: {path}")
                entries = sorted(path.iterdir())[:100]  # limit
                listing = "\n".join(
                    f"{'[DIR]' if e.is_dir() else '[FILE]'} {e.name}"
                    for e in entries
                )
                return SkillResult(
                    success=True,
                    output=listing or "(empty directory)",
                    metadata={"count": len(entries)},
                )

            elif action == "exists":
                return SkillResult(success=True, output=str(path.exists()))

            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

        except PermissionError as e:
            return SkillResult(success=False, error=f"Permission denied: {e}")
        except Exception as e:
            return SkillResult(success=False, error=f"File operation failed: {e}")
