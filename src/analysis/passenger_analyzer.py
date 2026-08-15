from ..world.passenger import Passenger


class PassengerAnalyzer:
    """
    Analiza el perfil y comportamiento potencial
    de un pasajero individual.
    """

    def __init__(self, passenger: Passenger):
        self.passenger = passenger

    def profile(self) -> dict:
        p = self.passenger

        return {
            "passenger_id": str(p.passenger_id),
            "name": f"{p.first_name} {p.last_name}",
            "age": p.age,
            "gender": p.gender.value,
            "nationality": p.nationality,
            "travel_purpose": p.travel_purpose.value,
            "loyalty": p.loyalty_level.value,
            "travel_experience": p.traits.travel_experience,
            "fitness": round(p.traits.fitness, 3),
            "stress_resilience": round(
                p.traits.stress_resilience,
                3,
            ),
            "distraction_proneness": round(
                p.traits.distraction_proneness,
                3,
            ),
            "arrival_margin": p.arrival_margin,
            "walking_speed": p.walking_speed,
            "online_checkin_probability": round(
                p.online_checkin_probability,
                3,
            ),
            "baggage_probability": round(
                p.baggage_probability,
                3,
            ),
        }

    def risk_profile(self) -> dict:
        """
        Estima factores que podrían provocar problemas
        durante el viaje.

        No es todavía un modelo predictivo.
        """

        p = self.passenger

        return {
            "late_arrival_risk": self._late_arrival_risk(),
            "missed_boarding_risk": self._missed_boarding_risk(),
            "checkin_delay_risk": self._checkin_delay_risk(),
        }

    def _late_arrival_risk(self) -> str:
        p = self.passenger

        score = 0.0

        if p.arrival_margin < 90:
            score += 0.5

        if p.traits.distraction_proneness > 0.7:
            score += 0.2

        if p.traits.travel_experience < 3:
            score += 0.15

        if p.traits.stress_resilience < 0.3:
            score += 0.15

        return self._risk_label(score)

    def _missed_boarding_risk(self) -> str:
        p = self.passenger

        score = 0.0

        if p.arrival_margin < 90:
            score += 0.3

        if p.traits.distraction_proneness > 0.7:
            score += 0.3

        if p.walking_speed < 1.0:
            score += 0.2

        if p.traits.travel_experience < 3:
            score += 0.1

        return self._risk_label(score)

    def _checkin_delay_risk(self) -> str:
        p = self.passenger

        score = 0.0

        if p.online_checkin_probability < 0.4:
            score += 0.4

        if p.traits.distraction_proneness > 0.7:
            score += 0.3

        if p.traits.travel_experience < 3:
            score += 0.2

        return self._risk_label(score)

    @staticmethod
    def _risk_label(score: float) -> str:
        if score >= 0.7:
            return "high"

        if score >= 0.4:
            return "medium"

        return "low"
