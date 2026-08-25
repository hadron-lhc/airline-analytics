world = generate_world(
    n_airports=12,
    n_flights=10,
    n_passengers=2000,
)

result = run_simulation(world)

result.save_events("data/output/simulation.json")
