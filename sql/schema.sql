DROP TABLE IF EXISTS simulation_events;

CREATE TABLE simulation_events (
    event_id BIGSERIAL PRIMARY KEY,
    event_time TIMESTAMP NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(30) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    flight_number VARCHAR(20),
    airport_code CHAR(3),
    zone VARCHAR(30),
    state VARCHAR(30),
    stress DOUBLE PRECISION,

    arrival_margin DOUBLE PRECISION,
    wait_seconds DOUBLE PRECISION,
    service_time DOUBLE PRECISION,
    queue_length INTEGER,
    security_occupancy INTEGER,
    security_congested BOOLEAN,
    time_pressure DOUBLE PRECISION,
    walking_speed DOUBLE PRECISION,
    distance DOUBLE PRECISION,
    walking_time DOUBLE PRECISION
);

CREATE INDEX idx_events_time ON simulation_events (event_time);
CREATE INDEX idx_events_flight ON simulation_events (flight_number);
CREATE INDEX idx_events_zone ON simulation_events (zone);