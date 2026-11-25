import os
import json
import openml
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def ingest_openml_datasets(limit=5):
    """Fetches public datasets using the official OpenML client and registers them into ModelTrace."""
    print("Connecting to Aiven cloud database...")
    engine = create_engine(DATABASE_URL)
    
    print(f"Fetching datasets using OpenML client (limit={limit})...")
    # Fetch active datasets as a pandas DataFrame using the official library
    datasets_df = openml.datasets.list_datasets(output_format="dataframe", size=limit)
    
    with engine.begin() as connection:
        for _, ds in datasets_df.iterrows():
            dataset_id_ext = int(ds.get("did"))
            name = str(ds.get("name"))
            version = str(ds.get("version", "1"))
            format_type = str(ds.get("format", "arff"))
            
            print(f"Processing OpenML Dataset: {name} (ID: {dataset_id_ext})")
            
            # Insert parent dataset record
            ds_result = connection.execute(
                text("""
                    INSERT INTO datasets (name, description, data_type)
                    VALUES (:name, :desc, :dtype)
                    RETURNING dataset_id;
                """),
                {
                    "name": name,
                    "desc": f"Imported via OpenML client (DID: {dataset_id_ext}, Status: {ds.get('status')})",
                    "dtype": format_type
                }
            )
            dataset_id = ds_result.fetchone()[0]
            
            # Construct statistics payload from OpenML metadata
            stats = {
                "number_of_instances": ds.get("NumberOfInstances"),
                "number_of_features": ds.get("NumberOfFeatures"),
                "number_of_classes": ds.get("NumberOfClasses"),
                "openml_did": dataset_id_ext
            }
            
            # Insert version record
            connection.execute(
                text("""
                    INSERT INTO dataset_versions (dataset_id, version_no, hash, statistics, storage_path)
                    VALUES (:did, :vno, :hash, :stats, :path);
                """),
                {
                    "did": dataset_id,
                    "vno": version,
                    "hash": f"openml_sha256_mock_{dataset_id_ext}",
                    "stats": json.dumps(stats),
                    "path": f"https://www.openml.org/d/{dataset_id_ext}"
                }
            )
            
    print("OpenML datasets successfully ingested into ModelTrace!")

if __name__ == "__main__":
    ingest_openml_datasets(limit=5)