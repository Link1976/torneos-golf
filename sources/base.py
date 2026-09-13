"""Modelo de datos y utilidades comunes a todas las fuentes.

Una fuente es cualquier federación u organismo que publica un calendario. Cada una
tiene su propio transporte (HTML, JSON, lo que sea) pero todas devuelven `Torneo`.

El calendario no es estable: los torneos cambian de fecha y se retiran a mitad de
temporada. Por eso esta capa no se limita a reemplazar lo anterior — lleva historial.
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

# Campos cuyo cambio se registra de una pasada a otra. Son los que invalidan un plan:
# la fecha de juego, el plazo para apuntarse y que el torneo siga en pie.
CAMPOS_VIGILADOS = (
    "fecha_inicio",
    "fecha_fin",
    "inscripcion_desde",
    "inscripcion_hasta",
    "estado",
)


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
    id: str                       # "madrid:68254" — único entre fuentes y estable
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

    # Elegibilidad — la rellena normalize/, no la fuente
    categorias: List[str] = field(default_factory=list)  # ADMITIDAS por el torneo, no la del jugador
    # El hándicap es un RANGO, no solo un techo: Fun&Golf exige un mínimo de 36,1 y
    # Access Series de 7. Un `hcp_max` a secas dejaría entrar a quien está excluido.
    hcp_min: Optional[float] = None
    hcp_max: Optional[float] = None
    sexo: Optional[str] = None    # "masculino" | "femenino" | None (mixto/desconocido)

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


# --------------------------------------------------------------------------- #
# Validación
# --------------------------------------------------------------------------- #

def validar(t: Dict[str, Any]) -> List[str]:
    """Devuelve los problemas de coherencia de un torneo, sin corregirlos.

    Las fuentes publican registros imposibles: hay un torneo en el calendario de
    Madrid cuya inscripción cierra una semana antes de abrirse. No se arreglan a
    ciegas — se marcan, para que la app pueda callarse en vez de mentir.
    """
    avisos = []
    desde, hasta = t.get("inscripcion_desde"), t.get("inscripcion_hasta")
    if desde and hasta and hasta < desde:
        avisos.append("ventana_de_inscripcion_invertida")
    if t.get("fecha_fin") and t.get("fecha_inicio") and t["fecha_fin"] < t["fecha_inicio"]:
        avisos.append("fechas_de_juego_invertidas")
    if hasta and t.get("fecha_inicio") and hasta[:10] > t["fecha_inicio"]:
        avisos.append("plazo_cierra_despues_del_torneo")
    return avisos


# --------------------------------------------------------------------------- #
# Escritura con historial
# --------------------------------------------------------------------------- #

def escribir_torneos(
    fuente: str,
    torneos: Iterable[Torneo],
    ruta: Path = RUTA_DATOS,
    hoy: Optional[date] = None,
) -> Dict[str, int]:
    """Vuelca los torneos de UNA fuente al JSON, conservando las demás y el historial.

    Tres reglas, todas nacidas de que el calendario es volátil:

    - **Nunca publicar vacío.** Si la fuente no trae nada, lanza `FuenteVacia` antes de
      tocar el fichero: el calendario anterior sobrevive a un scraper roto.
    - **Nunca borrar en silencio.** Un torneo que desaparece de la fuente no se elimina;
      se marca `en_fuente: false` con la fecha en que se le vio por última vez.
    - **Registrar lo que se mueve.** Cambios de fecha de juego o de plazo quedan
      apuntados en `cambios[]`, que es lo único que no se puede reconstruir después.

    Devuelve un recuento de lo ocurrido en esta pasada.
    """
    torneos = list(torneos)
    if not torneos:
        raise FuenteVacia(
            f"La fuente '{fuente}' ha devuelto 0 torneos. No se escribe nada: "
            f"se conserva {ruta.name} tal y como estaba."
        )

    hoy = hoy or date.today()
    sello = hoy.isoformat()
    documento = _leer_documento(ruta)

    previos = {t["id"]: t for t in documento.get("torneos", []) if t.get("fuente") == fuente}
    otras_fuentes = [t for t in documento.get("torneos", []) if t.get("fuente") != fuente]

    resultado = []
    recuento = {"total": len(torneos), "nuevos": 0, "modificados": 0, "retirados": 0, "reaparecidos": 0}

    for torneo in torneos:
        actual = torneo.a_dict()
        actual["avisos"] = validar(actual)
        anterior = previos.pop(actual["id"], None)

        if anterior is None:
            actual["cambios"] = []
            recuento["nuevos"] += 1
        else:
            cambios = list(anterior.get("cambios", []))
            nuevos_cambios = _diferencias(anterior, actual, sello)
            if not anterior.get("en_fuente", True):
                nuevos_cambios.append(_cambio(sello, "en_fuente", False, True))
                recuento["reaparecidos"] += 1
            if nuevos_cambios:
                recuento["modificados"] += 1
            actual["cambios"] = cambios + nuevos_cambios

        actual["en_fuente"] = True
        actual["visto_por_ultima_vez"] = sello
        actual["retirado_en"] = None
        resultado.append(actual)

    # Lo que ya no viene en la fuente: se conserva, marcado.
    for anterior in previos.values():
        retirado = dict(anterior)
        if retirado.get("en_fuente", True):
            retirado["en_fuente"] = False
            retirado["retirado_en"] = sello
            retirado["cambios"] = list(retirado.get("cambios", [])) + [
                _cambio(sello, "en_fuente", True, False)
            ]
            recuento["retirados"] += 1
        resultado.append(retirado)

    documento["torneos"] = sorted(
        otras_fuentes + resultado, key=lambda t: (t["fecha_inicio"], t["nombre"])
    )
    documento["generado_en"] = datetime.now(timezone.utc).isoformat()
    documento.setdefault("fuentes", {})[fuente] = {
        "recogido_en": documento["generado_en"],
        "torneos": len(torneos),
        "ultima_pasada": recuento,
    }

    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(documento, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return recuento


def _diferencias(anterior: Dict[str, Any], actual: Dict[str, Any], sello: str) -> List[Dict[str, Any]]:
    return [
        _cambio(sello, campo, anterior.get(campo), actual.get(campo))
        for campo in CAMPOS_VIGILADOS
        if anterior.get(campo) != actual.get(campo)
    ]


def _cambio(sello: str, campo: str, antes: Any, despues: Any) -> Dict[str, Any]:
    return {"detectado_en": sello, "campo": campo, "antes": antes, "despues": despues}


def _leer_documento(ruta: Path) -> Dict[str, Any]:
    if not ruta.exists():
        return {"torneos": [], "fuentes": {}}
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Un JSON corrupto no debe impedir regenerarlo.
        return {"torneos": [], "fuentes": {}}
