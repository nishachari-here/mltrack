-- ModelTrace Database Schema
-- Based on MLOps Experiment Tracking ER Diagram[cite: 1]

-- Enable UUID extension if needed, or use SERIAL primary keys
-- Using SERIAL for clean relational incrementing keys

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(100),
    affiliation VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE projects (
    project_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE datasets (
    dataset_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    data_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dataset_versions (
    dataset_version_id SERIAL PRIMARY KEY,
    dataset_id INT REFERENCES datasets(dataset_id) ON DELETE CASCADE,
    version_no VARCHAR(50) NOT NULL,
    hash VARCHAR(255) UNIQUE NOT NULL,
    statistics JSONB,
    storage_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pipelines (
    pipeline_id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(project_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pipeline_versions (
    pipeline_version_id SERIAL PRIMARY KEY,
    pipeline_id INT REFERENCES pipelines(pipeline_id) ON DELETE CASCADE,
    version_no VARCHAR(50) NOT NULL,
    description TEXT,
    code_path TEXT NOT NULL,
    hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE experiments (
    experiment_id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(project_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE feature_sets (
    feature_set_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE environments (
    environment_id SERIAL PRIMARY KEY,
    python_version VARCHAR(50),
    os VARCHAR(100),
    hardware VARCHAR(255),
    libraries JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE training_runs (
    training_run_id SERIAL PRIMARY KEY,
    experiment_id INT REFERENCES experiments(experiment_id) ON DELETE CASCADE,
    pipeline_version_id INT REFERENCES pipeline_versions(pipeline_version_id) ON DELETE SET NULL,
    dataset_version_id INT REFERENCES dataset_versions(dataset_version_id) ON DELETE SET NULL,
    run_number INT NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(50) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE hyperparameters (
    hyperparameter_id SERIAL PRIMARY KEY,
    training_run_id INT REFERENCES training_runs(training_run_id) ON DELETE CASCADE,
    param_name VARCHAR(255) NOT NULL,
    param_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE metrics (
    metric_id SERIAL PRIMARY KEY,
    training_run_id INT REFERENCES training_runs(training_run_id) ON DELETE CASCADE,
    metric_name VARCHAR(255) NOT NULL,
    metric_value FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE models (
    model_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    model_type VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE model_versions (
    model_version_id SERIAL PRIMARY KEY,
    model_id INT REFERENCES models(model_id) ON DELETE CASCADE,
    training_run_id INT REFERENCES training_runs(training_run_id) ON DELETE SET NULL,
    version_no VARCHAR(50) NOT NULL,
    artifact_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE deployments (
    deployment_id SERIAL PRIMARY KEY,
    model_version_id INT REFERENCES model_versions(model_version_id) ON DELETE CASCADE,
    deployment_name VARCHAR(255) NOT NULL,
    endpoint_uri TEXT,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reproducibility_checks (
    check_id SERIAL PRIMARY KEY,
    training_run_id INT REFERENCES training_runs(training_run_id) ON DELETE CASCADE,
    environment_id INT REFERENCES environments(environment_id) ON DELETE SET NULL,
    is_reproducible BOOLEAN DEFAULT FALSE,
    missing_components TEXT,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audit_logs (
    log_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE SET NULL,
    operation_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id INT NOT NULL,
    description TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);