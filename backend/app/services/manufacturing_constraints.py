"""Manufacturing constraint generators.

Each constraint class produces OpenFOAM dictionary entries or
post-processing filters that ensure the optimized design can be
manufactured with a specific process.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Base class ────────────────────────────────────────────────────────────────


class ManufacturingConstraint(ABC):
    """Abstract base for all manufacturing constraints."""

    @abstractmethod
    def to_openfoam_dict(self) -> dict[str, Any]:
        """Return OpenFOAM-compatible dictionary entries for adjointDict."""
        ...

    @abstractmethod
    def name(self) -> str:
        ...

    def validate(self, params: dict) -> list[str]:
        """Return a list of validation warnings/errors for given parameters."""
        return []


# ── Stamping (2.5D / no undercut) ────────────────────────────────────────────


@dataclass
class StampingConstraint(ManufacturingConstraint):
    """Constrains design to 2.5D (no undercuts) along a specified pull direction."""

    pull_direction: tuple[float, float, float] = (0.0, 0.0, 1.0)
    min_wall_thickness_mm: float = 1.0
    draft_angle_deg: float = 2.0

    def name(self) -> str:
        return "stamping"

    def to_openfoam_dict(self) -> dict[str, Any]:
        return {
            "manufacturingConstraint": "extrusion",
            "extrusionDirection": list(self.pull_direction),
            "minWallThickness": self.min_wall_thickness_mm / 1000.0,  # mm -> m
            "draftAngle": self.draft_angle_deg,
        }

    def validate(self, params: dict) -> list[str]:
        warnings = []
        if self.min_wall_thickness_mm < 0.5:
            warnings.append("Wall thickness < 0.5mm may cause stamping issues")
        if self.draft_angle_deg < 1.0:
            warnings.append("Draft angle < 1° — consider increasing for die release")
        return warnings


# ── CNC Machining ─────────────────────────────────────────────────────────────


@dataclass
class CNCConstraint(ManufacturingConstraint):
    """Constrains minimum feature size to tool radius and checks tool accessibility."""

    tool_diameter_mm: float = 3.0
    max_depth_mm: float = 50.0
    approach_direction: tuple[float, float, float] = (0.0, 0.0, 1.0)

    def name(self) -> str:
        return "cnc"

    def to_openfoam_dict(self) -> dict[str, Any]:
        return {
            "manufacturingConstraint": "cnc",
            "minFeatureSize": self.tool_diameter_mm / 1000.0,  # m
            "minCurvatureRadius": self.tool_diameter_mm / 2000.0,  # half diameter
            "maxDepth": self.max_depth_mm / 1000.0,
            "approachDirection": list(self.approach_direction),
        }

    def validate(self, params: dict) -> list[str]:
        warnings = []
        if self.tool_diameter_mm > 10:
            warnings.append("Large tool diameter — fine features may be lost")
        return warnings


# ── Chemical Etching ──────────────────────────────────────────────────────────


@dataclass
class ChemicalEtchingConstraint(ManufacturingConstraint):
    """Constrains minimum feature size and aspect ratio for chemical etching."""

    min_feature_size_mm: float = 0.1
    max_aspect_ratio: float = 5.0  # depth / width
    plate_thickness_mm: float = 1.0

    def name(self) -> str:
        return "chemical_etching"

    def to_openfoam_dict(self) -> dict[str, Any]:
        return {
            "manufacturingConstraint": "etching",
            "minFeatureSize": self.min_feature_size_mm / 1000.0,
            "maxAspectRatio": self.max_aspect_ratio,
            "plateThickness": self.plate_thickness_mm / 1000.0,
        }


# ── 3D Printing (Additive Manufacturing) ─────────────────────────────────────


@dataclass
class AdditiveManufacturingConstraint(ManufacturingConstraint):
    """Constrains overhang angle and minimum wall thickness for AM processes."""

    overhang_angle_deg: float = 45.0  # max overhang without supports
    min_wall_thickness_mm: float = 0.4  # typical for SLM/DMLS
    min_feature_size_mm: float = 0.2
    build_direction: tuple[float, float, float] = (0.0, 0.0, 1.0)
    layer_height_mm: float = 0.05

    def name(self) -> str:
        return "3d_print"

    def to_openfoam_dict(self) -> dict[str, Any]:
        import math
        # Convert overhang angle to cosine for the solver
        overhang_cos = math.cos(math.radians(90 - self.overhang_angle_deg))
        return {
            "manufacturingConstraint": "additive",
            "overhangCosine": overhang_cos,
            "overhangAngle": self.overhang_angle_deg,
            "minWallThickness": self.min_wall_thickness_mm / 1000.0,
            "minFeatureSize": self.min_feature_size_mm / 1000.0,
            "buildDirection": list(self.build_direction),
            "layerHeight": self.layer_height_mm / 1000.0,
        }

    def validate(self, params: dict) -> list[str]:
        warnings = []
        if self.overhang_angle_deg > 60:
            warnings.append("Overhang > 60° will likely require support structures")
        if self.min_wall_thickness_mm < 0.3:
            warnings.append("Wall < 0.3mm — check printer capability")
        return warnings


# ── Factory ───────────────────────────────────────────────────────────────────


def create_constraint(process: str, params: dict | None = None) -> ManufacturingConstraint:
    """Factory: create a constraint instance from process name and parameters."""
    params = params or {}
    mapping: dict[str, type[ManufacturingConstraint]] = {
        "stamping": StampingConstraint,
        "cnc": CNCConstraint,
        "chemical_etching": ChemicalEtchingConstraint,
        "3d_print": AdditiveManufacturingConstraint,
    }
    cls = mapping.get(process)
    if cls is None:
        raise ValueError(f"Unknown manufacturing process: {process!r}. "
                         f"Available: {list(mapping.keys())}")
    return cls(**params)
