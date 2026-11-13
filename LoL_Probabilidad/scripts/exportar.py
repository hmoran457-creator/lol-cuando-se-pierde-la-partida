r"""Ajusta los dos modelos elegidos con TODAS las partidas y los escribe para la herramienta.

    python LoL_Probabilidad/scripts/exportar.py

Los dos modelos (elegidos en LoL_Probabilidad/modelos/finalistas.py) son logísticas cuyo logit es

    logit = A(t) + sum_j x_j * B_j(t),      t = minuto recortado a [1, 40]

con A y B_j rectas en t (las de forma "lineal" de glm.py). Por eso basta guardar el valor de
cada recta en t = 1 y t = 40: entre ambos, interpolación lineal exacta. x_j va en unidades
naturales: diferencias de conteos (propio − rival), v en % del oro total y oro_dif en miles.

Escribe LoL_Probabilidad/herramienta/modelo.json con:
  * los coeficientes del ajuste con todas las partidas;
  * 200 juegos de coeficientes de ajustes con partidas remuestreadas (bootstrap por partida),
    de los que la página saca el rango del 95 %;
  * agregados para la página: partidas en juego por minuto, mediana del oro total por minuto,
    percentiles 1 y 99 de cada diferencia por minuto (para avisar de estados poco vistos),
    y las métricas de validación y de la prueba temporal.
Nada de eso es una fila de una partida.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

AQUI = pathlib.Path(__file__).resolve().parent
BASE = AQUI.parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(BASE / "modelos"))
import glm  # noqa: E402
from evaluar import DATOS, RESULTADOS, SEMILLA, leer_oof  # noqa: E402
from finalistas import ANTERIORES, ELEGIDOS, VARIANTES  # noqa: E402

SALIDA = BASE / "herramienta" / "modelo.json"
B = 200
T0, T1 = float(glm.NUDOS[0]), float(glm.NUDOS[-1])


def rectas(modelo, nombres):
    """Valor de A y de cada B_j en t = 1 y t = 40 (el modelo es lineal en x y en t recortado)."""
    dis, lr = modelo[0], modelo[-1]
    t = np.array([T0, T1])
    cero = {k: np.zeros(2) for k in nombres}
    logit = lambda v: dis.matriz(v, t) @ lr.coef_[0] + lr.intercept_[0]  # noqa: E731
    a = logit(cero)
    return [a.tolist()] + [(logit({**cero, k: np.ones(2)}) - a).tolist() for k in nombres]


def predecir(param, nombres, v, minuto):
    tt = (np.clip(minuto, T0, T1) - T0) / (T1 - T0)
    z = param[0][0] + (param[0][1] - param[0][0]) * tt
    for j, k in enumerate(nombres, start=1):
        z = z + v[k] * (param[j][0] + (param[j][1] - param[j][0]) * tt)
    return 1 / (1 + np.exp(-z))


def ajustar(nombre, d):
    fab, cols, notas = VARIANTES[nombre]
    modelo = fab().fit(d[cols], d["gane"].to_numpy())
    nombres = list(modelo[0].tv) + list(modelo[0].fijas)
    param = rectas(modelo, nombres)
    # Verificación: la fórmula exportada reproduce el pipeline en todas las filas.
    v = glm.variables(d[cols], nombres)
    err = np.abs(predecir(param, nombres, v, d["minuto"].to_numpy(float)) - modelo.predict_proba(d[cols])[:, 1]).max()
    assert err < 1e-9, f"{nombre}: la fórmula exportada no reproduce el modelo ({err:.2e})"

    rng = np.random.default_rng(SEMILLA)
    grupos = d.groupby("partida").indices
    llaves = list(grupos)
    boot = []
    for _ in range(B):
        filas = np.concatenate([grupos[llaves[i]] for i in rng.integers(0, len(llaves), len(llaves))])
        db = d.iloc[filas]
        mb = fab().fit(db[cols], db["gane"].to_numpy())
        boot.append(np.round(rectas(mb, nombres), 6).tolist())
    return {"nombre": nombre, "descripcion": notas, "variables": nombres,
            "param": np.round(param, 8).tolist(), "bootstrap": boot, "verificacion_max_error": float(err)}


def agregados(d):
    """Lo que la página necesita saber de los datos, solo en agregado."""
    en_juego = d.groupby("minuto")["partida"].nunique()
    minuto_max = int(en_juego[en_juego >= 30].index.max())
    mediana = d["oro_total"].groupby(d["minuto"]).median().reindex(range(0, minuto_max + 1)).interpolate().bfill()
    rangos = {}
    for c in ["asesinatos", "estructuras", "dragones", "atakhan", "nivel"]:
        dif = d[f"{c}_p"] - d[f"{c}_r"]
        q = dif.groupby(d["minuto"]).quantile([.01, .99]).unstack().reindex(range(1, minuto_max + 1)).ffill()
        rangos[f"dif_{c}"] = [q[.01].round(1).tolist(), q[.99].round(1).tolist()]
    q = d["v"].groupby(d["minuto"]).quantile([.01, .99]).unstack().reindex(range(1, minuto_max + 1)).ffill()
    rangos["v"] = [q[.01].round(1).tolist(), q[.99].round(1).tolist()]
    return {"partidas": int(d["partida"].nunique()),
            "partidas_prueba": int(d.loc[d["prueba_temporal"] == 1, "partida"].nunique()),
            "victorias": round(float(d.groupby("partida")["gane"].first().mean()), 4),
            "minuto_max": minuto_max,
            "en_juego": [int(en_juego.get(t, 0)) for t in range(0, minuto_max + 1)],
            "oro_total_mediana": [round(float(x)) for x in mediana.tolist()],
            # Suma típica de niveles de un equipo en cada minuto: el valor con que arranca la página.
            "nivel_mediana": [round(float(x)) for x in pd.concat([d["nivel_p"], d["nivel_r"]]).groupby(
                pd.concat([d["minuto"], d["minuto"]])).median().reindex(range(0, minuto_max + 1)).bfill().tolist()],
            "rangos": rangos}


def metricas():
    """Métricas de los elegidos y el mejor modelo de cada familia, leídos de resultados/."""
    todos = [json.loads(f.read_text(encoding="utf-8")) for f in RESULTADOS.glob("*.json")
             if f.name != "prueba_temporal.json"]
    prueba = json.loads((RESULTADOS / "prueba_temporal.json").read_text(encoding="utf-8"))
    filas = {}
    for modo, n in ELEGIDOS.items():
        cv = next(r for r in todos if r["nombre"] == n)
        filas[modo] = {"cv": {k: round(cv[k], 4) for k in ("perdida_log", "brier", "auc", "ece")},
                       "prueba": {k: round(prueba[n][k], 4) for k in ("perdida_log", "brier", "auc", "ece")}}

    def mejor(prefijo, con_oro):
        cands = [r for r in todos if r["nombre"].startswith(prefijo)
                 and ("v" in r["columnas"]) == con_oro and "asesinatos_p" in r["columnas"]]
        r = min(cands, key=lambda r: r["perdida_log"])
        return {"nombre": r["nombre"], "perdida_log": round(r["perdida_log"], 4)}

    filas["familias"] = {f"{fam}_{'oro' if oro else 'marcador'}": mejor(pre, oro)
                         for fam, pre in [("arboles", "arb_"), ("logistica", "glm_"), ("otros", "otr_")]
                         for oro in (False, True)}
    leer = lambda n: next(r for r in todos if r["nombre"] == n)  # noqa: E731
    filas["referencias"] = {n: round(leer(n)["perdida_log"], 4)
                            for n in ["base_proporcion", "base_oro_interaccion", "base_marcador_dif"]
                            + list(ANTERIORES.values())}
    filas["prueba"] = {n: round(r["perdida_log"], 4) for n, r in prueba.items()}
    return filas


def calibracion(nombre):
    """Observado contra predicho en 10 grupos de minutos de partida, fuera de muestra."""
    d = pd.read_parquet(DATOS)
    d = d[d["prueba_temporal"] == 0].reset_index(drop=True)
    p = leer_oof(nombre, d)
    grupo = pd.qcut(p, 10, labels=False, duplicates="drop")
    t = pd.DataFrame({"p": p, "y": d["gane"], "g": grupo}).groupby("g").mean()
    return [[round(float(a), 3), round(float(b), 3)] for a, b in zip(t["p"], t["y"])]


def main() -> int:
    d = pd.read_parquet(DATOS)
    salida = {"meta": {**agregados(d), "metricas": metricas(),
                       "calibracion": {m: calibracion(n) for m, n in ELEGIDOS.items()}}}
    for modo, n in ELEGIDOS.items():
        salida[modo] = ajustar(n, d)
        p = salida[modo]
        print(f"{modo}: {n}, verificación {p['verificacion_max_error']:.1e}")
        for j, (k, (a, b)) in enumerate(zip(["(minuto)"] + p["variables"], p["param"])):
            sb = np.array([bb[j] for bb in p["bootstrap"]])
            lo, hi = np.percentile(sb, [2.5, 97.5], axis=0)
            print(f"   {k:<16} t=1: {a:+.4f} [{lo[0]:+.3f}, {hi[0]:+.3f}]   "
                  f"t=40: {b:+.4f} [{lo[1]:+.3f}, {hi[1]:+.3f}]")
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{SALIDA.name}: {SALIDA.stat().st_size / 1e3:.0f} kB; minuto máximo {salida['meta']['minuto_max']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
