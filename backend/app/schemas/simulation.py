"""Pydantic schemas for Simulation endpoints."""

from datetime import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.simulation import SimulationStatus, SolverType


# ── Run-parameter schema ─────────────────────────────────────────────────────


class RunParams(BaseModel):
    """Parameters passed to the OpenFOAM solver."""
    inlet_velocity: list[float] = [0.1, 0.0, 0.0]  # [u, v, w] m/s
    outlet_pressure: float = 0.0                     # Pa gauge
    wall_temperature: float = 300.0                  # K
    fluid_density: float = 998.2                     # kg/m^3 (water)
    fluid_viscosity: float = 1.002e-3                # Pa·s
    fluid_specific_heat: float = 4182.0              # J/(kg·K)
    fluid_thermal_conductivity: float = 0.6          # W/(m·K)
    convergence_tolerance: float = 1e-5
    max_iterations: int = 500
    optimization_weight_thermal: float = 1.0         # weight for heat transfer objective
    optimization_weight_pressure: float = 0.1        # weight for pressure-drop penalty


# ── CRUD schemas ──────────────────────────────────────────────────────────────


class SimulationCreate(BaseModel):
    project_id: uuid.UUID
    solver_type: SolverType = SolverType.ADJOINT_SHAPE_OPT
    run_params: RunParams | None = None


class SimulationStatusUpdate(BaseModel):
    status: SimulationStatus


class SimulationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    solver_type: SolverType
    status: SimulationStatus
    case_dir: str | None
    mesh_cell_count: int | None
    mesh_quality_score: float | None
    run_params: dict[str, Any] | None
    residual_history: list[Any] | None
    final_residual: float | None
    iterations_completed: int | None
    wall_time_seconds: float | None
    celery_task_id: str | None
    created_at: datetime
    updated_at: datetime


class SimulationListRead(BaseModel):
    items: list[SimulationRead]
    total: int


class OptimizationResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    simulation_id: uuid.UUID
    iteration: int
    metrics: dict[str, Any] | None
    vtu_file_key: str | None
    stl_file_key: str | None
    porosity_field_key: str | None
    is_final: bool
    created_at: datetime
