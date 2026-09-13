# Torneos de Golf

Agregador de torneos de golf en España para padres de jugadores juveniles.

Encontrar los torneos en los que puede jugar un niño es hoy un trabajo manual y disperso: unos
aparecen en la web de la federación autonómica, otros en la de la RFEG, otros solo en la del club.
Y para saber si puede inscribirse hay que cruzar dos cosas — su categoría por edad y el hándicap
máximo del torneo. El dato que más se pierde no es el torneo: es la **fecha límite de inscripción**.

Esta herramienta recoge los calendarios, los normaliza y responde a una única pregunta:

> ¿En qué torneos puede jugar **este** jugador, en **su** comunidad, y hasta cuándo puede apuntarse?

## Estado

Fase 0 completada: auditoría de fuentes. Ver [FUENTES.md](FUENTES.md).

Fase 1 en curso: la **Federación de Golf de Madrid** ya se recoge entera — 105 torneos juveniles de
2026, con su ventana de inscripción. Falta la RFEG y la capa de elegibilidad por edad y hándicap.

```bash
source .venv/bin/activate
python -m sources.madrid      # escribe data/torneos.json
pytest tests/
```

## Alcance

Categorías juveniles (benjamín, alevín, infantil, cadete, sub-16, sub-18) en una primera fase.
El modelo de datos contempla desde el inicio la ampliación a absoluto y sénior.

## Aviso

Es un **agregador no oficial**. Cada torneo enlaza a su fuente oficial, que es la única válida a
efectos de inscripción. Verifica siempre allí antes de contar con una plaza.
