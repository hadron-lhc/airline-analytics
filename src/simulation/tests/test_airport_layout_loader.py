import json

import pytest

import src.loaders.airport_layout_loader as airport_layout_loader
from src.loaders.airport_layout_loader import (
    load_airport_layout,
    load_airport_layouts,
)

VALID_LAYOUT = {
    "airport_code": "TEST",
    "width": 1000,
    "height": 500,
    "locations": {
        "entrance": {"x": 10, "y": 20},
        "check_in": {"x": 30, "y": 20},
        "security": {"x": 50, "y": 20},
        "gate_A1": {"x": 70, "y": 20},
        "exit": {"x": 90, "y": 20},
    },
}


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(airport_layout_loader, "DATA_DIR", tmp_path)
    return tmp_path


def _write(data_dir, code, content):
    data_dir.joinpath(f"{code}.json").write_text(content, encoding="utf-8")


def test_load_valid_layout_parses_positions(data_dir):
    _write(data_dir, "TEST", json.dumps(VALID_LAYOUT))

    layout = load_airport_layout("test")

    assert layout.airport_code == "TEST"
    assert layout.width == 1000
    assert layout.height == 500
    assert layout.locations["entrance"].position.x == 10
    assert layout.locations["gate_A1"].position.y == 20


def test_load_missing_layout_raises_file_not_found(data_dir):
    with pytest.raises(FileNotFoundError):
        load_airport_layout("NOPE")


def test_load_malformed_json_raises_json_error(data_dir):
    _write(data_dir, "BAD", "{ this is not valid json !!!")

    with pytest.raises(json.JSONDecodeError):
        load_airport_layout("BAD")


def test_load_missing_locations_key_raises_key_error(data_dir):
    _write(data_dir, "NOLOC", json.dumps({"airport_code": "NOLOC", "width": 1, "height": 1}))

    with pytest.raises(KeyError):
        load_airport_layout("NOLOC")


def test_load_airport_layouts_loads_every_json(data_dir):
    def layout_for(code):
        data = dict(VALID_LAYOUT)
        data["airport_code"] = code
        return data

    _write(data_dir, "AAA", json.dumps(layout_for("AAA")))
    _write(data_dir, "BBB", json.dumps(layout_for("BBB")))

    layouts = load_airport_layouts()

    assert set(layouts.keys()) == {"AAA", "BBB"}
    assert layouts["AAA"].airport_code == "AAA"
    assert layouts["BBB"].airport_code == "BBB"


def test_load_uppercases_airport_code(data_dir):
    _write(data_dir, "MIA", json.dumps(VALID_LAYOUT))

    # El nombre de archivo se busca en mayúsculas aunque se pida en minúsculas;
    # el airport_code devuelto es el contenido del JSON.
    assert load_airport_layout("mia").airport_code == "TEST"


def test_get_location_missing_raises_value_error(data_dir):
    _write(data_dir, "TEST", json.dumps(VALID_LAYOUT))

    layout = load_airport_layout("TEST")

    with pytest.raises(ValueError, match="not found"):
        layout.get_location("nonexistent_zone")


def test_get_gate_location_resolves_gate_prefix(data_dir):
    _write(data_dir, "TEST", json.dumps(VALID_LAYOUT))

    layout = load_airport_layout("TEST")

    gate = layout.get_gate_location("A1")

    assert gate.code == "gate_A1"
