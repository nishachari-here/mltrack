from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from modeltrace.api.main import app


def test_health_and_dataset_registration(tmp_path, monkeypatch):
    database_path = tmp_path / "modeltrace.db"
    url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    engine = create_engine(url)

    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE datasets (
                dataset_id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                data_type VARCHAR(100),
                created_at TIMESTAMP
            )
        """))
        connection.execute(text("""
            CREATE TABLE dataset_versions (
                dataset_version_id INTEGER PRIMARY KEY,
                dataset_id INTEGER,
                version_no VARCHAR(50) NOT NULL,
                hash VARCHAR(255) UNIQUE NOT NULL,
                statistics TEXT,
                storage_path TEXT NOT NULL,
                created_at TIMESTAMP
            )
        """))
        connection.execute(text("""
            CREATE TABLE projects (
                project_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                created_at TIMESTAMP
            )
        """))

    with TestClient(app) as client:
        root_response = client.get("/", follow_redirects=False)
        assert root_response.status_code == 307
        assert root_response.headers["location"] == "/docs"
        assert client.get("/health").status_code == 200
        assert client.get("/projects").json() == []
        response = client.post("/datasets/register", json={
            "name": "iris",
            "description": "Test dataset",
            "data_type": "csv",
            "version_no": "1",
            "hash": "abc123",
            "statistics": {"rows": 150},
            "storage_path": "iris.csv",
        })
        assert response.status_code == 201
        assert response.json()["dataset_version_id"] == 1
