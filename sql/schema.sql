CREATE TABLE IF NOT EXISTS dim_date (
  date_key INTEGER PRIMARY KEY,
  full_date DATE NOT NULL UNIQUE,
  year SMALLINT NOT NULL,
  month SMALLINT NOT NULL,
  day SMALLINT NOT NULL,
  day_of_week SMALLINT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_payment (
  payment_key INTEGER PRIMARY KEY,
  payment_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_vendor (
  vendor_key INTEGER PRIMARY KEY,
  vendor_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_location (
  location_key INTEGER PRIMARY KEY,
  zone_name TEXT NOT NULL DEFAULT 'Not enriched'
);

CREATE TABLE IF NOT EXISTS fact_taxi_trips (
  trip_key TEXT PRIMARY KEY,
  pickup_datetime TIMESTAMP NOT NULL,
  dropoff_datetime TIMESTAMP NOT NULL,
  pickup_date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
  pickup_hour SMALLINT NOT NULL CHECK (pickup_hour BETWEEN 0 AND 23),
  vendor_key INTEGER NOT NULL REFERENCES dim_vendor(vendor_key),
  payment_key INTEGER NOT NULL REFERENCES dim_payment(payment_key),
  pickup_location_key INTEGER NOT NULL REFERENCES dim_location(location_key),
  dropoff_location_key INTEGER NOT NULL REFERENCES dim_location(location_key),
  passenger_count INTEGER,
  trip_distance DOUBLE PRECISION NOT NULL CHECK (trip_distance > 0),
  fare_amount NUMERIC(12,2) NOT NULL CHECK (fare_amount >= 0),
  total_amount NUMERIC(12,2) NOT NULL CHECK (total_amount >= 0)
);

CREATE INDEX IF NOT EXISTS idx_fact_pickup_date ON fact_taxi_trips(pickup_date_key);
CREATE INDEX IF NOT EXISTS idx_fact_pickup_hour ON fact_taxi_trips(pickup_hour);
CREATE INDEX IF NOT EXISTS idx_fact_payment ON fact_taxi_trips(payment_key);


CREATE TABLE IF NOT EXISTS etl_audit (
  id BIGSERIAL PRIMARY KEY,
  stage TEXT NOT NULL,
  status TEXT NOT NULL,
  row_count BIGINT,
  detail TEXT,
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
