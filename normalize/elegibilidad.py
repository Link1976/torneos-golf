"""¿Puede ESTE jugador inscribirse en ESTE torneo?

Tres respuestas posibles, y la tercera es la importante: **no se sabe**.

La app es un agregador, no la fuente de verdad. Cuando falta el dato —y en v1 falta
a menudo, porque las categorías admitidas y el hándicap viven en circulares PDF—
hay que decirlo y enlazar a la fuente oficial. Afirmar una elegibilidad que no
consta le cuesta a un niño una inscripción perdida.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

from .categorias import CATALOGO, edad_de_temporada

SI = "si"
NO = "no"
NO_SE_SABE = "no_se_sabe"


@dataclass(frozen=True)
class Jugador:
    nacimiento: date
    hcp: Optional[float] = None
    sexo: Optional[str] = None      # "masculino" | "femenino"


@dataclass(frozen=True)
class Veredicto:
    resultado: str                  # SI | NO | NO_SE_SABE
    motivos: List[str] = field(default_factory=list)

    @property
    def puede_jugar(self) -> bool:
        """Solo un SÍ explícito cuenta. Un 'no se sabe' nunca es un sí."""
        return self.resultado == SI


def evaluar(jugador: Jugador, torneo: Dict[str, Any]) -> Veredicto:
    """Cruza jugador y torneo. `torneo` es un dict del JSON publicado."""
    motivos: List[str] = []

    temporada = int(str(torneo["fecha_inicio"])[:4])
    edad = edad_de_temporada(jugador.nacimiento, temporada)

    # --- Categoría ---------------------------------------------------------
    claves = torneo.get("categorias") or []
    if not claves:
        motivos.append("El torneo no publica qué categorías admite: consulta la circular oficial.")
        veredicto_edad = NO_SE_SABE
    else:
        conocidas = [c for c in claves if c in CATALOGO]
        if not conocidas:
            motivos.append(f"Categorías no reconocidas: {', '.join(claves)}.")
            veredicto_edad = NO_SE_SABE
        elif any(CATALOGO[c].admite(edad) for c in conocidas):
            veredicto_edad = SI
        else:
            nombres = ", ".join(CATALOGO[c].nombre for c in conocidas)
            motivos.append(f"Con {edad} años en {temporada} no entra en {nombres}.")
            veredicto_edad = NO

    # --- Hándicap ----------------------------------------------------------
    # Es un rango, no solo un techo: hay torneos con hándicap MÍNIMO.
    hcp_min, hcp_max = torneo.get("hcp_min"), torneo.get("hcp_max")
    if hcp_min is None and hcp_max is None:
        veredicto_hcp = NO_SE_SABE if jugador.hcp is not None else SI
        if jugador.hcp is not None:
            motivos.append("El torneo no publica límite de hándicap: consulta la circular oficial.")
    elif jugador.hcp is None:
        motivos.append("Falta el hándicap del jugador para comprobar el límite.")
        veredicto_hcp = NO_SE_SABE
    elif hcp_max is not None and jugador.hcp > hcp_max:
        motivos.append(f"Hándicap {jugador.hcp} por encima del máximo admitido ({hcp_max}).")
        veredicto_hcp = NO
    elif hcp_min is not None and jugador.hcp < hcp_min:
        motivos.append(f"Hándicap {jugador.hcp} por debajo del mínimo admitido ({hcp_min}).")
        veredicto_hcp = NO
    else:
        veredicto_hcp = SI

    # --- Sexo --------------------------------------------------------------
    veredicto_sexo = SI
    if torneo.get("sexo") and jugador.sexo and torneo["sexo"] != jugador.sexo:
        motivos.append(f"El torneo es de categoría {torneo['sexo']}.")
        veredicto_sexo = NO

    # --- Estado del torneo -------------------------------------------------
    if torneo.get("estado") == "cancelada":
        return Veredicto(NO, ["El torneo está cancelado."])
    if torneo.get("en_fuente") is False:
        return Veredicto(NO_SE_SABE, ["El torneo ha desaparecido del calendario oficial."])
    for aviso in torneo.get("avisos") or []:
        motivos.append(f"La fuente publica datos incoherentes ({aviso}): verifica en la web oficial.")

    # --- Resolución --------------------------------------------------------
    partes = (veredicto_edad, veredicto_hcp, veredicto_sexo)
    if NO in partes:
        return Veredicto(NO, motivos)
    if NO_SE_SABE in partes:
        return Veredicto(NO_SE_SABE, motivos)
    return Veredicto(SI, motivos)
