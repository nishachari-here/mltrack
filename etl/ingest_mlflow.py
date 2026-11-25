import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def sync_mlflow_database(mlflow_sqlite_path="sqlite:///mlruns.db"):
    """Reads local MLflow SQLite metadata and syncs runs, params, and metrics to ModelTrace."""
    print("Connecting to local MLflow database and cloud target...")
    mlflow_engine = create_engine(mlflow_sqlite_path)
    cloud_engine = create_engine(DATABASE_URL)
    
    # 1. Read runs from MLflow
    try:
        with mlflow_engine.connect() as mlflow_conn:
            runs_query = text("SELECT run_uuid, experiment_id, name, status, start_time, end_time FROM runs;")
            mlflow_runs = mlflow_conn.execute(runs_query).fetchall()
    except Exception as e:
        print(f"Could not read local MLflow database ({e}). Ensure mlruns.db exists by running training scripts first.")
        return

    with cloud_engine.begin() as cloud_conn:
        

       # 2. Ensure a valid project exists to satisfy foreign key constraints
        proj_result = cloud_conn.execute(
            text("SELECT project_id FROM projects LIMIT 1;")
        ).fetchone()

        if proj_result:
            project_id = proj_result[0]
        else:
            print("No project found. Setting up default project...")
            
            # Check if any user already exists
            user_result = cloud_conn.execute(
                text("SELECT user_id FROM users LIMIT 1;")
            ).fetchone()

            if user_result:
                user_id = user_result[0]
            else:
                # Insert user providing all required NOT NULL fields
                user_result = cloud_conn.execute(
                    text("""
                        INSERT INTO users (email, name, role)
                        VALUES ('admin@modeltrace.internal', 'Admin User', 'Lead MLOps Engineer')
                        RETURNING user_id;
                    """)
                )
                user_id = user_result.fetchone()[0]

            proj_result = cloud_conn.execute(
                text("""
                    INSERT INTO projects (name, description, user_id)
                    VALUES ('Default MLOps Project', 'Auto-created project for MLflow sync', :uid)
                    RETURNING project_id;
                """),
                {"uid": user_id}
            )
            project_id = proj_result.fetchone()[0]
            print(f"Created default project ID: {project_id}")

        # 3. Create tracking experiment wrapper in ModelTrace
        exp_result = cloud_conn.execute(
            text("""
                INSERT INTO experiments (project_id, name, description)
                VALUES (:pid, :name, :desc)
                RETURNING experiment_id;
            """),
            {
                "pid": project_id,
                "name": "MLflow Migrated Experiments",
                "desc": "Baseline experiments synced from local MLflow SQLite store"
            }
        )
        experiment_id = exp_result.fetchone()[0]

        for run in mlflow_runs:
            run_uuid, mlf_exp_id, run_name, status, start_time, end_time = run
            run_name = run_name or f"Run-{run_uuid[:8]}"
            
            print(f"Syncing MLflow run: {run_name} ({status})")
            
            # Insert training run
            run_result = cloud_conn.execute(
                text("""
                    INSERT INTO training_runs (experiment_id, run_number, start_time, end_time, status)
                    VALUES (:eid, :rnum, TO_TIMESTAMP(:stime / 1000.0), TO_TIMESTAMP(:etime / 1000.0), :status)
                    RETURNING training_run_id;
                """),
                {
                    "eid": experiment_id,
                    "rnum": abs(hash(run_uuid)) % 10000,
                    "stime": start_time or 0,
                    "etime": end_time or 0,
                    "status": "COMPLETED" if status == "FINISHED" else "FAILED"
                }
            )
            training_run_id = run_result.fetchone()[0]
            
            # Fetch and sync parameters for this run
            with mlflow_engine.connect() as mlflow_conn:
                params = mlflow_conn.execute(
                    text("SELECT key, value FROM params WHERE run_uuid = :uuid;"),
                    {"uuid": run_uuid}
                ).fetchall()
                
                for param_name, param_value in params:
                    cloud_conn.execute(
                        text("""
                            INSERT INTO hyperparameters (training_run_id, param_name, param_value)
                            VALUES (:tr_id, :pname, :pval);
                        """),
                        {"tr_id": training_run_id, "pname": param_name, "pval": param_value}
                    )
                
                # Fetch and sync metrics for this run
                metrics = mlflow_conn.execute(
                    text("SELECT key, value FROM metrics WHERE run_uuid = :uuid;"),
                    {"uuid": run_uuid}
                ).fetchall()
                
                for metric_name, metric_value in metrics:
                    cloud_conn.execute(
                        text("""
                            INSERT INTO metrics (training_run_id, metric_name, metric_value)
                            VALUES (:tr_id, :mname, :mval);
                        """),
                        {"tr_id": training_run_id, "mname": metric_name, "mval": float(metric_value)}
                    )

    print("MLflow historical metadata successfully synchronized to the Aiven cloud database!")

if __name__ == "__main__":
    sync_mlflow_database()