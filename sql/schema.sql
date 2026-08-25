DROP TABLE IF EXISTS simulation_events;

CREATE TABLE simulation_events (
    event_id BIGSERIAL PRIMARY KEY,
    event_time TIMESTAMP NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(30) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    flight_number VARCHAR(20),
    airport_code CHAR(3)
);
