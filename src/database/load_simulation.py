import json
import os
from pathlib import Path
from dotenv import load_dotenv

import psycopg

JSON_PATH = (
    Path(__file__).parent.parent.parent / "data/exports/simulation_2026_07_13.json"
)

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),
}


def load_events_from_json(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def insert_events(events: list[dict]) -> None:
    with psycopg.connect(**DB_CONFIG) as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE simulation_events RESTART IDENTITY")

            for event in events:
                cursor.execute(
                    """
                    INSERT INTO simulation_events (
                        event_time,
                        event_type,
                        entity_type,
                        entity_id,
                        flight_number,
                        airport_code
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        event["time"],
                        event["event"],
                        event["entity"],
                        event["id"],
                        event.get("flight"),
                        event.get("airport"),
                    ),
                )


def main():
    events = load_events_from_json(JSON_PATH)
    print(f"Events loaded from JSON: {len(events)}")

    insert_events(events)

    print("Events inserted into PostgreSQL.")


if __name__ == "__main__":
    main()
