-- Distance-weighted fare per mile
SELECT round((sum(fare_amount) / nullif(sum(trip_distance),0))::numeric,2) AS fare_per_mile
FROM fact_taxi_trips;


-- Peak hours
SELECT pickup_hour, count(*) AS trips FROM fact_taxi_trips
GROUP BY pickup_hour ORDER BY trips DESC;


-- Total recorded charges per payment method
SELECT p.payment_name, sum(f.total_amount) AS total_charges
FROM fact_taxi_trips f JOIN dim_payment p ON p.payment_key=f.payment_key
GROUP BY p.payment_name ORDER BY total_charges DESC;
