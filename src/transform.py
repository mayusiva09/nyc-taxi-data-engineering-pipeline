from pathlib import Path
import duckdb
from .config import DATA_DIR, MONTHS
from .logging_config import get_logger
log = get_logger(__name__)

REQUIRED = {"tpep_pickup_datetime", "tpep_dropoff_datetime", "VendorID", "payment_type", "PULocationID", "DOLocationID", "trip_distance", "fare_amount", "total_amount"}


def transform():
    raw = [DATA_DIR / "raw" / f"yellow_tripdata_{m}.parquet" for m in MONTHS]
    for path in raw:
        if not path.exists():
            raise FileNotFoundError(path)
    processed = DATA_DIR / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    output = processed / "trips.csv"
    db = duckdb.connect()
    # Filename values originate from the hardcoded MONTHS list, not untrusted input.
    glob = str(DATA_DIR / "raw" / "yellow_tripdata_2023-*.parquet")
    cols = {r[0] for r in db.execute("DESCRIBE SELECT * FROM read_parquet(?)", [str(raw[0])]).fetchall()}
    missing = REQUIRED - cols
    if missing:
        raise ValueError(f"Missing source columns: {sorted(missing)}")
    for filename in raw:
        db.execute("SELECT count(*) FROM read_parquet(?)", [str(filename)]).fetchone()
    # Source has no guaranteed trip ID. Identical value rows are treated as duplicates.
    # This deliberate heuristic can collapse distinct trips with identical attributes.
    query = f"""
    WITH source AS (
      SELECT
        try_cast(tpep_pickup_datetime AS TIMESTAMP) AS pickup_datetime,
        try_cast(tpep_dropoff_datetime AS TIMESTAMP) AS dropoff_datetime,
        coalesce(try_cast(VendorID AS INTEGER),-1) AS vendor_key,
        coalesce(try_cast(payment_type AS INTEGER),-1) AS payment_key,
        coalesce(try_cast(PULocationID AS INTEGER),-1) AS pickup_location_key,
        coalesce(try_cast(DOLocationID AS INTEGER),-1) AS dropoff_location_key,
        try_cast(passenger_count AS INTEGER) AS passenger_count,
        try_cast(trip_distance AS DOUBLE) AS trip_distance,
        try_cast(fare_amount AS DECIMAL(12,2)) AS fare_amount,
        try_cast(total_amount AS DECIMAL(12,2)) AS total_amount
      FROM read_parquet('{glob}')
    ), filtered AS (
      SELECT * FROM source WHERE pickup_datetime >= TIMESTAMP '2023-01-01'
        AND pickup_datetime < TIMESTAMP '2023-03-01'
        AND dropoff_datetime >= pickup_datetime
        AND trip_distance > 0
        AND fare_amount >= 0 AND total_amount >= 0
    ), hashed AS (
      SELECT md5(concat_ws('|',
        coalesce(cast(pickup_datetime AS VARCHAR), '<null>'),
        coalesce(cast(dropoff_datetime AS VARCHAR), '<null>'),
        cast(vendor_key AS VARCHAR), cast(payment_key AS VARCHAR),
        cast(pickup_location_key AS VARCHAR), cast(dropoff_location_key AS VARCHAR),
        coalesce(cast(passenger_count AS VARCHAR), '<null>'),
        cast(trip_distance AS VARCHAR), cast(fare_amount AS VARCHAR),
        cast(total_amount AS VARCHAR))) AS trip_key, * FROM filtered
    )
    SELECT DISTINCT ON (trip_key)
      trip_key, pickup_datetime, dropoff_datetime,
      cast(strftime(pickup_datetime, '%Y%m%d') AS INTEGER) AS pickup_date_key,
      cast(extract(hour FROM pickup_datetime) AS INTEGER) AS pickup_hour,
      vendor_key, payment_key, pickup_location_key, dropoff_location_key,
      passenger_count, trip_distance, fare_amount, total_amount
    FROM hashed
    """
    db.execute(f"COPY ({query}) TO '{output}' (HEADER FALSE, DELIMITER ',', NULL '\\N')")
    rows = db.execute(f"SELECT count(*) FROM read_csv('{output}', header=false, nullstr='\\N')").fetchone()[0]
    log.info(f"Transformed and deduplicated rows: {rows}; output={output}")
    db.close()
    return rows
