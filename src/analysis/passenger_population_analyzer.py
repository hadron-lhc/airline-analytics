from collections import Counter, defaultdict
from statistics import mean, median, stdev, quantiles

from ..enums.world_enums import LoyaltyLevel
from ..world.passenger import Passenger


class PassengerPopulationAnalyzer:
    """
    Analiza una población de Passenger.

    El analyzer no modifica pasajeros ni genera datos.
    Su única responsabilidad es describir y validar
    estadísticamente la población generada.
    """

    def __init__(self, passengers: list[Passenger]):
        self.passengers = passengers

    # ============================================================
    # BASIC STATISTICS
    # ============================================================

    @staticmethod
    def _numeric_statistics(values: list[float | int]) -> dict:
        if not values:
            return {
                "count": 0,
                "mean": 0,
                "median": 0,
                "min": 0,
                "max": 0,
                "stdev": 0,
                "p10": 0,
                "p25": 0,
                "p75": 0,
                "p90": 0,
            }

        percentiles = quantiles(values, n=100, method="inclusive")

        return {
            "count": len(values),
            "mean": round(mean(values), 3),
            "median": round(median(values), 3),
            "min": min(values),
            "max": max(values),
            "stdev": round(stdev(values), 3) if len(values) > 1 else 0,
            "p10": round(percentiles[9], 3),
            "p25": round(percentiles[24], 3),
            "p75": round(percentiles[74], 3),
            "p90": round(percentiles[89], 3),
        }

    @staticmethod
    def _correlation(
        x: list[float | int],
        y: list[float | int],
    ) -> float:
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        mean_x = mean(x)
        mean_y = mean(y)

        numerator = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y))

        denominator_x = sum((a - mean_x) ** 2 for a in x)

        denominator_y = sum((b - mean_y) ** 2 for b in y)

        denominator = (denominator_x * denominator_y) ** 0.5

        if denominator == 0:
            return 0.0

        return numerator / denominator

    # ============================================================
    # AGE
    # ============================================================

    def age_statistics(self) -> dict:
        ages = [p.age for p in self.passengers]

        return self._numeric_statistics(ages)

    # ============================================================
    # TRAVEL PURPOSE
    # ============================================================

    def travel_purpose_distribution(self) -> dict[str, int]:
        return dict(Counter(p.travel_purpose.value for p in self.passengers))

    # ============================================================
    # FITNESS
    # ============================================================

    def fitness_statistics(self) -> dict:
        values = [p.traits.fitness for p in self.passengers]

        return self._numeric_statistics(values)

    # ============================================================
    # STRESS RESILIENCE
    # ============================================================

    def stress_resilience_statistics(self) -> dict:
        values = [p.traits.stress_resilience for p in self.passengers]

        return self._numeric_statistics(values)

    # ============================================================
    # DISTRACTION
    # ============================================================

    def distraction_statistics(self) -> dict:
        values = [p.traits.distraction_proneness for p in self.passengers]

        return self._numeric_statistics(values)

    # ============================================================
    # TRAVEL EXPERIENCE
    # ============================================================

    def travel_experience_statistics(self) -> dict:
        values = [p.traits.travel_experience for p in self.passengers]

        return self._numeric_statistics(values)

    # ============================================================
    # EXPERIENCE BY AGE
    # ============================================================

    def experience_by_age(self) -> dict[str, float]:
        groups = {
            "18-25": [],
            "26-40": [],
            "41-60": [],
            "61-85": [],
        }

        for passenger in self.passengers:
            age = passenger.age
            experience = passenger.traits.travel_experience

            if age <= 25:
                groups["18-25"].append(experience)

            elif age <= 40:
                groups["26-40"].append(experience)

            elif age <= 60:
                groups["41-60"].append(experience)

            else:
                groups["61-85"].append(experience)

        return {
            group: round(mean(values), 2) for group, values in groups.items() if values
        }

    # ============================================================
    # EXPERIENCE BY PURPOSE
    # ============================================================

    def experience_by_purpose(self) -> dict[str, float]:
        groups = defaultdict(list)

        for passenger in self.passengers:
            groups[passenger.travel_purpose.value].append(
                passenger.traits.travel_experience
            )

        return {purpose: round(mean(values), 2) for purpose, values in groups.items()}

    # ============================================================
    # ARRIVAL MARGIN
    # ============================================================

    def arrival_margin_statistics(self) -> dict:
        values = [p.arrival_margin for p in self.passengers]

        return self._numeric_statistics(values)

    # ============================================================
    # WALKING SPEED
    # ============================================================

    def walking_speed_statistics(self) -> dict:
        values = [p.walking_speed for p in self.passengers]

        return self._numeric_statistics(values)

    # ============================================================
    # WALKING SPEED BY AGE
    # ============================================================

    def walking_speed_by_age(self) -> dict[str, float]:
        groups = {
            "18-25": [],
            "26-40": [],
            "41-60": [],
            "61-85": [],
        }

        for passenger in self.passengers:
            age = passenger.age

            if age <= 25:
                groups["18-25"].append(passenger.walking_speed)

            elif age <= 40:
                groups["26-40"].append(passenger.walking_speed)

            elif age <= 60:
                groups["41-60"].append(passenger.walking_speed)

            else:
                groups["61-85"].append(passenger.walking_speed)

        return {
            group: round(mean(values), 3) for group, values in groups.items() if values
        }

    # ============================================================
    # WALKING SPEED BY FITNESS
    # ============================================================

    def walking_speed_by_fitness(self) -> dict[str, float]:
        groups = {
            "Low": [],
            "Medium": [],
            "High": [],
        }

        for passenger in self.passengers:
            fitness = passenger.traits.fitness

            if fitness < 0.33:
                groups["Low"].append(passenger.walking_speed)

            elif fitness < 0.66:
                groups["Medium"].append(passenger.walking_speed)

            else:
                groups["High"].append(passenger.walking_speed)

        return {
            group: round(mean(values), 3) for group, values in groups.items() if values
        }

    # ============================================================
    # ONLINE CHECK-IN
    # ============================================================

    def online_checkin_statistics(self) -> dict:
        values = [p.online_checkin_probability for p in self.passengers]

        return self._numeric_statistics(values)

    # ============================================================
    # BAGGAGE
    # ============================================================

    def baggage_statistics(self) -> dict:
        values = [p.baggage_probability for p in self.passengers]

        return self._numeric_statistics(values)

    # ============================================================
    # LOYALTY
    # ============================================================

    def loyalty_distribution(self) -> dict[str, int]:
        return dict(Counter(p.loyalty_level.value for p in self.passengers))

    # ============================================================
    # LOYALTY BY EXPERIENCE
    # ============================================================

    def loyalty_by_experience(self) -> dict[int, dict[str, int]]:
        result = defaultdict(Counter)

        for passenger in self.passengers:
            experience = passenger.traits.travel_experience
            loyalty = passenger.loyalty_level.value

            result[experience][loyalty] += 1

        return {
            experience: dict(counts) for experience, counts in sorted(result.items())
        }

    # ============================================================
    # BEHAVIOR BY TRAVEL PURPOSE
    # ============================================================

    def behavior_by_purpose(self) -> dict[str, dict[str, float]]:
        groups = {}

        for passenger in self.passengers:
            purpose = passenger.travel_purpose.value

            if purpose not in groups:
                groups[purpose] = {
                    "experience": [],
                    "arrival_margin": [],
                    "walking_speed": [],
                    "online_checkin": [],
                    "baggage": [],
                }

            groups[purpose]["experience"].append(passenger.traits.travel_experience)

            groups[purpose]["arrival_margin"].append(passenger.arrival_margin)

            groups[purpose]["walking_speed"].append(passenger.walking_speed)

            groups[purpose]["online_checkin"].append(
                passenger.online_checkin_probability
            )

            groups[purpose]["baggage"].append(passenger.baggage_probability)

        result = {}

        for purpose, values in groups.items():
            result[purpose] = {
                "experience": round(
                    mean(values["experience"]),
                    2,
                ),
                "arrival_margin": round(
                    mean(values["arrival_margin"]),
                    2,
                ),
                "walking_speed": round(
                    mean(values["walking_speed"]),
                    3,
                ),
                "online_checkin": round(
                    mean(values["online_checkin"]),
                    3,
                ),
                "baggage": round(
                    mean(values["baggage"]),
                    3,
                ),
            }

        return result

    # ============================================================
    # TRAIT CORRELATIONS
    # ============================================================

    def trait_correlations(self) -> dict[str, float]:
        fitness = [p.traits.fitness for p in self.passengers]

        age = [p.age for p in self.passengers]

        stress_resilience = [p.traits.stress_resilience for p in self.passengers]

        distraction = [p.traits.distraction_proneness for p in self.passengers]

        experience = [p.traits.travel_experience for p in self.passengers]

        walking_speed = [p.walking_speed for p in self.passengers]

        arrival_margin = [p.arrival_margin for p in self.passengers]

        online_checkin = [p.online_checkin_probability for p in self.passengers]

        loyalty = [
            {
                LoyaltyLevel.NONE: 0,
                LoyaltyLevel.SILVER: 1,
                LoyaltyLevel.GOLD: 2,
                LoyaltyLevel.PLATINUM: 3,
            }[p.loyalty_level]
            for p in self.passengers
        ]

        return {
            "Fitness ↔ Walking Speed": self._correlation(
                fitness,
                walking_speed,
            ),
            "Age ↔ Fitness": self._correlation(
                age,
                fitness,
            ),
            "Age ↔ Walking Speed": self._correlation(
                age,
                walking_speed,
            ),
            "Experience ↔ Stress Resilience": self._correlation(
                experience,
                stress_resilience,
            ),
            "Experience ↔ Arrival Margin": self._correlation(
                experience,
                arrival_margin,
            ),
            "Experience ↔ Loyalty": self._correlation(
                experience,
                loyalty,
            ),
            "Distraction ↔ Online Check-in": self._correlation(
                distraction,
                online_checkin,
            ),
            "Fitness ↔ Stress Resilience": self._correlation(
                fitness,
                stress_resilience,
            ),
        }

    # ============================================================
    # FULL REPORT
    # ============================================================

    def generate_report(self) -> str:
        lines = []

        lines.append("# PASSENGER POPULATION REPORT")
        lines.append("")
        lines.append(f"Passengers: {len(self.passengers):,}")
        lines.append("")

        # --------------------------------------------------------
        # AGE
        # --------------------------------------------------------

        lines.append("## Age")
        lines.append("")

        for key, value in self.age_statistics().items():
            lines.append(f"{key}: {value}")

        lines.append("")

        # --------------------------------------------------------
        # PURPOSE
        # --------------------------------------------------------

        lines.append("## Travel Purpose")
        lines.append("")

        for purpose, count in self.travel_purpose_distribution().items():
            lines.append(f"{purpose}: {count}")

        lines.append("")

        # --------------------------------------------------------
        # FITNESS
        # --------------------------------------------------------

        lines.append("## Fitness")
        lines.append("")

        for key, value in self.fitness_statistics().items():
            lines.append(f"{key}: {value}")

        lines.append("")

        # --------------------------------------------------------
        # STRESS RESILIENCE
        # --------------------------------------------------------

        lines.append("## Stress Resilience")
        lines.append("")

        for key, value in self.stress_resilience_statistics().items():
            lines.append(f"{key}: {value}")

        lines.append("")

        # --------------------------------------------------------
        # DISTRACTION
        # --------------------------------------------------------

        lines.append("## Distraction")
        lines.append("")

        for key, value in self.distraction_statistics().items():
            lines.append(f"{key}: {value}")

        lines.append("")

        # --------------------------------------------------------
        # TRAVEL EXPERIENCE
        # --------------------------------------------------------

        lines.append("## Travel Experience")
        lines.append("")

        for key, value in self.travel_experience_statistics().items():
            lines.append(f"{key}: {value}")

        lines.append("")

        # --------------------------------------------------------
        # EXPERIENCE BY AGE
        # --------------------------------------------------------

        lines.append("## Experience by Age")
        lines.append("")

        for group, value in self.experience_by_age().items():
            lines.append(f"{group}: {value}")

        lines.append("")

        # --------------------------------------------------------
        # EXPERIENCE BY PURPOSE
        # --------------------------------------------------------

        lines.append("## Experience by Purpose")
        lines.append("")

        for purpose, value in self.experience_by_purpose().items():
            lines.append(f"{purpose}: {value}")

        lines.append("")

        # --------------------------------------------------------
        # ARRIVAL MARGIN
        # --------------------------------------------------------

        lines.append("## Arrival Margin")
        lines.append("")

        for key, value in self.arrival_margin_statistics().items():
            lines.append(f"{key}: {value}")

        lines.append("")

        # --------------------------------------------------------
        # WALKING SPEED
        # --------------------------------------------------------

        lines.append("## Walking Speed")
        lines.append("")

        for key, value in self.walking_speed_statistics().items():
            lines.append(f"{key}: {value}")

        lines.append("")

        # --------------------------------------------------------
        # WALKING SPEED BY AGE
        # --------------------------------------------------------

        lines.append("## Walking Speed by Age")
        lines.append("")

        for group, value in self.walking_speed_by_age().items():
            lines.append(f"{group}: {value} m/s")

        lines.append("")

        # --------------------------------------------------------
        # WALKING SPEED BY FITNESS
        # --------------------------------------------------------

        lines.append("## Walking Speed by Fitness")
        lines.append("")

        for group, value in self.walking_speed_by_fitness().items():
            lines.append(f"{group}: {value} m/s")

        lines.append("")

        # --------------------------------------------------------
        # ONLINE CHECK-IN
        # --------------------------------------------------------

        lines.append("## Online Check-in")
        lines.append("")

        for key, value in self.online_checkin_statistics().items():
            lines.append(f"{key}: {value}")

        lines.append("")

        # --------------------------------------------------------
        # BAGGAGE
        # --------------------------------------------------------

        lines.append("## Baggage")
        lines.append("")

        for key, value in self.baggage_statistics().items():
            lines.append(f"{key}: {value}")

        lines.append("")

        # --------------------------------------------------------
        # LOYALTY
        # --------------------------------------------------------

        lines.append("## Loyalty")
        lines.append("")

        for loyalty, count in self.loyalty_distribution().items():
            lines.append(f"{loyalty}: {count}")

        lines.append("")

        # --------------------------------------------------------
        # LOYALTY BY EXPERIENCE
        # --------------------------------------------------------

        lines.append("## Loyalty by Experience")
        lines.append("")

        for experience, values in self.loyalty_by_experience().items():
            lines.append(f"{experience}: {values}")

        lines.append("")

        # --------------------------------------------------------
        # BEHAVIOR BY PURPOSE
        # --------------------------------------------------------

        lines.append("## Behavior by Travel Purpose")
        lines.append("")

        for purpose, values in self.behavior_by_purpose().items():
            lines.append(purpose)

            for metric, value in values.items():
                lines.append(f"  {metric}: {value}")

            lines.append("")

        # --------------------------------------------------------
        # CORRELATIONS
        # --------------------------------------------------------

        lines.append("## Trait Correlations")
        lines.append("")

        for name, value in self.trait_correlations().items():
            lines.append(f"{name}: {value:.3f}")

        lines.append("")

        return "\n".join(lines)
