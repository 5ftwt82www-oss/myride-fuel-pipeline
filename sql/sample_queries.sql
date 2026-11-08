-- Sample Athena queries on the gold layer (database: myride_gold)

-- 1. Busiest pickup areas and their average fare
SELECT a.area, a.state, COUNT(*) AS trips, ROUND(AVG(f.fare), 2) AS avg_fare
FROM fact_trips f
JOIN dim_area a ON f.pickup_area_id = a.area_id
GROUP BY a.area, a.state
ORDER BY trips DESC;

-- 2. Trips by hour of day (rush-hour pattern)
SELECT trip_hour, COUNT(*) AS trips
FROM fact_trips
GROUP BY trip_hour
ORDER BY trip_hour;

-- 3. Monthly fare per km vs RON95 price
SELECT d.year, d.month,
       ROUND(AVG(f.fare_per_km), 2) AS avg_fare_per_km,
       ROUND(AVG(f.ron95_price), 2) AS avg_ron95_price
FROM fact_trips f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month
ORDER BY d.year, d.month;

-- 4. Revenue and average rating by service type
SELECT s.service_type,
       COUNT(*) AS trips,
       ROUND(SUM(f.fare), 2) AS revenue,
       ROUND(AVG(f.rating), 2) AS avg_rating
FROM fact_trips f
JOIN dim_service s ON f.service_id = s.service_id
GROUP BY s.service_type
ORDER BY revenue DESC;

-- 5. Payment method share
SELECT p.payment_method,
       COUNT(*) AS trips,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_trips
FROM fact_trips f
JOIN dim_payment p ON f.payment_id = p.payment_id
GROUP BY p.payment_method
ORDER BY trips DESC;
