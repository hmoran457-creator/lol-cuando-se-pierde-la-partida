r"""Experimentos E2 (H1), E3 (H2) y E4 (H3) sobre las tablas públicas.

Definiciones del planteamiento, más las decisiones que hubo que precisar al construirlas
(todas antes de ver los resultados de cada experimento, y todas escritas aquí):

* Objetivos: ELITE_MONSTER_KILL (dragón, larvas, heraldo, barón, Atakhan) y
  BUILDING_KILL (torres e inhibidores). Las placas de torre NO cuentan. Cada larva es un
  evento propio. Los objetivos con equipoAutor = 300 (nadie los tomó) se excluyen.
* Un evento con marca de tiempo `ms` cae en el minuto floor(ms / 60000), y se juzga con
  v del cuadro de ese minuto (el estado al empezar ese minuto).
* Ventaja real: v >= 5 % y al menos 1,500 de oro (la regla de los arquetipos).

E2 · H1. Tasa de objetivos propios por minuto en los minutos con ventaja real,
     derrotas contra victorias. Tasa agregada (objetivos / minutos) e intervalo
     bootstrap remuestreando PARTIDAS (10,000 réplicas, semilla 20261010).
E3 · H2. Quiebre = D2 (último cruce de v hacia abajo), elegido como definición
     principal después de E1. El quiebre del cuadro t ocurre entre los minutos t-1 y t;
     «a ±1 minuto» = algún objetivo mayor del rival (monstruo épico) con minuto en
     [t-2, t+1). Nula: dentro de cada partida, los tiempos de los objetivos del rival se
     desplazan circularmente por un mismo desfase al azar (conserva cuántos hay y su
     espaciado); 10,000 permutaciones, semilla 20261010.
E4 · H3. Para cada minuto t, de las partidas que van abajo con v(t) <= -5 %, la
     proporción que terminó ganando, con intervalo de Wilson y el número en riesgo.

Uso:  python LoL_Analisis/scripts/e2_e4.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import e1_quiebre as e1  # noqa: E402  (filtro, v(t), quiebres, estilo, guardar, wilson)

import matplotlib.pyplot as plt  # noqa: E402

SEMILLA, B = 20261010, 10_000
MONSTRUOS = {"DRAGON", "HORDE", "RIFTHERALD", "BARON_NASHOR", "ATAKHAN"}


def cargar():
    pub = e1.PUBLICO
    partidas = pd.read_csv(pub / "partidas.csv", dtype={"parche": str})  # 15.10 ≠ 15.1
    muestra, _ = e1.filtrar(partidas)
    v = e1.medida_v(pd.read_csv(pub / "oro_equipo.csv"), muestra)
    ev = pd.read_csv(pub / "eventos_equipo.csv", usecols=["partida", "tipo", "ms", "equipoAutor",
                                                           "monsterType"])
    ev = ev[ev["partida"].isin(muestra["partida"])]
    obj = ev[(ev["tipo"] == "BUILDING_KILL") |
             ((ev["tipo"] == "ELITE_MONSTER_KILL") & ev["monsterType"].isin(MONSTRUOS))]
    neutrales = int((obj["equipoAutor"] == 300).sum())
    obj = obj[obj["equipoAutor"].isin([100, 200])].merge(
        muestra[["partida", "equipoPropio"]], on="partida")
    obj["propio"] = obj["equipoAutor"] == obj["equipoPropio"]
    obj["minuto"] = obj["ms"] // 60000
    return muestra, v, obj, neutrales


# ─────────────────────────────────────────── E2 · H1
def e2(v: pd.DataFrame, obj: pd.DataFrame) -> dict:
    v = v.copy()
    v["ventaja"] = (v["v"] >= .05) & ((v["oroPropio"] - v["oroRival"]) >= 1500)
    mins = v[v["ventaja"]].groupby("partida").size().rename("minutos")
    o = obj[obj["propio"]].merge(v[["partida", "minuto", "ventaja"]], on=["partida", "minuto"])
    o = o[o["ventaja"]].groupby("partida").size().rename("objetivos")
    por = pd.concat([mins, o], axis=1).fillna(0)
    por = por[por["minutos"] > 0].join(v.groupby("partida")["gane"].first())

    rng = np.random.default_rng(SEMILLA)
    out = {}
    tasas = {}
    for gane, nombre in ((0, "derrotas"), (1, "victorias")):
        sub = por[por["gane"] == gane]
        ob, mi = sub["objetivos"].to_numpy(), sub["minutos"].to_numpy()
        idx = rng.integers(0, len(sub), size=(B, len(sub)))
        boot = ob[idx].sum(1) / mi[idx].sum(1)
        tasas[nombre] = boot
        out[nombre] = {"partidas": len(sub), "minutos_con_ventaja": int(mi.sum()),
                       "objetivos": int(ob.sum()), "tasa": float(ob.sum() / mi.sum()),
                       "ic95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]}
    dif = tasas["victorias"] - tasas["derrotas"]
    out["diferencia_vic_menos_der"] = {
        "valor": out["victorias"]["tasa"] - out["derrotas"]["tasa"],
        "ic95": [float(np.percentile(dif, 2.5)), float(np.percentile(dif, 97.5))]}
    out["razon_der_entre_vic"] = out["derrotas"]["tasa"] / out["victorias"]["tasa"]
    out["por_fase"] = e2_por_fase(v, obj)
    return out


def e2_por_fase(v: pd.DataFrame, obj: pd.DataFrame) -> dict:
    """H1 dice «con la MISMA ventaja». La tasa agregada no lo cumple: al ganar, la ventaja
    suele ser mayor y más tardía, y en la fase tardía hay más objetivos disponibles. Se
    compara dentro de cada fase (verificación de supuestos, agregada al ver la tabla
    agregada; la definición de la tasa no cambia)."""
    v = v.copy()
    v["ventaja"] = (v["v"] >= .05) & ((v["oroPropio"] - v["oroRival"]) >= 1500)
    v["fase"] = pd.cut(v["minuto"], [0, 15, 25, 999], right=False, labels=["<15", "15-25", ">=25"])
    o = obj[obj["propio"]].groupby(["partida", "minuto"]).size().rename("obj").reset_index()
    vv = v[v["ventaja"]].merge(o, on=["partida", "minuto"], how="left").fillna({"obj": 0})
    por = vv.groupby(["fase", "gane", "partida"], observed=True).agg(
        minutos=("obj", "size"), obj=("obj", "sum")).reset_index()
    rng = np.random.default_rng(SEMILLA + 1)
    out = {}
    for fase in ("<15", "15-25", ">=25"):
        out[fase] = {}
        for gane, nombre in ((0, "derrotas"), (1, "victorias")):
            sub = por[(por["fase"] == fase) & (por["gane"] == gane)]
            ob, mi = sub["obj"].to_numpy(), sub["minutos"].to_numpy()
            idx = rng.integers(0, len(sub), size=(B, len(sub)))
            boot = ob[idx].sum(1) / mi[idx].sum(1)
            out[fase][nombre] = {"partidas": len(sub), "minutos": int(mi.sum()),
                                 "tasa": float(ob.sum() / mi.sum()),
                                 "ic95": [float(np.percentile(boot, 2.5)),
                                          float(np.percentile(boot, 97.5))]}
    return out


def fig_v3(r: dict) -> None:
    """Punto e intervalo por fase: la comparación justa de H1 (misma fase de partida)."""
    fases = [("<15", "antes del min 15"), ("15-25", "min 15 a 25"), (">=25", "min 25 o después")]
    fig, axes = plt.subplots(1, 3, figsize=(7.6, 2.4), sharex=True)
    tope = max(d["ic95"][1] for f, _ in fases for d in r["por_fase"][f].values()) + .1
    for ax, (f, titulo) in zip(axes, fases):
        for y, k, etq in ((1, "victorias", "Victorias"), (0, "derrotas", "Derrotas")):
            d = r["por_fase"][f][k]
            ax.plot(d["ic95"], [y, y], color=e1.AZUL, lw=2.5)
            ax.plot(d["tasa"], y, "o", color=e1.AZUL, ms=8, mec="white", mew=2)
            ax.text(d["tasa"], y + .28, f"{d['tasa']:.2f}  (n={d['partidas']})", ha="center",
                    fontsize=7.5, color=e1.SUAVE)
        ax.set_yticks([0, 1], ["Derrotas", "Victorias"] if ax is axes[0] else ["", ""])
        ax.set_ylim(-.6, 1.7)
        ax.set_xlim(0, tope)
        ax.grid(axis="y", visible=False)
        ax.set_title(titulo, fontsize=9, loc="left")
    axes[1].set_xlabel("objetivos propios por minuto con ventaja real (IC 95 % bootstrap)")
    fig.suptitle("H1 · Con ventaja, al perder se toman menos objetivos, sobre todo después "
                 "del minuto 15", fontsize=10.5, x=.01, ha="left", y=1.04)
    e1.guardar(fig, "v3_h1_objetivos")


# ─────────────────────────────────────────── E3 · H2
def e3(v: pd.DataFrame, obj: pd.DataFrame, q: pd.DataFrame, quiebre: str = "d2",
       semilla: int = SEMILLA) -> dict:
    """H2 con el quiebre `quiebre` («d2», el principal, o «d1», el registrado en el plan).

    Cada definición usa su propio generador: agregar la rama D1 no mueve ni un dígito de D2.
    """
    rival = obj[(~obj["propio"]) & (obj["tipo"] == "ELITE_MONSTER_KILL")]
    rng = np.random.default_rng(semilla)
    out = {}
    for gane, nombre in ((0, "derrotas"), (1, "victorias")):
        sub = q[(q["gane"] == gane) & q[quiebre].notna()]
        casos = []
        for _, f in sub.iterrows():
            tiempos = rival.loc[rival["partida"] == f["partida"], "ms"].to_numpy() / 60000
            casos.append((int(f[quiebre]), tiempos, f["ultimo"] + 1))
        def acierto(t, mins):
            return ((mins >= t - 2) & (mins < t + 1)).any(axis=-1)
        obs = float(np.mean([acierto(t, m) for t, m, _ in casos]))
        out[nombre] = {"partidas": len(casos), "observado": obs,
                       "quiebres_antes_min5": int(sum(t < 5 for t, _, _ in casos))}
        # Dos nulas. La REGISTRADA desplaza los objetivos por toda la partida. Pero
        # ningún objetivo mayor existe antes del minuto ~5 (el primero de la muestra
        # cae en el 5.4) y casi un tercio de los quiebres de derrotas ocurre antes:
        # esa nula les regala aciertos imposibles y queda inflada. La CORREGIDA
        # desplaza solo dentro de [5, fin). Se reportan las dos.
        for clave, inicio in (("nula_registrada", 0.0), ("nula_corregida", 5.0)):
            aciertos = np.zeros(B)
            for t, m, dur in casos:                 # vectorizado: (B, objetivos)
                if len(m) and dur > inicio:
                    movidos = inicio + (m[None, :] - inicio
                                        + rng.uniform(0, dur - inicio, size=(B, 1))) % (dur - inicio)
                    aciertos += acierto(t, movidos)
            nula = aciertos / len(casos)
            out[nombre][clave] = {
                "media": float(nula.mean()),
                "ic95": [float(np.percentile(nula, 2.5)), float(np.percentile(nula, 97.5))],
                "p_mayor": float((np.sum(nula >= obs) + 1) / (B + 1)),
                "p_menor": float((np.sum(nula <= obs) + 1) / (B + 1))}
            if gane == 0:
                out.setdefault("_nulas_derrotas", {})[clave] = nula
    out["primer_objetivo_mayor_min"] = float(rival["ms"].min() / 60000)
    return out


def fig_v4(r: dict) -> None:
    nulas, d = r.pop("_nulas_derrotas"), r["derrotas"]
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 2.7), sharex=True, sharey=True)
    paneles = (("nula_registrada", "Nula registrada (toda la partida)", "p_menor", "menor"),
               ("nula_corregida", "Nula corregida (desde el minuto 5)", "p_mayor", "mayor"))
    for ax, (clave, titulo, pk, sentido) in zip(axes, paneles):
        ax.hist(nulas[clave] * 100, bins=40, color=e1.AZUL, alpha=.45, rwidth=.9)
        ax.axvline(d["observado"] * 100, color=e1.TINTA, lw=2)
        ax.text(.03, .95, f"observado {100 * d['observado']:.1f} %\n"
                f"nula {100 * d[clave]['media']:.1f} %\np ({sentido}) = {d[clave][pk]:.3f}",
                transform=ax.transAxes, va="top", fontsize=8)
        ax.set_title(titulo, fontsize=9, loc="left")
        ax.grid(axis="y", visible=False)
        ax.set_xlabel("% de quiebres a ±1 min de un objetivo del rival")
    axes[0].set_ylabel("permutaciones")
    fig.suptitle(f"H2 · No concluyente: por debajo del azar con la nula registrada, apenas por "
                 f"encima con la corregida (D2, {d['partidas']} derrotas)",
                 fontsize=10.5, x=.01, ha="left", y=1.04)
    e1.guardar(fig, "v4_h2_permutacion")


# ─────────────────────────────────────────── E4 · H3
def e4(v: pd.DataFrame) -> pd.DataFrame:
    abajo = v[v["v"] <= -.05]
    filas = []
    for t, g in abajo.groupby("minuto"):
        n, k = g["partida"].nunique(), int(g.groupby("partida")["gane"].first().sum())
        lo, hi = e1.wilson(k, n)
        filas.append({"minuto": int(t), "en_riesgo": n, "remontaron": k,
                      "p": k / n, "lo": lo, "hi": hi})
    return pd.DataFrame(filas)


# H3 dice «existe un minuto a partir del cual mis derrotas ya casi nunca se revierten», pero
# el plan no fijó cuánto es «casi nunca». Se fija aquí, y se declara como desviación en el
# reporte: el punto sin regreso es el primer minuto desde el cual la remontada queda por
# debajo del umbral en TODOS los minutos siguientes con al menos 30 partidas en riesgo.
# Principal: 5 % (menos de 1 de cada 20). 3 % y 10 % se reportan como sensibilidad.
UMBRALES_H3 = (0.05, 0.03, 0.10)
MIN_EN_RIESGO = 30


def punto_sin_regreso(c: pd.DataFrame) -> dict:
    c = c[c["en_riesgo"] >= MIN_EN_RIESGO].reset_index(drop=True)
    out = {"regla": f"primer minuto desde el cual la remontada es menor al umbral en todos los "
                    f"minutos siguientes con al menos {MIN_EN_RIESGO} partidas en riesgo",
           "umbral_principal": UMBRALES_H3[0], "por_umbral": {}}
    for u in UMBRALES_H3:
        fila = next((c.iloc[i] for i in range(len(c)) if (c["p"].iloc[i:] < u).all()), None)
        out["por_umbral"][f"{u:.2f}"] = None if fila is None else {
            "minuto": int(fila["minuto"]), "en_riesgo": int(fila["en_riesgo"]),
            "remontaron": int(fila["remontaron"]), "p": round(float(fila["p"]), 4),
            "lo": round(float(fila["lo"]), 4), "hi": round(float(fila["hi"]), 4)}
    return out


def fig_v5(c: pd.DataFrame, punto: dict | None = None) -> None:
    c = c[c["en_riesgo"] >= 30]
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(6.6, 3.9), sharex=True,
                                  gridspec_kw={"height_ratios": [3, 1.1]})
    ax.fill_between(c["minuto"], c["lo"] * 100, c["hi"] * 100, color=e1.AZUL, alpha=.2, lw=0)
    ax.plot(c["minuto"], c["p"] * 100, color=e1.AZUL)
    ax.set_ylabel("% que terminó ganando")
    ax.set_ylim(0, max(40, c["hi"].max() * 100 + 5))
    p = (punto or {}).get("por_umbral", {}).get(f"{UMBRALES_H3[0]:.2f}")
    if p:
        u = 100 * UMBRALES_H3[0]
        ax.axhline(u, color=e1.TINTA, lw=.8, ls=(0, (3, 3)))
        ax.axvline(p["minuto"], color=e1.SUAVE, lw=1.4)   # no naranja: naranja = rival
        ax.text(p["minuto"] + .4, max(40, c["hi"].max() * 100 + 5) * .93,
                f"desde el minuto {p['minuto']}: menos de {u:.0f} %", fontsize=8, va="top")
        titulo = (f"H3 · La remontada baja poco a poco; desde el minuto {p['minuto']} "
                  f"casi nunca ocurre (< {u:.0f} %)")
    else:
        titulo = "H3 · Remontar desde abajo (v ≤ −5 %) por minuto"
    ax.set_title(titulo, fontsize=10, loc="left")
    ax2.bar(c["minuto"], c["en_riesgo"], color=e1.GRIS, width=.8)
    ax2.set_ylabel("en riesgo")
    ax2.set_xlabel("minuto (solo minutos con al menos 30 partidas en riesgo)")
    ax2.grid(axis="x", visible=False)
    e1.guardar(fig, "v5_h3_remontada")


def main() -> int:
    muestra, v, obj, neutrales = cargar()
    q = e1.quiebres(v)
    r2 = e2(v, obj)
    fig_v3(r2)
    r3 = e3(v, obj, q)
    fig_v4(r3)
    # La definición REGISTRADA en el plan era D1 (la mayor caída). Se reporta también,
    # con su propio generador, para no esconder la rama que no se usó como principal.
    r3_d1 = e3(v, obj, q, quiebre="d1", semilla=SEMILLA + 1)
    r3_d1.pop("_nulas_derrotas", None)
    r3["con_d1"] = {g: r3_d1[g] for g in ("derrotas", "victorias")}
    r3["alfa_bonferroni"] = round(0.05 / 3, 4)   # tres hipótesis
    c = e4(v)
    punto = punto_sin_regreso(c)
    fig_v5(c, punto)
    c.to_csv(e1.RES / "e4_remontada_por_minuto.csv", index=False)
    resumen_e4 = {f"min_{m}": {k: (round(float(x), 4) if isinstance(x, float) else int(x))
                               for k, x in c[c["minuto"] == m].iloc[0].items() if k != "minuto"}
                  for m in (5, 10, 15, 20, 25, 30, 35) if (c["minuto"] == m).any()}
    r = {"objetivos_neutrales_excluidos": neutrales, "e2_h1": r2, "e3_h2": r3, "e4_h3": resumen_e4,
         "e4_punto_sin_regreso": punto, "semilla": SEMILLA, "replicas": B}
    (e1.RES / "e2_e4.json").write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(r, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
