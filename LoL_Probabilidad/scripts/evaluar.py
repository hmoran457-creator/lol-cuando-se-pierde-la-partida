r"""Banco de pruebas común para los modelos de probabilidad de ganar.

Todos los modelos se comparan aquí, con las mismas reglas:

* Datos de DESARROLLO: las partidas anteriores a 2026-05 (963). Las de 2026-05 en adelante
  (232) son la PRUEBA TEMPORAL y solo se usan una vez, con los finalistas (`prueba_final`).
* Validación cruzada de 5 pliegues POR PARTIDA (StratifiedGroupKFold, semilla fija): todas las
  filas de una partida caen en el mismo pliegue, así que el modelo nunca ve otros minutos de la
  partida que predice.
* Métrica principal: pérdida logarítmica fuera de muestra, por fila. También Brier, AUC, error
  de calibración (ECE, 10 grupos) y la pérdida por tramo de minutos. El error estándar sale de la
  variación entre pliegues.
* `evaluar` guarda las predicciones fuera de muestra en datos/oof/ (privado) para comparar
  modelos partida por partida con `comparar`.

Uso desde otro script:

    from evaluar import evaluar, MARCADOR, ORO
    evaluar("logistica_simple", lambda: LogisticRegression(max_iter=1000), MARCADOR, "notas")

La fábrica devuelve un estimador nuevo con fit(X, y) y predict_proba(X); X es un DataFrame con
las columnas pedidas (la ingeniería de variables va dentro del estimador, p. ej. un Pipeline).
"""
from __future__ import annotations

import json
import pathlib
import time
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

BASE = pathlib.Path(__file__).resolve().parent.parent
DATOS = BASE / "datos" / "estado_por_minuto.parquet"
OOF = BASE / "datos" / "oof"
RESULTADOS = BASE / "resultados"
SEMILLA = 20261010

# Lo que se ve en el marcador dentro de una partida clasificatoria (_p mi equipo, _r el rival).
MARCADOR = ["minuto",
            "asesinatos_p", "asesinatos_r", "estructuras_p", "estructuras_r",
            "dragones_p", "dragones_r", "larvas_p", "larvas_r", "heraldos_p", "heraldos_r",
            "barones_p", "barones_r", "baron_activo_p", "baron_activo_r", "atakhan_p", "atakhan_r"]
# El oro: solo se conoce en repeticiones o como espectador.
ORO = ["minuto", "v", "oro_dif"]
MARCADOR_ORO = MARCADOR + ["v", "oro_dif"]
# Columnas que NO se deben usar: placas (no están en el marcador y su conteo cambia entre
# parches: hay partidas con 45 placas de un equipo) y las de identificación.
PROHIBIDAS = {"placas_p", "placas_r", "partida", "gane", "mes", "prueba_temporal", "oro_total"}
TRAMOS = [(1, 5), (6, 10), (11, 15), (16, 20), (21, 25), (26, 30), (31, 99)]


def cargar() -> tuple[pd.DataFrame, pd.DataFrame]:
    t = pd.read_parquet(DATOS)
    return t[t["prueba_temporal"] == 0].reset_index(drop=True), t[t["prueba_temporal"] == 1].reset_index(drop=True)


def pliegues(d: pd.DataFrame, k: int = 5) -> np.ndarray:
    """Número de pliegue de cada fila; estratificado por resultado, agrupado por partida."""
    asignado = np.empty(len(d), dtype=int)
    cv = StratifiedGroupKFold(n_splits=k, shuffle=True, random_state=SEMILLA)
    for i, (_, pru) in enumerate(cv.split(d, d["gane"], groups=d["partida"])):
        asignado[pru] = i
    return asignado


def _perdida(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def ece(y, p, grupos: int = 10) -> float:
    """Error de calibración esperado: |observado − predicho| promedio en 10 grupos de igual tamaño."""
    orden = np.argsort(p)
    total = 0.0
    for parte in np.array_split(orden, grupos):
        total += len(parte) * abs(y[parte].mean() - p[parte].mean())
    return total / len(y)


def metricas(d: pd.DataFrame, p: np.ndarray, plg: np.ndarray | None = None) -> dict:
    y = d["gane"].to_numpy()
    pl = _perdida(y, p)
    m = {"perdida_log": float(pl.mean()), "brier": float(brier_score_loss(y, p)),
         "auc": float(roc_auc_score(y, p)), "ece": float(ece(y, p))}
    if plg is not None:
        por = [pl[plg == i].mean() for i in np.unique(plg)]
        m["perdida_log_ee"] = float(np.std(por, ddof=1) / np.sqrt(len(por)))
    m["por_tramo"] = {f"{a}-{b if b < 99 else '+'}": float(pl[(d["minuto"] >= a) & (d["minuto"] <= b)].mean())
                      for a, b in TRAMOS}
    return m


def evaluar(nombre: str, fabrica: Callable, columnas: list[str], notas: str = "",
            guardar: bool = True) -> dict:
    """Validación cruzada por partida en los datos de desarrollo; guarda métricas y predicciones."""
    malas = set(columnas) & PROHIBIDAS
    assert not malas, f"columnas no permitidas: {malas}"
    d, _ = cargar()
    plg = pliegues(d)
    X, y = d[columnas], d["gane"].to_numpy()
    p = np.zeros(len(d))
    t0 = time.time()
    for i in range(plg.max() + 1):
        ent, pru = plg != i, plg == i
        modelo = fabrica().fit(X[ent], y[ent])
        p[pru] = modelo.predict_proba(X[pru])[:, 1]
    res = {"nombre": nombre, "columnas": columnas, "notas": notas,
           "segundos": round(time.time() - t0, 1), **metricas(d, p, plg)}
    if guardar:
        OOF.mkdir(parents=True, exist_ok=True)
        RESULTADOS.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"partida": d["partida"], "minuto": d["minuto"], "p": p}).to_parquet(
            OOF / f"{nombre}.parquet", index=False)
        (RESULTADOS / f"{nombre}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False),
                                                   encoding="utf-8")
    print(f"{nombre:<40} pérdida {res['perdida_log']:.4f} ± {res['perdida_log_ee']:.4f}  "
          f"brier {res['brier']:.4f}  auc {res['auc']:.4f}  ece {res['ece']:.4f}  ({res['segundos']} s)")
    return res


def leer_oof(nombre: str, d: pd.DataFrame) -> np.ndarray:
    """Predicciones fuera de muestra de un modelo, comprobando que van fila por fila con d."""
    o = pd.read_parquet(OOF / f"{nombre}.parquet")
    assert (o["partida"].to_numpy() == d["partida"].to_numpy()).all() and \
        (o["minuto"].to_numpy() == d["minuto"].to_numpy()).all(), f"{nombre}: filas desalineadas"
    return o["p"].to_numpy()


def comparar(a: str, b: str, B: int = 2000) -> dict:
    """Diferencia de pérdida b − a, remuestreando partidas (bootstrap). Negativa: b es mejor."""
    d, _ = cargar()
    pa, pb = (leer_oof(n, d) for n in (a, b))
    y = d["gane"].to_numpy()
    dif = pd.Series(_perdida(y, pb) - _perdida(y, pa)).groupby(d["partida"].to_numpy())
    suma, n = dif.sum().to_numpy(), dif.size().to_numpy()
    rng = np.random.default_rng(SEMILLA)
    idx = rng.integers(0, len(suma), (B, len(suma)))
    reps = suma[idx].sum(axis=1) / n[idx].sum(axis=1)
    return {"b_menos_a": float(suma.sum() / n.sum()),
            "ic95": [float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))]}


def prueba_final(nombre: str, fabrica: Callable, columnas: list[str]) -> dict:
    """Ajusta con todo el desarrollo y mide UNA vez en la prueba temporal. Solo para finalistas."""
    d, prueba = cargar()
    modelo = fabrica().fit(d[columnas], d["gane"].to_numpy())
    p = modelo.predict_proba(prueba[columnas])[:, 1]
    res = {"nombre": nombre, **metricas(prueba, p)}
    print(f"[prueba temporal] {nombre:<30} pérdida {res['perdida_log']:.4f}  brier {res['brier']:.4f}  "
          f"auc {res['auc']:.4f}  ece {res['ece']:.4f}")
    return res
