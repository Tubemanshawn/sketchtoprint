# SketchToPrint

Turn rough sketches and typed dimensions into accurate, printable 3D models for the Creality Ender 3 V3 Plus. Claude writes a parametric [build123d](https://github.com/gumyr/build123d) script; the script runs locally and exports STL, 3MF and GLB. See [CLAUDE.md](CLAUDE.md) for the full brief.

This is milestone 1: a command line proof of concept that goes from a text description to a script to an STL.

## Setup

Python 3.11 or 3.12 is recommended (build123d's OpenCascade wheels install fastest there).

```bash
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=sk-ant-...   # Windows: set ANTHROPIC_API_KEY=...
```

## Usage

Describe a part and let Claude design it:

```bash
sketchtoprint make "L-bracket, 40 mm legs, 20 mm wide, 3 mm thick, two M4 holes per leg"
```

The command prints Claude's assumptions and any questions, runs the checks, and saves everything to `output/<timestamp>-<part_name>/`: `part.stl`, `part.3mf`, `part.glb`, `part.py`, `params.json`, `prompt.txt` and `design.json`. If a critical dimension is missing, Claude asks instead of guessing and nothing is built; run the command again with the answer added.

Rebuild a script locally with different values, without calling Claude:

```bash
sketchtoprint run examples/l_bracket.py --set length=60 --set thickness=5
```

Open the `.3mf` (preferred) or `.stl` in Creality Print.

## How a script is checked and run

- `sketchtoprint/script_check.py` parses the script with `ast` and rejects anything outside the contract: imports other than `build123d` and `math`, file/OS/eval builtins, dunder attributes, build123d export/import helpers, and top-level statements other than imports, assignments and functions. It also validates `PARAMS`.
- `sketchtoprint/runner.py` runs the script in a separate `python -I` process with a 30 s timeout; the app, not the script, exports the files.
- `sketchtoprint/meshcheck.py` loads the STL with trimesh and warns if the mesh is not watertight or does not fit the 300 × 300 × 330 mm build volume.
- If a generated script fails a check or errors while building, the error goes back to Claude for up to two repair attempts.

## Settings

Environment variables: `SKETCHTOPRINT_MODEL` (default `claude-opus-5-5`), `SKETCHTOPRINT_EFFORT` (default `high`), `SKETCHTOPRINT_OUTPUT` (default `output`). Printer defaults live in `sketchtoprint/config.py`.

## Tests

```bash
pytest
```

The tests cover the script checks, the example parts, timeouts, and the Claude repair loop with a fake client, so they need no API key.
