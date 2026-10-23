"""Pipe spacer: a tube with a given outer diameter, inner diameter and height."""

# All dimensions in millimeters.
from build123d import Align, Cylinder

PARAMS = {
    "outer_d": {"value": 25.0, "min": 3, "max": 290, "label": "Outer diameter"},
    "inner_d": {"value": 16.4, "min": 1, "max": 280, "label": "Inner diameter (16 mm pipe + clearance)"},
    "height": {"value": 10.0, "min": 1, "max": 320, "label": "Height"},
}


def build(p):
    if p["outer_d"] - p["inner_d"] < 2 * 1.2:
        raise ValueError("wall would be thinner than 1.2 mm; increase outer_d or decrease inner_d")
    align = (Align.CENTER, Align.CENTER, Align.MIN)
    outer = Cylinder(p["outer_d"] / 2, p["height"], align=align)
    inner = Cylinder(p["inner_d"] / 2, p["height"], align=align)
    return outer - inner
