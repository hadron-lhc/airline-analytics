# Passenger

## Identity

──────────────
Passenger
│
├── IDENTITY
│ │
│ ├── passenger_id
│ ├── first_name
│ ├── last_name
│ ├── birth_date
│ ├── gender
│ ├── nationality
│ ├── document_type
│ └── document_number
│
├── PROFILE
│ │
│ ├── travel_purpose
│ ├── travel_experience
│ ├── loyalty_level
│ ├── preferred_airline
│ └── preferred_seat
│
├── BEHAVIORAL_TRAITS
│ │
│ ├── walking_speed
│ ├── punctuality
│ ├── patience
│ ├── risk_tolerance
│ ├── arrival_margin
│ ├── online_checkin_probability
│ └── baggage_probability
│
├── DYNAMIC_STATE
│ │
│ ├── state
│ ├── current_airport
│ ├── current_zone
│ ├── current_gate
│ ├── current_flight
│ ├── checked_in
│ ├── boarded
│ └── seat_number
│
├── TEMPORAL_STATE
│ │
│ ├── stress_level
│ ├── fatigue
│ ├── time_deviation
│ └── waiting_time
│
├── HISTORY
│ │
│ ├── flights_taken
│ ├── flights_missed
│ ├── checkins_completed
│ ├── baggage_count
│ └── total_travel_time
│

---

## Travel Profile

──────────────

loyalty_level

preferred_airline

preferred_seat

online_checkin_probability

baggage_probability

arrival_margin

walking_speed

travel_experience

---

## Simulation State

──────────────

state

current_airport

current_flight

current_gate

seat_number

boarding_time

checked_in

boarded

arrived

---

## Ciclo de vida

Compra un pasaje

↓

Permanece en casa

↓

Va al aeropuerto

↓

Hace check-in

↓

Pasa seguridad

↓

Espera en la puerta

↓

Aborda

↓

Vuela

↓

Desembarca

↓

Sale del aeropuerto
