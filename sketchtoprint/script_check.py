"""Static checks for generated part scripts.

A part script may only import build123d and math, may only contain imports,
assignments, and function definitions at the top level, and must define a
PARAMS dict literal and a build(p) function. Anything that could touch files,
the network, or the OS is rejected before the script runs.
"""

import ast
import re
from dataclasses import dataclass

ALLOWED_MODULES = {"build123d", "math"}

BLOCKED_NAMES = {
    "__import__", "breakpoint", "compile", "delattr", "dir", "eval", "exec",
    "exit", "getattr", "globals", "help", "input", "locals", "memoryview",
    "open", "quit", "setattr", "vars",
}

# build123d helpers that read or write files. The app does all exporting.
BLOCKED_BUILD123D = {"Mesher", "Export2D", "ExportDXF", "ExportSVG"}
BLOCKED_PATTERN = re.compile(r"^(export|import)_")

REQUIRED_PARAM_KEYS = {"value", "min", "max", "label"}


class ScriptError(ValueError):
    """The script breaks the script contract."""


@dataclass
class Param:
    name: str
    value: float
    min: float
    max: float
    label: str


def _is_blocked(name: str) -> bool:
    return (
        name in BLOCKED_NAMES
        or name in BLOCKED_BUILD123D
        or bool(BLOCKED_PATTERN.match(name))
        or (name.startswith("__") and name.endswith("__"))
    )


def check_script(source: str) -> list[Param]:
    """Validate a part script and return its parameters.

    Raises ScriptError listing every problem found.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise ScriptError(f"syntax error on line {e.lineno}: {e.msg}") from e

    problems: list[str] = []

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Assign, ast.AnnAssign)):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue  # docstring
        problems.append(
            f"line {node.lineno}: only imports, assignments and function definitions "
            "are allowed at the top level"
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_MODULES:
                    problems.append(f"line {node.lineno}: import of '{alias.name}' is not allowed")
        elif isinstance(node, ast.ImportFrom):
            if node.level or (node.module or "").split(".")[0] not in ALLOWED_MODULES:
                problems.append(f"line {node.lineno}: import from '{node.module}' is not allowed")
            for alias in node.names:
                if alias.name != "*" and _is_blocked(alias.name):
                    problems.append(f"line {node.lineno}: '{alias.name}' is not allowed")
        elif isinstance(node, ast.Name) and _is_blocked(node.id):
            problems.append(f"line {node.lineno}: '{node.id}' is not allowed")
        elif isinstance(node, ast.Attribute) and _is_blocked(node.attr):
            problems.append(f"line {node.lineno}: '.{node.attr}' is not allowed")
        elif isinstance(node, (ast.Global, ast.Nonlocal, ast.AsyncFunctionDef, ast.Await, ast.ClassDef)):
            problems.append(f"line {node.lineno}: {type(node).__name__} is not allowed")

    build_fn = next(
        (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build"), None
    )
    if build_fn is None:
        problems.append("missing a top-level build(p) function")
    elif len(build_fn.args.args) != 1:
        problems.append("build must take exactly one argument, the params dict")

    params: list[Param] = []
    params_node = next(
        (
            n.value
            for n in tree.body
            if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "PARAMS" for t in n.targets)
        ),
        None,
    )
    if params_node is None:
        problems.append("missing a top-level PARAMS dict")
    else:
        try:
            params = parse_params(ast.literal_eval(params_node))
        except (ValueError, TypeError, SyntaxError) as e:
            problems.append(f"PARAMS: {e}")

    if problems:
        raise ScriptError("\n".join(problems))
    return params


def parse_params(raw: object) -> list[Param]:
    if not isinstance(raw, dict) or not raw:
        raise ValueError("must be a non-empty dict literal")
    params = []
    for name, spec in raw.items():
        if not isinstance(name, str) or not name.isidentifier():
            raise ValueError(f"{name!r} is not a valid parameter name")
        if not isinstance(spec, dict) or not REQUIRED_PARAM_KEYS <= spec.keys():
            raise ValueError(f"'{name}' needs the keys {sorted(REQUIRED_PARAM_KEYS)}")
        try:
            value, lo, hi = float(spec["value"]), float(spec["min"]), float(spec["max"])
        except (TypeError, ValueError):
            raise ValueError(f"'{name}' value, min and max must be numbers") from None
        if not lo <= value <= hi:
            raise ValueError(f"'{name}' value {value} is outside [{lo}, {hi}]")
        params.append(Param(name, value, lo, hi, str(spec["label"])))
    return params


def resolve_params(params: list[Param], overrides: dict[str, float]) -> dict[str, float]:
    """Merge user overrides into the defaults, rejecting unknown or out-of-range values."""
    by_name = {p.name: p for p in params}
    values = {p.name: p.value for p in params}
    for name, value in overrides.items():
        if name not in by_name:
            raise ScriptError(f"unknown parameter '{name}' (known: {', '.join(by_name)})")
        p = by_name[name]
        if not p.min <= value <= p.max:
            raise ScriptError(f"'{name}' must be between {p.min} and {p.max}, got {value}")
        values[name] = value
    return values
