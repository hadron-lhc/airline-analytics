from pathlib import Path

from ..analysis.passenger_population_analyzer import (
    PassengerPopulationAnalyzer,
)
from ..simulation.generators.passenger_factory import generate_passengers


REPORT_PATH = Path("population_report.md")


def main():
    passengers = generate_passengers(10_000)

    analyzer = PassengerPopulationAnalyzer(passengers)

    report = analyzer.generate_report()

    REPORT_PATH.write_text(
        report,
        encoding="utf-8",
    )

    print("Passenger population generated successfully.")
    print(f"Passengers: {len(passengers):,}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
