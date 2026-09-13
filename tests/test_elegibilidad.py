"""El veredicto, y sobre todo su tercera respuesta: no se sabe."""

from datetime import date

from normalize.elegibilidad import NO, NO_SE_SABE, SI, Jugador, evaluar

ALEVIN = Jugador(nacimiento=date(2014, 5, 1), hcp=30.0)   # 12 años en 2026


def torneo(**kwargs):
    base = {
        "fecha_inicio": "2026-05-10", "estado": "abierta", "en_fuente": True,
        "categorias": [], "hcp_min": None, "hcp_max": None, "sexo": None, "avisos": [],
    }
    base.update(kwargs)
    return base


class TestNoAfirmarSinDatos:
    def test_sin_categorias_no_se_sabe(self):
        v = evaluar(ALEVIN, torneo())
        assert v.resultado == NO_SE_SABE
        assert not v.puede_jugar
        assert any("circular" in m for m in v.motivos)

    def test_sin_limite_de_handicap_no_se_sabe(self):
        v = evaluar(ALEVIN, torneo(categorias=["alevin"]))
        assert v.resultado == NO_SE_SABE

    def test_con_todo_el_dato_si(self):
        v = evaluar(ALEVIN, torneo(categorias=["alevin"], hcp_max=36.0))
        assert v.resultado == SI and v.puede_jugar

    def test_no_se_sabe_nunca_es_un_si(self):
        assert not evaluar(ALEVIN, torneo()).puede_jugar


class TestEdad:
    def test_un_alevin_no_entra_en_infantil(self):
        v = evaluar(ALEVIN, torneo(categorias=["infantil"], hcp_max=26.4))
        assert v.resultado == NO

    def test_un_alevin_si_entra_en_sub18(self):
        v = evaluar(ALEVIN, torneo(categorias=["sub18"], hcp_max=36.0))
        assert v.resultado == SI

    def test_torneo_que_admite_varias(self):
        v = evaluar(ALEVIN, torneo(categorias=["infantil", "alevin"], hcp_max=36.0))
        assert v.resultado == SI


class TestHandicap:
    def test_por_encima_del_maximo(self):
        v = evaluar(ALEVIN, torneo(categorias=["alevin"], hcp_max=26.4))
        assert v.resultado == NO

    def test_por_debajo_del_minimo(self):
        # Fun&Golf exige 36,1 o más: a un jugador bueno lo excluyen.
        v = evaluar(ALEVIN, torneo(categorias=["alevin"], hcp_min=36.1, hcp_max=54.0))
        assert v.resultado == NO
        assert any("mínimo" in m for m in v.motivos)

    def test_dentro_del_rango(self):
        bueno = Jugador(nacimiento=date(2014, 5, 1), hcp=40.0)
        v = evaluar(bueno, torneo(categorias=["alevin"], hcp_min=36.1, hcp_max=54.0))
        assert v.resultado == SI

    def test_sin_handicap_del_jugador(self):
        anon = Jugador(nacimiento=date(2014, 5, 1))
        v = evaluar(anon, torneo(categorias=["alevin"], hcp_max=36.0))
        assert v.resultado == NO_SE_SABE


class TestEstadoDelTorneo:
    def test_cancelado_es_no(self):
        v = evaluar(ALEVIN, torneo(categorias=["alevin"], hcp_max=36.0, estado="cancelada"))
        assert v.resultado == NO

    def test_retirado_del_calendario_no_se_sabe(self):
        v = evaluar(ALEVIN, torneo(categorias=["alevin"], hcp_max=36.0, en_fuente=False))
        assert v.resultado == NO_SE_SABE

    def test_datos_incoherentes_se_avisan(self):
        v = evaluar(ALEVIN, torneo(categorias=["alevin"], hcp_max=36.0,
                                   avisos=["ventana_de_inscripcion_invertida"]))
        assert any("incoherentes" in m for m in v.motivos)


def test_sexo():
    chica = Jugador(nacimiento=date(2014, 5, 1), hcp=30.0, sexo="femenino")
    v = evaluar(chica, torneo(categorias=["alevin"], hcp_max=36.0, sexo="masculino"))
    assert v.resultado == NO
