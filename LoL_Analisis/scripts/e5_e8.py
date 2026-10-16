r"""Arquetipos de derrota (E5), sensibilidad (E6), estabilidad (E7) y cuentas/rol (E8).

Las reglas son las registradas ANTES de ver los datos: la lámina de arquetipos del
planteamiento y su implementación de referencia, LoL_Presentacion/scripts/
probe_umbrales.py. Se siguen al pie de la letra, con UN cambio acordado y documentado:
A3 usa D2 (último cruce de v hacia abajo) en vez de «la mayor caída de v», porque E1
mostró que esa caída (D1) mide el ruido de los primeros minutos.

    v = diferencia de oro / oro total, en %; dif = diferencia de oro absoluta.
    ventaja real:     v >= U y dif >= 1,500         (U = 5 %)
    desventaja real:  v <= -U y dif <= -1,500
    A4 · v <= -10 % en algún minuto 0..15, y v <= -U en todos los minutos >= 15
    A2 · racha de >= 3 minutos con ventaja real, y alguna ventaja real en el minuto >= 15
    A1 · desventaja real en el minuto 15, y dif <= 0 en todos los minutos >= 15
    A3 · |v| < U en todos los minutos antes de D2, y un monstruo épico del rival
         (dragón, larvas, heraldo, barón, Atakhan) con |minuto - D2| <= 1
    Orden A4 -> A2 -> A1 -> A3; lo demás queda «sin clasificar».

E6 mueve U a 4 % y 6 % (la decisiva de 10 % no se mueve). E7 parte la muestra por mes.
E8 compara cuentas y repite todo solo con las partidas en BOTTOM.

Uso:  python LoL_Analisis/scripts/e5_e8.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import e1_quiebre as e1  # noqa: E402
import e2_e4 as e24  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

ARQ = ["A1", "A2", "A3", "A4", "Sin clasificar"]
NOMBRE = {"A1": "A1 · Derrota desde línea", "A2": "A2 · Ventaja desperdiciada",
          "A3": "A3 · Decidida en un objetivo", "A4": "A4 · Muy desigual",
          "Sin clasificar": "Sin clasificar"}
DECISIVA, PISO, RACHA, TARDE = 10.0, 1500, 3, 15


def clasificar(v: np.ndarray, dif: np.ndarray, d2: int | None, obj_rival: np.ndarray,
               u: float = 5.0) -> str:
    """v en %, dif en oro, obj_rival en minutos (float). Implementación de referencia."""
    n = len(v)
    vent = (v >= u) & (dif >= PISO)
    if (v[:min(TARDE + 1, n)] <= -DECISIVA).any() and (v[TARDE:] <= -u).all():
        return "A4"
    racha = mejor = 0
    for x in vent:
        racha = racha + 1 if x else 0
        mejor = max(mejor, racha)
    if mejor >= RACHA and vent[TARDE:].any():
        return "A2"
    if n > TARDE and v[TARDE] <= -u and dif[TARDE] <= -PISO and (dif[TARDE:] <= 0).all():
        return "A1"
    if d2 is not None and (np.abs(v[:d2]) < u).all() and (np.abs(obj_rival - d2) <= 1).any():
        return "A3"
    return "Sin clasificar"


def preparar():
    muestra, v, obj, _ = e24.cargar()
    q = e1.quiebres(v)
    rival = obj[(~obj["propio"]) & (obj["tipo"] == "ELITE_MONSTER_KILL")]
    rival_por = {p: g["ms"].to_numpy() / 60000 for p, g in rival.groupby("partida")}
    series = {p: (g["v"].to_numpy() * 100, (g["oroPropio"] - g["oroRival"]).to_numpy())
              for p, g in v.groupby("partida", sort=False)}
    d2 = dict(zip(q["partida"], q["d2"]))
    return muestra, v, obj, q, series, d2, rival_por


def arquetipos(derrotas: list[str], series, d2, rival_por, u: float = 5.0) -> pd.Series:
    vacio = np.array([])
    return pd.Series({p: clasificar(*series[p], None if pd.isna(d2[p]) else int(d2[p]),
                                    rival_por.get(p, vacio), u) for p in derrotas})


def frecuencias(arq: pd.Series) -> pd.DataFrame:
    n = len(arq)
    filas = []
    for a in ARQ:
        k = int((arq == a).sum())
        lo, hi = e1.wilson(k, n)
        filas.append({"arquetipo": a, "n": k, "p": k / n, "lo": lo, "hi": hi})
    return pd.DataFrame(filas)


# ─────────────────────────────────────────── figuras
def fig_v6(f: pd.DataFrame, n: int) -> None:
    fig, ax = plt.subplots(figsize=(6.6, 2.6))
    y = np.arange(len(f))[::-1]
    colores = [e1.GRIS if a == "Sin clasificar" else e1.AZUL for a in f["arquetipo"]]
    ax.barh(y, f["p"] * 100, color=colores, height=.6)
    ax.errorbar(f["p"] * 100, y, xerr=[(f["p"] - f["lo"]) * 100, (f["hi"] - f["p"]) * 100],
                fmt="none", ecolor=e1.TINTA, elinewidth=1, capsize=3)
    for yi, (_, r) in zip(y, f.iterrows()):
        ax.text(r["hi"] * 100 + 1, yi, f"{100 * r['p']:.0f} %  ({r['n']})", va="center", fontsize=8.5)
    ax.set_yticks(y, [NOMBRE[a] for a in f["arquetipo"]])
    ax.set_xlim(0, max(f["hi"]) * 100 + 14)
    ax.set_xlabel("% de las derrotas (IC 95 % de Wilson)")
    ax.grid(axis="y", visible=False)
    mayor = f.iloc[f["p"].idxmax()]["arquetipo"]
    ax.set_title(f"E5 · Cómo se reparten mis {n} derrotas"
                 + ("; casi la mitad no cae en ninguna regla" if mayor == "Sin clasificar"
                    and f["p"].max() > .4 else ""), fontsize=10, loc="left")
    e1.guardar(fig, "v6_arquetipos")


def fig_v2(v: pd.DataFrame, arq: pd.Series) -> None:
    fig, axes = plt.subplots(1, 5, figsize=(9.2, 2.6), sharey=True)
    for ax, a in zip(axes, ARQ):
        ps = arq[arq == a].index
        sub = v[v["partida"].isin(ps)]
        for _, g in sub.groupby("partida"):
            ax.plot(g["minuto"], g["v"] * 100, color=e1.AZUL, lw=.5, alpha=.12)
        n_min = sub.groupby("minuto")["partida"].nunique()
        med = sub.groupby("minuto")["v"].median()[n_min >= max(10, len(ps) // 5)] * 100
        ax.plot(med.index, med.values, color=e1.TINTA, lw=2)
        ax.axhline(0, color=e1.SUAVE, lw=.7)
        ax.set_title(f"{a} (n={len(ps)})", fontsize=9, loc="left")
        ax.set_xlabel("minuto")
        ax.set_ylim(-30, 30)
    axes[0].set_ylabel("v(t), %")
    fig.suptitle("V2 · v(t) de cada derrota por arquetipo (línea negra: mediana)",
                 fontsize=10.5, x=.01, ha="left", y=1.04)
    e1.guardar(fig, "v2_arquetipos_curvas")


def fig_v7(tabla: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 2.1))
    datos = tabla[ARQ].to_numpy()
    ax.imshow(datos, cmap="Blues", aspect="auto", vmin=0, vmax=datos.max() * 1.15)
    for i in range(datos.shape[0]):
        for j in range(datos.shape[1]):
            ax.text(j, i, str(datos[i, j]), ha="center", va="center", fontsize=9,
                    color="white" if datos[i, j] > datos.max() * .6 else e1.TINTA)
    ax.set_xticks(range(len(ARQ)), ARQ)
    ax.set_yticks(range(len(tabla)), [f"umbral {u:g} %" for u in tabla.index])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    a3 = tabla["A3"]
    ax.set_title(f"E6 · A3 es el arquetipo más inestable: {a3.iloc[0]} derrotas con 4 % "
                 f"y {a3.iloc[-1]} con 6 %", fontsize=10, loc="left")
    e1.guardar(fig, "v7_sensibilidad")


def fig_v10(por_cuenta: dict, p: float) -> None:
    cuentas = sorted(por_cuenta)
    fig, axes = plt.subplots(1, 5, figsize=(9.2, 2.6), sharey=True, sharex=True)
    for ax, a in zip(axes, ARQ):
        for y, c in enumerate(cuentas[::-1]):
            r = por_cuenta[c][a]
            ax.plot([r["lo"] * 100, r["hi"] * 100], [y, y], color=e1.AZUL, lw=2)
            ax.plot(r["p"] * 100, y, "o", color=e1.AZUL, ms=6, mec="white", mew=1.5)
        ax.set_yticks(range(len(cuentas)), [f"{c} (n={por_cuenta[c]['_n']})" for c in cuentas[::-1]])
        ax.set_title(a, fontsize=9, loc="left")
        ax.grid(axis="y", visible=False)
    axes[2].set_xlabel("% de las derrotas de cada cuenta (IC 95 % de Wilson)")
    fig.suptitle(f"V10 · Ninguna cuenta se aparta del resto (permutación, p = {p:.2f})",
                 fontsize=10.5, x=.01, ha="left", y=1.04)
    e1.guardar(fig, "v10_cuentas")


# ─────────────────────────────────────────── main
def main() -> int:
    muestra, v, obj, q, series, d2, rival_por = preparar()
    der = q.loc[q["gane"] == 0, "partida"].tolist()
    arq = arquetipos(der, series, d2, rival_por)
    f = frecuencias(arq)
    fig_v6(f, len(der))
    fig_v2(v, arq)
    r: dict = {"derrotas": len(der), "e5": f.round(4).to_dict("records")}

    # E6 · sensibilidad del umbral de 5 %
    alt = {u: arquetipos(der, series, d2, rival_por, u) for u in (4.0, 6.0)}
    tabla = pd.DataFrame({u: s.value_counts() for u, s in {4.0: alt[4.0], 5.0: arq, 6.0: alt[6.0]}.items()}
                         ).reindex(ARQ).fillna(0).astype(int).T
    fig_v7(tabla)
    r["e6"] = {"conteos": {str(u): tabla.loc[u].to_dict() for u in tabla.index},
               "cambian_con_4": int((alt[4.0] != arq).sum()),
               "cambian_con_6": int((alt[6.0] != arq).sum())}

    # E7 · estabilidad por fecha (la fecha está generalizada a mes)
    meses = muestra.set_index("partida")["mes"]
    m_der = meses.loc[der].sort_values()
    corte = m_der.iloc[len(m_der) // 2]
    primera = m_der[m_der < corte].index
    segunda = m_der[m_der >= corte].index
    d2s = q.set_index("partida")["d2"]
    med1, med2 = float(d2s.loc[primera].median()), float(d2s.loc[segunda].median())
    cont = pd.crosstab(pd.Series(np.where(arq.index.isin(primera), "1", "2"), index=arq.index), arq)
    chi7 = chi2_contingency(cont)
    r["e7"] = {"corte_mes": corte, "derrotas_primera": len(primera), "derrotas_segunda": len(segunda),
               "mediana_d2_primera": med1, "mediana_d2_segunda": med2,
               "se_mueve_mas_de_2_min": abs(med1 - med2) > 2,
               "arquetipos_primera": cont.loc["1"].to_dict(), "arquetipos_segunda": cont.loc["2"].to_dict(),
               "chi2_p": float(chi7.pvalue)}

    # E8 · cuentas
    cuenta = muestra.set_index("partida")["cuentaPropia"]
    por_cuenta = {}
    for c, ps in arq.groupby(cuenta.loc[arq.index]):
        fr = frecuencias(ps).set_index("arquetipo")
        por_cuenta[c] = {a: fr.loc[a].to_dict() for a in ARQ} | {"_n": len(ps)}
    cont8 = pd.crosstab(cuenta.loc[arq.index], arq)
    chi8 = chi2_contingency(cont8)
    # Con frecuencias esperadas < 5 la aproximación chi² no es confiable: valor p por
    # permutación de las etiquetas de cuenta (10 000 réplicas, misma semilla del proyecto).
    rng = np.random.default_rng(e24.SEMILLA)
    etiquetas, cats = cuenta.loc[arq.index].to_numpy(), arq.to_numpy()
    nulos = np.array([chi2_contingency(pd.crosstab(rng.permutation(etiquetas), cats)).statistic
                      for _ in range(e24.B)])
    r["e8_cuentas"] = {"tabla": cont8.to_dict("index"), "chi2": float(chi8.statistic),
                       "chi2_p_aprox": float(chi8.pvalue),
                       "esperado_min": float(chi8.expected_freq.min()),
                       "p_permutacion": float((np.sum(nulos >= chi8.statistic) + 1) / (e24.B + 1))}
    fig_v10(por_cuenta, r["e8_cuentas"]["p_permutacion"])

    # Observación EXPLORATORIA (no es hipótesis): cómo son las derrotas sin clasificar.
    stats = []
    for p in arq.index:
        vv, _ = series[p]
        stats.append({"arq": arq[p], "max_v": vv.max(), "min_v": vv.min(),
                      "min_tranquilo": int((np.abs(vv) < 5).sum()), "dur": len(vv) - 1,
                      "d2": d2[p]})
    st = pd.DataFrame(stats)
    sc = st[st["arq"] == "Sin clasificar"]
    r["exploratorio_sin_clasificar"] = {
        "n": len(sc),
        "mediana_max_v": round(float(sc["max_v"].median()), 1),
        "mediana_min_v": round(float(sc["min_v"].median()), 1),
        "pct_nunca_bajo_menos_10": round(100 * float((sc["min_v"] > -10).mean()), 1),
        "pct_nunca_arriba_mas_5": round(100 * float((sc["max_v"] < 5).mean()), 1),
        "mediana_pct_partida_con_abs_v_menor_5": round(
            100 * float((sc["min_tranquilo"] / (sc["dur"] + 1)).median()), 1),
        "mediana_d2": float(sc["d2"].median()), "mediana_duracion": float(sc["dur"].median()),
        "mediana_duracion_clasificadas": float(st[st["arq"] != "Sin clasificar"]["dur"].median()),
    }

    # E8 · solo BOTTOM: se repite E5 y las cifras principales de H1, H2 y H3
    bot = set(muestra.loc[muestra["rolPropio"] == "BOTTOM", "partida"])
    arq_b = arq[arq.index.isin(bot)]
    v_b, obj_b = v[v["partida"].isin(bot)], obj[obj["partida"].isin(bot)]
    q_b = q[q["partida"].isin(bot)]
    h1_b = e24.e2(v_b, obj_b)["por_fase"]
    h2_b = e24.e3(v_b, obj_b, q_b)
    h2_b.pop("_nulas_derrotas", None)
    c_b = e24.e4(v_b).set_index("minuto")
    r["e8_bottom"] = {
        "partidas": len(bot), "derrotas": len(arq_b),
        "e5": frecuencias(arq_b).round(4).to_dict("records"),
        "h1_por_fase": {f_: {k: round(d["tasa"], 3) for k, d in v_.items()} for f_, v_ in h1_b.items()},
        "h2_derrotas": {"observado": round(h2_b["derrotas"]["observado"], 3),
                        "nula_corregida": round(h2_b["derrotas"]["nula_corregida"]["media"], 3),
                        "p_mayor": round(h2_b["derrotas"]["nula_corregida"]["p_mayor"], 4)},
        "h3": {int(m): round(float(c_b.loc[m, "p"]), 3) for m in (5, 10, 15, 20, 25, 30) if m in c_b.index},
    }

    (e1.RES / "e5_e8.json").write_text(json.dumps(r, indent=1, ensure_ascii=False, default=str),
                                       encoding="utf-8")
    pd.DataFrame({"partida": arq.index, "arquetipo": arq.values}).to_csv(
        e1.RES / "arquetipos_por_derrota.csv", index=False)
    print(json.dumps(r, indent=1, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
