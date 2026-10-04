-- Run these on weather.db (table: daily_weather)
-- Columns: date, temp_max, temp_min, rain_mm, city, temp_range, rain_category

-- 1) Average max temperature per city
SELECT city, ROUND(AVG(temp_max), 1) AS avg_max_temp
FROM daily_weather
GROUP BY city
ORDER BY avg_max_temp DESC;

-- 2) Hottest day for each city (window function)
SELECT city, date, temp_max
FROM (
    SELECT city, date, temp_max,
           ROW_NUMBER() OVER (PARTITION BY city ORDER BY temp_max DESC) AS rn
    FROM daily_weather
)
WHERE rn = 1;

-- 3) Cities with more than 50 mm total rain (GROUP BY + HAVING)
SELECT city, ROUND(SUM(rain_mm), 1) AS total_rain
FROM daily_weather
GROUP BY city
HAVING SUM(rain_mm) > 50
ORDER BY total_rain DESC;

-- 4) Number of heavy rain days per city
SELECT city, COUNT(*) AS heavy_rain_days
FROM daily_weather
WHERE rain_category = 'Heavy'
GROUP BY city
ORDER BY heavy_rain_days DESC;

-- 5) 3-day moving average of max temp (window function)
SELECT city, date, temp_max,
       ROUND(AVG(temp_max) OVER (
           PARTITION BY city
           ORDER BY date
           ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
       ), 1) AS moving_avg_3day
FROM daily_weather
ORDER BY city, date;

-- 6) Day-to-day temperature change using LAG
SELECT city, date, temp_max,
       ROUND(temp_max - LAG(temp_max) OVER (PARTITION BY city ORDER BY date), 1) AS change_from_yesterday
FROM daily_weather
ORDER BY city, date;