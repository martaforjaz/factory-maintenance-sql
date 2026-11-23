ASSERT (
  SELECT COUNT(*) = 10000 AND COUNT(DISTINCT observation_id) = 10000
    AND SUM(failed) = 339
  FROM `factory_maintenance.ai4i_raw`
) AS 'Expected 10,000 distinct observations and 339 failures after replay';
