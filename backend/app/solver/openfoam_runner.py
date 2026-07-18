"""OpenFOAM case runner — high-level orchestration of meshing and solving."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def check_openfoam_installed() -> bool:
    """Verify that OpenFOAM is available on the system PATH."""
    try:
        result = subprocess.run(
            ["simpleFoam", "-help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 or "Usage" in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.warning("OpenFOAM not found on PATH — solver tasks will fail")
        return False


def parse_log_residuals(log_path: Path) -> list[float]:
    """Parse an OpenFOAM log file and extract initial residuals for Ux."""
    residuals = []
    if not log_path.exists():
        return residuals

    with open(log_path) as f:
        for line in f:
            if "Solving for Ux" in line and "Initial residual" in line:
                # e.g. "smoothSolver:  Solving for Ux, Initial residual = 0.0012 ..."
                try:
                    parts = line.split("Initial residual = ")
                    val = float(parts[1].split(",")[0].strip())
                    residuals.append(val)
                except (IndexError, ValueError):
                    pass
    return residuals


def parse_forces(forces_dir: Path) -> dict:
    """Parse OpenFOAM postProcessing/forces/ output (stub).

    In production this would read force coefficient files.
    """
    # TODO: implement real force parsing
    return {"drag": None, "lift": None, "pressure_drop_pa": None}
