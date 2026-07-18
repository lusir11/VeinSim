"""Pydantic schemas for Project endpoints."""

from datetime import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.project import ManufacturingProcess, ProjectStatus


# ── Nested constraint model ───────────────────────────────────────────────────


class HeatSource(BaseModel):
    """A point heat source on the cold plate surface."""
    x: float
    y: float
    z: float
    power_watts: float


class DesignConstraints(BaseModel):
    """User-defined constraints for topology optimization."""
    max_temperature_k: float | None = None        # Kelvin
    max_pressure_drop_pa: float | None = None      # Pascal
    inlet_flow_rate_kg_s: float | None = None      # kg/s
    inlet_velocity_m_s: float | None = None        # m/s
    fluid_type: str = "water"
    heat_sources: list[HeatSource] = []
    fixed_regions: list[str] = []                  # named regions that cannot be optimized
    min_feature_size_mm: float | None = None       # manufacturing min feature
    overhang_angle_deg: float | None = None         # 3D-print overhang constraint


# ── CRUD schemas ──────────────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    manufacturing_process: ManufacturingProcess | None = None
    constraints: DesignConstraints | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    manufacturing_process: ManufacturingProcess | None = None
    constraints: DesignConstraints | None = None
    is_public: bool | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    status: ProjectStatus
    geometry_file_key: str | None
    geometry_format: str | None
    constraints: dict[str, Any] | None
    manufacturing_process: ManufacturingProcess | None
    owner_id: uuid.UUID
    is_public: bool
    created_at: datetime
    updated_at: datetime


class ProjectListRead(BaseModel):
    """Paginated list wrapper."""
    items: list[ProjectRead]
    total: int
