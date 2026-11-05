"""Bridge to the Remotion director: compiles a Minecraft script with the kit and reports errors/warnings (no rendering)."""
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict

from config.settings import settings

logger = logging.getLogger(__name__)
COMPILER = settings.BASE_DIR / "scripts" / "mc_compile.mjs"


def compile_script(script: Dict[str, Any]) -> Dict[str, Any]:
    """Returns {ok, errors, warnings, frames, seconds, shots, sounds, beats}. Raises RuntimeError if node fails."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False)
        path = Path(f.name)
    try:
        proc = subprocess.run(["node", str(COMPILER), str(path)], capture_output=True, text=True, timeout=120, cwd=str(settings.BASE_DIR))
    finally:
        path.unlink(missing_ok=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(f"mc_compile failed: {(proc.stderr or proc.stdout)[-400:]}")
    return json.loads(proc.stdout)
