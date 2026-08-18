from ..loaders.airport_layout_loader import load_airport_layout


def main():
    layout = load_airport_layout("LAX")

    entrance = layout.get_location("entrance")
    check_in = layout.get_location("check_in")
    security = layout.get_location("security")
    gate = layout.get_location("gate_C1")

    print(f"Airport: {layout.airport_code}")
    print()

    print(
        f"Entrance → Check-in: {entrance.position.distance_to(check_in.position):.1f} m"
    )

    print(
        f"Check-in → Security: {check_in.position.distance_to(security.position):.1f} m"
    )

    print(f"Security → Gate C1: {security.position.distance_to(gate.position):.1f} m")


if __name__ == "__main__":
    main()
