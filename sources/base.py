"""Modelo de datos y utilidades comunes a todas las fuentes.

Una fuente es cualquier federación o organismo que publica un calendario. Cada una
tiene su propio transporte (HTML, JSON, lo que sea) pero todas devuelven `Torneo`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests

# Identificable y con contacto: scraping educado (ver CLAUDE.md).
USER_AGENT = (
    "torneos-golf/0.1 (agregador personal de calendarios de golf juvenil; "
    "+https://github.com/Link1976/torneos-golf)"
)

RUTA_DATOS = Path(__file__).resolve().parent.parent / "data" / "torneos.json"


class FuenteVacia(RuntimeError):
    """Una fuente ha devuelto cero torneos.

    Siempre es un error, nunca un resultado. Un calendario vacío publicado por un
    fallo de parser es peor que no publicar nada: el job debe fallar ruidosamente y
    dejar en pie el JSON anterior.
    """


@dataclass(frozen=True)
class Torneo:
    """Un torneo tal y como lo publica su fuente, sin interpretar.

    La normalización (categorías por edad, elegibilidad) vive en `normalize/`, no
    aquí. Esta capa recoge; no deduce.
    """

    # Identidad
    id: str                       # "madrid:68254" — único entre fuentes
    fuente: str                   # clave de la fuente: "madrid", "rfeg"...
    comunidad: str                # comunidad autónoma de la fuente

    # Qué y cuándo
    nombre: str
    fecha_inicio: date
    fecha_fin: date               # = fecha_inicio si es de una sola jornada
    jornadas: List[date]
    club: Optional[str]           # algunas fichas lo traen vacío

    # Inscripción
    inscripcion_desde: Optional[datetime]
    inscripcion_hasta: Optional[datetime]   # LA fecha límite: el dato que más se pierde
    modo_inscripcion: str         # "online" | "club" | "desconocido"
    url_inscripcion: str          # fuente oficial, siempre presente
    estado: str                   # "abierta" | "finalizada" | "cancelada"

    # Elegibilidad — se rellena en normalize/, no en la fuente
    categorias: List[str] = field(default_factory=list)  # ADMITIDAS por el torneo, no la del jugador
    hcp_max: Optional[float] = None   # vive en circulares PDF: null en v1
    sexo: Optional[str] = None        # "masculino" | "femenino" | None (mixto/desconocido)

    # Contexto
    circuitos: List[str] = field(default_factory=list)
    recogido_en: Optional[datetime] = None

    def a_dict(self) -> Dict[str, Any]:
        """Serializa a tipos JSON, con fechas en ISO 8601."""
        crudo = asdict(self)
        return {k: _serializar(v) for k, v in crudo.items()}


def _serializar(valor: Any) -> Any:
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, list):
        return [_serializar(v) for v in valor]
    return valor


def sesion_http() -> requests.Session:
    """Sesión con User-Agent identificable. Una pasada al día por fuente."""
    sesion = requests.Session()
    sesion.headers.update({"User-Agent": USER_AGENT})
    return sesion


def escribir_torneos(fuente: str, torneos: Iterable[Torneo], ruta: Path = RUTA_DATOS) -> int:
    """Vuelca los torneos de UNA fuente al JSON, conservando las demás.

    Lanza `FuenteVacia` antes de tocar el fichero si la fuente no trae nada, de modo
    que el calendario anterior sobrevive a un scraper roto.
    """
    torneos = list(torneos)
    if not torneos:
        raise FuenteVacia(
            f"La fuente '{fuente}' ha devuelto 0 torneos. No se escribe nada: "
            f"se conserva {ruta.name} tal y como estaba."
        )

    documento = _leer_documento(ruta)
    otros = [t for t in documento.get("torneos", []) if t.get("fuente") != fuente]
    nuevos = [t.a_dict() for t in torneos]

    documento["torneos"] = sorted(otros + nuevos, key=lambda t: (t["fecha_inicio"], t["nombre"]))
    documento["generado_en"] = datetime.now(timezone.utc).isoformat()
    documento.setdefault("fuentes", {})[fuente] = {
        "recogido_en": documento["generado_en"],
        "torneos": len(nuevos),
    }

    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(documento, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(nuevos)


def _leer_documento(ruta: Path) -> Dict[str, Any]:
    if not ruta.exists():
        return {"torneos": [], "fuentes": {}}
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Un JSON corrupto no debe impedir regenerarlo.
        return {"torneos": [], "fuentes": {}}
