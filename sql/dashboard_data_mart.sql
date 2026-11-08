-- Wide table feeding the Looker Studio dashboard (used as the OWOX Data Mart query).
-- Joins the star schema back into one row per trip.
SELECT d.date, d.year, d.month, d.day_name, d.is_weekend,
       f.trip_hour,
       pa.area AS pickup_area, pa.state,
       da.area AS dropoff_area,
       s.service_type, p.payment_method,
       f.distance_km, f.surge_multiplier, f.fare, f.fare_per_km,
       f.rating, f.ron95_price, f.diesel_price
FROM myride_gold.fact_trips f
JOIN myride_gold.dim_date d ON f.date_key = d.date_key
JOIN myride_gold.dim_area pa ON f.pickup_area_id = pa.area_id
JOIN myride_gold.dim_area da ON f.dropoff_area_id = da.area_id
JOIN myride_gold.dim_service s ON f.service_id = s.service_id
JOIN myride_gold.dim_payment p ON f.payment_id = p.payment_id;
