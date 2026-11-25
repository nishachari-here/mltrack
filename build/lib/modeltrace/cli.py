from __future__ import annotations

import argparse
import sys
from typing import Sequence

from sqlalchemy import text


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="modeltrace")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init", help="Initialize database tables")
    subparsers.add_parser("status", help="Check database connectivity and table row counts")

    serve = subparsers.add_parser("serve", help="Start the FastAPI server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")

    mlflow = subparsers.add_parser("sync-mlflow", help="Import MLflow metadata")
    mlflow.add_argument("--uri", default="sqlite:///mlruns.db")

    inspect_run = subparsers.add_parser("inspect-run", help="Print a run lineage tree")
    inspect_run.add_argument("run_id", type=int)

    args = parser.parse_args(argv)

    if args.command == "init":
        from .db import init_db
        init_db()
        print("Database initialized.")
        return 0

    if args.command == "status":
        from .db import get_engine
        engine = get_engine()
        table_names = [
            "users", "projects", "datasets", "dataset_versions", "feature_sets",
            "environments", "pipelines", "pipeline_versions", "experiments",
            "training_runs", "hyperparameters", "metrics", "models",
            "model_versions", "deployments", "reproducibility_checks", "audit_logs",
        ]
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            print("Database: connected")
            for table in table_names:
                count = connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"{table}: {count}")
        return 0

    if args.command == "serve":
        import uvicorn
        uvicorn.run("modeltrace.api.main:app", host=args.host, port=args.port, reload=args.reload)
        return 0

    if args.command == "sync-mlflow":
        try:
            from etl.ingest_mlflow import sync_mlflow_database
        except ImportError as exc:
            print(f"MLflow sync is not available: {exc}", file=sys.stderr)
            return 1
        sync_mlflow_database(args.uri)
        return 0

    if args.command == "inspect-run":
        from .db import get_engine
        from .api.queries import QueryEngine
        lineage = QueryEngine(get_engine()).lineage_run(args.run_id)
        if not lineage:
            print(f"Run {args.run_id} not found", file=sys.stderr)
            return 1
        print(f"User: {lineage['user']}")
        print(f"Project: {lineage['project']}")
        print(f"Dataset: {lineage['dataset']}")
        print(f"Feature sets: {lineage['feature_sets']}")
        print(f"Pipeline: {lineage['pipeline']}")
        print(f"Environment: {lineage['environment']}")
        print(f"Experiment: {lineage['experiment']}")
        print(f"Run: {lineage['run']}")
        print(f"Hyperparameters: {lineage['hyperparameters']}")
        print(f"Metrics: {lineage['metrics']}")
        print(f"Model versions: {lineage['model_versions']}")
        print(f"Deployments: {lineage['deployments']}")
        print(f"Reproducibility checks: {lineage['reproducibility_checks']}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
