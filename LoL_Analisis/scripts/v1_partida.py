r"""V1 · La partida de ejemplo propia: la mediana de su arquetipo.

El planteamiento fijó cómo se elige, para que no sea la partida más dramática: se toma el
arquetipo de la historia que abre la presentación (A2, «iban ganando y perdieron») y,
dentro de él, la partida cuya curva v(t) está más cerca de la curva mediana del
arquetipo (distancia cuadrática media sobre los minutos que tienen las dos). Es un
algoritmo, no una elección a ojo: quien lo corra obtiene la misma partida.

Requiere haber corrido antes e5_e8.py (usa resultados/arquetipos_por_derrota.csv).
El seudónimo de la partida cambia con cada anonimización (llave efímera); la partida
elegida no, porque la regla depende solo de los datos.

Uso:  python LoL_Analisis/scripts/v1_partida.py [--arquetipo A2]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import e1_quiebre as e1  # noqa: E402
import e2_e4 as e24  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

ETIQUETA = {"DRAGON": "Dragón", "HORDE": "Larvas", "RIFTHERALD": "Heraldo",
            "BARON_NASHOR": "Barón", "ATAKHAN": "Atakhan"}


def elegir(v: pd.DataFrame, arq: pd.DataFrame, arquetipo: str) -> tuple[str, float, int]:
    ps = arq.loc[arq["arquetipo"] == arquetipo, "partida"]
    sub = v[v["partida"].isin(ps)]
    n_min = sub.groupby("minuto")["partida"].nunique()
    mediana = sub.groupby("minuto")["v"].median()[n_min >= len(ps) / 2]
    mejor, dist = None, np.inf
    for p, g in sub.groupby("partida"):
        s = g.set_index("minuto")["v"]
        comun = s.index.intersection(mediana.index)
        d = float(np.sqrt(((s[comun] - mediana[comun]) ** 2).mean()))
        if d < dist:
            mejor, dist = p, d
    return mejor, dist, len(ps)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arquetipo", default="A2")
    args = ap.parse_args()

    muestra, v, obj, _ = e24.cargar()
    arq = pd.read_csv(e1.RES / "arquetipos_por_derrota.csv")
    faltan = set(arq["partida"]) - set(v["partida"])
    assert not faltan, "arquetipos de otra anonimización: corre e5_e8.py otra vez"
    pid, dist, n = elegir(v, arq, args.arquetipo)

    g = v[v["partida"] == pid].sort_values("minuto")
    q = e1.quiebres(g).iloc[0]
    o = obj[obj["partida"] == pid].copy()
    o["min"] = o["ms"] / 60000
    dif = (g["oroPropio"] - g["oroRival"]).to_numpy()
    t, vv = g["minuto"].to_numpy(), g["v"].to_numpy() * 100
    i_max = int(np.argmax(vv))
    dur = float(muestra.loc[muestra["partida"] == pid, "duracionMin"].iloc[0])

    fig, ax = plt.subplots(figsize=(7.6, 3.4))
    ax.fill_between(t, 0, vv, where=vv >= 0, color=e1.AZUL, alpha=.25, lw=0, interpolate=True)
    ax.fill_between(t, 0, vv, where=vv < 0, color=e1.NARANJA, alpha=.25, lw=0, interpolate=True)
    ax.plot(t, vv, color=e1.TINTA, lw=2)
    ax.axhline(0, color=e1.SUAVE, lw=.8)
    alto = max(abs(vv).max(), 5) * 1.35
    for propio, y, color in ((True, alto * .86, e1.AZUL), (False, -alto * .86, e1.NARANJA)):
        sub = o[o["propio"] == propio]
        for _, r in sub.iterrows():
            marca = "D" if r["tipo"] == "ELITE_MONSTER_KILL" else "s"
            ax.plot(r["min"], y, marca, color=color, ms=6 if marca == "s" else 7,
                    mec="white", mew=1)
    ax.text(.4, alto * .86, "mi equipo", fontsize=7.5, color=e1.SUAVE, va="center")
    ax.text(.4, -alto * .86, "rival", fontsize=7.5, color=e1.SUAVE, va="center")
    if pd.notna(q["d2"]):
        ax.axvline(q["d2"], color=e1.TINTA, lw=1, ls="--")
        ax.text(q["d2"] - .4, alto * .55, f"quiebre (D2)\nminuto {int(q['d2'])}", fontsize=8,
                ha="right")
    # El rótulo va debajo de la línea, en la zona sin marcas, con una guía al pico.
    oro_max = f"{dif[i_max]:+,.0f}".replace(",", " ")
    ax.annotate(f"ventaja máxima: {vv[i_max]:+.1f} % del oro\n({oro_max} de oro, minuto {t[i_max]})",
                (t[i_max], vv[i_max]), xytext=(t[i_max] + 1, -alto * .45),
                fontsize=8, arrowprops={"arrowstyle": "-", "color": e1.SUAVE, "lw": .8})
    ax.set_ylim(-alto, alto)
    ax.set_xlim(0, t[-1] + .5)
    ax.set_xlabel("minuto")
    ax.set_ylabel("v(t), % del oro del mapa")
    # «Arriba» y «abajo» se cuentan cuadro por cuadro: el tramo no es continuo (en esta
    # partida hubo un minuto abajo temprano), así que «arriba hasta el minuto N» engañaba.
    arriba, abajo = int((vv > 0).sum()), [int(m) for m in t[vv < 0]]
    ax.set_title(f"V1 · Una derrota mía típica de {args.arquetipo}: arriba en oro {arriba} de "
                 f"{int(dur)} minutos, y aun así perdida", fontsize=10, loc="left")
    e1.guardar(fig, "v1_partida_ejemplo")

    # El remate: los últimos 2 minutos. Cuánta ventaja quedaba justo antes y quién tomó qué.
    t_remate = dur - 2
    remate = o[o["min"] >= t_remate]
    i_antes = int(np.searchsorted(t, int(t_remate)))

    r = {"arquetipo": args.arquetipo, "derrotas_en_el_arquetipo": n,
         "distancia_a_la_mediana_v": round(dist, 4), "duracion_min": dur,
         "ventaja_max_pct": round(float(vv[i_max]), 1), "ventaja_max_oro": int(dif[i_max]),
         "minuto_ventaja_max": int(t[i_max]), "d2": None if pd.isna(q["d2"]) else int(q["d2"]),
         "v_final_pct": round(float(vv[-1]), 1),
         "objetivos_propios": int(o["propio"].sum()), "objetivos_rival": int((~o["propio"]).sum()),
         "minutos_arriba": arriba, "minutos_abajo": abajo,
         "minuto_antes_del_remate": int(t[i_antes]), "v_antes_del_remate_pct": round(float(vv[i_antes]), 1),
         "objetivos_rival_remate": int((~remate["propio"]).sum()),
         "objetivos_propios_remate": int(remate["propio"].sum()),
         "monstruos_rival_despues_de_d2": [
             ETIQUETA.get(m, m) for m in o.loc[(~o["propio"]) & (o["tipo"] == "ELITE_MONSTER_KILL")
                                               & (o["min"] >= (q["d2"] or 0) - 1), "monsterType"]]}
    (e1.RES / "v1.json").write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(r, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
