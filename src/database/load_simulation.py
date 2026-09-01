import json
import os
from pathlib import Path
from dotenv import load_dotenv

import psycopg

JSON_PATH = (
    Path(__file__).parent.parent.parent / "data/exports/simulation_2026_07_13.json"
)

SCHEMA_PATH = Path(__file__).parent.parent.parent / "sql/schema.sql"

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),
}

METRIC_COLUMNS = [
    "arrival_margin",
    "wait_seconds",
    "service_time",
    "queue_length",
    "security_occupancy",
    "security_congested",
    "time_pressure",
    "walking_speed",
    "distance",
    "walking_time",
    "stress",
]


def apply_schema(path: Path = SCHEMA_PATH) -> None:
    with open(path, "r", encoding="utf-8") as file:
        schema = file.read()

    with psycopg.connect(**DB_CONFIG) as connection:
        connection.execute(schema)


def load_events_from_json(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def insert_events(events: list[dict]) -> None:
    metric_placeholders = ", ".join([f"%s"] * len(METRIC_COLUMNS))

    with psycopg.connect(**DB_CONFIG) as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE simulation_events RESTART IDENTITY")

            for event in events:
                metric_values = [event.get(column) for column in METRIC_COLUMNS]

                cursor.execute(
                    f"""
                    INSERT INTO simulation_events (
                        event_time,
                        event_type,
                        entity_type,
                        entity_id,
                        flight_number,
                        airport_code,
                        zone,
                        state,
                        {", ".join(METRIC_COLUMNS)}
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, {metric_placeholders})
                    """,
                    (
                        event["time"],
                        event["event"],
                        event["entity"],
                        event["id"],
                        event.get("flight"),
                        event.get("airport"),
                        event.get("zone"),
                        event.get("state"),
                        *metric_values,
                    ),
                )


def main():
    events = load_events_from_json(JSON_PATH)
    print(f"Events loaded from JSON: {len(events)}")

    insert_events(events)

    print("Events inserted into PostgreSQL.")


if __name__ == "__main__":
    main()