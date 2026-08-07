# Roadmap: hacer que la simulación esté más viva

## 1. Diagnóstico: el estado actual es "ruido", no "personalidad"

Antes de agregar mecánicas, hay que reconocer un problema de base: hoy la
variación de la simulación no proviene de las características de cada pasajero,
sino de ruido aleatorio. Los pasos a corregir:

- Los rasgos del Travel Profile **nunca se generan**. `passenger_factory`
  solo crea la identidad del pasajero; todos los campos de comportamiento quedan
  en el default del dataclass (`loyalty=NONE`, `experience=3`, `speed=1.2`,
  `margin=120`, `online_checkin_probability=0.5`, `baggage_probability=0.5`).
- La variación sale de `np.random` dentro de los `time_models`, no de las
  características del pasajero → ruido no correlacionado.
- `walking_speed` **no se usa en ningún cómputo** (no existe modelo espacial).
- No hay colas reales ni recursos: seguridad y check-in son lognormales por
  pasajero, no dependen de cuánta gente haya en ese momento.
- Los tiempos de viaje se **precalculan** en `passenger_journey.calculate_times`;
  el engine solo reproduce los eventos. Los pasajeros no pueden interactuar ni
  afectarse entre sí.
- No hay demoras, no-shows, conexiones, equipaje real ni motivo de viaje.
  `travel_class` siempre es ECONOMY, `boarding_group` nunca se asigna y
  `preferred_seat` no influye en la asignación de asiento.

El objetivo de este roadmap es invertir esa lógica: que cada pasajero nazca con
un perfil coherente y que ese perfil genere comportamientos complejos y
realistas en su interacción con el mundo.

---

## 2. Fases propuestas

### Fase 0 — Arquetipos y rasgos correlacionados

Es la base de todo. Si no hay perfil de pasajero, ninguna mecánica posterior
produce datos interesantes.

| Mecánica                                              | ¿Qué aporta a la simulación?                                                             | ¿Qué análisis habilita?                                  |
| ----------------------------------------------------- | ---------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| Motivo de viaje (Business / Leisure / Family / Visit) | Define sensibilidad al precio, clase, equipaje, margen de llegada y conexiones           | Cohorte motivo → comportamiento                          |
| Factores latentes (affluence, fitness, routine)       | Derivan rasgos correlacionados sin combos imposibles (ej. no hay abuelo de 85 que corre) | Distribuciones reales de speed / margin / experience     |
| Loyalty derivada de `flight_history`                  | Los pasajeros acumulan viajes y suben de nivel                                           | Relación loyalty ↔ boarding / upgrades                   |
| Generación de rasgos en `passenger_factory`           | Cada pasajero nace con perfil único y coherente                                          | Las distribuciones del analyzer dejan de ser degeneradas |

### Fase 1 — Mundo físico y recursos

| Mecánica                                    | ¿Qué aporta a la simulación?                       | ¿Qué análisis habilita?                        |
| ------------------------------------------- | -------------------------------------------------- | ---------------------------------------------- |
| Layout de terminal (distancias entre zonas) | La velocidad de caminata afecta los tiempos reales | Distribución de tiempos de llegada a la puerta |
| Colas de seguridad/check-in con capacidad   | Congestión real que depende de la hora del día     | Tiempo medio de espera y horas pico            |

### Fase 2 — Motor reactivo

| Mecánica                          | ¿Qué aporta a la simulación?                               | ¿Qué análisis habilita?                               |
| --------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------- |
| Scheduling en cascada por handler | El próximo evento depende del estado del mundo al procesar | Interacciones entre pasajeros visibles en la timeline |
| Embarque por grupos               | Duración según ocupación y clase                           | Puntualidad de boarding por grupo                     |
| Cierre de puerta a `DOORS_CLOSE`  | Los pasajeros tardíos pierden el vuelo                     | Tasa de missed flights                                |

### Fase 3 — Fracasos e irregularidades

| Mecánica                                          | ¿Qué aporta a la simulación?             | ¿Qué análisis habilita?                          |
| ------------------------------------------------- | ---------------------------------------- | ------------------------------------------------ |
| Demoras de vuelo (turnaround, tripulación, clima) | Los horarios reales cambian              | Análisis de puntualidad y propagación de demoras |
| No-shows y pasajeros que pierden el vuelo         | Rebook o pasajeros varados               | Correlación no-show ↔ antelación de compra       |
| Peso de equipaje                                  | Afecta velocidad de caminata y seguridad | Tiempo perdido por equipaje pesado               |

### Fase 4 — Itinerarios y múltiples viajes

| Mecánica                     | ¿Qué aporta a la simulación?                      | ¿Qué análisis habilita?                           |
| ---------------------------- | ------------------------------------------------- | ------------------------------------------------- |
| Conexiones y viajes redondos | Riesgo de perder conexión, sprint por el terminal | Árboles de propagación, tiempo mínimo de conexión |
| Simulación multidía          | Los pasajeros vuelven a volar y acumulan loyalty  | Evolución de clientes en el tiempo                |

### Fase 5 — Micro-comportamientos sociales

| Mecánica                         | ¿Qué aporta a la simulación?                        | ¿Qué análisis habilita?           |
| -------------------------------- | --------------------------------------------------- | --------------------------------- |
| Viajes en grupo / familia        | Rasgos correlacionados; el más lento marca el ritmo | Clusters reales en los datos      |
| Compras / restauración en espera | El margen de llegada se convierte en gasto ancillar | Ingresos ancillares por arquetipo |

### Fase 6 — Entorno

| Mecánica              | ¿Qué aporta a la simulación?                    | ¿Qué análisis habilita?         |
| --------------------- | ----------------------------------------------- | ------------------------------- |
| Hora del día + turnos | Picos business vs leisure, carriles según turno | Heatmaps de congestión por hora |
| Clima por aeropuerto  | Demoras y cancelaciones                         | Operaciones irregulares         |

---

## 3. Prioridad

Orden recomendado de implementación:

1. **Fase 0** — Arquetipos y rasgos correlacionados (la base).
2. **Fase 1** — Mundo físico y recursos.
3. **Fase 2** — Motor reactivo.

Estas tres fases destraban los cinco ítems del roadmap original (velocidad de
caminata, colas en seguridad, retrasos de vuelos, check-in en casa y peso de
equipaje). Las fases 3 a 6 quedan después.

**Nota**: la Fase 2 (motor reactivo) es requisito para que las Fases 3–6 tengan
sentido. Sin scheduling en cascada, las demoras y conexiones no pueden
realimentar el mundo y volverían a ser números precalculados.
