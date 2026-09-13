# Torneos de Golf

Agregador de torneos de golf en España. Dada una comunidad autónoma y el perfil de un jugador
(fecha de nacimiento + hándicap), devuelve el calendario de torneos en los que **ese jugador
concreto** puede inscribirse. Alcance inicial: categorías juveniles. Uso personal y familiar.

**Estado:** Fase 1 en curso. Madrid operativa con historial de cambios (`python -m sources.madrid`
→ 105 torneos juveniles de 2026). `normalize/` tiene ya las categorías y el veredicto de
elegibilidad. Pendientes: extracción de reglas de las normativas PDF, la RFEG, y el frontend.

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Recolección | Python 3.9.6 + `.venv` en el proyecto |
| Automatización | GitHub Actions (cron diario) |
| Almacenamiento | JSON plano en el repo (`data/torneos.json`) |
| Frontend | HTML single-file, sin build step |
| Hosting | GitHub Pages |

Sin servidor y sin base de datos: el scraper escribe un JSON al repo y el frontend lo lee.

---

## Estructura

- `sources/` — un módulo por fuente. `base.py` define el dataclass `Torneo` y la interfaz común
- `normalize/` — categorías por edad, elegibilidad y deduplicación
- `data/` — salida del scraper (`torneos.json`)
- `web/` — frontend single-file
- `tests/` — pytest
- `agent_docs/` — documentación de trabajo
- `FUENTES.md` — **auditoría de fuentes: esquemas de URL, códigos por sitio y restricciones legales**

---

## Comandos

```bash
source .venv/bin/activate
pip install -r requirements.txt
python -m sources.madrid        # recolecta y escribe data/torneos.json
pytest tests/
python -m http.server 8000      # servir web/ en local
```

---

## Convenciones críticas

**Un esquema, un módulo por fuente.** Las fuentes comparten el *vocabulario* de filtros pero no el
transporte: Madrid sirve **JSON** por `POST /ajax/competiciones`, la RFEG es **HTML** renderizado en
servidor (no tiene ese endpoint: 404). Lo común es el dataclass `Torneo` de `sources/base.py`, no el
código de extracción. Los **códigos internos difieren** (Juvenil es `committe=17` en la RFEG y
`comite=9` en Madrid; los meses son `0-11` en una y `01-12` en la otra) y **no se adivinan**: se leen
del `<select>` de cada sitio y viven como configuración, nunca hardcodeados en la lógica.

**`categorias[]` es el conjunto de categorías ADMITIDAS por el torneo**, no la categoría del jugador.

**Las categorías NO anidan todas hacia abajo.** Alevín (11-12) e Infantil (13-14) son bandas
**cerradas**; Benjamín ("10 o menos") y los Sub-N ("X o menos") son abiertas hacia abajo. Un jugador
de 12 años sí puede jugar un Sub-18, pero **no** un Infantil. Ver `normalize/categorias.py`.

**La edad va por año natural**: `edad = año_temporada - año_nacimiento`. Fuente: *Normativa Circuito
Juvenil 2026* (Circular 2/2026 RFGM) — "cumplan 11 o 12 años en el año en curso".

**El hándicap es un RANGO, no un techo.** Fun&Golf exige un mínimo de 36,1 y Access Series de 7:
hay torneos donde a un buen jugador lo excluyen por arriba de bueno. De ahí `hcp_min` y `hcp_max`.

La elegibilidad es `edad_jugador ∈ franja(categoría_admitida)` **Y** `hcp_min ≤ hcp ≤ hcp_max`, y
tiene **tres** resultados: sí, no y **no se sabe**. Un "no se sabe" nunca es un sí.

**Nunca publicar un JSON vacío.** Si un scraper falla, el job falla ruidosamente y el calendario
anterior se queda en pie. Un agregador que un día enseña "no hay torneos" por un fallo de parser es
peor que no tener app.

**Nunca borrar en silencio.** El calendario es volátil: los torneos cambian de fecha y se retiran a
mitad de temporada. Un torneo que desaparece de la fuente se marca `en_fuente: false` con su
`visto_por_ultima_vez`, no se elimina. Y lo que se mueve queda en `cambios[]` — el historial es lo
único que no se puede reconstruir a posteriori.

**Siempre enlazar a la fuente oficial.** La app es un agregador, no la fuente de verdad. Cada torneo
lleva su `url_inscripcion`. El perjuicio de un error es una inscripción perdida.

**Scraping educado.** Una pasada al día por fuente, User-Agent identificable, respetar `robots.txt`.
Nunca peticiones a la fuente en cada visita de usuario.

---

## Gotchas conocidos

- **NextCaddy está vetada al rastreo.** Su `robots.txt` prohíbe `/tour/*/` y `/rest/*`, justo lo que
  haría falta. Se usa **solo como enlace de salida** para que el usuario se inscriba. No scrapear.
- **Los límites de hándicap y las categorías admitidas viven en las normativas PDF**, una por
  circuito, enlazadas desde `/circuito/{id}`. No están en el HTML ni en el JSON de ninguna fuente.
  Se extraen una vez por temporada a configuración revisada, no en cada pasada del scraper.
- **La fecha de referencia de la edad está RESUELTA**: año natural (ver *Convenciones críticas*).
  Ojo con el alcance — es la normativa de Madrid; confirmar el reglamento nacional antes de
  aplicarla a la RFEG.
- **Las fuentes publican registros imposibles.** Hay un torneo en el calendario de Madrid cuya
  inscripción cierra una semana antes de abrirse. `sources.base.validar()` los marca en `avisos[]`;
  no se corrigen a ciegas.
- **El emparejamiento difuso de nombres no sirve** para cruzar torneos con circulares: probado sobre
  los 12 torneos sin circuito, 2 de los 4 "aciertos" eran falsos. Falla inventándose
  correspondencias con aspecto de correctas.
- **El HTML de la familia RFEG trae texto de relleno en producción** (`contenidossss de dentro`).
  Anclar el parser a etiquetas del bloque, nunca a posiciones.
- **La RFEG ignora `size` y `page`**: devuelve siempre 9 resultados por consulta.
- **Madrid ignora los parámetros de la URL** (`?year=&committe=`): son decorativos, el filtrado real
  va por `POST /ajax/competiciones` con los nombres `anio`/`mes`/`comite`/`circuito`. También ignora
  `limit`: una petición trae el año entero, sin paginación.
- **El JSON de Madrid no trae categorías ni sexo.** Solo están en el texto del nombre del torneo y en
  el circuito. Inferirlos es trabajo de `normalize/`; el scraper deja `categorias=[]` a propósito.

---

## Privacidad y alcance

Uso personal: sin cuentas, sin login, sin datos de terceros. Los perfiles de jugador viven en
`localStorage` del navegador, nunca en el repo. No hardcodear Madrid ni datos personales en el
código — la arquitectura es multi-comunidad desde la primera línea.
