r"""Tabla de entrenamiento del modelo de probabilidad de ganar: una fila por partida y minuto.

    python LoL_Probabilidad/scripts/datos.py

Cada fila describe el estado de una partida en el cuadro t (el minuto t:00), contado desde mi
lado, y la etiqueta es si mi equipo ganó. Se usan las 1,195 partidas del embudo del proyecto y
los minutos 1 .. último − 1 (el último cuadro es el final de la partida).

Lo que ya pasó en el cuadro t son los eventos con floor(ms / 60000) < t: la convención de E2-E4
(un evento del minuto m ocurre entre los cuadros m y m + 1).

Columnas (sufijo _p = mi equipo, _r = el rival):
  marcador, lo que se ve dentro de la partida:
    asesinatos, estructuras (torres e inhibidores), dragones, larvas, heraldos, barones,
    atakhan, baron_activo (barón tomado hace menos de 3 minutos: la mejora dura 3 min)
  oro, lo que NO se ve en una partida clasificatoria (solo en repeticiones o como espectador):
    oro_dif (oro propio − rival) y v (oro_dif / oro total × 100); oro_total no es variable de
    ningún modelo, solo sirve para la mediana del oro por minuto de la página
  placas (oro de placas de torre: tampoco está en el marcador)

Lee tablas por participante que no se publican; la salida va a LoL_Probabilidad/datos/, que
está en .gitignore. Lo único que sale de esa carpeta son métricas y coeficientes agregados.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
sys.path.insert(0, str(RAIZ / "LoL_Analisis" / "scripts"))
import e1_quiebre as e1  # noqa: E402

PRIVADO = RAIZ / "LoL_Datos" / "anonimizado"
SALIDA = AQUI.parent / "datos" / "estado_por_minuto.parquet"
MONSTRUOS = {"DRAGON": "dragones", "HORDE": "larvas", "RIFTHERALD": "heraldos",
             "BARON_NASHOR": "barones", "ATAKHAN": "atakhan"}
# Prueba temporal: las partidas de estos meses nunca se usan para elegir el modelo.
MES_PRUEBA = "2026-05"


def construir() -> pd.DataFrame:
    partidas = pd.read_csv(e1.PUBLICO / "partidas.csv", dtype={"parche": str})
    muestra, _ = e1.filtrar(partidas)
    v = e1.medida_v(pd.read_csv(e1.PUBLICO / "oro_equipo.csv"), muestra)
    ultimo = v.groupby("partida")["minuto"].max()
    v = v[(v["minuto"] >= 1) & (v["minuto"] < v["partida"].map(ultimo))].copy()
    lado = muestra.set_index("partida")["equipoPropio"]

    ev = pd.read_csv(PRIVADO / "eventos.csv",
                     usecols=["partida", "tipo", "ms", "equipoAutor", "equipoVictima", "killerId", "monsterType"])
    ev = ev[ev["partida"].isin(muestra["partida"])].copy()
    ev["m"] = ev["ms"] // 60000

    # Quién se lleva cada evento, desde mi lado. Las ejecuciones (muertes ante una torre o los
    # súbditos, killerId 0) no suman al marcador del juego, que es lo que se escribe en la página.
    k = ev[(ev["tipo"] == "CHAMPION_KILL") & (ev["killerId"] > 0)].copy()
    k["quien"] = np.where(k["equipoVictima"] == k["partida"].map(lado), "r", "p")   # muere uno mío: punto del rival
    k["clase"] = "asesinatos"
    o = ev[ev["tipo"].isin(["BUILDING_KILL", "TURRET_PLATE_DESTROYED", "ELITE_MONSTER_KILL"])
           & ev["equipoAutor"].isin([100, 200])].copy()
    o["quien"] = np.where(o["equipoAutor"] == o["partida"].map(lado), "p", "r")
    o["clase"] = np.select([o["tipo"] == "BUILDING_KILL", o["tipo"] == "TURRET_PLATE_DESTROYED"],
                           ["estructuras", "placas"], o["monsterType"].map(MONSTRUOS).fillna(""))
    todos = pd.concat([k, o])
    todos = todos[todos["clase"] != ""]
    todos["col"] = todos["clase"] + "_" + todos["quien"]

    # Conteo por minuto y acumulado: en el cuadro t cuentan los eventos con m < t.
    por_min = todos.groupby(["partida", "m", "col"]).size().unstack(fill_value=0)
    cols = sorted(por_min.columns)
    filas = v[["partida", "minuto"]].copy()
    filas["m"] = filas["minuto"] - 1                       # acumulado hasta el minuto t − 1
    rejilla = pd.MultiIndex.from_frame(filas[["partida", "m"]])
    completo = por_min.reindex(
        pd.MultiIndex.from_tuples([(p, m) for p, u in ultimo.items() for m in range(int(u) + 1)],
                                  names=["partida", "m"]), fill_value=0)
    acumulado = completo.groupby(level="partida").cumsum()
    estado = acumulado.reindex(rejilla).fillna(0).astype(int).reset_index(drop=True)

    # Barón activo: tomado en los minutos t − 3 .. t − 1.
    bar = todos[todos["clase"] == "barones"]
    for q in ("p", "r"):
        b = bar[bar["quien"] == q].groupby(["partida", "m"]).size()
        activo = np.zeros(len(filas), dtype=int)
        for atras in (1, 2, 3):
            idx = pd.MultiIndex.from_arrays([filas["partida"], filas["minuto"] - atras])
            activo += b.reindex(idx).fillna(0).to_numpy(dtype=int)
        estado[f"baron_activo_{q}"] = (activo > 0).astype(int)

    tabla = pd.concat([filas[["partida", "minuto"]].reset_index(drop=True), estado], axis=1)
    tabla["oro_dif"] = (v["oroPropio"] - v["oroRival"]).to_numpy()
    tabla["oro_total"] = (v["oroPropio"] + v["oroRival"]).to_numpy()     # solo para agregados
    tabla["v"] = (v["v"] * 100).to_numpy()
    tabla["azul"] = (tabla["partida"].map(lado) == 100).astype(int).to_numpy()
    info = muestra.set_index("partida")
    tabla["gane"] = tabla["partida"].map(info["gane"]).astype(int)
    tabla["mes"] = tabla["partida"].map(info["mes"])
    tabla["prueba_temporal"] = (tabla["mes"] >= MES_PRUEBA).astype(int)
    for c in cols:
        tabla[c] = tabla[c].astype(int)
    return tabla


def main() -> int:
    tabla = construir()
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    tabla.to_parquet(SALIDA, index=False)
    n = tabla.groupby("prueba_temporal")["partida"].nunique()
    print(f"{len(tabla):,} filas · {tabla['partida'].nunique():,} partidas "
          f"({n.get(0, 0)} para elegir el modelo, {n.get(1, 0)} de prueba temporal desde {MES_PRUEBA})")
    print("columnas:", ", ".join(tabla.columns))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
