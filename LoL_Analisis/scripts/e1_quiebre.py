r"""Medida v(t) y experimento E1: ¿en qué minuto se quiebra una partida perdida?

Solo usa las tablas PÚBLICAS de la anonimización (partidas.csv y oro_equipo.csv), así
que cualquiera puede reproducirlo desde el repositorio sin el JSON crudo.

Definiciones, fijadas en el planteamiento ANTES de ver estos datos:

* v(t) = (oro de mi equipo - oro del rival) / oro total de los diez, en el cuadro t.
  Los cuadros se indexan por posición (minuto = número de cuadro), nunca por
  timestamp // 60000.
* D1 (principal): el minuto de la mayor caída de v en un solo cuadro,
  argmin_t [v(t) - v(t-1)]. En empate, el primero.
* D2 (control): el último cambio de signo de v hacia abajo: el último t con
  v(t-1) >= 0 y v(t) < 0. Si v nunca cruza hacia abajo, D2 no existe y se reporta.
* E1 reporta el % de derrotas con |D1 - D2| > 2 minutos (con intervalo de Wilson).

Las victorias entran como control: también tienen su mayor caída de v.

Uso:  python LoL_Analisis/scripts/e1_quiebre.py [--publico <carpeta>]
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
PUBLICO = ROOT.parent / "LoL_Datos" / "anonimizado" / "publico"
FIG, TAB, RES = ROOT / "figuras", ROOT / "tablas", ROOT / "resultados"

# Paleta del proyecto, validada con el script de la guía de visualización (pasa CVD).
AZUL, NARANJA = "#2a78d6", "#eb6834"
TINTA, SUAVE, REJILLA, GRIS = "#1a1a19", "#52514e", "#d9d8d4", "#b9c0c8"
plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 110, "font.family": "DejaVu Sans", "font.size": 9,
    "axes.edgecolor": SUAVE, "axes.labelcolor": TINTA, "text.color": TINTA,
    "xtick.color": SUAVE, "ytick.color": SUAVE, "axes.grid": True,
    "grid.color": REJILLA, "grid.linewidth": .7, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white", "legend.frameon": False,
    "lines.linewidth": 2,
})


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (c - h, c + h)


def filtrar(partidas: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, int]]]:
    """El embudo del planteamiento, rehecho desde la tabla pública."""
    p = partidas[partidas["equipoPropio"].notna()]
    pasos = [("Con registro y línea temporal", len(p))]
    for etq, m in [
        ("Cola 420 confirmada en el registro", p["cola"] == 420),
        ("Diez participantes", p["jugadores"] == 10),
        ("Sin remake", p["rendicionTemprana"] == 0),
        ("Duración de al menos 5 minutos", p["duracionMin"] >= 5),
        ("Sin rendición antes del minuto 10", ~((p["rendicion"] == 1) & (p["duracionMin"] < 10))),
    ]:
        p = p[m.loc[p.index]]
        pasos.append((etq, len(p)))
    return p, pasos


def medida_v(oro: pd.DataFrame, partidas: pd.DataFrame) -> pd.DataFrame:
    """v(t) por partida y minuto, desde el lado propio."""
    ancho = oro.pivot_table(index=["partida", "minuto"], columns="teamId",
                            values="oroTotal", aggfunc="sum").reset_index()
    ancho = ancho.merge(partidas[["partida", "equipoPropio", "gane", "duracionMin"]],
                        on="partida", how="inner")
    propio = np.where(ancho["equipoPropio"] == 100, ancho[100], ancho[200])
    rival = np.where(ancho["equipoPropio"] == 100, ancho[200], ancho[100])
    ancho["oroPropio"], ancho["oroRival"] = propio, rival
    ancho["v"] = (propio - rival) / (propio + rival)
    return ancho.sort_values(["partida", "minuto"])[
        ["partida", "minuto", "oroPropio", "oroRival", "v", "gane", "duracionMin"]]


def quiebres(v: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for pid, g in v.groupby("partida", sort=False):
        serie = g["v"].to_numpy()
        minutos = g["minuto"].to_numpy()
        assert (np.diff(minutos) == 1).all() and minutos[0] == 0, "cuadros no contiguos"
        dv = np.diff(serie)                                  # dv[i] = v(i+1) - v(i)
        i1 = int(np.argmin(dv))                              # primer mínimo en empate
        cruces = np.where((serie[:-1] >= 0) & (serie[1:] < 0))[0]
        filas.append({
            "partida": pid, "gane": int(g["gane"].iloc[0]), "ultimo": int(minutos[-1]),
            "d1": int(minutos[i1 + 1]), "caida_d1": float(dv[i1]),
            "d1_en_ultimo_cuadro": int(i1 + 1 == len(serie) - 1),
            "d2": int(minutos[cruces[-1] + 1]) if len(cruces) else None,
            "v_final": float(serie[-1]), "v_max": float(serie.max()), "v_min": float(serie.min()),
        })
    return pd.DataFrame(filas)


def fig_embudo(pasos: list[tuple[str, int]], total_lista: int) -> None:
    etq = ["Cola 420, partidas únicas"] + [p[0] for p in pasos[1:]]
    val = [pasos[0][1]] + [p[1] for p in pasos[1:]]
    fig, ax = plt.subplots(figsize=(7.4, 2.9))
    y = np.arange(len(val))[::-1]
    ax.barh(y, val, color=AZUL, height=.62)
    for yi, vi, prev in zip(y, val, [None] + val[:-1]):
        quita = f"  (-{prev - vi})" if prev is not None and prev != vi else ""
        ax.text(vi + 8, yi, f"{vi:,}{quita}".replace(",", " "), va="center", fontsize=8.5)
    ax.set_yticks(y, etq)
    ax.set_xlim(0, max(val) * 1.18)
    ax.set_xlabel("partidas")
    ax.grid(axis="y", visible=False)
    ax.set_title(f"De {val[0]:,} partidas de cola 420 quedan {val[-1]:,}".replace(",", " "),
                 fontsize=10, loc="left")
    guardar(fig, "v8_embudo")


def fig_v(v: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 2.9), sharey=True)
    for ax, gane, titulo in ((axes[0], 0, "Derrotas"), (axes[1], 1, "Victorias")):
        sub = v[v["gane"] == gane]
        q = sub.groupby("minuto")["v"].quantile([.25, .5, .75]).unstack()
        n = sub.groupby("minuto")["partida"].nunique()
        q = q[n >= 30]                                  # con menos de 30 partidas, no se dibuja
        ax.fill_between(q.index, q[.25] * 100, q[.75] * 100, color=AZUL, alpha=.18, lw=0)
        ax.plot(q.index, q[.5] * 100, color=AZUL)
        ax.axhline(0, color=SUAVE, lw=.8)
        ax.set_title(f"{titulo} (n = {sub['partida'].nunique():,})".replace(",", " "),
                     fontsize=9.5, loc="left")
        ax.set_xlabel("minuto")
    axes[0].set_ylabel("v(t), % del oro del mapa")
    fig.suptitle("v(t) de mi equipo: mediana y rango intercuartil", fontsize=10.5,
                 x=.01, ha="left", y=1.02)
    guardar(fig, "v_mediana")


def fig_d1(q: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 2.7), sharey=True)
    bins = np.arange(0, q["d1"].max() + 2) - .5
    for ax, gane, titulo in ((axes[0], 0, "Derrotas"), (axes[1], 1, "Victorias")):
        sub = q[q["gane"] == gane]
        ax.hist(sub["d1"], bins=bins, color=AZUL, rwidth=.8,
                weights=np.full(len(sub), 100 / len(sub)))
        ax.axvline(sub["d1"].median(), color=TINTA, lw=1, ls="--")
        ax.text(sub["d1"].median() + .6, ax.get_ylim()[1] * .9,
                f"mediana {sub['d1'].median():.0f}", fontsize=8)
        ax.set_title(titulo, fontsize=9.5, loc="left")
        ax.set_xlabel("minuto de la mayor caída de v (D1)")
    axes[0].set_ylabel("% de partidas")
    fig.suptitle("La mayor caída de v (D1) llega igual de temprano al ganar que al perder",
                 fontsize=10.5, x=.01, ha="left", y=1.02)
    guardar(fig, "d1_minuto")


def fig_v9(q: pd.DataFrame, pct: float) -> None:
    sub = q[(q["gane"] == 0) & q["d2"].notna()]
    rng = np.random.default_rng(7)                         # solo para el jitter visual
    jx = sub["d2"] + rng.uniform(-.25, .25, len(sub))
    jy = sub["d1"] + rng.uniform(-.25, .25, len(sub))
    lim = max(sub["d1"].max(), sub["d2"].max()) + 2
    fig, ax = plt.subplots(figsize=(4.6, 4.3))
    ax.fill_between([0, lim], [-2, lim - 2], [2, lim + 2], color=GRIS, alpha=.35, lw=0,
                    label="|D1 − D2| ≤ 2 min")
    ax.plot([0, lim], [0, lim], color=SUAVE, lw=.8)
    ax.scatter(jx, jy, s=10, color=AZUL, alpha=.55, lw=0)
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.set_xlabel("D2: último cruce de v hacia abajo (min)")
    ax.set_ylabel("D1: mayor caída de v (min)")
    ax.legend(loc="upper left", fontsize=8)
    ax.set_title(f"Las dos definiciones discrepan en el {pct:.0f} % de las derrotas",
                 fontsize=10, loc="left")
    guardar(fig, "v9_d1_vs_d2")


def guardar(fig, nombre: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    # Sin fecha de creación: así volver a correr el análisis no cambia los PDF si los
    # datos no cambiaron (antes cada corrida ensuciaba el repositorio).
    fig.savefig(FIG / f"{nombre}.pdf", bbox_inches="tight", metadata={"CreationDate": None})
    fig.savefig(FIG / f"{nombre}.png", bbox_inches="tight", dpi=130)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--publico", type=pathlib.Path, default=PUBLICO)
    args = ap.parse_args()

    partidas = pd.read_csv(args.publico / "partidas.csv", dtype={"parche": str})  # 15.10 ≠ 15.1
    oro = pd.read_csv(args.publico / "oro_equipo.csv")
    muestra, pasos = filtrar(partidas)
    v = medida_v(oro, muestra)
    q = quiebres(v)

    der, vic = q[q["gane"] == 0], q[q["gane"] == 1]
    con_d2 = der[der["d2"].notna()]
    desac = int((abs(con_d2["d1"] - con_d2["d2"]) > 2).sum())
    lo, hi = wilson(desac, len(con_d2))
    r = {
        "embudo": [{"paso": e, "n": n} for e, n in pasos],
        "partidas": len(q), "derrotas": len(der), "victorias": len(vic),
        "v0_cero": bool((v[v["minuto"] == 0]["v"].abs() < 1e-12).all()),
        "e1": {
            "derrotas_con_d2": len(con_d2), "derrotas_sin_d2": int(der["d2"].isna().sum()),
            "desacuerdo_mas_de_2_min": desac,
            "pct_desacuerdo": round(100 * desac / len(con_d2), 1),
            "ic95_wilson": [round(100 * lo, 1), round(100 * hi, 1)],
            "mediana_abs_dif": float((con_d2["d1"] - con_d2["d2"]).abs().median()),
            "d1_antes_de_d2": int((con_d2["d1"] < con_d2["d2"] - 2).sum()),
            "d1_despues_de_d2": int((con_d2["d1"] > con_d2["d2"] + 2).sum()),
        },
        "d1": {
            "mediana_derrotas": float(der["d1"].median()), "mediana_victorias": float(vic["d1"].median()),
            "pct_d1_antes_min5_derrotas": round(100 * (der["d1"] < 5).mean(), 1),
            "pct_d1_antes_min5_victorias": round(100 * (vic["d1"] < 5).mean(), 1),
            "pct_d1_ultimo_cuadro_derrotas": round(100 * der["d1_en_ultimo_cuadro"].mean(), 1),
            "caida_mediana_derrotas_pp": round(100 * der["caida_d1"].median(), 2),
            "caida_mediana_victorias_pp": round(100 * vic["caida_d1"].median(), 2),
        },
        "d2": {"mediana_derrotas": float(con_d2["d2"].median())},
        "derrotas_nunca_detras": int((der["v_min"] >= 0).sum()),
        "derrotas_terminan_arriba": int((der["v_final"] > 0).sum()),
    }

    RES.mkdir(parents=True, exist_ok=True)
    (RES / "e1.json").write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
    q.to_csv(RES / "quiebres_por_partida.csv", index=False)

    fig_embudo(pasos, 0)
    fig_v(v)
    fig_d1(q)
    fig_v9(q, r["e1"]["pct_desacuerdo"])

    print(json.dumps(r, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
