CREATE TABLE telemetry (
  observation_id INTEGER PRIMARY KEY,
  product_id TEXT NOT NULL UNIQUE,
  grade TEXT NOT NULL CHECK (grade IN ('L','M','H')),
  air_k REAL NOT NULL CHECK (air_k > 0),
  process_k REAL NOT NULL CHECK (process_k > 0),
  rpm INTEGER NOT NULL CHECK (rpm > 0),
  torque_nm REAL NOT NULL CHECK (torque_nm >= 0),
  wear_min INTEGER NOT NULL CHECK (wear_min >= 0)
) STRICT;

CREATE TABLE outcomes (
  observation_id INTEGER PRIMARY KEY REFERENCES telemetry,
  failed INTEGER NOT NULL CHECK (failed IN (0,1))
) STRICT;

-- Keep source identifiers and outcome fields out of the feature columns.
CREATE VIEW model_features AS
SELECT observation_id, grade, air_k, process_k, process_k-air_k AS temperature_delta_k,
       rpm, torque_nm, rpm * torque_nm * 2 * 3.141592653589793 / 60 AS power_w,
       wear_min
FROM telemetry;

CREATE VIEW failure_rates AS
WITH cohorts AS (
  SELECT grade, CASE WHEN wear_min < 100 THEN '0–99'
                     WHEN wear_min < 200 THEN '100–199' ELSE '200+' END AS wear_band,
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

CREATE VIEW quality_checks AS
SELECT 'expected source rows (10000)' AS check_name, ABS(COUNT(*) - 10000) AS violations FROM telemetry
UNION ALL
SELECT 'missing outcome', COUNT(*) FROM telemetry LEFT JOIN outcomes USING (observation_id)
WHERE failed IS NULL
UNION ALL
SELECT 'product grade mismatch', COUNT(*) FROM telemetry WHERE substr(product_id, 1, 1) <> grade
UNION ALL
SELECT 'invalid temperature ordering', COUNT(*) FROM telemetry WHERE process_k < air_k;
