"""Categorías juveniles por edad.

La regla está resuelta y viene de documento oficial, no de deducción: la *Normativa
Circuito Juvenil 2026* (Circular 2/2026 de la RFGM) dice literalmente "Jugadores/as
que cumplan 11 o 12 años **en el año en curso**".

Es decir: **la edad se computa por año natural**. No a 31 de diciembre, no en la
fecha del torneo. La edad que cuenta es la que el jugador cumple durante la temporada:

    edad_de_temporada = año_de_la_temporada - año_de_nacimiento

⚠️ Alcance: esto es la normativa **de Madrid**. Vale para los torneos de Madrid.
Antes de aplicarlo a la RFEG hay que confirmarlo con el reglamento nacional.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

FUENTE_REGLA = (
    "Normativa Circuito Juvenil 2026 (Circular 2/2026 RFGM), "
    "https://fedgolfmadrid.com/circuito/225 — leída el 13/09/2026"
)


@dataclass(frozen=True)
class Categoria:
    """Una categoría y la franja de edad que admite.

    `edad_min` a `None` significa que no tiene suelo: admite a cualquiera más joven.
    Esa es la diferencia que importa, y no es uniforme (ver `CATALOGO`).
    """

    nombre: str
    edad_max: int
    edad_min: Optional[int] = None

    def admite(self, edad: int) -> bool:
        if edad > self.edad_max:
            return False
        return self.edad_min is None or edad >= self.edad_min


# ⚠️ Las categorías NO anidan todas hacia abajo.
#
# Alevín e Infantil son bandas CERRADAS: "cumplan 11 o 12 años", "cumplan 13 y 14".
# Benjamín y los Sub-N son abiertas hacia abajo: "cumplan 16 años o menos".
#
# Consecuencia práctica: un jugador de 12 años SÍ puede jugar un Sub-18, pero NO un
# Infantil. Tratarlas todas como anidadas le diría a un padre que su hijo puede
# inscribirse donde no le admiten. La propia normativa lo corrobora al decir que la
# RFGM "no recomienda" que alevines jueguen pruebas Sub-16 y Sub-18: si lo
# desaconseja, es que está permitido.
CATALOGO: Dict[str, Categoria] = {
    "benjamin": Categoria("Benjamín", edad_max=10),
    "alevin":   Categoria("Alevín",   edad_max=12, edad_min=11),
    "infantil": Categoria("Infantil", edad_max=14, edad_min=13),
    # Cadete no lo define la normativa de Madrid, que solo lo nombra entre los
    # participantes. La franja (15 y 16) viene del Comité Juvenil de la RFEG.
    "cadete":   Categoria("Cadete",   edad_max=16, edad_min=15),
    "sub16":    Categoria("Sub-16",   edad_max=16),
    "sub18":    Categoria("Sub-18",   edad_max=18),
    "sub25":    Categoria("Sub-25",   edad_max=25),
}


def edad_de_temporada(nacimiento: date, temporada: int) -> int:
    """Años que el jugador cumple durante la temporada. Año natural, no cumpleaños."""
    return temporada - nacimiento.year


def categorias_admitidas(nacimiento: date, temporada: int) -> List[str]:
    """Claves de las categorías en las que ese jugador puede competir esa temporada."""
    edad = edad_de_temporada(nacimiento, temporada)
    return [clave for clave, cat in CATALOGO.items() if cat.admite(edad)]


def admite(clave: str, nacimiento: date, temporada: int) -> Optional[bool]:
    """¿Esa categoría admite a ese jugador? `None` si la categoría no se conoce."""
    categoria = CATALOGO.get(clave)
    if categoria is None:
        return None
    return categoria.admite(edad_de_temporada(nacimiento, temporada))
