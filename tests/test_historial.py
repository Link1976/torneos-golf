"""El calendario es volátil: torneos que se mueven de fecha y torneos que se retiran.

Lo que no se registre en su momento no se puede reconstruir después.
"""

import json
from datetime import date, datetime

import pytest

from sources.base import Torneo, escribir_torneos, validar


def torneo(id="madrid:1", fecha="2026-05-10", hasta="2026-05-04T10:00:00+02:00", estado="abierta"):
    d = date.fromisoformat(fecha)
    return Torneo(
        id=id, fuente="madrid", comunidad="Madrid", nombre="Torneo Alevín",
        fecha_inicio=d, fecha_fin=d, jornadas=[d], club="Club",
        inscripcion_desde=datetime.fromisoformat("2026-04-27T10:00:00+02:00"),
        inscripcion_hasta=datetime.fromisoformat(hasta),
        modo_inscripcion="online", url_inscripcion="https://www.nextcaddy.com/tour/1",
        estado=estado,
    )


def leer(ruta):
    return {t["id"]: t for t in json.loads(ruta.read_text(encoding="utf-8"))["torneos"]}


@pytest.fixture
def ruta(tmp_path):
    return tmp_path / "torneos.json"


class TestCambioDeFecha:
    def test_se_registra_el_movimiento(self, ruta):
        escribir_torneos("madrid", [torneo()], ruta=ruta, hoy=date(2026, 4, 1))
        escribir_torneos("madrid", [torneo(fecha="2026-05-17")], ruta=ruta, hoy=date(2026, 4, 2))

        cambios = leer(ruta)["madrid:1"]["cambios"]
        campos = {c["campo"] for c in cambios}
        assert "fecha_inicio" in campos
        movimiento = next(c for c in cambios if c["campo"] == "fecha_inicio")
        assert movimiento == {
            "detectado_en": "2026-04-02", "campo": "fecha_inicio",
            "antes": "2026-05-10", "despues": "2026-05-17",
        }

    def test_se_registra_el_cambio_de_plazo(self, ruta):
        escribir_torneos("madrid", [torneo()], ruta=ruta, hoy=date(2026, 4, 1))
        escribir_torneos("madrid", [torneo(hasta="2026-05-06T10:00:00+02:00")],
                         ruta=ruta, hoy=date(2026, 4, 2))
        assert any(c["campo"] == "inscripcion_hasta" for c in leer(ruta)["madrid:1"]["cambios"])

    def test_sin_cambios_no_inventa_historial(self, ruta):
        escribir_torneos("madrid", [torneo()], ruta=ruta, hoy=date(2026, 4, 1))
        escribir_torneos("madrid", [torneo()], ruta=ruta, hoy=date(2026, 4, 2))
        assert leer(ruta)["madrid:1"]["cambios"] == []

    def test_el_historial_se_acumula(self, ruta):
        escribir_torneos("madrid", [torneo()], ruta=ruta, hoy=date(2026, 4, 1))
        escribir_torneos("madrid", [torneo(fecha="2026-05-17")], ruta=ruta, hoy=date(2026, 4, 2))
        escribir_torneos("madrid", [torneo(fecha="2026-05-24")], ruta=ruta, hoy=date(2026, 4, 3))
        fechas = [c for c in leer(ruta)["madrid:1"]["cambios"] if c["campo"] == "fecha_inicio"]
        assert len(fechas) == 2


class TestRetirada:
    def test_un_torneo_que_desaparece_no_se_borra(self, ruta):
        escribir_torneos("madrid", [torneo("madrid:1"), torneo("madrid:2")],
                         ruta=ruta, hoy=date(2026, 4, 1))
        recuento = escribir_torneos("madrid", [torneo("madrid:1")], ruta=ruta, hoy=date(2026, 4, 2))

        datos = leer(ruta)
        assert "madrid:2" in datos                      # sigue ahí
        assert datos["madrid:2"]["en_fuente"] is False
        assert datos["madrid:2"]["retirado_en"] == "2026-04-02"
        assert datos["madrid:2"]["visto_por_ultima_vez"] == "2026-04-01"
        assert recuento["retirados"] == 1

    def test_no_se_re_retira_cada_dia(self, ruta):
        escribir_torneos("madrid", [torneo("madrid:1"), torneo("madrid:2")],
                         ruta=ruta, hoy=date(2026, 4, 1))
        escribir_torneos("madrid", [torneo("madrid:1")], ruta=ruta, hoy=date(2026, 4, 2))
        escribir_torneos("madrid", [torneo("madrid:1")], ruta=ruta, hoy=date(2026, 4, 3))

        retirado = leer(ruta)["madrid:2"]
        assert retirado["retirado_en"] == "2026-04-02"   # la fecha original, no la de hoy
        assert len([c for c in retirado["cambios"] if c["campo"] == "en_fuente"]) == 1

    def test_si_reaparece_se_nota(self, ruta):
        escribir_torneos("madrid", [torneo("madrid:1"), torneo("madrid:2")],
                         ruta=ruta, hoy=date(2026, 4, 1))
        escribir_torneos("madrid", [torneo("madrid:1")], ruta=ruta, hoy=date(2026, 4, 2))
        recuento = escribir_torneos("madrid", [torneo("madrid:1"), torneo("madrid:2")],
                                    ruta=ruta, hoy=date(2026, 4, 3))

        vuelto = leer(ruta)["madrid:2"]
        assert vuelto["en_fuente"] is True
        assert vuelto["retirado_en"] is None
        assert recuento["reaparecidos"] == 1


class TestCancelacion:
    def test_pasar_a_cancelada_queda_registrado(self, ruta):
        escribir_torneos("madrid", [torneo()], ruta=ruta, hoy=date(2026, 4, 1))
        escribir_torneos("madrid", [torneo(estado="cancelada")], ruta=ruta, hoy=date(2026, 4, 2))
        cambio = next(c for c in leer(ruta)["madrid:1"]["cambios"] if c["campo"] == "estado")
        assert cambio["antes"] == "abierta" and cambio["despues"] == "cancelada"


class TestValidacion:
    def test_ventana_invertida(self):
        # Caso real del calendario de Madrid: cierra antes de abrir.
        assert "ventana_de_inscripcion_invertida" in validar({
            "inscripcion_desde": "2026-11-09T12:00:00+01:00",
            "inscripcion_hasta": "2026-11-02T10:00:00+01:00",
        })

    def test_torneo_sano_no_genera_avisos(self, ruta):
        escribir_torneos("madrid", [torneo()], ruta=ruta, hoy=date(2026, 4, 1))
        assert leer(ruta)["madrid:1"]["avisos"] == []

    def test_plazo_posterior_al_torneo(self):
        assert "plazo_cierra_despues_del_torneo" in validar({
            "fecha_inicio": "2026-05-10",
            "inscripcion_hasta": "2026-05-20T10:00:00+02:00",
        })


def test_recuento_de_la_pasada(ruta):
    r = escribir_torneos("madrid", [torneo("madrid:1"), torneo("madrid:2")],
                         ruta=ruta, hoy=date(2026, 4, 1))
    assert r == {"total": 2, "nuevos": 2, "modificados": 0, "retirados": 0, "reaparecidos": 0}
