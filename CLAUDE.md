# Torneos de Golf

Agregador de torneos de golf en España. Dada una comunidad autónoma y el perfil de un jugador
(fecha de nacimiento + hándicap), devuelve el calendario de torneos en los que **ese jugador
concreto** puede inscribirse. Alcance inicial: categorías juveniles. Uso personal y familiar.

**Estado:** Fase 1 en curso. Fuente de Madrid operativa (`python -m sources.madrid` → 105 torneos
juveniles de 2026). Pendientes: RFEG y `normalize/`.

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
Las categorías anidan hacia abajo: un torneo que admite `Sub-18, Cadete, Infantil, Alevín` acepta a
todos ellos. La elegibilidad es `categoría_jugador ∈ categorías_torneo` **Y** `hcp_jugador ≤ hcp_max`.

**Nunca publicar un JSON vacío.** Si un scraper falla, el job falla ruidosamente y el calendario
anterior se queda en pie. Un agregador que un día enseña "no hay torneos" por un fallo de parser es
peor que no tener app.

**Siempre enlazar a la fuente oficial.** La app es un agregador, no la fuente de verdad. Cada torneo
lleva su `url_inscripcion`. El perjuicio de un error es una inscripción perdida.

**Scraping educado.** Una pasada al día por fuente, User-Agent identificable, respetar `robots.txt`.
Nunca peticiones a la fuente en cada visita de usuario.

---

## Gotchas conocidos

- **NextCaddy está vetada al rastreo.** Su `robots.txt` prohíbe `/tour/*/` y `/rest/*`, justo lo que
  haría falta. Se usa **solo como enlace de salida** para que el usuario se inscriba. No scrapear.
- **`hcp_max` no está en el HTML de ninguna fuente.** Vive en circulares PDF. En v1 va a `null`, y la
  app no debe afirmar elegibilidad basándose solo en la edad.
- **La fecha de referencia de la edad está sin resolver.** La normativa RFEG dice "15 y 16 años", no
  "año de nacimiento". Falta determinar si se computa a 31 de diciembre, en la fecha del torneo o por
  año natural. **Bloquea `normalize/categorias.py`** — resolver con el reglamento oficial antes de
  escribirlo, no inventarlo.
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
