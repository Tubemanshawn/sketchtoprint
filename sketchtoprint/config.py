"""Printer defaults and app settings. All lengths are in millimeters."""

import os
from pathlib import Path

# Creality Ender 3 V3 Plus. Verify against the official spec sheet.
BUILD_VOLUME = (300.0, 300.0, 330.0)  # X, Y, Z
NOZZLE_DIAMETER = 0.4
MIN_WALL = 1.2
FIT_CLEARANCE = 0.2
HOLE_COMPENSATION = 0.2  # added to hole diameters, holes print undersized
OVERHANG_WARN_DEG = 45.0

# Claude settings. The API key is read from ANTHROPIC_API_KEY by the SDK.
MODEL = os.environ.get("SKETCHTOPRINT_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("SKETCHTOPRINT_EFFORT", "high")
MAX_TOKENS = 16000
MAX_REPAIR_ATTEMPTS = 2

SCRIPT_TIMEOUT_S = 30
OUTPUT_DIR = Path(os.environ.get("SKETCHTOPRINT_OUTPUT", "output"))
