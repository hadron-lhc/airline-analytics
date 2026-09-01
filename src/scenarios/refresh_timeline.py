from ..database import load_simulation
from ..analysis import run_timeline_analysis
from . import export_timeline


def main():
    print("=" * 60)
    print("STEP 1/4 - Generating timeline")
    print("=" * 60)

    export_timeline.main()

    print("\n" + "=" * 60)
    print("STEP 2/4 - Applying schema")
    print("=" * 60)

    load_simulation.apply_schema()
    print("Schema applied.")

    print("\n" + "=" * 60)
    print("STEP 3/4 - Loading events into PostgreSQL")
    print("=" * 60)

    events = load_simulation.load_events_from_json(load_simulation.JSON_PATH)
    load_simulation.insert_events(events)
    print(f"Events inserted: {len(events)}")

    print("\n" + "=" * 60)
    print("STEP 4/4 - Timeline analysis")
    print("=" * 60)

    run_timeline_analysis.main()


if __name__ == "__main__":
    main()