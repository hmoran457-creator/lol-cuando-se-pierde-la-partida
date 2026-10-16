r"""Figuras de la presentación final, con el tema oscuro del mazo.

Son las mismas gráficas del reporte, calculadas con las mismas funciones (se importan
de LoL_Analisis/scripts), pero sin título —el titular lo pone la lámina— y con la
paleta del mazo: azul = mi equipo / ventaja, rojo = rival / desventaja, dorado solo
para anotaciones que siempre llevan texto.

Se exportan como SVG con el texto COMO TEXTO (svg.fonttype = none): construir.py las
incrusta en el HTML, así que heredan la tipografía Archivo de la página.

Uso:  python LoL_PresentacionFinal/scripts/figuras_deck.py
"""
from __future__ import annotations

import pathlib
import re
import sys

import numpy as np
import pandas as pd

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
sys.path.insert(0, str(RAIZ / "LoL_Analisis" / "scripts"))
import e1_quiebre as e1  # noqa: E402
import e2_e4 as e24  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

FIG = AQUI.parent / "figuras"
AZUL, ROJO, ORO, ORO_CLARO = "#0E9EB4", "#DE4361", "#BC8B2C", "#E8C87A"
# NEUTRO aclarado de #4A5D72 (2.6:1 sobre el fondo) a #5E7590 (3.7:1): las barras grises
# son marcas de datos y deben pasar 3:1.
TINTA, PERGAMINO, TENUE, LINEA, NEUTRO = "#DCE6F0", "#F0E6D2", "#8FA6BE", "#1E3A56", "#5E7590"
plt.rcParams.update({
    "svg.fonttype": "none", "font.family": "DejaVu Sans", "font.size": 13,
    "figure.facecolor": "none", "axes.facecolor": "none", "savefig.transparent": True,
    "figure.constrained_layout.use": True,
    "axes.edgecolor": LINEA, "axes.labelcolor": TENUE, "text.color": TINTA,
    "xtick.color": TENUE, "ytick.color": TENUE, "axes.grid": True,
    "grid.color": LINEA, "grid.linewidth": .8, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "lines.linewidth": 2.5,
})


def px(w: int, h: int) -> tuple[float, float]:
    """Tamaño en PÍXELES de la lámina. Un SVG de matplotlib mide en puntos (1/72 in),
    así que w/72 pulgadas da un viewBox de w unidades: incrustado a su ancho real no
    se estira, y una letra de 14 px se ve de 14 px. Si la figura se dibujara más
    chica y se estirara al ancho de la lámina, el texto crecería con ella."""
    return (w / 72, h / 72)


def guardar(fig, nombre: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    ruta = FIG / f"{nombre}.svg"
    # Sin bbox «tight» (cambiaría el tamaño) y sin fecha en los metadatos.
    fig.savefig(ruta, metadata={"Date": None})
    plt.close(fig)
    # La tipografía la pone la página: se cambia cualquier familia por Archivo.
    svg = ruta.read_text(encoding="utf-8")
    svg = re.sub(r"font-family:\s*[^;\"]*", "font-family: Archivo, sans-serif", svg)
    svg = re.sub(r"font: ([\d.]+px) '[^']*'", r"font: \1 Archivo, sans-serif", svg)
    ruta.write_text(svg, encoding="utf-8")


def embudo(pasos) -> None:
    etq = [p[0] for p in pasos]
    val = [p[1] for p in pasos]
    fig, ax = plt.subplots(figsize=px(840, 360))
    y = np.arange(len(val))[::-1]
    ax.barh(y, val, color=AZUL, height=.6)
    for yi, vi, prev in zip(y, val, [None] + val[:-1]):
        quita = f"   −{prev - vi}" if prev is not None and prev != vi else ""
        ax.text(vi + 15, yi, f"{vi:,}{quita}", va="center", fontsize=13, color=TINTA)
    ax.set_yticks(y, etq, fontsize=12)
    ax.set_xlim(0, max(val) * 1.3)
    ax.set_xticks([])
    ax.grid(False)
    ax.spines["bottom"].set_visible(False)
    guardar(fig, "embudo")


def v_mediana(v: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=px(1400, 330), sharey=True)
    for ax, gane, titulo in ((axes[0], 0, "Derrotas"), (axes[1], 1, "Victorias")):
        sub = v[v["gane"] == gane]
        q = sub.groupby("minuto")["v"].quantile([.25, .5, .75]).unstack()
        q = q[sub.groupby("minuto")["partida"].nunique() >= 30] * 100
        color = ROJO if gane == 0 else AZUL
        ax.fill_between(q.index, q[.25], q[.75], color=color, alpha=.18, lw=0)
        ax.plot(q.index, q[.5], color=color)
        ax.axhline(0, color=TENUE, lw=1, ls=(0, (4, 4)))
        ax.set_title(f"{titulo} · n = {sub['partida'].nunique():,}", loc="left", fontsize=14,
                     color=PERGAMINO)
        ax.set_xlabel("minuto")
    axes[0].set_ylabel("v(t), % del oro del mapa")
    guardar(fig, "v_mediana")


def d1_hist(q: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=px(1400, 300), sharey=True)
    bins = np.arange(0, 41) - .5
    for ax, gane, titulo in ((axes[0], 0, "Derrotas"), (axes[1], 1, "Victorias")):
        sub = q[q["gane"] == gane]
        ax.hist(sub["d1"].clip(upper=39), bins=bins, color=NEUTRO, rwidth=.8,
                weights=np.full(len(sub), 100 / len(sub)))
        med = sub["d1"].median()
        ax.axvline(med, color=ORO, lw=2)
        ax.text(med + .8, ax.get_ylim()[1] * .88, f"mediana: minuto {med:.0f}",
                color=ORO_CLARO, fontsize=13)
        ax.set_title(titulo, loc="left", fontsize=14, color=PERGAMINO)
        ax.set_xlabel("minuto de la mayor caída de v (D1)")
    axes[0].set_ylabel("% de partidas")
    guardar(fig, "d1_hist")


def h1(r: dict) -> None:
    fases = [("<15", "antes del min 15"), ("15-25", "min 15 a 25"), (">=25", "min 25 o después")]
    fig, axes = plt.subplots(1, 3, figsize=px(1400, 300), sharex=True)
    tope = max(d["ic95"][1] for f, _ in fases for d in r["por_fase"][f].values()) + .2
    for ax, (f, titulo) in zip(axes, fases):
        for y, k, color in ((1, "victorias", AZUL), (0, "derrotas", ROJO)):
            d = r["por_fase"][f][k]
            ax.plot(d["ic95"], [y, y], color=color, lw=4, solid_capstyle="round")
            ax.plot(d["tasa"], y, "o", color=color, ms=11, mec="#0A1A2B", mew=2.5)
            ax.text(d["tasa"], y + .3, f"{d['tasa']:.2f}", ha="center", fontsize=14, color=TINTA)
        ax.set_yticks([0, 1], ["Derrotas", "Victorias"] if ax is axes[0] else ["", ""], fontsize=13)
        ax.set_ylim(-.6, 1.75)
        ax.set_xlim(0, tope)
        ax.grid(axis="y", visible=False)
        ax.set_title(titulo, loc="left", fontsize=14, color=PERGAMINO)
    axes[1].set_xlabel("objetivos propios por minuto con ventaja real")
    guardar(fig, "h1_fases")


def h2(nulas: dict, d: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=px(1400, 320), sharex=True, sharey=True)
    paneles = (("nula_registrada", "Azar registrado: toda la partida", "p_menor", "por debajo"),
               ("nula_corregida", "Azar corregido: desde el minuto 5", "p_mayor", "por encima"))
    for ax, (clave, titulo, pk, lado) in zip(axes, paneles):
        ax.hist(nulas[clave] * 100, bins=40, color=NEUTRO, rwidth=.9)
        ax.axvline(d["observado"] * 100, color=ORO, lw=3)
        ax.text(.03, .93, f"observado {100 * d['observado']:.1f} %\n"
                f"azar {100 * d[clave]['media']:.1f} %\n{lado} · p = {d[clave][pk]:.3f}",
                transform=ax.transAxes, va="top", fontsize=13, color=ORO_CLARO)
        ax.set_title(titulo, loc="left", fontsize=14, color=PERGAMINO)
        ax.grid(axis="y", visible=False)
        ax.set_yticks([])
        ax.spines["left"].set_visible(False)
        ax.set_xlabel("% de quiebres a ±1 min de un objetivo del rival")
    guardar(fig, "h2_nulas")


def h3(c: pd.DataFrame, punto: dict | None = None) -> None:
    c = c[c["en_riesgo"] >= 30]
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=px(1400, 470), sharex=True,
                                  gridspec_kw={"height_ratios": [3, 1]})
    ax.fill_between(c["minuto"], c["lo"] * 100, c["hi"] * 100, color=AZUL, alpha=.2, lw=0)
    ax.plot(c["minuto"], c["p"] * 100, color=AZUL)
    for m in (5, 15, 30):
        f = c[c["minuto"] == m].iloc[0]
        ax.plot(m, f["p"] * 100, "o", color=AZUL, ms=9, mec="#0A1A2B", mew=2)
        ax.text(m + .5, f["p"] * 100 + 4, f"{100 * f['p']:.0f} %", fontsize=15, color=TINTA)
    ax.set_ylabel("% que terminó ganando")
    ax.set_ylim(0, 70)
    p = (punto or {}).get("por_umbral", {}).get(f"{(punto or {}).get('umbral_principal', 0):.2f}")
    if p:                                   # el punto sin regreso de H3 (umbral principal)
        u = 100 * punto["umbral_principal"]
        ax.axhline(u, color=ORO, lw=1.5, ls=(0, (4, 4)))
        ax.axvline(p["minuto"], color=ORO, lw=2)
        ax.text(p["minuto"] + .5, 58, f"desde el minuto {p['minuto']}:\nmenos de {u:.0f} %",
                fontsize=15, color=ORO_CLARO, va="top")
    ax2.bar(c["minuto"], c["en_riesgo"], color=NEUTRO, width=.75)
    ax2.set_ylabel("en riesgo")
    ax2.set_xlabel("minuto en que la partida va abajo (v ≤ −5 %)")
    ax2.grid(axis="x", visible=False)
    guardar(fig, "h3_curva")


def curvas_arquetipo(v: pd.DataFrame, arq: pd.DataFrame) -> None:
    orden = ["A1", "A2", "A3", "A4", "Sin clasificar"]
    fig, axes = plt.subplots(1, 5, figsize=px(1400, 290), sharey=True)
    for ax, a in zip(axes, orden):
        ps = arq.loc[arq["arquetipo"] == a, "partida"]
        sub = v[v["partida"].isin(ps)]
        for _, g in sub.groupby("partida"):
            ax.plot(g["minuto"], g["v"] * 100, color=AZUL, lw=.6, alpha=.13)
        n_min = sub.groupby("minuto")["partida"].nunique()
        med = sub.groupby("minuto")["v"].median()[n_min >= max(10, len(ps) // 5)] * 100
        ax.plot(med.index, med.values, color=PERGAMINO, lw=2.5)
        ax.axhline(0, color=TENUE, lw=1, ls=(0, (4, 4)))
        ax.set_title(f"{a.replace('Sin clasificar', 'Sin clasif.')} · {len(ps)}", loc="left",
                     fontsize=14, color=PERGAMINO)
        ax.set_ylim(-25, 25)
        ax.set_xlim(0, 45)
    axes[0].set_ylabel("v(t), %")
    guardar(fig, "curvas_arquetipo")


def main() -> int:
    import json
    muestra, v, obj, _ = e24.cargar()
    _, pasos = e1.filtrar(pd.read_csv(e1.PUBLICO / "partidas.csv", dtype={"parche": str}))
    q = e1.quiebres(v)
    r = json.loads((e1.RES / "e2_e4.json").read_text(encoding="utf-8"))
    nulas = e24.e3(v, obj, q).pop("_nulas_derrotas")   # mismas semillas: mismas nulas
    embudo([("Cola 420, partidas únicas", pasos[0][1])] + pasos[1:])
    v_mediana(v)
    d1_hist(q)
    h1(r["e2_h1"])
    h2(nulas, r["e3_h2"]["derrotas"])
    h3(pd.read_csv(e1.RES / "e4_remontada_por_minuto.csv"), r.get("e4_punto_sin_regreso"))
    curvas_arquetipo(v, pd.read_csv(e1.RES / "arquetipos_por_derrota.csv"))
    print("figuras:", ", ".join(sorted(p.stem for p in FIG.glob("*.svg"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
