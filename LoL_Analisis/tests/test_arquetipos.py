r"""El clasificador de arquetipos contra casos que se conocían antes de ver los datos."""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "scripts"))
from e5_e8 import clasificar  # noqa: E402

NADA = np.array([])


def serie(*tramos):
    """Concatena tramos (valor_v_en_%, minutos); la diferencia de oro se fija en 300 por punto."""
    v = np.concatenate([np.full(m, x, dtype=float) for x, m in tramos])
    return v, v * 300


def test_a4_muy_desigual():
    v, d = serie((0, 3), (-12, 10), (-15, 15))
    assert clasificar(v, d, 3, NADA) == "A4"


def test_a2_ventaja_desperdiciada():
    v, d = serie((0, 5), (8, 15), (-3, 10))
    assert clasificar(v, d, 21, NADA) == "A2"


def test_a2_necesita_ventaja_despues_del_15():
    v, d = serie((0, 3), (8, 5), (-2, 20))       # ventaja solo temprana
    assert clasificar(v, d, 9, NADA) != "A2"


def test_a1_derrota_desde_linea():
    v, d = serie((0, 3), (-3, 8), (-7, 20))
    assert clasificar(v, d, 4, NADA) == "A1"


def test_a3_tranquila_hasta_d2_y_objetivo_del_rival():
    v, d = serie((1, 20), (-8, 10))
    assert clasificar(v, d, 20, np.array([19.5])) == "A3"
    assert clasificar(v, d, 20, np.array([25.0])) == "Sin clasificar", "objetivo lejos del quiebre"


def test_el_orden_a4_antes_que_a1():
    v, d = serie((0, 3), (-11, 12), (-8, 15))    # cumple A4 y A1
    assert clasificar(v, d, 3, NADA) == "A4"


def test_la_partida_de_ejemplo_de_la_presentacion_es_a2():
    """La lámina de arquetipos afirma que EUW1_6569580003 (ejemplo público, no del autor)
    es A2. Se calcula desde el lado del equipo que perdió, con el oro por equipo de cada
    cuadro, guardado en tests/datos/ para que la prueba corra en una copia limpia (el JSON
    crudo no se publica)."""
    oro = json.loads((AQUI / "datos" / "oro_ejemplo_a2.json").read_text(encoding="utf-8"))
    a, b = np.array(oro["perdedor"]), np.array(oro["ganador"])
    v = 100 * (a - b) / (a + b)
    assert clasificar(v, a - b, None, NADA) == "A2"
