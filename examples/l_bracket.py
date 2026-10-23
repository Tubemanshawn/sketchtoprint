"""L-bracket with two M4 clearance holes in each leg. Prints lying on the base leg."""

# All dimensions in millimeters.
from build123d import Align, Box, Cylinder, Pos, Rot

PARAMS = {
    "length": {"value": 40.0, "min": 15, "max": 290, "label": "Leg length"},
    "width": {"value": 20.0, "min": 8, "max": 290, "label": "Width"},
    "thickness": {"value": 4.0, "min": 1.2, "max": 20, "label": "Thickness"},
    "hole_d": {"value": 4.4, "min": 1, "max": 20, "label": "Hole diameter (M4 + clearance)"},
}


def build(p):
    length, width, t, hole_d = p["length"], p["width"], p["thickness"], p["hole_d"]
    if hole_d >= width - 2 * 1.2:
        raise ValueError("holes are too wide for the bracket width")

    corner = (Align.MIN, Align.MIN, Align.MIN)
    base = Box(length, width, t, align=corner)
    upright = Box(t, width, length, align=corner)
    bracket = base + upright

    # Holes at 1/3 and 2/3 along the free part of each leg, centered across the width.
    free = length - t
    stops = [t + free / 3, t + 2 * free / 3]
    y = width / 2
    for s in stops:
        bracket -= Pos(s, y, t / 2) * Cylinder(hole_d / 2, t * 2)
        bracket -= Pos(t / 2, y, s) * Rot(0, 90, 0) * Cylinder(hole_d / 2, t * 2)
    return bracket
