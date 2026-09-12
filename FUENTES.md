# Auditoría de fuentes — torneos de golf juvenil

**Fecha:** 12 septiembre 2026
**Fase:** 0 (auditoría). No se ha escrito código de aplicación.

---

## Resumen ejecutivo

La hipótesis de partida del plan era: *empezar por una fuente nacional (RFEG) que cubra toda España*. **La auditoría la desmiente en parte.**

- La RFEG publica **solo 9 competiciones juveniles en todo 2026**, todas de "alto nivel" (puntuables nacionales y zonales). Es el circuito de élite, no el suministro ordinario de torneos.
- El volumen real de torneos donde pueden jugar los niños está en las **federaciones autonómicas**. El calendario de Madrid lista decenas: *Torneo Sub16 Masculino "Retamares"*, *Torneo Infantil Masculino "Illescas"*, *Final Circuito Alevín y Benjamín de P&P*…
- **Buena noticia:** `fedgolfmadrid.com` y `rfegolf.es` corren la **misma familia de plataforma** (mismo esquema de URLs y de filtros, distintos códigos internos). Un solo parser con un diccionario de configuración por sitio puede cubrir ambas — y probablemente más federaciones.
- **Mala noticia:** NextCaddy, que es el motor de inscripciones de las federaciones, **prohíbe el rastreo de sus páginas de torneo en `robots.txt`**. Queda descartada como fuente. Se usará solo como *enlace de salida*.

**Recomendación:** invertir el orden. La unidad de cobertura no es el organismo nacional, es la **federación autonómica**. Construir un parser de la "familia RFEG", validarlo contra Madrid (alto volumen, es tu comunidad) y la RFEG (cobertura nacional de élite), y medir cuántas de las 19 federaciones usan esa misma plataforma antes de decidir el resto.

---

## Ficha por fuente

### 1. RFEG — `rfegolf.es/competiciones` ✅ USABLE (volumen bajo)

| Aspecto | Hallazgo |
|---|---|
| Formato | **HTML renderizado en servidor.** No hay XHR a la API; el contenido viene en el HTML |
| Autenticación | **No requiere** |
| `robots.txt` | Solo `Disallow: /*.aspx$`. `/competiciones` **permitido** |
| Volumen juvenil 2026 | **9 competiciones en todo el año** |
| Nivel | Todas "COMPETICIONES DE ALTO NIVEL" |

**Esquema de URL descifrado:**

```
https://rfegolf.es/competiciones?year=2026&month=-1&size=9&page=1&view=card&committe=17&entity-type=rfeg
```

| Parámetro | Valores | Notas |
|---|---|---|
| `year` | 2000–2027 | |
| `month` | `-1` (todo el año), `0`–`11` | **Cero-indexado**: `0`=Enero |
| `committe` | `15` Masc, `16` Fem, **`17` Juvenil**, `18` Prof, `19` P&P, `20` Adaptado | Escrito así, con esa errata |
| `size` / `page` | — | **Ignorados**: `size=100` y `page=2` devuelven los mismos 9 resultados |
| `entity-type` | `rfeg` | No se han encontrado otros valores válidos |
| estado | `Playing`, `Finished`, `RegistrationsOpen`, `Soon` | |

**La ficha de competición es rica.** `/competicion/{slug}.html?id={id}` contiene un bloque «Información Torneo»:

```
Inscripciones: 16/07/2026 - 17/08/2026     ← ventana y FECHA LÍMITE
Fecha de juego: 02/09/2026 - 05/09/2026
Nº Jugadores: 120
Estilo de Juego: Stroke Play
Modo de Juego: Individual
Categoría de Edad: Sub-18, Junior, Cadete, Infantil, Alevín
Sexo: Masculino
```

Más dirección completa del club: `TOMARES, SEVILLA, ANDALUCÍA, España` → **la comunidad autónoma es derivable**.

**Lo que NO está:** el **hándicap máximo**. Vive dentro de las circulares en PDF enlazadas. Ver *Riesgos*.

**Aviso de parser:** el HTML contiene texto de relleno repetido (`contenidossss de dentro`). Markup descuidado — el parser debe anclarse a etiquetas del bloque, no a posiciones.

---

### 2. Federación de Golf de Madrid — `fedgolfmadrid.com/competiciones` ✅ USABLE (alto volumen) ⭐

**La fuente más valiosa encontrada.**

| Aspecto | Hallazgo |
|---|---|
| Formato | HTML renderizado en servidor, **misma familia de plataforma que rfegolf.es** |
| `robots.txt` | **404 — no existe.** Sin restricciones declaradas |
| Volumen | Decenas de torneos por temporada, del tipo exacto que se busca |
| Inscripción | Enlaza a `nextcaddy.com/tour/{id}/inscripcion` |

**Misma arquitectura de filtros, códigos distintos:**

| | RFEG | Madrid |
|---|---|---|
| Juvenil | `committe=17` | `committe=9` |
| Meses | `-1`, `0`–`11` | vacío, `01`–`12` |
| Circuitos | no existe | **sí** — selector propio |

El selector de **Circuitos** de Madrid es una capa que la RFEG no tiene: *Circuito Access Series*, *Circuito 5ª Categoría de 9 Hoyos*, *Circuito Fun&Golf*, *Circuito Amateur*, *Circuito Senior Masculino*. Aquí es donde vive el golf de base.

**Conclusión de diseño:** un parser, un diccionario de config por sitio. No 17 scrapers a medida.

---

### 3. NextCaddy — `nextcaddy.com` ❌ DESCARTADA COMO FUENTE

**`robots.txt` prohíbe explícitamente lo que necesitaríamos:**

```
User-agent: *
Disallow: /tour/*/          ← las páginas de torneo
Disallow: /rest/*           ← su API
Disallow: /rest-mobile/*
Disallow: /ajax/*
```

Rastrear `/tour/*` de forma automatizada iría contra su `robots.txt` declarado. **No se hará.**

**Uso permitido:** pasar su URL como `url_inscripcion` para que el usuario la abra. La app no necesita los internos de NextCaddy — necesita decir "este torneo existe, apúntate aquí". Enlazar no es rastrear.

*(La ficha técnica se consultó una vez, manualmente, para esta auditoría: contiene plazas disponibles, lista de espera, categoría y tarifa. Operado por GREEN SLOPE SL para la federación.)*

---

### 4. Federación Cántabra — `federacioncantabradegolf.com` ✅ USABLE (plataforma distinta)

| Aspecto | Hallazgo |
|---|---|
| Plataforma | **WordPress** — NO es la familia RFEG |
| `robots.txt` | Solo bloquea `/wp-admin/` y uploads de WooCommerce. Competiciones **permitidas** |
| Sitemap | `https://federacioncantabradegolf.com/wp-sitemap.xml` ✅ |
| Rutas | `/competiciones/`, `/competiciones-abiertas/` |

⚠️ Existen **dos dominios** (`.com` y `.es`). Determinar cuál es el canónico antes de escribir nada.

Es el caso de control: confirma que **no todas las federaciones comparten plataforma**. Para las WordPress, el extractor con LLM previsto en el plan es la vía razonable.

---

### 5. Las 19 federaciones — censo pendiente ⏳

Todas tienen ficha en rfegolf.es con id propio, pero **la ficha es solo una tarjeta de contacto: no contiene calendario**. Los calendarios viven en las webs propias.

```
Madrid 989 · Cantabria 980 · Andalucía 985 · Catalana 987 · Canaria 990
Gallega 992 · Valenciana 994 · Vasca 998 · Aragonesa 978 · Asturiana 979
Balear 986 · Cast-León 982 · Cast-La Mancha 983 · Extremeña 984
Melillense 995 · Murciana 996 · Navarra 981 · Riojana 997 · Ceuta 988
```

**Solo se han auditado 2 de 19** (Madrid, Cantabria). El censo de plataformas es el trabajo que queda de Fase 0, y es el que determina el esfuerzo total: si 10 federaciones corren la familia RFEG, el proyecto es corto; si son 3, hay que apoyarse mucho en el extractor LLM.

---

### 6. Golf Directo — no auditada ⏳

Pendiente. Prioridad baja: cubre torneos sociales de club, no juveniles federados.

---

## Categorías por edad — normativa oficial

Del Comité Juvenil de la RFEG (`rfegolf.es/comite/juvenil?type=17`), cita literal:

> "CADETE: 15 y 16 años · INFANTIL: 13 y 14 años · ALEVÍN: 11 y 12 años · BENJAMIN: …, 7, 8, 9 y 10 años"

También: el hándicap máximo asignable en cualquier categoría es **54.0**, y el jugador **conserva su hándicap** al cambiar de categoría.

### ⚠️ Dos cuestiones abiertas, que NO deben inventarse

1. **Fecha de referencia de la edad.** La normativa dice "años", no "año de nacimiento". Falta determinar si la edad se computa a 31 de diciembre de la temporada, en la fecha del torneo, o por año natural de nacimiento. **Es la diferencia entre que un niño entre o no en una categoría.** Fuente a consultar: *Reglamento Ranking Nacional Juvenil 2026*.

2. **Las categorías anidan hacia abajo.** Un torneo que admite `Sub-18, Junior, Cadete, Infantil, Alevín` acepta a todos esos. Es decir, **`categorias[]` es el conjunto de categorías admitidas**, y un jugador menor puede jugar por encima de su categoría. La elegibilidad es:

   ```
   categoría_del_jugador ∈ categorías_admitidas_del_torneo   Y   hcp_jugador ≤ hcp_max
   ```

   Esto valida el diseño del esquema: `categorias` como lista, no como valor único.

---

## Impacto sobre el plan

| Supuesto del plan | Veredicto |
|---|---|
| "Empezar por fuente nacional que cubra toda España" | ⚠️ **Parcialmente falso.** La RFEG da geografía pero solo 9 eventos/año |
| "NextCaddy como fuente" | ❌ **Descartada.** `robots.txt` lo prohíbe. Solo enlace de salida |
| "17 scrapers frágiles" | ✅ **Mejor de lo temido.** Al menos RFEG y Madrid comparten plataforma |
| "El esquema soporta absoluto y sénior" | ✅ **Confirmado.** Madrid ya publica circuitos Senior y Amateur |
| "hcp_max disponible" | ❌ **No en HTML.** Vive en circulares PDF → `null` en v1 |

### Cambio propuesto para la Fase 1

Que la primera fuente **no sea la RFEG, sino Madrid** — alto volumen, es tu comunidad, y permite validar de verdad la utilidad de la app. La RFEG entra inmediatamente después reutilizando el mismo parser con otra config, y aporta la cobertura nacional de élite.

Esto **no rompe la estrategia horizontal**: el parser nace multi-sitio desde la primera línea, con la config como dato, no como código.

---

## Riesgos registrados

1. **`hcp_max` no disponible en v1.** Está en PDFs. La app debe mostrarlo como "consultar en la circular" y **nunca** afirmar que un jugador es elegible basándose solo en la edad. Se mitiga enlazando siempre a la fuente.
2. **Fecha de referencia de edad sin confirmar.** Bloquea la Fase 2. Hay que resolverlo con el reglamento oficial antes de escribir `categorias.py`.
3. **Códigos de comité distintos por federación.** No se pueden adivinar: hay que leerlos del `<select>` de cada sitio. Conviene un comando que los extraiga y los vuelque a la config.
4. **Markup descuidado en la familia RFEG.** Texto de relleno en producción. Parser por anclas, y test de humo que falle si una fuente devuelve cero torneos.
