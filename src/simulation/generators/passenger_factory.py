from ...world.passenger import Passenger
from ...world.passenger_traits import PassengerTraits
from ...enums.world_enums import (
    Gender,
    DocumentType,
    TravelPurpose,
)
from .passenger_helpers.traits import (
    generate_fitness,
    generate_travel_experience,
    generate_stress_resilience,
)
from .passenger_helpers.distributions import generate_distraction
from .passenger_helpers.derived_behavior import (
    generate_arrival_margin,
    generate_walking_speed,
    generate_online_checkin_probability,
    generate_baggage_probability,
    generate_loyalty_level,
)
import json
import random
import os
import unicodedata
from faker import Faker

from datetime import date


"""
Datos básicos de cada Passenger:

    first_name= str,
    last_name= str,
    birth_date = date,
    gender = Gender,
    nationality = str,
    document_type = DocumentType,
    document_number = str,
    email = str,
    phone= str,

"""


def load_configuration(file_name="config.json"):
    """Loads configuration data using an absolute path to avoid directory errors."""
    # Obtiene la ruta absoluta de la carpeta donde está este script ejecutable
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, file_name)

    with open(file_path, "r", encoding="utf-8") as file:
        config = json.load(file)
    return config["countries_config"]


COUNTRIES_DATA = load_configuration()
countries = list(COUNTRIES_DATA.keys())
weights = [info["weight"] for info in COUNTRIES_DATA.values()]

DOC_TYPE_MAP = {
    "Passport": "Passport",
    "ID Card": "Id_card",
    "DNI": "Dni",
    "INE": "Ine",
    "Aadhaar": "Aadhaar",
    "RG": "Rg",
    "Cédula": "Cédula",
}

# Inicializar Faker para cada región
fakers = {
    info["faker_locale"]: Faker(info["faker_locale"])
    for info in COUNTRIES_DATA.values()
}


def limpiar_texto(texto):
    """Elimina acentos y caracteres especiales para crear emails limpios."""
    texto_normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(
        [c for c in texto_normalizado if not unicodedata.combining(c)]
    ).lower()


def generate_travel_purpose() -> TravelPurpose:
    return random.choices(
        population=[
            TravelPurpose.BUSINESS,
            TravelPurpose.LEISURE,
            TravelPurpose.FAMILY,
            TravelPurpose.VISITING,
        ],
        weights=[
            0.20,
            0.40,
            0.20,
            0.20,
        ],
        k=1,
    )[0]


def create_random_passenger() -> Passenger:
    # Identity
    selected_country = random.choices(
        countries,
        weights=weights,
        k=1,
    )[0]

    config = COUNTRIES_DATA[selected_country]
    local_faker = fakers[config["faker_locale"]]

    gender = random.choice([Gender.MALE, Gender.FEMALE])

    if gender == Gender.MALE:
        first_name = local_faker.first_name_male()
        last_name = local_faker.last_name_male()
    else:
        first_name = local_faker.first_name_female()
        last_name = local_faker.last_name_female()

    birth_date = local_faker.date_of_birth(
        minimum_age=18,
        maximum_age=85,
    )

    age = (date.today() - birth_date).days // 365

    travel_purpose = generate_travel_purpose()

    travel_experience = generate_travel_experience(
        age,
        travel_purpose,
    )

    # Stable traits

    fitness = generate_fitness(age)

    experience = generate_travel_experience(
        age,
        travel_purpose,
    )

    stress_resilience = generate_stress_resilience(
        age,
        fitness,
        experience,
    )

    distraction = generate_distraction(
        travel_purpose,
        experience,
    )

    traits = PassengerTraits(
        fitness=fitness,
        stress_resilience=stress_resilience,
        distraction_proneness=distraction,
        travel_experience=experience,
    )

    # Derived behavior

    arrival_margin = generate_arrival_margin(
        travel_purpose,
        experience,
        distraction,
        stress_resilience,
    )

    walking_speed = generate_walking_speed(
        age,
        fitness,
        experience,
        distraction,
    )

    online_checkin_probability = generate_online_checkin_probability(
        travel_purpose,
        experience,
        distraction,
    )

    baggage_probability = generate_baggage_probability(
        travel_purpose,
        distraction,
    )

    # Identity details

    str_fecha = birth_date.strftime("%Y%m%d")
    random_digits = random.randint(1000, 9999)

    nombre_limpio = limpiar_texto(first_name)
    apellido_limpio = limpiar_texto(last_name).replace(" ", "")

    domain = random.choice(["gmail.com", "yahoo.com", "outlook.com"])

    email = f"{nombre_limpio}.{apellido_limpio}{random.randint(10, 99)}@{domain}"

    num_local = "".join(str(random.randint(0, 9)) for _ in range(8))

    phone_number = f"{config['phone_prefix']} {num_local}"

    loyalty_level = generate_loyalty_level(travel_experience, travel_purpose)

    return Passenger(
        first_name=first_name,
        last_name=last_name,
        birth_date=birth_date,
        gender=gender,
        nationality=selected_country,
        document_type=DocumentType(DOC_TYPE_MAP[config["doc_type"]]),
        document_number=int(f"{str_fecha}{random_digits}"),
        email=email,
        phone=phone_number,
        travel_purpose=travel_purpose,
        traits=traits,
        loyalty_level=loyalty_level,
        online_checkin_probability=(online_checkin_probability),
        baggage_probability=baggage_probability,
        arrival_margin=arrival_margin,
        walking_speed=walking_speed,
    )


def generate_passengers(n):
    list = []
    for i in range(n):
        list.append(create_random_passenger())

    return list


def main():
    # crear 10 pasajeros de prueba y visualizar sus estadisticas y guardarlo en un .txt

    passengers = generate_passengers(10)

    file_name = "passenger_data.txt"
    with open(file_name, "w", encoding="utf-8") as f:
        for passenger in passengers:
            f.write(f"Passenger: {passenger.first_name} {passenger.last_name}\n")
            f.write(f"  Age: {(date.today() - passenger.birth_date).days // 365}\n")
            f.write(f"  Travel Purpose: {passenger.travel_purpose.value}\n")
            f.write(f"  Fitness: {passenger.traits.fitness:.2f}\n")
            f.write(f"  Stress Resilience: {passenger.traits.stress_resilience:.2f}\n")
            f.write(
                f"  Distraction Proneness: {passenger.traits.distraction_proneness:.2f}\n"
            )
            f.write(f"  Travel Experience: {passenger.traits.travel_experience}\n")
            f.write(f"  Arrival Margin: {passenger.arrival_margin} minutes\n")
            f.write(f"  Walking Speed: {passenger.walking_speed} m/s\n")
            f.write(
                f"  Online Check-in Probability: {passenger.online_checkin_probability:.2f}\n"
            )
            f.write(f"  Baggage Probability: {passenger.baggage_probability:.2f}\n")

    print(f"Passenger data saved to {file_name}")


if __name__ == "__main__":
    main()
