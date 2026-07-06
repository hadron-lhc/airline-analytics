-- ============================================================================
-- DESCRIPCIÓN: Definición de tablas con restricciones explícitas y con nombre.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- LIMPIEZA DE TABLAS EXISTENTES
-- ============================================================================
DROP TABLE IF EXISTS check_ins;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS flights;
DROP TABLE IF EXISTS aircraft;
DROP TABLE IF EXISTS passengers;
DROP TABLE IF EXISTS airlines;
DROP TABLE IF EXISTS airports;

-- ============================================================================
-- CREACIÓN DE TABLAS Y RESTRICCIONES (CONSTRAINTS)
-- ============================================================================

-- 1. AIRPORTS
CREATE TABLE airports (
    airport_id CHAR(3) PRIMARY KEY,
    icao_code CHAR(4) NOT NULL,
    name VARCHAR(150) NOT NULL,
    continent VARCHAR(50) NOT NULL,
    municipality VARCHAR(100) NOT NULL,
    country CHAR(2) NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    elevation_ft INT NOT NULL,
    
    -- Restricciones
    CONSTRAINT uq_airports_icao UNIQUE (icao_code),
    CONSTRAINT chk_airports_latitude CHECK (latitude BETWEEN -90.00000000 AND 90.00000000),
    CONSTRAINT chk_airports_longitude CHECK (longitude BETWEEN -180.00000000 AND 180.00000000)
);

-- 2. AIRLINES
CREATE TABLE airlines (
    airline_id CHAR(3) PRIMARY KEY,
    iata_code CHAR(2) NOT NULL,
    name VARCHAR(100) NOT NULL,
    country CHAR(2) NOT NULL,
    alliance VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Restricciones
    CONSTRAINT uq_airlines_iata UNIQUE (iata_code)
);

-- 3. PASSENGERS
CREATE TABLE passengers (
    passenger_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    birth_date DATE NOT NULL,
    gender CHAR(1) NOT NULL,
    document_type VARCHAR(20) NOT NULL,
    document_number VARCHAR(30) NOT NULL,
    nationality CHAR(2) NOT NULL,
    registration_date DATE NOT NULL DEFAULT CURRENT_DATE,
    email VARCHAR(100) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    loyalty_level VARCHAR(10) NOT NULL DEFAULT 'None',
    
    -- Restricciones con Nombre (Valores fijos aplicados)
    CONSTRAINT uq_passengers_document UNIQUE (document_type, document_number),
    CONSTRAINT chk_passengers_gender CHECK (gender IN ('M', 'F')),
    CONSTRAINT chk_passengers_loyalty CHECK (loyalty_level IN ('None', 'Silver', 'Gold', 'Platinum')),
    CONSTRAINT chk_passengers_dates CHECK (registration_date >= birth_date)
);

-- 4. AIRCRAFT
CREATE TABLE aircraft (
    aircraft_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    registration_number VARCHAR(20) NOT NULL,
    airline_id CHAR(3) NOT NULL,
    model VARCHAR(50) NOT NULL,
    capacity INT NOT NULL,
    manufacture_year INT NOT NULL,
    
    -- Restricciones
    CONSTRAINT uq_aircraft_registration UNIQUE (registration_number),
    CONSTRAINT fk_aircraft_airline FOREIGN KEY (airline_id) REFERENCES airlines(airline_id) ON DELETE RESTRICT,
    CONSTRAINT chk_aircraft_capacity CHECK (capacity > 0),
    CONSTRAINT chk_aircraft_year CHECK (manufacture_year BETWEEN 1903 AND 2026)
);

-- 5. FLIGHTS
CREATE TABLE flights (
    flight_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    flight_number VARCHAR(10) NOT NULL,
    airline_id CHAR(3) NOT NULL,
    aircraft_id UUID NOT NULL,
    departure_airport_id CHAR(3) NOT NULL,
    arrival_airport_id CHAR(3) NOT NULL,
    scheduled_departure TIMESTAMP WITH TIME ZONE NOT NULL,
    scheduled_arrival TIMESTAMP WITH TIME ZONE NOT NULL,
    actual_departure TIMESTAMP WITH TIME ZONE,
    actual_arrival TIMESTAMP WITH TIME ZONE,
    distance_km INT NOT NULL,
    delay_minutes INT NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'Scheduled',
    
    -- Claves Foráneas
    CONSTRAINT fk_flights_airline FOREIGN KEY (airline_id) REFERENCES airlines(airline_id) ON DELETE RESTRICT,
    CONSTRAINT fk_flights_aircraft FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id) ON DELETE RESTRICT,
    CONSTRAINT fk_flights_departure_airport FOREIGN KEY (departure_airport_id) REFERENCES airports(airport_id) ON DELETE RESTRICT,
    CONSTRAINT fk_flights_arrival_airport FOREIGN KEY (arrival_airport_id) REFERENCES airports(airport_id) ON DELETE RESTRICT,
    
    -- Restricciones de Negocio y Valores Fijos
    CONSTRAINT chk_flights_status CHECK (status IN ('Scheduled', 'Delayed', 'Departed', 'Arrived', 'Cancelled')),
    CONSTRAINT chk_flights_route CHECK (departure_airport_id <> arrival_airport_id),
    CONSTRAINT chk_flights_distance CHECK (distance_km > 0),
    CONSTRAINT chk_flights_scheduled_timeline CHECK (scheduled_arrival > scheduled_departure),
    CONSTRAINT chk_flights_actual_timeline CHECK (actual_arrival > actual_departure)
);

-- 6. BOOKINGS
CREATE TABLE bookings (
    booking_id UUID PRIMARY KEY,
    booking_reference CHAR(6) NOT NULL,
    passenger_id UUID NOT NULL,
    flight_id BIGINT NOT NULL,
    booking_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    amount DECIMAL(10, 2) NOT NULL,
    fare_class VARCHAR(20) NOT NULL,
    booking_channel VARCHAR(20) NOT NULL,
    
    -- Claves Foráneas
    CONSTRAINT fk_bookings_passenger FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id) ON DELETE RESTRICT,
    CONSTRAINT fk_bookings_flight FOREIGN KEY (flight_id) REFERENCES flights(flight_id) ON DELETE RESTRICT,
    
    -- Restricciones de Negocio y Valores Fijos
    CONSTRAINT uq_bookings_reference UNIQUE (booking_reference),
    CONSTRAINT chk_bookings_amount CHECK (amount >= 0.00),
    CONSTRAINT chk_bookings_fare_class CHECK (fare_class IN ('Economy', 'Premium Economy', 'Business', 'First')),
    CONSTRAINT chk_bookings_channel CHECK (booking_channel IN ('Website', 'Mobile App', 'Travel Agency'))
);

-- 7. CHECK_INS
CREATE TABLE check_ins (
    check_in_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    booking_id UUID NOT NULL,
    check_in_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    boarded BOOLEAN NOT NULL DEFAULT FALSE,
    seat_number VARCHAR(5) NOT NULL,
    baggage_count INT NOT NULL DEFAULT 0,
    baggage_weight_kg DECIMAL(5, 2) NOT NULL DEFAULT 0.00,
    
    -- Claves Foráneas y Unicidad (1:1 con Booking)
    CONSTRAINT uq_check_ins_booking UNIQUE (booking_id),
    CONSTRAINT fk_check_ins_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    
    -- Restricciones
    CONSTRAINT chk_check_ins_baggage_count CHECK (baggage_count >= 0),
    CONSTRAINT chk_check_ins_baggage_weight CHECK (baggage_weight_kg >= 0.00)
);


---------------------------------------------------------------------------------------

-- ÍNDICES ADICIONALES RECOMENDADOS PARA EL RENDIMIENTO DE LA SIMULACIÓN

-- Optimiza búsquedas de vuelos por estado y rango horario (Crucial para el motor de simulación)
CREATE INDEX idx_flights_status_departure ON flights (status, scheduled_departure);

-- Optimiza la búsqueda de reservas de un vuelo en particular
CREATE INDEX idx_bookings_flight_id ON bookings (flight_id);
