from ..loaders.airport_layout_loader import load_airport_layouts


def main():
    layouts = load_airport_layouts()

    print(f"Airports loaded: {len(layouts)}")

    for code, layout in layouts.items():
        print(
            f"{code}: "
            f"{layout.width}x{layout.height} | "
            f"locations={len(layout.locations)}"
        )


if __name__ == "__main__":
    main()
