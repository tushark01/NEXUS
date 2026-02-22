"""Subprocess-based skill sandboxing — isolated execution environment."""

from __future__ import annotations

import asyncio
import json
import logging
import textwrap
from typing import Any

from nexus.core.errors import SandboxError, SandboxTimeoutError

logger = logging.getLogger(__name__)

# Restricted Python environment for sandboxed execution
SANDBOX_WRAPPER = textwrap.dedent("""\
    import sys
    import json

    # Restrict dangerous imports
    _BLOCKED_MODULES = {
        'subprocess', 'shutil', 'ctypes', 'importlib',
        'socket', 'http', 'urllib', 'ftplib', 'smtplib',
        'webbrowser', 'antigravity',
    }

    _original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

    def _restricted_import(name, *args, **kwargs):
        top_level = name.split('.')[0]
        if top_level in _BLOCKED_MODULES:
            raise ImportError(f"Module '{name}' is not allowed in sandbox")
        return _original_import(name, *args, **kwargs)

    import builtins
    builtins.__import__ = _restricted_import

    # Read input
    _input_data = json.loads(sys.stdin.readline())
    _code = _input_data['code']
    _params = _input_data.get('params', {})

    # Execute
    _namespace = {'params': _params, '__builtins__': builtins}
    try:
        exec(_code, _namespace)
        _result = _namespace.get('result', None)
        print(json.dumps({'success': True, 'result': str(_result) if _result is not None else None}))
    except Exception as e:
        print(json.dumps({'success': False, 'error': f'{type(e).__name__}: {e}'}))
""")


class SkillSandbox:
    """Execute code in isolated subprocesses with resource limits."""

    def __init__(self, timeout_seconds: int = 30, enabled: bool = True) -> None:
        self._timeout = timeout_seconds
        self._enabled = enabled

    async def execute(
        self,
        code: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run code in a sandboxed subprocess.

        Returns:
            {"success": bool, "result": Any, "error": str | None}
        """
        if not self._enabled:
            # Sandbox disabled — run in-process (development mode)
            namespace: dict[str, Any] = {"params": params or {}}
            try:
                exec(code, namespace)
                return {"success": True, "result": str(namespace.get("result"))}
            except Exception as e:
                return {"success": False, "error": f"{type(e).__name__}: {e}"}

        input_data = json.dumps({"code": code, "params": params or {}})

        try:
            proc = await asyncio.create_subprocess_exec(
                "python3",
                "-c",
                SANDBOX_WRAPPER,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=input_data.encode()),
                timeout=self._timeout,
            )

            if proc.returncode != 0:
                error_msg = stderr.decode().strip() or f"Process exited with code {proc.returncode}"
                return {"success": False, "error": error_msg}

            output = stdout.decode().strip()
            if output:
                return json.loads(output)
            return {"success": False, "error": "No output from sandbox"}

        except asyncio.TimeoutError:
            if proc:
                proc.kill()
            raise SandboxTimeoutError(
                f"Sandbox execution timed out after {self._timeout}s"
            )
        except json.JSONDecodeError as e:
            raise SandboxError(f"Invalid sandbox output: {e}") from e
        except Exception as e:
            raise SandboxError(f"Sandbox execution failed: {e}") from e
