import psycopg
from .config import DB_URL, DATA_DIR, SCHEMA_SQL
from .logging_config import get_logger
log = get_logger(__name__)
STAGE_DDL = """CREATE TEMP TABLE stage_trips (
  trip_key TEXT, pickup_datetime TIMESTAMP, dropoff_datetime TIMESTAMP,
  pickup_date_key INTEGER, pickup_hour INTEGER, vendor_key INTEGER,
  payment_key INTEGER, pickup_location_key INTEGER, dropoff_location_key INTEGER,
  passenger_count INTEGER, trip_distance DOUBLE PRECISION,
  fare_amount NUMERIC(12,2), total_amount NUMERIC(12,2)
) ON COMMIT DROP"""

def initialize_schema():
    with psycopg.connect(DB_URL) as conn:
        conn.execute(SCHEMA_SQL.read_text())
    log.info("Schema created or verified")

def load():
    csv_path = DATA_DIR / "processed" / "trips.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(csv_path)
    initialize_schema()
    with psycopg.connect(DB_URL) as conn:
        # All warehouse changes are one atomic transaction.
        with conn.cursor() as cur:
            cur.execute(STAGE_DDL)
            with cur.copy("COPY stage_trips FROM STDIN WITH (FORMAT CSV, NULL '\\N')") as copy:
                with csv_path.open("rb") as source:
                    while chunk := source.read(1024 * 1024):
                        copy.write(chunk)
            cur.execute("""INSERT INTO dim_date
                SELECT DISTINCT pickup_date_key, pickup_datetime::date,
                EXTRACT(YEAR FROM pickup_datetime)::int,
                EXTRACT(MONTH FROM pickup_datetime)::int,
                EXTRACT(DAY FROM pickup_datetime)::int,
                EXTRACT(ISODOW FROM pickup_datetime)::int
                FROM stage_trips ON CONFLICT DO NOTHING""")
            cur.execute("""INSERT INTO dim_payment
                SELECT DISTINCT payment_key, CASE payment_key
                WHEN 0 THEN 'Flex Fare' WHEN 1 THEN 'Credit card'
                WHEN 2 THEN 'Cash' WHEN 3 THEN 'No charge'
                WHEN 4 THEN 'Dispute' WHEN 5 THEN 'Unknown'
                WHEN 6 THEN 'Voided trip' ELSE 'Unknown/missing' END
                FROM stage_trips ON CONFLICT DO NOTHING""")
            cur.execute("""INSERT INTO dim_vendor
                SELECT DISTINCT vendor_key, CASE vendor_key
                WHEN 1 THEN 'Creative Mobile Technologies'
                WHEN 2 THEN 'VeriFone' ELSE 'Other/unknown' END
                FROM stage_trips ON CONFLICT DO NOTHING""")
            cur.execute("""INSERT INTO dim_location
                SELECT DISTINCT location_key, 'Not enriched' FROM (
                SELECT pickup_location_key AS location_key FROM stage_trips
                UNION SELECT dropoff_location_key FROM stage_trips
                ) x ON CONFLICT DO NOTHING""")
            cur.execute("""INSERT INTO fact_taxi_trips
                SELECT trip_key, pickup_datetime, dropoff_datetime, pickup_date_key,
                pickup_hour, vendor_key, payment_key, pickup_location_key,
                dropoff_location_key, passenger_count, trip_distance,
                fare_amount, total_amount
                FROM stage_trips ON CONFLICT (trip_key) DO NOTHING""")
            inserted = cur.rowcount
            cur.execute("INSERT INTO etl_audit(stage,status,row_count) VALUES ('load','success',%s)", (inserted,))
    log.info(f"Warehouse commit complete; new fact rows={inserted}")
    return inserted

def quality_checks():
    with psycopg.connect(DB_URL) as conn:
        total = conn.execute("SELECT count(*) FROM fact_taxi_trips").fetchone()[0]
        orphans = conn.execute("""SELECT count(*) FROM fact_taxi_trips f
            LEFT JOIN dim_date d ON f.pickup_date_key=d.date_key
            LEFT JOIN dim_payment p ON f.payment_key=p.payment_key
            WHERE d.date_key IS NULL OR p.payment_key IS NULL""").fetchone()[0]
        if total == 0 or orphans:
            raise AssertionError(f"Data quality failed: rows={total}, orphans={orphans}")
        log.info(f"Data quality passed: rows={total}, orphans={orphans}")
        return total
