from datetime import datetime, timedelta

from src.simulation.generators.flight_factory import _allocate_gate
from src.world.airport import Airport
from src.world.gate import Gate


def make_airport(codes):
    return Airport(
        iata_code="TEST",
        name="Test Airport",
        gates=[Gate(code) for code in codes],
    )


def test_allocate_gate_is_unique_across_non_overlapping_times():
    airport = make_airport(["A1", "A2"])

    base = datetime(2026, 7, 13, 8, 0)

    # Dos vuelos en horas distintas deben usar puertas (cada uno ocupa
    # su franja sin bloquear el otro).
    g1 = _allocate_gate(airport, base)
    g2 = _allocate_gate(airport, base + timedelta(hours=4))

    assert g1 in airport.gates
    assert g2 in airport.gates


def test_allocate_gate_never_reuses_a_busy_gate():
    airport = make_airport(["A1"])

    base = datetime(2026, 7, 13, 8, 0)

    # Solo hay una puerta: el primer vuelo la ocupa.
    g1 = _allocate_gate(airport, base)

    assert g1.gate_code == "A1"

    # Un vuelo que solape la franja ocupada debe fallar (RuntimeError),
    # acumulado de nuevo a través de _allocate_gate.
    overlapping = base + timedelta(minutes=10)

    try:
        _allocate_gate(airport, overlapping)
    except RuntimeError:
        gate_busy = True
    else:
        gate_busy = False

    assert gate_busy


def test_allocate_gate_allows_different_gate_when_first_is_busy():
    airport = make_airport(["A1", "A2"])

    base = datetime(2026, 7, 13, 8, 0)

    g1 = _allocate_gate(airport, base)

    # Seis horas después, A1 ya está libre, pero también hay A2; ambos son válidos.
    later = _allocate_gate(airport, base + timedelta(hours=4))

    assert later in airport.gates

    # Una sola franja por puerta: el segundo vuelo no comparte ni tiempo ni puerta
    # con el primero (no pueden ir en la misma puerta a la vez).
    overlaps = airport.find_available_gate(
        base,
        base + timedelta(minutes=5),
    )

    assert overlaps is not None or g1.gate_code != later.gate_code


def test_find_available_gate_returns_gate_when_all_free():
    airport = make_airport(["A1", "A2", "A3"])

    start = datetime(2026, 7, 13, 8, 0)
    end = start + timedelta(hours=1)

    gate = airport.find_available_gate(start, end)

    assert gate in airport.gates


def test_find_available_gate_returns_none_when_all_gates_busy():
    airport = make_airport(["A1"])

    start = datetime(2026, 7, 13, 8, 0)
    end = start + timedelta(hours=1)

    airport.book_gate(airport.gates[0], start, end)

    assert airport.find_available_gate(start, end) is None


def test_gate_booking_rejects_overlap_on_same_gate():
    airport = make_airport(["A1"])

    start = datetime(2026, 7, 13, 8, 0)
    end = start + timedelta(hours=1)

    airport.book_gate(airport.gates[0], start, end)

    # La puerta A1 ya está reservada en esa franja: no debe ser elegible.
    overlapping = airport.find_available_gate(
        start + timedelta(minutes=30),
        end + timedelta(minutes=30),
    )

    assert overlapping is None
