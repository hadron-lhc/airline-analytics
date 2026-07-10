# World Design

## 1. Objetivo

El objetivo de este proyecto es construir un simulador de una aerolínea capaz de generar datos sintéticos consistentes y realistas para su posterior análisis utilizando Python, NumPy, Pandas y PostgreSQL.

La simulación deberá representar el comportamiento de pasajeros, vuelos, aeronaves y aeropuertos a lo largo del tiempo mediante un sistema de eventos discretos.

Los datos generados serán utilizados para:

- Poblar una base de datos PostgreSQL.
- Practicar consultas SQL.
- Realizar análisis exploratorio con Pandas.
- Generar visualizaciones.
- Alimentar una futura animación del funcionamiento del aeropuerto.

---

# 2. Filosofía del simulador

El objetivo principal no es reproducir el funcionamiento exacto de una aerolínea real, sino construir un sistema consistente, coherente y suficientemente realista para realizar análisis de datos.

Cada decisión del simulador debe intentar responder a la pregunta:

> "¿Este comportamiento produciría datos interesantes para analizar?"

Se priorizará:

- simplicidad
- coherencia
- modularidad
- facilidad para extender el sistema

sobre el realismo absoluto.

---

# 3. El mundo

El simulador representa un mundo compuesto por diferentes entidades que existen y evolucionan a lo largo del tiempo.

Cada entidad posee:

- información permanente
- estado actual
- comportamiento

Las entidades interactúan entre sí mediante eventos.

Todos los eventos ocurren sobre una línea temporal común.

La simulación avanza únicamente cuando ocurre un evento.

No existe un avance continuo del tiempo.

---

# 4. Entidades principales

Inicialmente el mundo estará compuesto por las siguientes entidades:

- Passenger
- Flight
- Aircraft
- Airport
- Airline

En futuras versiones podrán incorporarse nuevas entidades como:

- Gates
- Security Checkpoints
- Baggage
- Runways
- Weather
- Crews

---

# 5. Estados

Cada entidad mantiene un estado interno.

Por ejemplo, un pasajero podrá encontrarse en estados como:

- At Home
- Going to Airport
- Check-in
- Security
- Waiting at Gate
- Boarding
- On Flight
- Arrived

Estos estados serán definidos en detalle más adelante.

---

# 6. Eventos

Todo cambio dentro del mundo ocurre mediante eventos.

Ejemplos:

- Passenger enters airport
- Passenger completes check-in
- Boarding starts
- Passenger boards aircraft
- Flight departs
- Flight lands

Los eventos constituyen la fuente principal de información de la simulación.

---

# 7. Tiempo

La simulación utilizará un reloj virtual.

El tiempo no avanzará segundo por segundo.

El motor avanzará directamente al siguiente evento programado.

Este enfoque permitirá simular grandes cantidades de pasajeros de forma eficiente.

---

# 8. Persistencia

Durante la simulación existirán dos tipos de información.

## Estado actual

Representa cómo se encuentra el mundo en un instante determinado.

Ejemplo:

- dónde está un pasajero
- qué avión está asignado a un vuelo
- qué pasajeros ya abordaron

## Historial

Representa todo lo que ocurrió durante la simulación.

Cada cambio de estado generará un evento que podrá almacenarse para análisis o para reproducir posteriormente la simulación.

---

# 9. Objetivos de diseño

El simulador deberá cumplir los siguientes principios:

- Modular.
- Extensible.
- Fácil de mantener.
- Determinista cuando se utilice una semilla aleatoria.
- Capaz de generar datasets grandes.
- Capaz de reproducir una simulación completa mediante su historial de eventos.

---

# 10. Alcance de la primera versión

La primera versión del simulador incluirá únicamente el flujo básico de un pasajero:

Compra del pasaje

↓

Llegada al aeropuerto

↓

Check-in

↓

Control de seguridad

↓

Espera en la puerta

↓

Embarque

↓

Despegue

↓

Vuelo

↓

Aterrizaje

↓

Llegada al destino

Características más complejas como retrasos dinámicos, mantenimiento de aeronaves, meteorología o conexiones entre vuelos quedarán para futuras versiones.
