-- =============================================================
-- Timeline Analysis - first simulation export
-- Each query block is marked with:  -- QUERY: <name>
-- Run them individually in psql or via run_timeline_analysis.py
-- =============================================================

-- QUERY: events_per_type
SELECT event_type, COUNT(*) AS events
FROM simulation_events
GROUP BY event_type
ORDER BY events DESC;

-- QUERY: passenger_count_by_flight
SELECT flight_number, COUNT(DISTINCT entity_id) AS passengers
FROM simulation_events
WHERE entity_type = 'passenger'
GROUP BY flight_number
ORDER BY flight_number;

-- QUERY: zone_events
SELECT zone, state, COUNT(*) AS events
FROM simulation_events
WHERE entity_type = 'passenger' AND zone IS NOT NULL
GROUP BY zone, state
ORDER BY zone, events DESC;

-- QUERY: average_wait_by_security
SELECT
    ROUND(AVG(wait_seconds::numeric) FILTER (WHERE event_type = 'Security_Started')) AS avg_wait_s,
    MAX(wait_seconds) FILTER (WHERE event_type = 'Security_Started') AS max_wait_s,
    SUM(CASE WHEN security_congested THEN 1 ELSE 0 END) AS congested_events,
    ROUND(AVG(service_time::numeric) FILTER (WHERE event_type = 'Security_Started')) AS avg_service_s
FROM simulation_events;

-- QUERY: stress_by_zone
SELECT zone,
    COUNT(*) AS events,
    ROUND(AVG(stress)::numeric, 3) AS avg_stress,
    ROUND(MIN(stress)::numeric, 3) AS min_stress,
    ROUND(MAX(stress)::numeric, 3) AS max_stress
FROM simulation_events
WHERE entity_type = 'passenger' AND zone IS NOT NULL
GROUP BY zone
ORDER BY avg_stress DESC;

-- QUERY: arrival_margins
SELECT flight_number,
    ROUND(AVG(arrival_margin)::numeric, 1) AS avg_margin_min,
    MIN(arrival_margin) AS earliest_min,
    MAX(arrival_margin) AS latest_min
FROM simulation_events
WHERE event_type = 'Arrive_Airport'
GROUP BY flight_number
ORDER BY flight_number;

-- QUERY: walking_speed_by_leg
SELECT zone,
    ROUND(AVG(walking_speed)::numeric, 3) AS avg_speed_ms,
    ROUND(MIN(walking_speed)::numeric, 3) AS min_speed_ms,
    ROUND(MAX(walking_speed)::numeric, 3) AS max_speed_ms,
    ROUND(AVG(distance)::numeric, 1) AS avg_distance_m
FROM simulation_events
WHERE entity_type = 'passenger'
  AND walking_speed IS NOT NULL
GROUP BY zone
ORDER BY avg_speed_ms DESC;

-- QUERY: boarding_windows
SELECT
    b.flight_number,
    b.boarding_started,
    MAX(p.event_time) AS last_boarded
FROM (
    SELECT entity_id AS flight_number,
        MIN(event_time) AS boarding_started
    FROM simulation_events
    WHERE entity_type = 'flight' AND event_type = 'Boarding_Started'
    GROUP BY entity_id
) AS b
LEFT JOIN simulation_events AS p
    ON p.event_type = 'Passenger_Boarded'
   AND p.flight_number = b.flight_number
GROUP BY b.flight_number, b.boarding_started
ORDER BY b.flight_number;

-- QUERY: journey_duration_per_flight
SELECT
    flight_number,
    ROUND(AVG(EXTRACT(EPOCH FROM (boarded - arrived)) / 60.0), 1) AS avg_journey_min,
    ROUND(MIN(EXTRACT(EPOCH FROM (boarded - arrived)) / 60.0), 1) AS min_journey_min,
    ROUND(MAX(EXTRACT(EPOCH FROM (boarded - arrived)) / 60.0), 1) AS max_journey_min
FROM (
    SELECT entity_id,
        MAX(flight_number) AS flight_number,
        MAX(event_time) FILTER (WHERE event_type = 'Arrive_Airport') AS arrived,
        MAX(event_time) FILTER (WHERE event_type = 'Passenger_Boarded') AS boarded
    FROM simulation_events
    WHERE entity_type = 'passenger'
    GROUP BY entity_id
) AS per_passenger
WHERE boarded IS NOT NULL AND arrived IS NOT NULL
GROUP BY flight_number
ORDER BY flight_number;

-- QUERY: hourly_zone_activity
SELECT
    date_trunc('hour', event_time) AS hour,
    zone,
    COUNT(*) AS events
FROM simulation_events
WHERE entity_type = 'passenger' AND zone IS NOT NULL
GROUP BY hour, zone
ORDER BY hour, zone;

-- QUERY: security_occupancy_timeline
SELECT
    date_trunc('hour', event_time) AS hour,
    ROUND(AVG(security_occupancy)::numeric, 1) AS avg_occupancy,
    MAX(security_occupancy) AS peak_occupancy
FROM simulation_events
WHERE event_type = 'Security_Started'
GROUP BY hour
ORDER BY hour;