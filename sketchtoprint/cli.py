"""Command line interface.

    sketchtoprint make "L-bracket, 40 mm legs, 20 mm wide, 3 mm thick, two M4 holes per leg"
    sketchtoprint run examples/l_bracket.py --set length=60
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from . import config
from .runner import RunError, RunResult, ScriptError, run_script


def _parse_overrides(pairs: list[str]) -> dict[str, float]:
    overrides = {}
    for pair in pairs:
        name, sep, value = pair.partition("=")
        try:
            if not sep:
                raise ValueError
            overrides[name.strip()] = float(value)
        except ValueError:
            raise SystemExit(f"--set expects name=number, got '{pair}'") from None
    return overrides


def _part_dir(base: Path, name: str) -> Path:
    slug = re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_") or "part"
    return base / f"{datetime.now():%Y%m%d-%H%M%S}-{slug}"


def _report(run: RunResult) -> None:
    m = run.mesh
    print("Size: {:.1f} x {:.1f} x {:.1f} mm, volume {:.0f} mm3".format(*m.size_mm, m.volume_mm3))
    for kind, path in run.files.items():
        print(f"{kind.upper():>4}: {path}")
    for w in run.warnings:
        print(f"Warning: {w}")


def cmd_run(args) -> int:
    source = Path(args.script).read_text()
    out_dir = Path(args.out) if args.out else _part_dir(config.OUTPUT_DIR, Path(args.script).stem)
    try:
        run = run_script(source, out_dir, _parse_overrides(args.set))
    except (ScriptError, RunError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    (out_dir / "part.py").write_text(source)
    (out_dir / "params.json").write_text(json.dumps(run.params, indent=2))
    _report(run)
    return 0


def cmd_make(args) -> int:
    import anthropic

    from .generate import DesignError, design_part

    description = " ".join(args.description)
    staging = _part_dir(Path(args.out) if args.out else config.OUTPUT_DIR, "pending")
    try:
        result = design_part(description, staging)
    except DesignError as e:
        print(f"Error: {e}", file=sys.stderr)
        if e.design is not None:
            staging.mkdir(parents=True, exist_ok=True)
            (staging / "part.py").write_text(e.design.script)
            print(f"Last script saved to {staging / 'part.py'}", file=sys.stderr)
        return 1
    except anthropic.AnthropicError as e:
        print(f"Claude API error: {e}", file=sys.stderr)
        return 1
    except TypeError as e:
        if "authentication" not in str(e):
            raise
        print("No Claude API key found. Set the ANTHROPIC_API_KEY environment variable.", file=sys.stderr)
        return 1

    d = result.design
    if d.status == "need_info":
        print("Claude needs more information before it can design this part:")
        for q in d.questions:
            print(f"  - {q}")
        print("Run the command again with the answers added to the description.")
        return 2

    out_dir = staging.with_name(staging.name.replace("pending", re.sub(r"[^a-z0-9_]+", "_", d.part_name.lower())))
    staging.rename(out_dir)
    run = result.run
    run.files = {k: out_dir / p.name for k, p in run.files.items()}
    (out_dir / "part.py").write_text(d.script)
    (out_dir / "params.json").write_text(json.dumps(run.params, indent=2))
    (out_dir / "prompt.txt").write_text(description + "\n")
    (out_dir / "design.json").write_text(d.model_dump_json(indent=2))

    print(f"Part: {d.part_name}")
    if d.assumptions:
        print("Assumptions:")
        for a in d.assumptions:
            print(f"  - {a}")
    if d.questions:
        print("Questions:")
        for q in d.questions:
            print(f"  - {q}")
    if result.errors:
        print(f"(Repaired {len(result.errors)} failed script attempt(s).)")
    _report(run)
    print(f"Tweak and re-run without Claude: sketchtoprint run {out_dir / 'part.py'} --set name=value")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sketchtoprint", description="Text to printable parametric parts.")
    sub = parser.add_subparsers(dest="command", required=True)

    make = sub.add_parser("make", help="describe a part and have Claude design it")
    make.add_argument("description", nargs="+")
    make.add_argument("-o", "--out", help=f"output folder (default {config.OUTPUT_DIR})")
    make.set_defaults(func=cmd_make)

    run = sub.add_parser("run", help="build an existing part script locally")
    run.add_argument("script")
    run.add_argument("--set", action="append", default=[], metavar="NAME=VALUE", help="override a parameter")
    run.add_argument("-o", "--out", help="exact output folder")
    run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
