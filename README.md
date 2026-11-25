# mltrack

ModelTrace is an ML experiment-tracking project. It includes a PostgreSQL schema, a Python package, a REST API for querying lineage and tracking deployments, and a command-line interface.

## Requirements

- Python 3.10 or newer
- PostgreSQL (local or hosted)

## Set up the Python environment

Run these commands from the repository root in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

For the optional MLflow/OpenML integrations and test tools, install the package extras:

```powershell
pip install -e ".[mlflow,openml,test]"
```

`requirements.txt` contains the pinned environment used by the existing ETL and training scripts. Install it when setting up that full environment:

```powershell
pip install -r requirements.txt
```

## Configure PostgreSQL

Create a PostgreSQL database and user, or obtain the connection details for a hosted PostgreSQL instance. For a local installation with `psql` available, you can create a database with:

```powershell
psql -U postgres -c "CREATE DATABASE mltrack;"
```

The initializer reads `DATABASE_URL` from a `.env` file in the repository root. Create that file if it does not exist, or add/update the variable if it already exists:

```dotenv
DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>:5432/<database>
```

For example, a local connection might use `localhost` as the host and `mltrack` as the database name. Replace all placeholders with your actual PostgreSQL credentials. For a hosted database that requires TLS, append `?sslmode=require` to the URL:

```dotenv
DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>:5432/<database>?sslmode=require
```

If the username or password contains URL-reserved characters (such as `@`, `:`, `/`, or `#`), percent-encode those characters in the connection URL. Keep `.env` private; do not commit database credentials.

## Initialize the database

With the virtual environment active and `DATABASE_URL` configured, initialize the schema using either the Python package or CLI:

```powershell
python -c "import modeltrace; modeltrace.init_db()"
modeltrace init
```

The existing initializer script is also available:

```powershell
python .\database\init_db.py
```

The initializer applies `database/schema.sql`, which uses repeatable table creation and adds run-environment and feature-set dataset-version relationships used by lineage queries.

If you initialized the database before those relationships were added, run `modeltrace init` again before inspecting runs so the schema migrations are applied.

## Run the API

With `DATABASE_URL` configured and the database initialized:

```powershell
modeltrace serve
```

The server listens on `http://127.0.0.1:8000` by default. Interactive API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Use `modeltrace serve --host 0.0.0.0 --port 8000` to configure the bind address and port.

Read endpoints:

- `GET /health`
- `GET /projects` and `GET /projects/{project_id}/experiments`
- `GET /datasets` and `GET /datasets/{dataset_id}/versions`
- `GET /runs` (optional `experiment_id`, `status`, and `dataset_version_id` filters) and `GET /runs/{run_id}`
- `GET /models` and `GET /models/{model_id}/versions`
- `GET /lineage/run/{run_id}` and `GET /lineage/model/{model_version_id}`

Lifecycle endpoints: `POST /datasets/register`, `POST /runs`, `POST /deployments`, `PATCH /deployments/{deployment_id}/status`, and `POST /reproducibility-checks`. Deployment and reproducibility writes create audit-log entries.

## CLI

- `modeltrace init` initializes the schema.
- `modeltrace status` checks database connectivity and prints table row counts.
- `modeltrace serve` starts the API.
- `modeltrace sync-mlflow --uri sqlite:///mlruns.db` runs the existing MLflow ETL importer.
- `modeltrace inspect-run <run_id>` prints the run's lineage.

## Inspect table row counts

To list PostgreSQL tables and their estimated live-row counts, run [etl/SELECT.pgsql](etl/SELECT.pgsql) with `psql` or open it in a PostgreSQL-aware editor:

```sql
SELECT
    schemaname,
    relname AS table_name,
    n_live_tup AS row_count
FROM
    pg_stat_user_tables
ORDER BY
    n_live_tup DESC;
```

The values in `n_live_tup` are estimates maintained by PostgreSQL statistics and may not match exact `COUNT(*)` results until the statistics are refreshed.

## ETL scripts

- `etl/ingest_openml.py` — Imports public datasets from OpenML.
- `etl/ingest_mlflow.py` — Copies runs, parameters, and metrics from a local MLflow SQLite database into PostgreSQL.
- `etl/ingest_lineage.py` — Adds sample pipeline, environment, model, deployment, reproducibility, and audit lineage records.

The database is hosted on Aiven, and `DATABASE_URL` points the scripts to that database. Do not rerun the ETL scripts if they have already been executed and the database contents are current; rerunning the current scripts may insert duplicate records.

Only run an ETL script again after initializing a new/empty database or intentionally adding new source data:

```powershell
& .\.venv\Scripts\python.exe .\etl\ingest_openml.py

# Create mlruns.db before syncing local MLflow metadata.
& .\.venv\Scripts\python.exe .\train_model.py
& .\.venv\Scripts\python.exe .\etl\ingest_mlflow.py

& .\.venv\Scripts\python.exe .\etl\ingest_lineage.py
```

## Project files

- `database/schema.sql` — PostgreSQL tables for users, projects, datasets, pipelines, experiments, training runs, models, deployments, and audit logs.
- `database/init_db.py` — Loads `DATABASE_URL` from `.env` and applies the schema.
- `src/modeltrace/api/` — FastAPI routes, Pydantic schemas, and relational queries.
- `src/modeltrace/cli.py` — `modeltrace` command-line entry point.
- `pyproject.toml` — Installable package metadata, dependencies, and console script.
- `etl/SELECT.pgsql` — Lists user tables ordered by estimated live-row count.
- `train_model.py` — Training entry point.
- `requirements.txt` — Python dependencies.
