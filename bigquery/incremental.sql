-- Load a batch into ai4i_stage before running this script.
ASSERT (
  SELECT COUNT(*) > 0 AND COUNT(*) = COUNT(DISTINCT observation_id)
  FROM `factory_maintenance.ai4i_stage`
) AS 'The staged batch must have unique, non-null observation IDs';

CREATE TABLE IF NOT EXISTS `factory_maintenance.ai4i_raw` AS
SELECT * FROM `factory_maintenance.ai4i_stage` WHERE FALSE;

-- Observation IDs are immutable. Reject conflicting replays rather than
-- silently replacing a historical observation.
BEGIN TRANSACTION;
ASSERT (
  SELECT COUNT(*) = 0
  FROM `factory_maintenance.ai4i_raw` AS existing
  JOIN `factory_maintenance.ai4i_stage` AS incoming USING (observation_id)
  WHERE TO_JSON_STRING(existing) != TO_JSON_STRING(incoming)
) AS 'Staged data conflicts with an existing observation';

MERGE `factory_maintenance.ai4i_raw` AS target
USING `factory_maintenance.ai4i_stage` AS source
ON target.observation_id = source.observation_id
WHEN NOT MATCHED THEN INSERT ROW;
COMMIT TRANSACTION;
