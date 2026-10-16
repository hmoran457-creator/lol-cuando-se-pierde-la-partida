r"""Las definiciones centrales del análisis, contra casos construidos a mano.

v(t), D1 (la mayor caída), D2 (el último cruce hacia abajo), el embudo de filtrado y el
punto sin regreso de H3. Todo lo demás del proyecto se apoya en estas cinco piezas.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "scripts"))
import e1_quiebre as e1  # noqa: E402
from e2_e4 import punto_sin_regreso  # noqa: E402


def oro_de(partida: str, propio: list[float], rival: list[float], equipo: int = 100) -> pd.DataFrame:
    otro = 200 if equipo == 100 else 100
    filas = [{"partida": partida, "minuto": m, "teamId": equipo, "oroTotal": a} for m, a in enumerate(propio)]
    filas += [{"partida": partida, "minuto": m, "teamId": otro, "oroTotal": b} for m, b in enumerate(rival)]
    return pd.DataFrame(filas)


def partida(pid: str, equipo: int = 100, gane: int = 0, dur: float = 30.0) -> dict:
    return {"partida": pid, "equipoPropio": equipo, "gane": gane, "duracionMin": dur}


def test_v_es_la_diferencia_sobre_el_oro_total_y_desde_el_lado_propio():
    # mismo oro por equipo en las dos partidas (equipo 100: 600, equipo 200: 400); solo
    # cambia de qué lado juego yo
    oro = pd.concat([oro_de("a", [600, 500], [400, 500], equipo=100),
                     oro_de("b", [600, 500], [400, 500], equipo=100)])
    v = e1.medida_v(oro, pd.DataFrame([partida("a", 100), partida("b", 200)]))
    va, vb = v[v.partida == "a"]["v"].to_numpy(), v[v.partida == "b"]["v"].to_numpy()
    assert np.allclose(va, [0.2, 0.0])        # (600-400)/1000
    assert np.allclose(vb, [-0.2, 0.0])       # el mismo oro visto desde el otro equipo


def serie_v(pid: str, valores: list[float], gane: int = 0) -> pd.DataFrame:
    return pd.DataFrame({"partida": pid, "minuto": range(len(valores)), "v": valores,
                         "gane": gane, "duracionMin": len(valores) - 1})


def test_d1_es_la_mayor_caida_y_d2_el_ultimo_cruce_hacia_abajo():
    #            min: 0     1     2     3     4     5     6
    v = serie_v("x", [0.0, 0.05, -0.02, 0.03, 0.04, -0.06, -0.07])
    q = e1.quiebres(v).iloc[0]
    assert q["d1"] == 5                       # la caída de 0.04 a -0.06 es la mayor
    assert q["d2"] == 5                       # dos cruces (en 2 y en 5): cuenta el último


def test_d2_es_nulo_si_nunca_se_va_abajo_y_d1_puede_ser_temprano():
    v = serie_v("y", [0.0, 0.10, 0.02, 0.05, 0.06], gane=1)
    q = e1.quiebres(v).iloc[0]
    assert pd.isna(q["d2"])                   # nunca cruzó hacia abajo
    assert q["d1"] == 2                       # la mayor caída es la del minuto 2


def test_el_embudo_quita_lo_que_dice_y_en_ese_orden():
    base = dict(equipoPropio=100, cola=420, jugadores=10, rendicionTemprana=0,
                duracionMin=30.0, rendicion=0)
    filas = [
        {"partida": "ok", **base},
        {"partida": "sin-linea", **{**base, "equipoPropio": None}},
        {"partida": "otra-cola", **{**base, "cola": 440}},
        {"partida": "arena", **{**base, "jugadores": 16}},
        {"partida": "remake", **{**base, "rendicionTemprana": 1}},
        {"partida": "corta", **{**base, "duracionMin": 4.5}},
        {"partida": "rendida", **{**base, "rendicion": 1, "duracionMin": 9.0}},
        {"partida": "rendida-tarde", **{**base, "rendicion": 1, "duracionMin": 22.0}},
    ]
    muestra, pasos = e1.filtrar(pd.DataFrame(filas))
    assert sorted(muestra["partida"]) == ["ok", "rendida-tarde"]
    assert [n for _, n in pasos] == [7, 6, 5, 4, 3, 2]


def test_punto_sin_regreso_exige_quedarse_bajo_el_umbral():
    c = pd.DataFrame({"minuto": range(20, 27), "en_riesgo": [200] * 6 + [10],
                      "remontaron": [20, 8, 12, 6, 4, 2, 5],
                      "p": [.10, .04, .06, .03, .02, .01, .50], "lo": 0.0, "hi": 0.1})
    r = punto_sin_regreso(c)["por_umbral"]
    # el 21 ya está bajo 5 %, pero el 22 vuelve a subir: el punto es el 23. El minuto 26
    # (50 %) no cuenta porque tiene menos de 30 partidas en riesgo.
    assert r["0.05"]["minuto"] == 23
    assert r["0.10"]["minuto"] == 21
    assert r["0.03"]["minuto"] == 24
