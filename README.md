# mltrack

mltrack is an ML experiment-tracking project. The current repository includes a PostgreSQL schema and a Python script that creates its tables.

## Requirements

- Python 3.10 or newer
- PostgreSQL (local or hosted)

## Set up the Python environment

Run these commands from the repository root in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell prevents virtual environment activation, either adjust the execution policy for your user or run the environment's Python directly as `.\.venv\Scripts\python.exe`.

## Configure PostgreSQL

Create a PostgreSQL database and user, or obtain the connection details for a hosted PostgreSQL instance. For a local installation with `psql` available, you can create a database with:

```powershell
psql -U postgres -c "CREATE DATABASE mltrack;"
```

The initializer reads `DATABASE_URL` from a `.env` file in the repository root. Create that file if it does not exist, or add/update the variable if it already exists:

```dotenv
DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>:5432/<database>
```

For example, a local connection might use `localhost` as the host and `mltrack` as the database name. Replace all placeholders with your actual PostgreSQL credentials. For a hosted database that requires TLS, append `?sslmode=require` to the URL:

```dotenv
DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>:5432/<database>?sslmode=require
```

If the username or password contains URL-reserved characters (such as `@`, `:`, `/`, or `#`), percent-encode those characters in the connection URL. Keep `.env` private; do not commit database credentials.

## Initialize the database

With the virtual environment active and `DATABASE_URL` configured, run this once against a new, empty database:

```powershell
python .\database\init_db.py
```

The script loads `database/schema.sql` and creates the project tables. The schema uses plain `CREATE TABLE` statements, so the initializer is not repeatable against a database where these tables already exist.

## Project files

- `database/schema.sql` — PostgreSQL tables for users, projects, datasets, pipelines, experiments, training runs, models, deployments, and audit logs.
- `database/init_db.py` — Loads `DATABASE_URL` from `.env` and applies the schema.
- `requirements.txt` — Python dependencies.

The current repository does not include a configured application-server startup command.
