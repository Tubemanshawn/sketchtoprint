"""Runs one part script in a child process and exports the result.

Started by runner.py with `python -I worker.py`. Reads a JSON job from stdin:
{"source": str, "params": {name: float}, "out_dir": str, "stem": str}
and writes a JSON result to stdout. Kept free of package imports so it can
run in isolated mode.
"""

import json
import sys
import traceback
from pathlib import Path


def main() -> None:
    job = json.load(sys.stdin)
    out_dir = Path(job["out_dir"])
    stem = job["stem"]
    try:
        import build123d as bd

        namespace: dict = {"__name__": "part_script"}
        exec(compile(job["source"], "part.py", "exec"), namespace)
        part = namespace["build"](dict(job["params"]))
        if hasattr(part, "part") and not isinstance(part, bd.Shape):
            part = part.part  # a BuildPart builder was returned
        if not isinstance(part, bd.Shape):
            raise TypeError(f"build() must return a build123d Part, got {type(part).__name__}")
        if not part.solids():
            raise ValueError("build() returned a shape with no solids")

        stl = out_dir / f"{stem}.stl"
        three_mf = out_dir / f"{stem}.3mf"
        glb = out_dir / f"{stem}.glb"
        bd.export_stl(part, str(stl))
        mesher = bd.Mesher()
        mesher.add_shape(part)
        mesher.write(str(three_mf))
        bd.export_gltf(part, str(glb), binary=True)

        result = {"ok": True, "stl": str(stl), "3mf": str(three_mf), "glb": str(glb)}
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        script_lines = [f"line {f.lineno}" for f in tb if f.filename == "part.py"]
        where = f" ({script_lines[-1]} of the script)" if script_lines else ""
        result = {"ok": False, "error": f"{type(e).__name__}: {e}{where}"}
    sys.stdout.write("\n" + json.dumps(result))


if __name__ == "__main__":
    main()
