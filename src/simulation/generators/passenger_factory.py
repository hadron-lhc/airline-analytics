from ...world.passenger import Passenger
from ...enums.world_enums import Gender, DocumentType
import json
import random
import os
import unicodedata
from faker import Faker

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


def create_random_passenger() -> Passenger:
    # 1. Selección del país
    selected_country = random.choices(countries, weights=weights, k=1)[0]
    config = COUNTRIES_DATA[selected_country]
    local_faker = fakers[config["faker_locale"]]

    # 2. Género y Nombre
    gender = random.choice(["Male", "Female"])
    if gender == "Male":
        first_name = local_faker.first_name_male()
        last_name = local_faker.last_name_male()
    else:
        first_name = local_faker.first_name_female()
        last_name = local_faker.last_name_female()

    # 3. Edad y Fecha de Nacimiento
    birth_date = local_faker.date_of_birth(minimum_age=18, maximum_age=85)

    # 4. Tipo y Número de Documento (basado en nacimiento y país)
    str_fecha = birth_date.strftime("%Y%m%d")
    random_digits = random.randint(1000, 9999)

    # 5. Email basado en el nombre (limpio de acentos y espacios)
    nombre_limpio = limpiar_texto(first_name)
    apellido_limpio = limpiar_texto(last_name).replace(" ", "")
    domain = random.choice(["gmail.com", "yahoo.com", "outlook.com"])
    email = f"{nombre_limpio}.{apellido_limpio}{random.randint(10, 99)}@{domain}"

    # 6. Teléfono con prefijo del país
    num_local = "".join([str(random.randint(0, 9)) for _ in range(8)])
    phone_number = f"{config['phone_prefix']} {num_local}"

    passenger = Passenger(
        first_name=first_name,
        last_name=last_name,
        birth_date=birth_date,
        gender=Gender.MALE if gender == "Male" else Gender.FEMALE,
        nationality=selected_country,
        document_type=DocumentType(DOC_TYPE_MAP[config["doc_type"]]),
        document_number=int(f"{str_fecha}{random_digits}"),
        email=email,
        phone=phone_number,
    )

    return passenger


def generate_passengers(n):
    list = []
    for i in range(n):
        list.append(create_random_passenger())

    return list


def main():
    pasajeros = generate_passengers(10)
    print(pasajeros)


if __name__ == "__main__":
    main()
