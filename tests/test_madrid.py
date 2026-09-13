"""Tests del parser de Madrid sobre una respuesta real del endpoint.

El fixture es una muestra literal de `POST /ajax/competiciones` (comité juvenil,
2026), recortada para cubrir los casos raros: torneo cancelado, club vacío, varias
jornadas, inscripción en club, y `modo` sin documentar.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from sources import madrid
from sources.base import FuenteVacia, escribir_torneos

FIXTURE = Path(__file__).parent / "fixtures" / "madrid_juvenil_2026.json"


@pytest.fixture
def crudo():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def torneos(crudo):
    return {t.id: t for t in madrid.parsear(crudo)}


def test_parsea_todas_las_competiciones(crudo):
    assert len(madrid.parsear(crudo)) == len(crudo[0])


def test_id_lleva_prefijo_de_fuente(torneos):
    assert "madrid:68254" in torneos
    assert all(t.fuente == "madrid" and t.comunidad == "Madrid" for t in torneos.values())


def test_fecha_fin_sale_de_la_ultima_jornada(torneos):
    t = torneos["madrid:68254"]  # Copa Alianza Juvenil, 3 jornadas
    assert t.fecha_inicio == date(2026, 9, 18)
    assert t.fecha_fin == date(2026, 9, 20)
    assert len(t.jornadas) == 3


def test_torneo_de_un_dia_tiene_inicio_igual_a_fin(torneos):
    t = torneos["madrid:67586"]
    assert t.fecha_inicio == t.fecha_fin == date(2026, 3, 5)


def test_fecha_limite_de_inscripcion(torneos):
    # El dato que más se pierde: hasta cuándo se puede uno apuntar.
    t = torneos["madrid:65858"]
    assert t.inscripcion_hasta is not None
    assert t.inscripcion_hasta.date() == date(2026, 1, 5)


def test_las_jornadas_no_son_la_ventana_de_inscripcion(torneos):
    # 67779 abre inscripción en enero para jugarse en abril: no confundirlas.
    t = torneos["madrid:67779"]
    assert t.inscripcion_desde.date() == date(2026, 1, 22)
    assert t.fecha_inicio == date(2026, 4, 25)


def test_modo_de_inscripcion(torneos):
    assert torneos["madrid:68254"].modo_inscripcion == "online"   # modo 3
    assert torneos["madrid:67779"].modo_inscripcion == "club"     # modo 2
    assert torneos["madrid:68535"].modo_inscripcion == "desconocido"  # modo 1, sin documentar


def test_club_vacio_es_none(torneos):
    assert torneos["madrid:68535"].club is None
    assert torneos["madrid:68254"].club == "Naturavila Golf"


def test_estado_se_conserva_tal_cual(torneos):
    assert torneos["madrid:68237"].estado == "cancelada"
    assert torneos["madrid:68254"].estado == "abierta"


def test_circuitos(torneos):
    assert torneos["madrid:68254"].circuitos == ["Circuito Juvenil 2026"]


def test_siempre_hay_url_de_inscripcion(torneos):
    assert all(t.url_inscripcion.startswith("https://www.nextcaddy.com/") for t in torneos.values())
    assert torneos["madrid:68254"].url_inscripcion == "https://www.nextcaddy.com/tour/68254"


def test_elegibilidad_se_deja_vacia_a_proposito(torneos):
    # La fuente no publica categorías ni hándicap máximo. No se inventan aquí.
    for t in torneos.values():
        assert t.categorias == []
        assert t.hcp_max is None


def test_serializa_fechas_a_iso(torneos):
    d = torneos["madrid:68254"].a_dict()
    assert d["fecha_inicio"] == "2026-09-18"
    assert d["jornadas"] == ["2026-09-18", "2026-09-19", "2026-09-20"]
    json.dumps(d)  # debe ser serializable sin ayuda


def test_respuesta_como_objeto_tambien_se_acepta(crudo):
    como_dict = {"0": crudo[0], "1": crudo[1]}
    assert len(madrid.parsear(como_dict)) == len(crudo[0])


class TestEscritura:
    def test_no_se_publica_un_json_vacio(self, tmp_path):
        ruta = tmp_path / "torneos.json"
        anterior = '{"torneos": [{"id": "madrid:1", "fuente": "madrid", "fecha_inicio": "2026-01-01", "nombre": "x"}]}'
        ruta.write_text(anterior, encoding="utf-8")

        with pytest.raises(FuenteVacia):
            escribir_torneos("madrid", [], ruta=ruta)

        assert ruta.read_text(encoding="utf-8") == anterior  # el calendario anterior sigue en pie

    def test_una_fuente_no_pisa_las_demas(self, tmp_path, crudo):
        ruta = tmp_path / "torneos.json"
        ruta.write_text(json.dumps({
            "torneos": [{"id": "rfeg:1", "fuente": "rfeg", "fecha_inicio": "2026-07-01", "nombre": "Nacional"}],
            "fuentes": {"rfeg": {"torneos": 1}},
        }), encoding="utf-8")

        escribir_torneos("madrid", madrid.parsear(crudo), ruta=ruta)

        doc = json.loads(ruta.read_text(encoding="utf-8"))
        fuentes = {t["fuente"] for t in doc["torneos"]}
        assert fuentes == {"rfeg", "madrid"}
        assert doc["fuentes"]["madrid"]["torneos"] == len(crudo[0])

    def test_reejecutar_no_duplica(self, tmp_path, crudo):
        ruta = tmp_path / "torneos.json"
        escribir_torneos("madrid", madrid.parsear(crudo), ruta=ruta)
        escribir_torneos("madrid", madrid.parsear(crudo), ruta=ruta)

        doc = json.loads(ruta.read_text(encoding="utf-8"))
        ids = [t["id"] for t in doc["torneos"]]
        assert len(ids) == len(set(ids)) == len(crudo[0])

    def test_salen_ordenados_por_fecha(self, tmp_path, crudo):
        ruta = tmp_path / "torneos.json"
        escribir_torneos("madrid", madrid.parsear(crudo), ruta=ruta)
        doc = json.loads(ruta.read_text(encoding="utf-8"))
        fechas = [t["fecha_inicio"] for t in doc["torneos"]]
        assert fechas == sorted(fechas)
