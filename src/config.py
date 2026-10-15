import os
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("TAXI_DATA_DIR", BASE / "data"))
DB_URL = os.getenv("TAXI_DATABASE_URL", "postgresql://taxi_user:mayu1996@localhost:5433/taxi_data")
SCHEMA_SQL = Path(os.getenv("TAXI_SQL_FILE", BASE / "sql/schema.sql"))
MONTHS = ("2023-01", "2023-02")
BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
