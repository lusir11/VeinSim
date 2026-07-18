"""Solver orchestration service — bridges the API layer with OpenFOAM."""

import json
import logging
import os
import random
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE_CASES_DIR = Path(settings.OPENFOAM_CASES_DIR)
TEMPLATE_DIR = Path(__file__).parent.parent / "solver" / "templates"


# ── Case directory management ─────────────────────────────────────────────────


def create_case_dir(simulation_id: uuid.UUID, template_name: str = "coldplate_2d") -> Path:
    """Copy a template case directory and return the new case path."""
    case_dir = BASE_CASES_DIR / str(simulation_id)
    case_dir.mkdir(parents=True, exist_ok=True)

    template_src = TEMPLATE_DIR / template_name
    if template_src.exists():
        shutil.copytree(template_src, case_dir, dirs_exist_ok=True)
        logger.info("Copied template %s -> %s", template_name, case_dir)
    else:
        logger.warning("Template %s not found at %s — created empty case dir", template_name, template_src)

    return case_dir


# ── OpenFOAM dictionary writers ───────────────────────────────────────────────


def write_transport_properties(case_dir: Path, params: dict) -> None:
    """Write constant/transportProperties from run parameters."""
    content = f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      transportProperties;
}}

nu              [0 2 -1 0 0 0 0] {params.get('kinematic_viscosity', 1.004e-6)};
Cp              [0 2 -2 -1 0 0 0] {params.get('fluid_specific_heat', 4182.0)};
k               [0 2 -1 -1 0 0 0] {params.get('fluid_thermal_conductivity', 0.6)};
rho             [1 -3 0 0 0 0 0] {params.get('fluid_density', 998.2)};
"""
    const_dir = case_dir / "constant"
    const_dir.mkdir(exist_ok=True)
    (const_dir / "transportProperties").write_text(content)


def write_control_dict(case_dir: Path, params: dict) -> None:
    """Write system/controlDict."""
    max_iters = params.get("max_iterations", 500)
    content = f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      controlDict;
}}

application     adjointShapeOptimizationFoam;
startFrom       latestTime;
startTime       0;
stopAt          endTime;
endTime         {max_iters};
deltaT          1;
writeControl    timeStep;
writeInterval   50;
purgeWrite      0;
writeFormat     binary;
writePrecision  8;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable yes;
"""
    sys_dir = case_dir / "system"
    sys_dir.mkdir(exist_ok=True)
    (sys_dir / "controlDict").write_text(content)


def write_adjoint_dict(case_dir: Path, params: dict) -> None:
    """Write system/adjointDict for topology optimization objectives."""
    w_thermal = params.get("optimization_weight_thermal", 1.0)
    w_pressure = params.get("optimization_weight_pressure", 0.1)
    content = f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      adjointDict;
}}

// ── Objective function weights ──────────────────────────────────────────────
objectiveWeight
{{
    heatTransfer    {w_thermal};
    pressureDrop    {w_pressure};
}}

// ── Design variable: porosity field (alpha) ─────────────────────────────────
designVariable
{{
    type        porosity;
    fieldName   alpha;
    lowerBound  0.0;
    upperBound  1.0;
}}

// ── Constraints ─────────────────────────────────────────────────────────────
constraints
{{
    // volume fraction constraint (solid cannot exceed this fraction)
    maxSolidFraction  0.6;
}}
"""
    sys_dir = case_dir / "system"
    sys_dir.mkdir(exist_ok=True)
    (sys_dir / "adjointDict").write_text(content)


# ── Solver execution ──────────────────────────────────────────────────────────


def run_meshing(case_dir: Path) -> dict:
    """Run snappyHexMesh and return mesh statistics."""
    if settings.SOLVER_MOCK:
        logger.info("[MOCK] Running meshing in %s", case_dir)
        time.sleep(1)  # simulate meshing time
        cell_count = random.randint(12000, 45000)
        return {
            "success": True,
            "stdout": f"[MOCK] Mesh generation complete: {cell_count} cells",
            "stderr": "",
            "cell_count": cell_count,
        }

    logger.info("Running snappyHexMesh in %s", case_dir)
    result = subprocess.run(
        ["snappyHexMesh", "-overwrite", "-case", str(case_dir)],
        capture_output=True,
        text=True,
        timeout=settings.SOLVER_TIMEOUT_SECONDS,
    )
    cell_count = 0
    for line in result.stdout.splitlines():
        if "nCells:" in line:
            try:
                cell_count = int(line.split(":")[-1].strip())
            except ValueError:
                pass

    return {
        "success": result.returncode == 0,
        "stdout": result.stdout[-2000:],  # last 2000 chars
        "stderr": result.stderr[-2000:],
        "cell_count": cell_count,
    }


def run_solver(case_dir: Path, parallel: int = 0) -> dict:
    """Run the OpenFOAM solver and return execution metadata."""
    if settings.SOLVER_MOCK:
        return _run_mock_solver(case_dir)

    cmd = []
    n_procs = parallel if parallel > 0 else settings.SOLVER_MAX_PARALLEL

    if n_procs > 1:
        # Decompose first
        subprocess.run(
            ["decomposePar", "-case", str(case_dir)],
            capture_output=True,
            timeout=300,
        )
        cmd = ["mpirun", "-np", str(n_procs),
               "adjointShapeOptimizationFoam", "-parallel", "-case", str(case_dir)]
    else:
        cmd = ["adjointShapeOptimizationFoam", "-case", str(case_dir)]

    logger.info("Running solver: %s", " ".join(cmd))
    start = time.time()

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=settings.SOLVER_TIMEOUT_SECONDS,
    )
    wall_time = time.time() - start

    # Parse residuals from log
    residual_history = []
    final_residual = None
    iterations = 0
    for line in result.stdout.splitlines():
        if "Initial residual" in line:
            try:
                val = float(line.split("Initial residual = ")[1].split(",")[0].strip())
                residual_history.append(val)
                final_residual = val
            except (IndexError, ValueError):
                pass
        if "Time =" in line:
            try:
                iterations = int(line.split("=")[1].strip().rstrip(";"))
            except (ValueError, IndexError):
                pass

    return {
        "success": result.returncode == 0,
        "wall_time_seconds": round(wall_time, 2),
        "iterations": iterations,
        "final_residual": final_residual,
        "residual_history": residual_history,
        "stdout_tail": result.stdout[-3000:],
        "stderr_tail": result.stderr[-3000:],
    }


def _run_mock_solver(case_dir: Path) -> dict:
    """Generate realistic mock solver results with exponential decay residuals."""
    logger.info("[MOCK] Running solver in %s", case_dir)

    # Read max_iterations from controlDict if available
    max_iters = 500
    control_dict_path = case_dir / "system" / "controlDict"
    if control_dict_path.exists():
        content = control_dict_path.read_text()
        for line in content.splitlines():
            if "endTime" in line and not line.strip().startswith("//"):
                try:
                    max_iters = int(line.split()[-1].rstrip(";"))
                except (ValueError, IndexError):
                    pass

    # Generate exponential decay residual curve
    initial_residual = random.uniform(0.1, 1.0)
    decay = random.uniform(0.008, 0.018)
    iterations = random.randint(int(max_iters * 0.6), max_iters)

    residual_history = []
    for i in range(iterations):
        base = initial_residual * np.exp(-decay * i)
        noise = base * random.gauss(0, 0.05)
        res = max(base + noise, 1e-8)
        residual_history.append(float(res))

    final_residual = residual_history[-1] if residual_history else 1e-5
    wall_time = random.uniform(30, 120)

    # Simulate solver execution time
    time.sleep(3)

    return {
        "success": True,
        "wall_time_seconds": round(wall_time, 2),
        "iterations": iterations,
        "final_residual": final_residual,
        "residual_history": residual_history,
        "stdout_tail": f"[MOCK] Solver completed {iterations} iterations, final residual: {final_residual:.2e}",
        "stderr_tail": "",
    }


# ── Mock alpha field generation ──────────────────────────────────────────────


def generate_mock_alpha_field(shape: tuple[int, int, int] = (30, 30, 10)) -> np.ndarray:
    """Generate a mock 3D porosity field with channel-like structures.

    Uses random noise + Gaussian smoothing to create a pseudo-optimized
    topology with connected flow channels.
    """
    from scipy.ndimage import gaussian_filter

    logger.info("[MOCK] Generating alpha field with shape %s", shape)

    # Base random field
    np.random.seed(42)  # reproducible for consistent results
    noise = np.random.random(shape)

    # Smooth to create connected structures
    alpha = gaussian_filter(noise, sigma=2.5)

    # Normalize to [0, 1]
    alpha = (alpha - alpha.min()) / (alpha.max() - alpha.min())

    # Create inlet/outlet channels (left/right faces = fluid)
    alpha[:, :2, :] = np.clip(alpha[:, :2, :] + 0.4, 0, 1)
    alpha[:, -2:, :] = np.clip(alpha[:, -2:, :] + 0.4, 0, 1)

    # Create some branching structure via thresholding
    alpha = np.where(alpha > 0.55, np.clip(alpha + 0.2, 0, 1), np.clip(alpha - 0.15, 0, 1))

    return alpha


# ── Result post-processing ────────────────────────────────────────────────────


def extract_metrics(case_dir: Path) -> dict:
    """Parse log and postProcessing output to extract performance metrics."""
    if settings.SOLVER_MOCK:
        logger.info("[MOCK] Extracting metrics from %s", case_dir)
        return {
            "max_temperature_k": round(345.2 + random.uniform(-5, 5), 2),
            "avg_temperature_k": round(318.7 + random.uniform(-3, 3), 2),
            "pressure_drop_pa": round(1250.0 + random.uniform(-200, 200), 1),
            "nusselt_number": round(8.5 + random.uniform(-1, 1), 3),
            "thermal_resistance_k_w": round(0.042 + random.uniform(-0.005, 0.005), 4),
            "pumping_power_w": round(2.3 + random.uniform(-0.3, 0.3), 2),
        }

    # TODO: parse real postProcessing/ data
    return {
        "max_temperature_k": None,
        "avg_temperature_k": None,
        "pressure_drop_pa": None,
        "nusselt_number": None,
        "thermal_resistance_k_w": None,
        "pumping_power_w": None,
    }
