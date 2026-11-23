-- Run in the same project as the factory_maintenance dataset.
CREATE TEMP TABLE telemetry AS
SELECT observation_id, product_id, grade, air_k, process_k, rpm, torque_nm, wear_min
FROM `factory_maintenance.ai4i_raw`;

CREATE TEMP TABLE outcomes AS
SELECT observation_id, failed FROM `factory_maintenance.ai4i_raw`;

ASSERT (
  SELECT COUNT(*) = 10000 AND COUNT(DISTINCT observation_id) = 10000
    AND COUNT(DISTINCT product_id) = 10000
    AND COUNTIF(grade IN ('L', 'M', 'H') AND STARTS_WITH(product_id, grade)
      AND air_k > 0 AND process_k >= air_k AND rpm > 0 AND torque_nm >= 0
      AND wear_min >= 0) = 10000
  FROM telemetry
) AS 'Unexpected row count or invalid telemetry';

ASSERT (SELECT COUNTIF(failed IN (0,1)) = 10000 FROM outcomes)
AS 'Missing or invalid outcomes';

CREATE OR REPLACE TABLE `factory_maintenance.model_features` AS
SELECT observation_id, grade, air_k, process_k, process_k - air_k AS temperature_delta_k,
  rpm, torque_nm, rpm * torque_nm * 2 * 3.141592653589793 / 60 AS power_w, wear_min
FROM telemetry;

CREATE OR REPLACE TABLE `factory_maintenance.failure_rates` AS
WITH cohorts AS (
  SELECT grade,
    CASE WHEN wear_min < 100 THEN '0–99' WHEN wear_min < 200 THEN '100–199'
      ELSE '200+' END AS wear_band,
    failed
  FROM telemetry JOIN outcomes USING (observation_id)
), totals AS (
  SELECT grade, wear_band, COUNT(*) AS observations, SUM(failed) AS failures,
    AVG(failed) AS failure_rate
  FROM cohorts GROUP BY grade, wear_band
)
SELECT *, ROUND(100 * failure_rate, 2) AS failure_pct,
  DENSE_RANK() OVER (PARTITION BY grade ORDER BY failure_rate DESC) AS risk_rank_within_grade
FROM totals;
