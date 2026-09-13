"""La regla de edad y las franjas, tal y como las fija la normativa de la RFGM."""

from datetime import date

import pytest

from normalize.categorias import CATALOGO, admite, categorias_admitidas, edad_de_temporada


def test_la_edad_va_por_ano_natural():
    # Nacido en diciembre: cumple 12 en 2026 aunque el torneo se juegue en enero.
    assert edad_de_temporada(date(2014, 12, 31), 2026) == 12
    assert edad_de_temporada(date(2014, 1, 1), 2026) == 12


def test_no_depende_del_cumpleanos():
    enero, diciembre = date(2014, 1, 1), date(2014, 12, 31)
    assert categorias_admitidas(enero, 2026) == categorias_admitidas(diciembre, 2026)


class TestBandasCerradas:
    """Alevín e Infantil no admiten a los más pequeños. Es la trampa del modelo."""

    def test_alevin_no_admite_a_un_benjamin(self):
        benjamin = date(2016, 5, 1)  # cumple 10 en 2026
        assert admite("alevin", benjamin, 2026) is False

    def test_infantil_no_admite_a_un_alevin(self):
        alevin = date(2014, 5, 1)  # cumple 12 en 2026
        assert admite("infantil", alevin, 2026) is False
        assert admite("alevin", alevin, 2026) is True

    def test_alevin_son_exactamente_11_y_12(self):
        assert admite("alevin", date(2015, 1, 1), 2026) is True   # 11
        assert admite("alevin", date(2014, 1, 1), 2026) is True   # 12
        assert admite("alevin", date(2013, 1, 1), 2026) is False  # 13


class TestBandasAbiertasHaciaAbajo:
    """Benjamín y los Sub-N sí admiten a cualquiera más joven."""

    def test_un_alevin_puede_jugar_un_sub18(self):
        alevin = date(2014, 5, 1)  # 12 años
        assert admite("sub18", alevin, 2026) is True
        assert admite("sub16", alevin, 2026) is True

    def test_sub16_corta_por_arriba(self):
        assert admite("sub16", date(2010, 1, 1), 2026) is True   # cumple 16
        assert admite("sub16", date(2009, 1, 1), 2026) is False  # cumple 17

    def test_benjamin_es_10_o_menos(self):
        assert admite("benjamin", date(2016, 1, 1), 2026) is True   # 10
        assert admite("benjamin", date(2015, 1, 1), 2026) is False  # 11


def test_categoria_desconocida_no_afirma_nada():
    assert admite("absoluto", date(2014, 1, 1), 2026) is None


def test_catalogo_de_un_alevin():
    # Un alevín de 12 años: su categoría, y los Sub-N por encima. Nunca infantil.
    claves = set(categorias_admitidas(date(2014, 5, 1), 2026))
    assert claves == {"alevin", "sub16", "sub18", "sub25"}


@pytest.mark.parametrize("clave", CATALOGO)
def test_toda_categoria_tiene_techo(clave):
    assert CATALOGO[clave].edad_max is not None
