"""Real Federación de Golf de Madrid — fedgolfmadrid.com

La web no hay que rasparla: el calendario se pinta en cliente desde un endpoint
propio que devuelve JSON (`POST /ajax/competiciones`). Pedimos ese JSON directamente.

`robots.txt` del sitio devuelve 404 — no declara restricción alguna (FUENTES.md §2).

Los códigos de comité y circuito NO se adivinan: se leen del `<select>` del sitio y
viven aquí como configuración, separados de la lógica (CLAUDE.md, "un parser, config
por sitio"). Releídos el 13/09/2026.
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import requests

from .base import FuenteVacia, Torneo, escribir_torneos, sesion_http

FUENTE = "madrid"
COMUNIDAD = "Madrid"

ENDPOINT = "https://fedgolfmadrid.com/ajax/competiciones"
REFERER = "https://fedgolfmadrid.com/competiciones"

# Valores del <select data-nombre="comite">. Distintos de los de la RFEG: allí
# Juvenil es 17, aquí es 9. No son intercambiables.
COMITES = {
    "juvenil": "9",
    "profesionales": "11",
    "clubes_sin_campo": "12",
    "pitch_and_putt": "14",
    "golf_adaptado": "15",
    "amateur_femenino": "54",
    "amateur_masculino": "55",
    "alta_competicion": "87",
}

# El sitio enlaza a NextCaddy para inscribirse. Enlazar no es rastrear: su
# robots.txt prohíbe /tour/*, así que solo componemos la URL (FUENTES.md §3).
URL_TORNEO = "https://www.nextcaddy.com/tour/{id}"
URL_AGRUPACION = "https://www.nextcaddy.com/agrupacion/{id}"

# Campo `modo` del JSON. 2 y 3 salen del propio JS del sitio; 1 aparece en los datos
# sin que el JS lo trate, así que no lo interpretamos.
MODOS = {3: "online", 2: "club"}


def recoger(anio: int, comite: str = "juvenil", sesion: Optional[requests.Session] = None) -> List[Torneo]:
    """Devuelve los torneos de un comité para un año completo."""
    sesion = sesion or sesion_http()
    crudo = _pedir(sesion, anio=anio, comite=COMITES[comite])
    return parsear(crudo)


def _pedir(sesion: requests.Session, anio: int, comite: str) -> Any:
    """Una petición, un año entero.

    El servidor ignora `limit` y devuelve el año completo, así que no hay paginación
    que recorrer. `mes` vacío = todos los meses (aquí son "01".."12", no 0-11 como
    en la RFEG).
    """
    respuesta = sesion.post(
        ENDPOINT,
        data={
            "exportar": "false",
            "page": "0",
            "anio": str(anio),
            "mes": "",
            "comite": comite,
            "circuito": "",
            "id": "",
            "slug": "",
            "count": "0",
            "limit": "500",
        },
        headers={"X-Requested-With": "XMLHttpRequest", "Referer": REFERER},
        timeout=30,
    )
    respuesta.raise_for_status()
    return respuesta.json()


def parsear(crudo: Any) -> List[Torneo]:
    """Convierte la respuesta cruda en `Torneo`.

    La respuesta son dos bloques: `[0]` la lista de competiciones y `[1]` un mapa
    id -> [[nombre_circuito, id_circuito], ...]. Nos anclamos a las claves, nunca a
    posiciones dentro de cada competición.
    """
    competiciones, circuitos_por_id = _desempaquetar(crudo)
    recogido_en = datetime.now().astimezone()
    return [_a_torneo(c, circuitos_por_id, recogido_en) for c in competiciones]


def _desempaquetar(crudo: Any):
    # El endpoint devuelve un array JSON, pero requests lo entrega como dict con
    # claves "0"/"1" cuando el servidor lo serializa como objeto. Aceptamos ambos.
    if isinstance(crudo, dict):
        competiciones = crudo.get("0") or []
        circuitos = crudo.get("1") or {}
    else:
        competiciones = crudo[0] if len(crudo) > 0 else []
        circuitos = crudo[1] if len(crudo) > 1 else {}
    return competiciones, (circuitos or {})


def _a_torneo(c: Dict[str, Any], circuitos_por_id: Dict[str, Any], recogido_en: datetime) -> Torneo:
    id_nc = c["id"]
    jornadas = _jornadas(c)
    plantilla = URL_AGRUPACION if c.get("grouping") else URL_TORNEO

    return Torneo(
        id=f"{FUENTE}:{id_nc}",
        fuente=FUENTE,
        comunidad=COMUNIDAD,
        nombre=(c.get("nombre") or "").strip(),
        fecha_inicio=jornadas[0],
        fecha_fin=jornadas[-1],
        jornadas=jornadas,
        club=(c.get("nombreClub") or "").strip() or None,
        inscripcion_desde=_fecha_hora(c.get("inicio")),
        inscripcion_hasta=_fecha_hora(c.get("fin")),
        modo_inscripcion=MODOS.get(c.get("modo"), "desconocido"),
        url_inscripcion=plantilla.format(id=id_nc),
        estado=(c.get("estado") or "desconocido").strip(),
        circuitos=[nombre for nombre, _ in circuitos_por_id.get(str(id_nc), [])],
        recogido_en=recogido_en,
        # categorias, hcp_max y sexo se quedan vacíos a propósito: esta fuente no los
        # publica. Los rellena normalize/, y la app no debe afirmar elegibilidad sin ellos.
    )


def _jornadas(c: Dict[str, Any]) -> List[date]:
    """Días de juego, ordenados. `fechasJornadas` es "YYYY-MM-DD,YYYY-MM-DD,..."."""
    crudo = c.get("fechasJornadas") or ""
    dias = sorted({_fecha(p) for p in crudo.split(",") if p.strip()})
    if not dias:
        dias = [_fecha(c["fecha"])]
    return dias


def _fecha(valor: str) -> date:
    return date.fromisoformat(valor.strip()[:10])


def _fecha_hora(valor: Optional[str]) -> Optional[datetime]:
    """Parsea "2026-09-18T12:00:00+02:00" en Python 3.9."""
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor)
    except ValueError:
        return None


def main(anio: Optional[int] = None) -> int:
    anio = anio or date.today().year
    torneos = recoger(anio)
    escritos = escribir_torneos(FUENTE, torneos)
    print(f"{FUENTE}: {escritos} torneos juveniles de {anio}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else None))
    except FuenteVacia as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
