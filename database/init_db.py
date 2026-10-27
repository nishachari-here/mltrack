import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Automatically fix legacy postgres:// prefixes for SQLAlchemy compatibility
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def initialize_database():
    print("Connecting to Aiven cloud database...")
    engine = create_engine(DATABASE_URL)
    
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r") as f:
        sql_script = f.read()
        
    print("Executing schema script...")
    with engine.connect() as connection:
        connection.exec_driver_sql(sql_script)
        connection.commit()
        
    print("Database tables successfully created on Aiven!")

if __name__ == "__main__":
    initialize_database()