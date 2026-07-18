"""Celery application and async simulation tasks with progress reporting."""

import logging
import uuid

from celery import Celery

from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "veinsim_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=settings.SOLVER_TIMEOUT_SECONDS + 600,
    task_soft_time_limit=settings.SOLVER_TIMEOUT_SECONDS,
)


@celery_app.task(bind=True, name="run_simulation")
def run_simulation_task(self, simulation_id: str, run_params: dict) -> dict:
    """
    Celery task: prepare OpenFOAM case -> mesh -> solve -> post-process.
    Publishes progress events to Redis for WebSocket forwarding.
    """
    from app.services.solver_service import (
        create_case_dir,
        write_transport_properties,
        write_control_dict,
        write_adjoint_dict,
        run_meshing,
        run_solver,
        extract_metrics,
    )
    from app.services.progress_publisher import (
        publish_status,
        publish_iteration,
        publish_result,
    )

    sim_id = simulation_id
    logger.info("Starting simulation %s", sim_id)

    # ── Step 1: Prepare case directory ────────────────────────────────────
    publish_status(sim_id, "meshing", message="Preparing case directory...")
    case_dir = create_case_dir(uuid.UUID(sim_id))

    # ── Step 2: Write OpenFOAM dictionaries ──────────────────────────────
    write_transport_properties(case_dir, run_params)
    write_control_dict(case_dir, run_params)
    write_adjoint_dict(case_dir, run_params)

    # ── Step 3: Meshing ──────────────────────────────────────────────────
    publish_status(sim_id, "meshing", message="Generating mesh...")
    mesh_result = run_meshing(case_dir)
    if not mesh_result["success"]:
        publish_status(sim_id, "failed", phase="meshing", error=mesh_result["stderr"])
        return {
            "status": "failed",
            "phase": "meshing",
            "error": mesh_result["stderr"],
            "cell_count": mesh_result.get("cell_count", 0),
        }
    publish_status(sim_id, "running", message="Mesh complete, starting solver...",
                   cell_count=mesh_result["cell_count"])

    # ── Step 4: Solve ────────────────────────────────────────────────────
    solve_result = run_solver(case_dir)

    # Parse iteration-by-iteration residuals and publish progress
    for i, res in enumerate(solve_result.get("residual_history", [])):
        publish_iteration(sim_id, iteration=i, residual=res)

    if not solve_result["success"]:
        publish_status(sim_id, "failed", phase="solving", error=solve_result["stderr_tail"])
        return {
            "status": "failed",
            "phase": "solving",
            "error": solve_result["stderr_tail"],
            "mesh_cell_count": mesh_result["cell_count"],
            "wall_time_seconds": solve_result.get("wall_time_seconds"),
        }

    # ── Step 5: Post-process ─────────────────────────────────────────────
    metrics = extract_metrics(case_dir)
    publish_status(sim_id, "converged", message="Optimization converged!")
    publish_result(sim_id, metrics=metrics, file_keys={
        "case_dir": str(case_dir),
    })

    return {
        "status": "converged",
        "simulation_id": simulation_id,
        "mesh_cell_count": mesh_result["cell_count"],
        "iterations_completed": solve_result["iterations"],
        "final_residual": solve_result["final_residual"],
        "wall_time_seconds": solve_result["wall_time_seconds"],
        "metrics": metrics,
        "case_dir": str(case_dir),
    }
