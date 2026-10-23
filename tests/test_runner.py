import zipfile

import pytest

from sketchtoprint.runner import RunError, run_script


def test_calibration_cube(examples_dir, tmp_path):
    run = run_script((examples_dir / "calibration_cube.py").read_text(), tmp_path)
    assert run.mesh.watertight
    assert run.mesh.size_mm == pytest.approx((20, 20, 20))
    assert run.mesh.volume_mm3 == pytest.approx(8000)
    assert all(p.exists() and p.stat().st_size > 0 for p in run.files.values())
    with zipfile.ZipFile(run.files["3mf"]) as z:
        model = z.read("3D/3dmodel.model").decode()
    assert model.count("<vertex ") >= 8 and model.count("<triangle ") >= 12


def test_l_bracket_volume_and_override(examples_dir, tmp_path):
    run = run_script((examples_dir / "l_bracket.py").read_text(), tmp_path, {"length": 60})
    assert run.mesh.watertight
    assert run.mesh.size_mm == pytest.approx((60, 20, 60))
    # two 60x20x4 legs sharing a 4x20x4 corner, minus four 4.4 mm holes through 4 mm
    expected = 2 * 60 * 20 * 4 - 4 * 20 * 4 - 4 * 3.14159265 * 2.2**2 * 4
    assert run.mesh.volume_mm3 == pytest.approx(expected, rel=1e-2)


def test_pipe_spacer(examples_dir, tmp_path):
    run = run_script((examples_dir / "pipe_spacer.py").read_text(), tmp_path)
    assert run.mesh.watertight
    assert run.mesh.size_mm[2] == pytest.approx(10)


def test_build_error_is_reported(examples_dir, tmp_path):
    src = (examples_dir / "pipe_spacer.py").read_text()
    with pytest.raises(RunError, match="thinner than 1.2"):
        run_script(src, tmp_path, {"outer_d": 17})


def test_oversized_part_warns(examples_dir, tmp_path):
    src = (examples_dir / "calibration_cube.py").read_text().replace('"max": 100', '"max": 400')
    run = run_script(src, tmp_path, {"size": 340})
    assert not run.mesh.fits_build_volume
    assert any("build volume" in w for w in run.warnings)


def test_timeout(tmp_path):
    src = '''
from build123d import Box

PARAMS = {"n": {"value": 1.0, "min": 0, "max": 2, "label": "n"}}


def build(p):
    while True:
        pass
'''
    with pytest.raises(RunError, match="longer than"):
        run_script(src, tmp_path, timeout=3)
