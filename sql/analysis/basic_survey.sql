SELECT
  entity_type,
  COUNT(*) AS total
FROM simulation_events
GROUP BY entity_type
ORDER BY entity_type;


SELECT *
FROM simulation_events
LIMIT 10;


