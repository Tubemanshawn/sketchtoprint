import pytest

from sketchtoprint.script_check import ScriptError, check_script, resolve_params

VALID = '''
from build123d import Box
import math

PARAMS = {"size": {"value": 20.0, "min": 5, "max": 100, "label": "Size"}}


def build(p):
    return Box(p["size"], p["size"], p["size"])
'''


def test_valid_script_returns_params():
    params = check_script(VALID)
    assert [(p.name, p.value) for p in params] == [("size", 20.0)]


@pytest.mark.parametrize(
    "bad, message",
    [
        ("import os", "import of 'os'"),
        ("import subprocess as sp", "import of 'subprocess'"),
        ("from pathlib import Path", "import from 'pathlib'"),
        ("from build123d import export_stl", "'export_stl'"),
        ("from build123d import Mesher", "'Mesher'"),
        ("x = open('f')", "'open'"),
        ("x = eval('1')", "'eval'"),
        ("x = __import__('os')", "'__import__'"),
        ("x = ().__class__", "'.__class__'"),
        ("x = getattr(1, 'real')", "'getattr'"),
        ("print('hi')", "top level"),
        ("for i in range(3):\n    pass", "top level"),
    ],
)
def test_rejects_unsafe_code(bad, message):
    with pytest.raises(ScriptError, match=message):
        check_script(VALID + "\n" + bad + "\n")


def test_rejects_export_method_inside_build():
    src = VALID.replace("return Box", "b = Box(1, 1, 1)\n    b.export_stl('x.stl')\n    return Box")
    with pytest.raises(ScriptError, match="export_stl"):
        check_script(src)


def test_requires_build_and_params():
    with pytest.raises(ScriptError) as e:
        check_script("import math\n")
    assert "build(p)" in str(e.value) and "PARAMS" in str(e.value)


def test_params_value_must_be_in_range():
    with pytest.raises(ScriptError, match="outside"):
        check_script(VALID.replace('"value": 20.0', '"value": 200.0'))


def test_params_must_be_literal():
    with pytest.raises(ScriptError, match="PARAMS"):
        check_script(VALID.replace('PARAMS = {', 'PARAMS = dict(**{').replace('"Size"}}', '"Size"}})'))


def test_resolve_params_overrides():
    params = check_script(VALID)
    assert resolve_params(params, {"size": 30}) == {"size": 30}
    with pytest.raises(ScriptError, match="between"):
        resolve_params(params, {"size": 1})
    with pytest.raises(ScriptError, match="unknown"):
        resolve_params(params, {"length": 10})


def test_examples_pass_check(examples_dir):
    for path in examples_dir.glob("*.py"):
        assert check_script(path.read_text()), path.name
