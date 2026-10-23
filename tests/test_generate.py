"""design_part with a fake Claude client, so no API key is needed."""

from types import SimpleNamespace

from sketchtoprint.generate import PartDesign, design_part

BROKEN = "from build123d import Box\nimport os\n"


def _response(design: PartDesign):
    return SimpleNamespace(
        stop_reason="end_turn",
        parsed_output=design,
        content=[SimpleNamespace(type="text", text=design.model_dump_json())],
    )


class FakeClient:
    def __init__(self, designs):
        self.designs = list(designs)
        self.calls = []
        self.messages = SimpleNamespace(parse=self._parse)

    def _parse(self, **kwargs):
        self.calls.append([dict(m) for m in kwargs["messages"]])
        return _response(self.designs.pop(0))


def _design(script, status="ok"):
    return PartDesign(status=status, part_name="cube", script=script, assumptions=["a"], questions=[])


def test_happy_path(examples_dir, tmp_path):
    client = FakeClient([_design((examples_dir / "calibration_cube.py").read_text())])
    result = design_part("a 20 mm cube", tmp_path, client)
    assert result.run.mesh.watertight
    assert result.errors == []


def test_repairs_bad_script(examples_dir, tmp_path):
    good = (examples_dir / "calibration_cube.py").read_text()
    client = FakeClient([_design(BROKEN), _design(good)])
    result = design_part("a 20 mm cube", tmp_path, client)
    assert result.run is not None
    assert len(result.errors) == 1
    feedback = client.calls[1][-1]["content"]
    assert "import of 'os'" in feedback


def test_need_info_skips_run(tmp_path):
    client = FakeClient([_design("", status="need_info")])
    result = design_part("a bracket for my shelf", tmp_path, client)
    assert result.run is None
    assert result.design.status == "need_info"
