"""Mesh checks on an exported STL. Problems are reported as warnings, not failures."""

from dataclasses import dataclass, field
from pathlib import Path

import trimesh

from . import config


@dataclass
class MeshReport:
    watertight: bool
    volume_mm3: float
    size_mm: tuple[float, float, float]
    fits_build_volume: bool
    warnings: list[str] = field(default_factory=list)


def check_mesh(stl_path: Path) -> MeshReport:
    mesh = trimesh.load_mesh(stl_path)
    size = tuple(float(s) for s in mesh.extents)
    # Allow any axis order on the XY plane since the part can be rotated on the bed.
    x, y = sorted(size[:2])
    bx, by = sorted(config.BUILD_VOLUME[:2])
    fits = x <= bx and y <= by and size[2] <= config.BUILD_VOLUME[2]

    warnings = []
    if not mesh.is_watertight:
        warnings.append("mesh is not watertight; the slicer may fail or repair it")
    if not fits:
        warnings.append(
            "part is {:.1f} x {:.1f} x {:.1f} mm and does not fit the {:.0f} x {:.0f} x {:.0f} mm build volume".format(
                *size, *config.BUILD_VOLUME
            )
        )
    return MeshReport(
        watertight=bool(mesh.is_watertight),
        volume_mm3=float(mesh.volume),
        size_mm=size,
        fits_build_volume=fits,
        warnings=warnings,
    )
