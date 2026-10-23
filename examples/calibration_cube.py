"""20 mm calibration cube."""

# All dimensions in millimeters.
from build123d import Align, Box

PARAMS = {
    "size": {"value": 20.0, "min": 5, "max": 100, "label": "Edge length"},
}


def build(p):
    return Box(p["size"], p["size"], p["size"], align=(Align.CENTER, Align.CENTER, Align.MIN))
