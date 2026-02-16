from __future__ import annotations

import os
import subprocess
from typing import Any, Dict

from ..settings import settings

SAFE_BASE = settings.WORKSPACE_DIR


def _safe_path(rel_path: str) -> str:
    rel = (rel_path or "").lstrip("/").lstrip("\\")
    full = os.path.abspath(os.path.join(SAFE_BASE, rel))
    base = os.path.abspath(SAFE_BASE)
    if not full.startswith(base):
        raise ValueError("Path escapes /workspace sandbox")
    return full


def write_file(path: str, content: str) -> Dict[str, Any]:
    full = _safe_path(path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content or "")
    return {"ok": True, "action": "write_file", "path": path, "bytes": len((content or "").encode("utf-8"))}


def exec_cmd(cmd: str, allow: bool = False) -> Dict[str, Any]:
    if not bool(settings.LOCAL_ACTIONS_ENABLED) or not allow:
        return {"ok": False, "error": "disabled", "message": "Command exec disabled unless LOCAL_ACTIONS_ENABLED=1 and allow=true"}

    proc = subprocess.run(cmd, shell=True, cwd=SAFE_BASE, capture_output=True, text=True, timeout=30)
    return {
        "ok": True,
        "action": "exec",
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
