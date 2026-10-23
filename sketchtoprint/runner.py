"""Checks a part script, runs it in a subprocess with a timeout, and validates the mesh."""

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import config
from .meshcheck import MeshReport, check_mesh
from .script_check import ScriptError, check_script, resolve_params

WORKER = Path(__file__).with_name("worker.py")


class RunError(RuntimeError):
    """The script failed to build or export."""


@dataclass
class RunResult:
    files: dict[str, Path]
    params: dict[str, float]
    mesh: MeshReport
    warnings: list[str] = field(default_factory=list)


def run_script(
    source: str,
    out_dir: Path,
    overrides: dict[str, float] | None = None,
    stem: str = "part",
    timeout: float = config.SCRIPT_TIMEOUT_S,
) -> RunResult:
    params = check_script(source)
    values = resolve_params(params, overrides or {})

    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    job = {"source": source, "params": values, "out_dir": str(out_dir), "stem": stem}
    try:
        proc = subprocess.run(
            [sys.executable, "-I", str(WORKER)],
            input=json.dumps(job),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=out_dir,
        )
    except subprocess.TimeoutExpired:
        raise RunError(f"script took longer than {timeout:.0f} s and was stopped") from None

    try:
        result = json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        raise RunError(f"worker crashed (exit {proc.returncode}): {proc.stderr.strip()[-2000:]}") from None
    if not result["ok"]:
        raise RunError(result["error"])

    files = {kind: Path(result[kind]) for kind in ("stl", "3mf", "glb")}
    mesh = check_mesh(files["stl"])
    warnings = list(mesh.warnings)
    for p in params:
        if values[p.name] < config.MIN_WALL and any(
            word in p.name for word in ("thick", "wall")
        ):
            warnings.append(
                f"'{p.name}' is {values[p.name]} mm, under the {config.MIN_WALL} mm minimum wall"
            )
    return RunResult(files=files, params=values, mesh=mesh, warnings=warnings)


__all__ = ["RunError", "RunResult", "ScriptError", "run_script"]
