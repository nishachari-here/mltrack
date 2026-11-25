from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine


def rows(connection, statement: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    result = connection.execute(text(statement), params or {})
    return [dict(row._mapping) for row in result]


def one(connection, statement: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    result = connection.execute(text(statement), params or {})
    row = result.mappings().first()
    return dict(row) if row else None


class QueryEngine:
    def __init__(self, engine: Engine):
        self.engine = engine

    def projects(self) -> list[dict[str, Any]]:
        with self.engine.connect() as c:
            return rows(c, "SELECT * FROM projects ORDER BY project_id")

    def experiments(self, project_id: int) -> list[dict[str, Any]]:
        with self.engine.connect() as c:
            return rows(c, "SELECT * FROM experiments WHERE project_id = :project_id ORDER BY experiment_id",
                        {"project_id": project_id})

    def datasets(self) -> list[dict[str, Any]]:
        with self.engine.connect() as c:
            return rows(c, "SELECT * FROM datasets ORDER BY dataset_id")

    def dataset_versions(self, dataset_id: int) -> list[dict[str, Any]]:
        with self.engine.connect() as c:
            return rows(c, "SELECT * FROM dataset_versions WHERE dataset_id = :dataset_id ORDER BY dataset_version_id",
                        {"dataset_id": dataset_id})

    def runs(self, experiment_id: int | None = None, status: str | None = None,
             dataset_version_id: int | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: dict[str, Any] = {}
        if experiment_id is not None:
            clauses.append("experiment_id = :experiment_id")
            params["experiment_id"] = experiment_id
        if status is not None:
            clauses.append("status = :status")
            params["status"] = status
        if dataset_version_id is not None:
            clauses.append("dataset_version_id = :dataset_version_id")
            params["dataset_version_id"] = dataset_version_id
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.engine.connect() as c:
            return rows(c, f"SELECT * FROM training_runs{where} ORDER BY training_run_id", params)

    def run_detail(self, run_id: int) -> dict[str, Any] | None:
        with self.engine.connect() as c:
            run = one(c, "SELECT * FROM training_runs WHERE training_run_id = :run_id", {"run_id": run_id})
            if not run:
                return None
            run["hyperparameters"] = rows(c,
                "SELECT hyperparameter_id, training_run_id, param_name, param_value, created_at "
                "FROM hyperparameters WHERE training_run_id = :run_id ORDER BY hyperparameter_id",
                {"run_id": run_id})
            run["metrics"] = rows(c,
                "SELECT metric_id, training_run_id, metric_name, metric_value, created_at "
                "FROM metrics WHERE training_run_id = :run_id ORDER BY metric_id",
                {"run_id": run_id})
            return run

    def models(self) -> list[dict[str, Any]]:
        with self.engine.connect() as c:
            return rows(c, "SELECT * FROM models ORDER BY model_id")

    def model_versions(self, model_id: int) -> list[dict[str, Any]]:
        with self.engine.connect() as c:
            return rows(c, "SELECT * FROM model_versions WHERE model_id = :model_id ORDER BY model_version_id",
                        {"model_id": model_id})

    def lineage_run(self, run_id: int) -> dict[str, Any] | None:
        with self.engine.connect() as c:
            run = one(c, """
                SELECT tr.*,
                       e.experiment_id AS lineage_experiment_id, e.name AS experiment_name, e.description AS experiment_description,
                       p.project_id AS lineage_project_id, p.name AS project_name,
                       u.user_id AS lineage_user_id, u.name AS user_name, u.email AS user_email,
                       dv.dataset_version_id AS lineage_dataset_version_id, dv.version_no AS dataset_version,
                       dv.hash AS dataset_hash, dv.statistics AS dataset_statistics, dv.storage_path AS dataset_storage_path,
                       d.dataset_id AS lineage_dataset_id, d.name AS dataset_name, d.description AS dataset_description,
                       pv.pipeline_version_id AS lineage_pipeline_version_id, pv.version_no AS pipeline_version,
                       pv.hash AS pipeline_hash, pv.code_path AS code_path,
                       pipe.pipeline_id AS lineage_pipeline_id, pipe.name AS pipeline_name,
                       env.environment_id AS lineage_environment_id, env.python_version, env.os, env.hardware, env.libraries
                FROM training_runs tr
                LEFT JOIN experiments e ON e.experiment_id = tr.experiment_id
                LEFT JOIN projects p ON p.project_id = e.project_id
                LEFT JOIN users u ON u.user_id = p.user_id
                LEFT JOIN dataset_versions dv ON dv.dataset_version_id = tr.dataset_version_id
                LEFT JOIN datasets d ON d.dataset_id = dv.dataset_id
                LEFT JOIN pipeline_versions pv ON pv.pipeline_version_id = tr.pipeline_version_id
                LEFT JOIN pipelines pipe ON pipe.pipeline_id = pv.pipeline_id
                LEFT JOIN environments env ON env.environment_id = tr.environment_id
                WHERE tr.training_run_id = :run_id
            """, {"run_id": run_id})
            if not run:
                return None
            params = rows(c, "SELECT * FROM hyperparameters WHERE training_run_id = :run_id", {"run_id": run_id})
            metrics = rows(c, "SELECT * FROM metrics WHERE training_run_id = :run_id", {"run_id": run_id})
            feature_sets = rows(c, """
                SELECT fs.* FROM feature_sets fs
                LEFT JOIN dataset_versions dv ON dv.dataset_version_id = fs.dataset_version_id
                WHERE fs.dataset_version_id = :dataset_version_id
            """, {"dataset_version_id": run["dataset_version_id"]}) if run["dataset_version_id"] else []
            model_versions = rows(c, "SELECT * FROM model_versions WHERE training_run_id = :run_id", {"run_id": run_id})
            deployments: list[dict[str, Any]] = []
            for mv in model_versions:
                deployments.extend(rows(c, "SELECT * FROM deployments WHERE model_version_id = :mvid",
                                        {"mvid": mv["model_version_id"]}))
            checks = rows(c, "SELECT * FROM reproducibility_checks WHERE training_run_id = :run_id", {"run_id": run_id})
            return {
                "run": run,
                "user": {"user_id": run.pop("lineage_user_id", None), "name": run.pop("user_name", None), "email": run.pop("user_email", None)},
                "project": {"project_id": run.pop("lineage_project_id", None), "name": run.pop("project_name", None)},
                "dataset": {"dataset_id": run.pop("lineage_dataset_id", None), "name": run.pop("dataset_name", None),
                            "description": run.pop("dataset_description", None),
                            "version": {"dataset_version_id": run.pop("lineage_dataset_version_id", None),
                                        "version_no": run.pop("dataset_version", None), "hash": run.pop("dataset_hash", None),
                                        "statistics": run.pop("dataset_statistics", None), "storage_path": run.pop("dataset_storage_path", None)}},
                "feature_sets": feature_sets,
                "pipeline": {"pipeline_id": run.pop("lineage_pipeline_id", None), "name": run.pop("pipeline_name", None),
                             "version": {"pipeline_version_id": run.pop("lineage_pipeline_version_id", None),
                                         "version_no": run.pop("pipeline_version", None), "hash": run.pop("pipeline_hash", None),
                                         "code_path": run.pop("code_path", None)}},
                "environment": {"environment_id": run.pop("lineage_environment_id", None),
                                "python_version": run.pop("python_version", None), "os": run.pop("os", None),
                                "hardware": run.pop("hardware", None), "libraries": run.pop("libraries", None)},
                "experiment": {"experiment_id": run.pop("lineage_experiment_id", None),
                               "name": run.pop("experiment_name", None), "description": run.pop("experiment_description", None)},
                "hyperparameters": params,
                "metrics": metrics,
                "model_versions": model_versions,
                "deployments": deployments,
                "reproducibility_checks": checks,
            }

    def lineage_model(self, model_version_id: int) -> dict[str, Any] | None:
        with self.engine.connect() as c:
            mv = one(c, """
                SELECT mv.*, m.name AS model_name, m.model_type, m.description AS model_description,
                       tr.*,
                       dv.hash AS dataset_hash, dv.statistics AS dataset_statistics, dv.version_no AS dataset_version,
                       d.name AS dataset_name,
                       pv.hash AS pipeline_hash, pv.version_no AS pipeline_version, pv.code_path,
                       env.python_version, env.os, env.hardware, env.libraries
                FROM model_versions mv
                LEFT JOIN models m ON m.model_id = mv.model_id
                LEFT JOIN training_runs tr ON tr.training_run_id = mv.training_run_id
                LEFT JOIN dataset_versions dv ON dv.dataset_version_id = tr.dataset_version_id
                LEFT JOIN datasets d ON d.dataset_id = dv.dataset_id
                LEFT JOIN pipeline_versions pv ON pv.pipeline_version_id = tr.pipeline_version_id
                LEFT JOIN environments env ON env.environment_id = tr.environment_id
                WHERE mv.model_version_id = :model_version_id
            """, {"model_version_id": model_version_id})
            if not mv:
                return None
            deployments = rows(c, "SELECT * FROM deployments WHERE model_version_id = :model_version_id",
                               {"model_version_id": model_version_id})
            checks = rows(c, "SELECT * FROM reproducibility_checks WHERE training_run_id = :run_id",
                          {"run_id": mv.get("training_run_id")})
            return {"model_version": mv, "deployments": deployments, "reproducibility_checks": checks}
