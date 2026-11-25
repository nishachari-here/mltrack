import os
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def fill_all_remaining_tables():
    print("Connecting to Aiven cloud database...")
    engine = create_engine(DATABASE_URL)
    
    with engine.begin() as connection:
        print("1. Ensuring base user and project exist...")
        # Check or insert a system user
        user_res = connection.execute(
            text("SELECT user_id FROM users LIMIT 1;")
        ).fetchone()
        
        if user_res:
            user_id = user_res[0]
        else:
            user_res = connection.execute(
                text("""
                    INSERT INTO users (email, name, role)
                    VALUES ('admin@modeltrace.internal', 'MLOps System Admin', 'Lead Engineer')
                    RETURNING user_id;
                """)
            )
            user_id = user_res.fetchone()[0]

        # Check or insert a project
        proj_res = connection.execute(
            text("SELECT project_id FROM projects LIMIT 1;")
        ).fetchone()
        
        if proj_res:
            project_id = proj_res[0]
        else:
            proj_res = connection.execute(
                text("""
                    INSERT INTO projects (name, description, user_id)
                    VALUES ('ModelTrace Production Pipeline', 'End-to-end MLOps tracking and lineage engine', :uid)
                    RETURNING project_id;
                """),
                {"uid": user_id}
            )
            project_id = proj_res.fetchone()[0]

        print(f"Using Project ID: {project_id}, User ID: {user_id}")

        print("2. Populating environments...")
        env_res = connection.execute(
            text("""
                INSERT INTO environments (python_version, os, hardware, libraries)
                VALUES ('3.10.12', 'Linux', 'CUDA 12.1', :libraries)
                RETURNING environment_id;
            """),
            {"libraries": json.dumps({"torch": "2.1.0", "scikit-learn": "1.3.0", "pandas": "2.0.3", "mlflow": "2.8.0"})}
        )
        environment_id = env_res.fetchone()[0]

        print("3. Populating pipelines and pipeline versions...")
        pipe_res = connection.execute(
            text("""
                INSERT INTO pipelines (project_id, name, description)
                VALUES (:pid, 'Classifier Training & Evaluation Pipeline', 'End-to-end classifier training and evaluation pipeline')
                RETURNING pipeline_id;
            """),
            {"pid": project_id}
        )
        pipeline_id = pipe_res.fetchone()[0]

        pipe_ver_res = connection.execute(
            text("""
                INSERT INTO pipeline_versions (pipeline_id, version_no, description, code_path, hash)
                VALUES (:pipe_id, '1.0.0', 'Initial training pipeline version', 'train_pytorch.py', 'a1b2c3d4e5f67890')
                RETURNING pipeline_version_id;
            """),
            {"pipe_id": pipeline_id}
        )
        pipeline_version_id = pipe_ver_res.fetchone()[0]

        print("4. Populating feature sets...")
        connection.execute(
            text("""
                INSERT INTO feature_sets (name, description)
                VALUES ('Standardized Telemetry Features', :description);
            """),
            {"description": "Standardized features: feature_1, feature_2, target_label, normalized_timestamp"}
        )

        print("5. Populating models and model versions...")
        model_res = connection.execute(
            text("""
                INSERT INTO models (name, model_type, description)
                VALUES ('BreastCancerClassifier', 'Ensemble classifier', 'Ensemble Random Forest and Neural Network binary classifier')
                RETURNING model_id;
            """)
        )
        model_id = model_res.fetchone()[0]

        run_res = connection.execute(
            text("SELECT training_run_id FROM training_runs LIMIT 1;")
        ).fetchone()
        training_run_id = run_res[0] if run_res else None

        model_ver_res = connection.execute(
            text("""
                INSERT INTO model_versions (model_id, training_run_id, version_no, artifact_path)
                VALUES (:mid, :run_id, '1.0.0', 'mlruns/models/pytorch_mlp_model')
                RETURNING model_version_id;
            """),
            {"mid": model_id, "run_id": training_run_id}
        )
        model_version_id = model_ver_res.fetchone()[0]

        print("6. Populating deployments...")
        connection.execute(
            text("""
                INSERT INTO deployments (model_version_id, deployment_name, endpoint_uri, status)
                VALUES (:mvid, 'Production Kubernetes Cluster', 'https://api.modeltrace.internal/v1/predict', 'ACTIVE');
            """),
            {"mvid": model_version_id}
        )

        print("7. Populating reproducibility checks...")
        if training_run_id:
            connection.execute(
                text("""
                    INSERT INTO reproducibility_checks (training_run_id, environment_id, is_reproducible, missing_components)
                    VALUES (:tr_id, :env_id, TRUE, 'Deterministic execution verified across container environments.');
                """),
                    {"tr_id": training_run_id, "env_id": environment_id}
            )

        print("8. Populating audit logs...")
        connection.execute(
            text("""
                INSERT INTO audit_logs (user_id, operation_type, entity_type, entity_id, description)
                VALUES (:uid, 'BATCH_INGESTION_COMPLETED', 'model_version', :entity_id, :details);
            """),
            {
                "uid": user_id,
                "entity_id": model_version_id,
                "details": json.dumps({"status": "SUCCESS", "tables_updated": "all_lineage_tables", "source": "Aiven Cloud Sync"})
            }
        )

    print("All remaining ModelTrace database tables successfully populated!")

if __name__ == "__main__":
    fill_all_remaining_tables()