from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent.parent


if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.world.passenger import Passenger
from src.world.enums import Gender


# ==== Nuestro primer pasajero ======

# Nombre: Juan
# Apellido: Maldacena
# Nacimiento: 10/09/1968

pasajero_0 = Passenger(
    first_name="Juan",
    last_name="Maldacena",
    birth_date=date(1968, 9, 10),
    gender=Gender.MALE,
    nationality="Argentina",
    document_type="Dni",
    document_number="19324548",
    email="juanmartinmaldacena@gmail.com",
    phone="+549221328901",
)
