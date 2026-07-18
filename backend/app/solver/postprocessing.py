"""Topology optimization post-processing.

Converts the "gray" porosity field (alpha in [0,1]) from the optimizer
into a clean binary (solid/fluid) field and extracts CAD-ready geometry.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# ── Heaviside projection (gray -> binary) ─────────────────────────────────────


def heaviside_projection(alpha: np.ndarray, threshold: float = 0.5,
                         beta: float = 10.0) -> np.ndarray:
    """Apply smooth Heaviside projection to binarize the porosity field.

    Args:
        alpha: Porosity field, values in [0, 1]. 0=solid, 1=fluid.
        threshold: Cutoff value (default 0.5).
        beta: Sharpness parameter. Higher = sharper transition.

    Returns:
        Binarized field with values close to 0 or 1.
    """
    # Smoothed Heaviside: H(x) = tanh(beta * threshold) + tanh(beta * (x - threshold))
    #                            / (tanh(beta * threshold) + tanh(beta * (1 - threshold)))
    numerator = np.tanh(beta * threshold) + np.tanh(beta * (alpha - threshold))
    denominator = np.tanh(beta * threshold) + np.tanh(beta * (1.0 - threshold))
    return numerator / denominator


def binary_threshold(alpha: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    """Simple hard threshold binarization."""
    return np.where(alpha >= threshold, 1.0, 0.0)


# ── Volume fraction enforcement ───────────────────────────────────────────────


def enforce_volume_fraction(alpha: np.ndarray, target_fraction: float,
                            tolerance: float = 0.01) -> np.ndarray:
    """Adjust threshold to achieve a target fluid volume fraction.

    Uses binary search on the threshold to find the value that produces
    the desired volume fraction of fluid cells.
    """
    low, high = 0.0, 1.0
    for _ in range(50):  # binary search iterations
        mid = (low + high) / 2
        binary = binary_threshold(alpha, mid)
        fraction = binary.mean()
        if abs(fraction - target_fraction) < tolerance:
            return binary
        if fraction > target_fraction:
            low = mid  # need higher threshold -> less fluid
        else:
            high = mid  # need lower threshold -> more fluid
    return binary_threshold(alpha, mid)


# ── Minimum feature size filter ──────────────────────────────────────────────


def apply_density_filter(alpha: np.ndarray, min_feature_cells: int = 3) -> np.ndarray:
    """Apply a simple averaging filter to enforce minimum feature size.

    Cells whose averaged neighborhood value is below 0.5 are set to solid.
    This approximates the PDE-based filtering used in topology optimization.
    """
    from scipy.ndimage import uniform_filter
    filtered = uniform_filter(alpha, size=min_feature_cells)
    return binary_threshold(filtered, 0.5)


# ── Isosurface extraction ─────────────────────────────────────────────────────


def extract_isosurface_stl(alpha_3d: np.ndarray, threshold: float = 0.5,
                           spacing: tuple[float, float, float] = (1e-3, 1e-3, 1e-3),
                           origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
                           ) -> bytes:
    """Extract an STL mesh from the porosity field using marching cubes.

    Args:
        alpha_3d: 3D numpy array of porosity values.
        threshold: Isosurface level.
        spacing: Physical cell size in meters (dx, dy, dz).
        origin: Origin of the grid in meters.

    Returns:
        Binary STL file content as bytes.
    """
    try:
        import trimesh
        from skimage import measure
    except ImportError:
        logger.error("trimesh and scikit-image required for STL extraction")
        return b""

    # Marching cubes
    verts, faces, normals, _ = measure.marching_cubes(
        alpha_3d,
        level=threshold,
        spacing=spacing,
    )
    # Shift to origin
    verts[:, 0] += origin[0]
    verts[:, 1] += origin[1]
    verts[:, 2] += origin[2]

    # Create trimesh and export as STL
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, vertex_normals=normals)
    mesh.fix_normals()

    stl_bytes = trimesh.exchange.stl.export_stl(mesh)
    logger.info("Extracted isosurface: %d vertices, %d faces", len(verts), len(faces))
    return stl_bytes


# ── High-level post-processing pipeline ──────────────────────────────────────


def post_process_optimization(
    alpha_field: np.ndarray,
    target_volume_fraction: float = 0.4,
    min_feature_cells: int = 3,
    use_heaviside: bool = True,
    heaviside_beta: float = 20.0,
    extract_stl: bool = True,
    cell_spacing_m: tuple[float, float, float] = (1e-3, 1e-3, 1e-3),
) -> dict[str, Any]:
    """Full post-processing pipeline for topology optimization results.

    Steps:
    1. Apply density filter (minimum feature enforcement)
    2. Apply Heaviside projection (sharpen boundaries)
    3. Enforce target volume fraction
    4. Extract STL isosurface (if 3D)

    Returns dict with keys:
    - alpha_processed: Final processed porosity field
    - volume_fraction: Actual fluid volume fraction achieved
    - stl_bytes: Binary STL content (if extract_stl and 3D)
    """
    result: dict[str, Any] = {}

    # Step 1: Minimum feature filter
    if min_feature_cells > 1:
        alpha_field = apply_density_filter(alpha_field, min_feature_cells)

    # Step 2: Heaviside projection
    if use_heaviside:
        alpha_field = heaviside_projection(alpha_field, beta=heaviside_beta)

    # Step 3: Volume fraction enforcement
    alpha_field = enforce_volume_fraction(alpha_field, target_volume_fraction)

    result["alpha_processed"] = alpha_field
    result["volume_fraction"] = float(alpha_field.mean())

    # Step 4: STL extraction (only for 3D fields)
    if extract_stl and alpha_field.ndim == 3:
        stl = extract_isosurface_stl(alpha_field, spacing=cell_spacing_m)
        result["stl_bytes"] = stl

    return result
