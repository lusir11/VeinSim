"""OpenFOAM solver integration — case management, log parsing, and post-processing."""

from app.solver.openfoam_runner import (
    check_openfoam_installed,
    parse_log_residuals,
    parse_forces,
)
from app.solver.postprocessing import (
    heaviside_projection,
    binary_threshold,
    enforce_volume_fraction,
    apply_density_filter,
    extract_isosurface_stl,
    post_process_optimization,
)

__all__ = [
    "check_openfoam_installed",
    "parse_log_residuals",
    "parse_forces",
    "heaviside_projection",
    "binary_threshold",
    "enforce_volume_fraction",
    "apply_density_filter",
    "extract_isosurface_stl",
    "post_process_optimization",
]
