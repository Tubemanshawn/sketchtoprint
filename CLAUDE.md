# SketchToPrint — Project Brief

A desktop app that turns rough sketches (photos) and typed dimensions into accurate, printable 3D models for an Ender 3 V3 Plus, exported for Creality Print.

## Core idea

Do NOT generate meshes directly from images. Claude reads the sketch or text and writes a parametric CAD script (build123d, Python). The script runs locally and produces exact geometry. This keeps dimensions accurate and lets the user tweak values without regenerating.

## Target user and parts

- One user, a hobbyist making functional parts: brackets, mounts, enclosures, spacers, adapters, organizers, replacement parts.
- Input is a hand-drawn sketch photo, typed text, or both together.
- Organic or sculpted shapes are out of scope for v1.

## Printer constraints (bake in as defaults)

- Printer: Creality Ender 3 V3 Plus. Build volume is 300 × 300 × 330 mm; verify against the official spec sheet.
- Nozzle: 0.4 mm. Minimum recommended wall is 1.2 mm.
- Fit clearance: 0.2 mm default for sliding or press fits, user-adjustable. Holes print slightly undersized, so add an optional hole compensation of +0.2 mm on diameter.
- Overhangs: warn above roughly 45°. Prefer designs with a flat face on the bed.
- Export: 3MF (preferred) and STL. Creality Print opens both.

## Tech stack

- Language: Python 3.11+
- CAD kernel: build123d (OCP/OpenCascade). CadQuery is an acceptable fallback.
- LLM: Anthropic Python SDK. Use a vision-capable Claude model, with the model ID set in config. The API key comes from the `ANTHROPIC_API_KEY` env var and is never hardcoded.
- Mesh checks: trimesh (watertight check, bounding box, volume).
- Desktop shell: FastAPI backend plus a local HTML/JS frontend, wrapped with pywebview so it opens as a desktop window.
- 3D viewer: three.js loading the exported STL or GLB.

## How it works

1. **Input:** the user drops in a sketch photo and/or types a description, e.g. "L-bracket, 40 mm legs, 20 mm wide, 3 mm thick, two M4 holes per leg."
2. **Interpretation:** Claude receives the image, the text, and a system prompt containing the printer constraints and script rules. It returns:
   - a build123d script,
   - a list of assumptions it made, e.g. "assumed holes centered 10 mm from the edge,"
   - questions about anything missing or ambiguous. If a critical dimension is missing, it asks instead of guessing.
3. **Execution:** the script runs in a sandboxed subprocess with a timeout of about 30 s, then exports STL, 3MF, and a GLB for preview.
4. **Validation:** the app checks that the mesh is watertight, fits the build volume, and has no walls under 1.2 mm where detectable. It also suggests a flat base orientation. Results appear as warnings, not hard failures.
5. **Preview and tweak:** a three.js viewer shows the model alongside an auto-generated slider or number field for each entry in `PARAMS`. Changing a value re-runs the script locally without calling Claude.
6. **Refine:** a chat box handles changes like "make it 3 mm taller" or "add a chamfer to the top edges." Claude gets the current script and returns an edited version.
7. **Export and library:** the app saves 3MF/STL to an output folder, plus the script, params, source image, and prompt, so any part can be reopened and edited later.

## Script contract (what Claude must generate)

```python
# All dimensions in millimeters.
PARAMS = {
    "length": {"value": 40.0, "min": 5, "max": 300, "label": "Leg length"},
    "thickness": {"value": 3.0, "min": 1.2, "max": 20, "label": "Thickness"},
    "hole_d": {"value": 4.4, "min": 1, "max": 20, "label": "Hole diameter (M4 + clearance)"},
}


def build(p):
    # p is a dict of name -> float
    # return a build123d Part
    ...
```

- Only `build123d` and `math` imports are allowed. No file, network, or OS access.
- The app, not the script, handles exporting.
- Validate the script before running it: parse it with `ast` and reject disallowed imports and calls.

## Milestones

1. CLI proof of concept: text description → script → STL. Confirm the output opens in Creality Print.
2. Image input: sketch photo plus optional text, returning the assumptions and questions.
3. Sandbox and validation: AST allowlist, subprocess timeout, trimesh checks, build volume check.
4. Desktop UI: pywebview window with input panel, three.js preview, and warnings panel.
5. Parameter controls: sliders generated from `PARAMS` that re-render live.
6. Refine chat: iterative edits to the existing script.
7. Library: saved parts with thumbnails; reopen and edit.
8. Nice-to-haves: common hardware presets (M3/M4/M5 holes, heat-set insert pockets, screw countersinks), and a "send to Creality Print" button that opens the exported file.

## Test cases to keep in /examples

- A 20 mm calibration cube
- An L-bracket with 4 screw holes
- A rectangular box with a snap-fit or sliding lid
- A pipe spacer: outer diameter, inner diameter, height
- A wall-mount hook from a hand-drawn sketch photo

## Guiding principles

- Accuracy over cleverness. Ask the user rather than guess dimensions.
- Every generated part stays editable through its params.
- Keep it local and simple; the only network call is to the Claude API.
