from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Project(BaseModel):
    project_id: int
    user_id: int | None = None
    name: str
    description: str | None = None
    created_at: datetime | None = None


class Experiment(BaseModel):
    experiment_id: int
    project_id: int | None = None
    name: str
    description: str | None = None
    created_at: datetime | None = None


class Dataset(BaseModel):
    dataset_id: int
    name: str
    description: str | None = None
    data_type: str | None = None
    created_at: datetime | None = None


class DatasetVersion(BaseModel):
    dataset_version_id: int
    dataset_id: int | None = None
    version_no: str
    hash: str
    statistics: dict[str, Any] | None = None
    storage_path: str
    created_at: datetime | None = None


class TrainingRun(BaseModel):
    training_run_id: int
    experiment_id: int | None = None
    pipeline_version_id: int | None = None
    dataset_version_id: int | None = None
    environment_id: int | None = None
    run_number: int
    start_time: datetime | None = None
    end_time: datetime | None = None
    status: str | None = None
    created_at: datetime | None = None


class TrainingRunDetail(TrainingRun):
    hyperparameters: list[dict[str, Any]] = Field(default_factory=list)
    metrics: list[dict[str, Any]] = Field(default_factory=list)


class Model(BaseModel):
    model_id: int
    name: str
    model_type: str | None = None
    description: str | None = None
    created_at: datetime | None = None


class ModelVersion(BaseModel):
    model_version_id: int
    model_id: int | None = None
    training_run_id: int | None = None
    version_no: str
    artifact_path: str
    created_at: datetime | None = None


class DatasetRegisterRequest(BaseModel):
    name: str
    description: str | None = None
    data_type: str | None = None
    version_no: str = "1"
    hash: str
    statistics: dict[str, Any] | None = None
    storage_path: str


class RunCreateRequest(BaseModel):
    experiment_id: int
    pipeline_version_id: int | None = None
    dataset_version_id: int | None = None
    environment_id: int | None = None
    run_number: int | None = None
    status: str = "RUNNING"
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)


class DeploymentCreateRequest(BaseModel):
    model_version_id: int
    deployment_name: str
    endpoint_uri: str | None = None
    status: str = "ACTIVE"


class DeploymentStatusRequest(BaseModel):
    status: str


class ReproducibilityCheckRequest(BaseModel):
    training_run_id: int
    environment_id: int | None = None
    reference_run_id: int | None = None
    is_reproducible: bool
    missing_components: str | None = None
