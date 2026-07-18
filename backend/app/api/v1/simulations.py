"""Simulation CRUD and launch endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.simulation import Simulation, OptimizationResult, SimulationStatus
from app.models.user import User
from app.schemas.simulation import (
    SimulationCreate,
    SimulationRead,
    SimulationListRead,
    OptimizationResultRead,
    StlUrlRead,
    DashboardStatsRead,
)
from app.services.auth_service import get_current_user
from app.services.minio_service import get_presigned_url
from app.celery_worker import run_simulation_task

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("", response_model=SimulationRead, status_code=status.HTTP_201_CREATED)
async def create_simulation(
    payload: SimulationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a simulation record and optionally launch the solver."""
    run_params_dict = payload.run_params.model_dump() if payload.run_params else {}

    sim = Simulation(
        project_id=payload.project_id,
        solver_type=payload.solver_type,
        status=SimulationStatus.QUEUED,
        run_params=run_params_dict,
    )
    db.add(sim)
    await db.flush()
    await db.refresh(sim)

    # Dispatch Celery task
    task = run_simulation_task.delay(str(sim.id), run_params_dict)
    sim.celery_task_id = task.id
    sim.status = SimulationStatus.RUNNING
    await db.flush()
    await db.refresh(sim)

    return sim


@router.get("", response_model=SimulationListRead)
async def list_simulations(
    project_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List simulations, optionally filtered by project."""
    base_q = select(Simulation)
    count_q = select(sa_func.count(Simulation.id))

    if project_id:
        base_q = base_q.where(Simulation.project_id == project_id)
        count_q = count_q.where(Simulation.project_id == project_id)

    total = (await db.execute(count_q)).scalar() or 0
    stmt = base_q.order_by(Simulation.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return SimulationListRead(items=items, total=total)


# ── Dashboard stats (must be BEFORE /{simulation_id} to avoid path conflict) ─


@router.get("/stats/dashboard", response_model=DashboardStatsRead)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return aggregated statistics for the dashboard."""
    from app.models.project import Project

    total_projects = (await db.execute(
        select(sa_func.count(Project.id)).where(Project.owner_id == current_user.id)
    )).scalar() or 0

    total_simulations = (await db.execute(
        select(sa_func.count(Simulation.id))
    )).scalar() or 0

    converged_count = (await db.execute(
        select(sa_func.count(Simulation.id)).where(Simulation.status == SimulationStatus.CONVERGED)
    )).scalar() or 0

    running_count = (await db.execute(
        select(sa_func.count(Simulation.id)).where(
            Simulation.status.in_([
                SimulationStatus.RUNNING,
                SimulationStatus.MESHING,
                SimulationStatus.QUEUED,
            ])
        )
    )).scalar() or 0

    return DashboardStatsRead(
        total_projects=total_projects,
        total_simulations=total_simulations,
        converged_count=converged_count,
        running_count=running_count,
    )


@router.get("/{simulation_id}", response_model=SimulationRead)
async def get_simulation(
    simulation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Simulation).where(Simulation.id == simulation_id)
    result = await db.execute(stmt)
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim


@router.post("/{simulation_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_simulation(
    simulation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a running simulation."""
    stmt = select(Simulation).where(Simulation.id == simulation_id)
    result = await db.execute(stmt)
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if sim.celery_task_id:
        from app.celery_worker import celery_app
        celery_app.control.revoke(sim.celery_task_id, terminate=True)

    sim.status = SimulationStatus.CANCELLED
    await db.flush()
    return {"detail": "Simulation cancelled", "simulation_id": str(sim.id)}


@router.get("/{simulation_id}/results", response_model=list[OptimizationResultRead])
async def get_simulation_results(
    simulation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all optimization result records for a simulation."""
    stmt = (
        select(OptimizationResult)
        .where(OptimizationResult.simulation_id == simulation_id)
        .order_by(OptimizationResult.iteration)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{simulation_id}/stl-url", response_model=StlUrlRead)
async def get_simulation_stl_url(
    simulation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a presigned URL for the optimized STL geometry."""
    stmt = select(OptimizationResult).where(
        OptimizationResult.simulation_id == simulation_id,
        OptimizationResult.is_final == True,
    )
    result = await db.execute(stmt)
    opt = result.scalar_one_or_none()

    if not opt or not opt.stl_file_key:
        raise HTTPException(status_code=404, detail="No STL result available for this simulation")

    url = get_presigned_url(opt.stl_file_key, expires_hours=1)
    return StlUrlRead(url=url, expires_in=3600)
