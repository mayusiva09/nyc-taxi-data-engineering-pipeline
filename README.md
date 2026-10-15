# NYC Taxi Batch ETL — Interview Demo

## Architecture
NYC TLC Parquet → local raw files → DuckDB transformation → CSV staging → PostgreSQL star schema → Streamlit. Airflow orchestrates extraction, transformation, load and quality check. Uses Airflow 2.10.5 and PostgreSQL 16 for a small local demo. **This is a local demonstration, not a production configuration.**

## Prerequisites
Linux, Docker Engine, `docker compose` v2, Python 3.10+, ~4GB+ free RAM, 3GB+ disk space, internet access. Docker must be accessible to your user.

## Quick start
```bash
chmod +x setup.sh
./setup.sh
# First run may pull Docker images and install packages.
docker compose up -d --build
# Airflow: http://localhost:8080 — admin / admin
# In Airflow UI: enable and manually trigger nyc_yellow_taxi_batch_etl
# Dashboard: http://localhost:8501 (refresh after DAG succeeds)
```
Or run stages locally after setup: `source .venv/bin/activate && python -m src.cli run` (PostgreSQL is on port 5433 from your host).

## Inspect the data
```bash
docker compose exec postgres psql -U taxi -d taxi_analytics -c 'SELECT count(*) FROM fact_taxi_trips;'
docker compose exec postgres psql -U taxi -d taxi_analytics -f /dev/stdin < sql/analytics_queries.sql
pytest -q
```

## Show idempotency
Re-trigger the same DAG; `fact_taxi_trips.trip_key` is a deterministic MD5 fingerprint of chosen source fields and `ON CONFLICT DO NOTHING` prevents duplicate insertions. This is a **heuristic**, not a guaranteed unique trip ID. Extremely similar real trips can collapse.

## Data quality decisions
Invalid date order, non-positive miles, negative fares/totals, missing timestamps, and pickups outside Jan–Feb 2023 are filtered out. Null dimensional codes are mapped to -1. Null passenger count stays null. Outliers are not capped. The starter currently reports accepted row counts but **does not persist rejected records**; adding a rejection audit is a sensible next enhancement. `dim_location` holds location IDs and placeholder names; an NYC taxi-zone lookup enrichment is optional.

## Troubleshooting
- Airflow task errors: `docker compose logs -f airflow-scheduler`
- Database: `docker compose ps` and `docker compose logs postgres`
- Dashboard error before DAG run is expected; refresh after the data loads.
- If port 5433/8080/8501 is taken, modify host-side compose ports accordingly.
- The schema init script runs only on a *fresh* Postgres volume. **`docker compose down -v` permanently wipes both databases**.
- For minimal RAM, stop dashboard until after the DAG: `docker compose stop dashboard` then `docker compose start dashboard`.

## Candidate explanation
- Fact grain: 1 accepted trip row, identified by a deterministic fingerprint (not an official trip ID).
- Role-playing dimension: dim_location referenced once for pickup and again for drop-off.
- Idempotence: staging temp table + unique key + `ON CONFLICT DO NOTHING`.
- Atomic load: COPY staging and all dimension/fact SQL execute in one transaction.
- Rate metric: `SUM(fare_amount) / SUM(trip_distance)` is distance-weighted, not average of each per-trip ratio.
- Revenue metric: SUM(total_amount) is recorded passenger charges; excludes unrecorded cash tips.
- Airflow retries cover failures while PostgreSQL transaction rollback prevents partial loads.

## Limitations
Local-only credentials and exposed ports; do not reuse in production. Parquet file integrity check validates that DuckDB reads the file but does not verify checksum from TLC. Entire selected source period is recomputed on each run (no incremental partition watermark). Some dataset versions may have slightly different optional fields. Airflow's published 2.x image is pinned for stability of this demo, not for production security support.
