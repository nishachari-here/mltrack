from __future__ import annotations

from contextlib import asynccontextmanager
import json
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from ..db import get_engine
from .queries import QueryEngine
from .schemas import (
    DatasetRegisterRequest, DeploymentCreateRequest, DeploymentStatusRequest,
    ReproducibilityCheckRequest, RunCreateRequest,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.engine = get_engine()
        app.state.queries = QueryEngine(app.state.engine)
    except RuntimeError:
        app.state.engine = None
        app.state.queries = None
    yield


app = FastAPI(title="ModelTrace API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health")
def health() -> dict[str, str]:
    engine = getattr(app.state, "engine", None)
    if engine is None:
        return {"status": "ok", "database": "not_configured"}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from exc


@app.get("/projects")
def projects() -> list[dict[str, Any]]:
    if app.state.queries is None:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")
    return app.state.queries.projects()


@app.get("/projects/{project_id}/experiments")
def experiments(project_id: int) -> list[dict[str, Any]]:
    return app.state.queries.experiments(project_id)


@app.get("/datasets")
def datasets() -> list[dict[str, Any]]:
    return app.state.queries.datasets()


@app.get("/datasets/{dataset_id}/versions")
def dataset_versions(dataset_id: int) -> list[dict[str, Any]]:
    return app.state.queries.dataset_versions(dataset_id)


@app.get("/runs")
def runs(
    experiment_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    dataset_version_id: int | None = Query(default=None),
) -> list[dict[str, Any]]:
    return app.state.queries.runs(experiment_id, status, dataset_version_id)


@app.get("/runs/{run_id}")
def run_detail(run_id: int) -> dict[str, Any]:
    result = app.state.queries.run_detail(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Training run not found")
    return result


@app.get("/models")
def models() -> list[dict[str, Any]]:
    return app.state.queries.models()


@app.get("/models/{model_id}/versions")
def model_versions(model_id: int) -> list[dict[str, Any]]:
    return app.state.queries.model_versions(model_id)


@app.get("/lineage/run/{run_id}")
def lineage_run(run_id: int) -> dict[str, Any]:
    result = app.state.queries.lineage_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Training run not found")
    return result


@app.get("/lineage/model/{model_version_id}")
def lineage_model(model_version_id: int) -> dict[str, Any]:
    result = app.state.queries.lineage_model(model_version_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Model version not found")
    return result


@app.post("/datasets/register", status_code=201)
def register_dataset(payload: DatasetRegisterRequest) -> dict[str, Any]:
    engine = app.state.engine
    with engine.begin() as connection:
        existing = connection.execute(
            text("SELECT dataset_id FROM datasets WHERE name = :name"),
            {"name": payload.name},
        ).mappings().first()
        if existing:
            dataset_id = existing["dataset_id"]
        else:
            inserted = connection.execute(
                text("INSERT INTO datasets (name, description, data_type) VALUES (:name, :description, :data_type) RETURNING dataset_id"),
                payload.model_dump(exclude={"version_no", "hash", "statistics", "storage_path"}),
            )
            dataset_id = inserted.mappings().first()["dataset_id"]
        version = connection.execute(
            text("SELECT dataset_version_id FROM dataset_versions WHERE hash = :hash"),
            {"hash": payload.hash},
        ).mappings().first()
        if version:
            return dict(version)
        result = connection.execute(
            text("""INSERT INTO dataset_versions
                    (dataset_id, version_no, hash, statistics, storage_path)
                    VALUES (:dataset_id, :version_no, :hash, :statistics, :storage_path)
                    RETURNING dataset_version_id"""),
            {
                "dataset_id": dataset_id,
                "version_no": payload.version_no,
                "hash": payload.hash,
                "statistics": json.dumps(payload.statistics) if payload.statistics is not None else None,
                "storage_path": payload.storage_path,
            },
        )
        return dict(result.mappings().first())


@app.post("/runs", status_code=201)
def create_run(payload: RunCreateRequest) -> dict[str, Any]:
    engine = app.state.engine
    with engine.begin() as connection:
        if payload.run_number is None:
            current = connection.execute(
                text("SELECT COALESCE(MAX(run_number), 0) FROM training_runs WHERE experiment_id = :experiment_id"),
                {"experiment_id": payload.experiment_id},
            ).scalar()
            run_number = int(current or 0) + 1
        else:
            run_number = payload.run_number
        result = connection.execute(
            text("""INSERT INTO training_runs
                    (experiment_id, pipeline_version_id, dataset_version_id, environment_id, run_number, status, start_time)
                    VALUES (:experiment_id, :pipeline_version_id, :dataset_version_id, :environment_id, :run_number, :status, CURRENT_TIMESTAMP)
                    RETURNING training_run_id"""),
            {**payload.model_dump(exclude={"hyperparameters", "metrics"}), "run_number": run_number},
        )
        run_id = result.mappings().first()["training_run_id"]
        for name, value in payload.hyperparameters.items():
            connection.execute(
                text("""INSERT INTO hyperparameters (training_run_id, param_name, param_value)
                        VALUES (:run_id, :name, :value)"""),
                {"run_id": run_id, "name": str(name), "value": str(value)},
            )
        for name, value in payload.metrics.items():
            connection.execute(
                text("""INSERT INTO metrics (training_run_id, metric_name, metric_value)
                        VALUES (:run_id, :name, :value)"""),
                {"run_id": run_id, "name": str(name), "value": float(value)},
            )
        return {"training_run_id": run_id}


@app.post("/deployments", status_code=201)
def create_deployment(payload: DeploymentCreateRequest) -> dict[str, Any]:
    engine = app.state.engine
    with engine.begin() as connection:
        result = connection.execute(
            text("""INSERT INTO deployments (model_version_id, deployment_name, endpoint_uri, status)
                    VALUES (:model_version_id, :deployment_name, :endpoint_uri, :status)
                    RETURNING deployment_id"""),
            payload.model_dump(),
        )
        deployment_id = result.mappings().first()["deployment_id"]
        connection.execute(
            text("""INSERT INTO audit_logs (operation_type, entity_type, entity_id, description)
                    VALUES ('DEPLOYMENT_CREATED', 'deployment', :entity_id, :description)"""),
            {"entity_id": deployment_id, "description": f"Created deployment {payload.deployment_name}"},
        )
        return {"deployment_id": deployment_id}


@app.patch("/deployments/{deployment_id}/status")
def update_deployment_status(deployment_id: int, payload: DeploymentStatusRequest) -> dict[str, Any]:
    engine = app.state.engine
    with engine.begin() as connection:
        result = connection.execute(
            text("UPDATE deployments SET status = :status WHERE deployment_id = :deployment_id RETURNING deployment_id"),
            {"deployment_id": deployment_id, "status": payload.status},
        ).mappings().first()
        if not result:
            raise HTTPException(status_code=404, detail="Deployment not found")
        connection.execute(
            text("""INSERT INTO audit_logs (operation_type, entity_type, entity_id, description)
                    VALUES ('DEPLOYMENT_STATUS_CHANGED', 'deployment', :entity_id, :description)"""),
            {"entity_id": deployment_id, "description": f"Changed deployment status to {payload.status}"},
        )
        return dict(result)


@app.post("/reproducibility-checks", status_code=201)
def create_reproducibility_check(payload: ReproducibilityCheckRequest) -> dict[str, Any]:
    engine = app.state.engine
    with engine.begin() as connection:
        result = connection.execute(
            text("""INSERT INTO reproducibility_checks
                    (training_run_id, environment_id, is_reproducible, missing_components)
                    VALUES (:training_run_id, :environment_id, :is_reproducible, :missing_components)
                    RETURNING check_id"""),
            payload.model_dump(exclude={"reference_run_id"}),
        )
        check_id = result.mappings().first()["check_id"]
        connection.execute(
            text("""INSERT INTO audit_logs (operation_type, entity_type, entity_id, description)
                    VALUES ('REPRODUCIBILITY_CHECK_RECORDED', 'reproducibility_check', :entity_id, :description)"""),
            {"entity_id": check_id, "description": "Recorded reproducibility check"},
        )
        return {"check_id": check_id}
