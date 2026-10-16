r"""EDA piloto del corpus de League of Legends — figuras, tablas y resultados.

Corpus: 7 pares partida+línea temporal públicos (MingweiSamuel/riotapi-schema).
NO son partidas de Héctor: son el material con el que se probó el canal de datos
antes de tener llave. Por eso todo lo de aquí describe el MÉTODO y la ESTRUCTURA
del dato, nunca el desempeño de un jugador.

Salidas: figuras/*.pdf, tablas/*.tex, datos/resultados.json
"""
from __future__ import annotations

import json
import pathlib
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DAT, FIG, TAB = ROOT / "datos", ROOT / "figuras", ROOT / "tablas"
for d in (FIG, TAB):
    d.mkdir(parents=True, exist_ok=True)

AZUL, NARANJA, AQUA, AMAR, VIOLETA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#4a3aa7"
TINTA, SUAVE, REJILLA = "#1a1a19", "#52514e", "#d9d8d4"
plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 110, "font.family": "DejaVu Sans", "font.size": 9,
    "axes.edgecolor": SUAVE, "axes.labelcolor": TINTA, "text.color": TINTA,
    "xtick.color": SUAVE, "ytick.color": SUAVE, "axes.grid": True,
    "grid.color": REJILLA, "grid.linewidth": .7, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white", "legend.frameon": False,
})

R: dict = {}
COLAS = {420: "Clasif. individual", 440: "Clasif. flexible", 480: "Swiftplay",
         700: "Clash", 1700: "Arena"}


def guardar(fig, n):
    fig.tight_layout(); fig.savefig(FIG / f"{n}.pdf", bbox_inches="tight"); plt.close(fig)
    print(f"  figura  {n}.pdf")


def tabla(dfx, n, cap, lab, fmt="%.2f"):
    body = dfx.to_latex(index=False, escape=True, float_format=lambda v: fmt % v,
                        column_format="l" + "r" * (len(dfx.columns) - 1))
    (TAB / f"{n}.tex").write_text(
        "\\begin{table}[H]\n\\centering\n\\small\n"
        f"\\caption{{{cap}}}\n\\label{{tab:{lab}}}\n{body}\\end{{table}}\n", encoding="utf-8")
    print(f"  tabla   {n}.tex")


# ═══════════════════════════════════════════ CARGA A TRES GRANOS
ids = sorted(p.name[9:-5] for p in DAT.glob("getMatch_*.json"))
partidas, participantes, cuadros, eventos = [], [], [], []

for mid in ids:
    m = json.loads((DAT / f"getMatch_{mid}.json").read_text(encoding="utf-8"))["info"]
    t = json.loads((DAT / f"getTimeline_{mid}.json").read_text(encoding="utf-8"))["info"]
    ganador = next((x["teamId"] for x in m["teams"] if x.get("win")), None)
    partidas.append({
        "matchId": mid, "parche": ".".join(str(m.get("gameVersion")).split(".")[:2]),
        "cola": m.get("queueId"), "jugadores": len(m["participants"]),
        "equipos": len(set(p["teamId"] for p in m["participants"])),
        "duracionMin": round(m.get("gameDuration", 0) / 60, 2),
        "cuadros": len(t["frames"]), "intervaloMs": t.get("frameInterval"),
        "ganador": ganador,
    })
    pid_team = {p["participantId"]: p["teamId"] for p in m["participants"]}
    for p in m["participants"]:
        participantes.append({
            "matchId": mid, "cola": m.get("queueId"), "participantId": p["participantId"],
            "teamId": p["teamId"], "campeon": p.get("championName"),
            "rol": p.get("teamPosition") or "", "gano": int(bool(p.get("win"))),
            "k": p.get("kills"), "d": p.get("deaths"), "a": p.get("assists"),
            "oro": p.get("goldEarned"), "cs": p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0),
            "dano": p.get("totalDamageDealtToChampions"), "vision": p.get("visionScore"),
            "nivel": p.get("champLevel"),
        })
    for i, fr in enumerate(t["frames"]):
        for k, pf in fr["participantFrames"].items():
            cuadros.append({
                "matchId": mid, "minuto": i, "participantId": int(k),
                "teamId": pid_team.get(int(k)),
                "oroTotal": pf.get("totalGold"), "xp": pf.get("xp"),
                "nivel": pf.get("level"), "cs": pf.get("minionsKilled", 0) + pf.get("jungleMinionsKilled", 0),
                "x": (pf.get("position") or {}).get("x"), "y": (pf.get("position") or {}).get("y"),
            })
        for e in fr.get("events", []):
            eventos.append({
                "matchId": mid, "tipo": e["type"], "ms": e.get("timestamp"),
                "minuto": round(e.get("timestamp", 0) / 60000, 2),
                "tienePos": "position" in e, "tieneAsist": "assistingParticipantIds" in e,
                "killerId": e.get("killerId"), "monsterType": e.get("monsterType"),
                "killerTeamId": e.get("killerTeamId"), "claves": len(e.keys()),
            })

P = pd.DataFrame(partidas); PJ = pd.DataFrame(participantes)
CF = pd.DataFrame(cuadros); EV = pd.DataFrame(eventos)
R["n_partidas"], R["n_participantes"] = len(P), len(PJ)
R["n_cuadros"], R["n_eventos"] = len(CF), len(EV)
R["colas"] = {int(k): int(v) for k, v in P["cola"].value_counts().items()}
R["parches"] = sorted(P["parche"].unique().tolist())
R["intervalos"] = sorted(set(int(x) for x in P["intervaloMs"]))

# la de Arena rompe el supuesto 5v5
ARENA = P.loc[P["jugadores"] != 10, "matchId"].tolist()
R["arena"] = ARENA
VALIDAS = P.loc[P["jugadores"] == 10, "matchId"].tolist()
R["n_validas"] = len(VALIDAS)
R["n_cola420"] = int((P["cola"] == 420).sum())

tabla(P.assign(cola=P["cola"].map(lambda c: f"{c} · {COLAS.get(c, '?')}"))
       [["matchId", "parche", "cola", "jugadores", "duracionMin", "cuadros", "intervaloMs"]],
      "corpus", "Las siete partidas del corpus. Una no es 5v5.", "corpus", "%.1f")

# ═══════════════════════════════════════════ 1 · COMPOSICIÓN
fig, axes = plt.subplots(1, 3, figsize=(7.6, 2.5))
vc = P["cola"].value_counts().sort_index()
axes[0].bar([f"{c}" for c in vc.index], vc.values,
            color=[AZUL if c == 420 else "#b9c0c8" for c in vc.index], width=.6)
axes[0].set_title("Colas distintas", fontsize=9.5, loc="left"); axes[0].set_ylabel("partidas")
axes[0].set_xlabel("queueId")
pv = P["parche"].value_counts().sort_index()
axes[1].bar(pv.index, pv.values, color="#b9c0c8", width=.6)
axes[1].set_title("Parches distintos", fontsize=9.5, loc="left"); axes[1].tick_params(axis="x", rotation=45)
jv = P["jugadores"].value_counts().sort_index()
axes[2].bar([str(i) for i in jv.index], jv.values,
            color=[NARANJA if i != 10 else AQUA for i in jv.index], width=.5)
for i, v in enumerate(jv.values):
    axes[2].text(i, v + .08, str(v), ha="center", fontsize=9, color=TINTA)
axes[2].set_title("Jugadores por partida", fontsize=9.5, loc="left")
fig.suptitle("El corpus NO es homogéneo: cinco colas, seis parches y una partida que no es 5v5",
             fontsize=10.5, x=.005, ha="left", y=1.06)
guardar(fig, "corpus")

# ═══════════════════════════════════════════ 2 · CALIDAD
tipos = EV["tipo"].value_counts()
R["tipos_evento"] = int(EV["tipo"].nunique())
R["top_eventos"] = {k: int(v) for k, v in tipos.head(6).items()}

opc = []
for tp in ["CHAMPION_KILL", "BUILDING_KILL", "ELITE_MONSTER_KILL", "WARD_PLACED", "ITEM_PURCHASED"]:
    sub = EV[EV["tipo"] == tp]
    if not len(sub):
        continue
    opc.append({"Evento": tp, "n": len(sub),
                "\\% con position": round(100 * sub["tienePos"].mean(), 1),
                "\\% con asistencias": round(100 * sub["tieneAsist"].mean(), 1),
                "Claves (mín--máx)": f"{sub['claves'].min()}--{sub['claves'].max()}"})
OP = pd.DataFrame(opc)
OP.columns = [c.replace("\\%", "%") for c in OP.columns]
tabla(OP, "opcionales", "Campos opcionales por tipo de evento: la forma del payload cambia "
      "dentro del mismo tipo.", "opcionales", "%.1f")
R["pos_global"] = float(100 * EV["tienePos"].mean())
R["kill_sin_asist"] = int(((EV["tipo"] == "CHAMPION_KILL") & (~EV["tieneAsist"])).sum())
R["kill_total"] = int((EV["tipo"] == "CHAMPION_KILL").sum())
R["killer_cero"] = int(((EV["tipo"] == "CHAMPION_KILL") & (EV["killerId"] == 0)).sum())

fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.0))
top = tipos.head(10)[::-1]
axes[0].barh(top.index, top.values, color=AZUL, height=.68)
for i, v in enumerate(top.values):
    axes[0].text(v * 1.02, i, f"{v:,}", va="center", fontsize=8, color=TINTA)
axes[0].set_xscale("log"); axes[0].set_xlabel("eventos (log)")
axes[0].set_title(f"{R['tipos_evento']} tipos de evento en {len(EV):,} registros", fontsize=9.5, loc="left")

sub = OP.set_index("Evento")["% con position"]
axes[1].bar(range(len(sub)), sub.values, color=[AQUA if v > 99 else NARANJA for v in sub.values], width=.55)
axes[1].set_xticks(range(len(sub)), [s.replace("_", "\n") for s in sub.index], fontsize=7.5)
axes[1].set_ylim(0, 105); axes[1].set_ylabel("% de eventos con coordenadas")
axes[1].set_title("«Los eventos traen posición» no es cierto para todos", fontsize=9.5, loc="left")
fig.suptitle("Vocabulario y forma del payload", fontsize=10.5, x=.005, ha="left", y=1.04)
guardar(fig, "eventos")

# ═══════════════════════════════════════════ 3 · CURVAS DE ORO
def curva(mid: str):
    """Diferencia de oro por minuto (equipo 100 menos equipo 200). Solo 5v5."""
    c = CF[CF["matchId"] == mid]
    piv = c.pivot_table(index="minuto", columns="teamId", values="oroTotal", aggfunc="sum")
    if 100 not in piv or 200 not in piv:
        return None
    return (piv[100] - piv[200])


R["curvas"] = {}
fig, axes = plt.subplots(2, 3, figsize=(7.8, 4.2), sharex=False)
for ax, mid in zip(axes.ravel(), VALIDAS):
    d = curva(mid)
    row = P[P["matchId"] == mid].iloc[0]
    gan = row["ganador"]
    # siempre desde el punto de vista del que PERDIO
    serie = d if gan == 200 else -d
    ax.axhline(0, color=SUAVE, linestyle="--", linewidth=1)
    ax.fill_between(serie.index, 0, serie.values, where=serie.values >= 0, color=AZUL, alpha=.20)
    ax.fill_between(serie.index, 0, serie.values, where=serie.values < 0, color=NARANJA, alpha=.20)
    ax.plot(serie.index, serie.values, color=AZUL if serie.max() > 0 else NARANJA, linewidth=1.6)
    ax.set_title(f"{mid.split('_')[1]} · cola {row['cola']}", fontsize=8.5, loc="left")
    ax.tick_params(labelsize=7.5)
    R["curvas"][mid] = {"max": float(serie.max()), "min": float(serie.min()),
                        "final": float(serie.iloc[-1])}
axes.ravel()[-1].axis("off")
fig.supxlabel("minuto", fontsize=9); fig.supylabel("ventaja del equipo que perdió (oro)", fontsize=9)
fig.suptitle("Las seis partidas 5v5, siempre desde el equipo que perdió",
             fontsize=10.5, x=.005, ha="left", y=1.02)
guardar(fig, "curvas")

# ═══════════════════════════════════════════ 4 · MÉTRICAS Y VARIANZA
NUM = ["oro", "cs", "dano", "vision", "k", "d", "a", "nivel"]
desc = PJ[NUM].describe().T.rename(columns={"count": "n", "mean": "media", "std": "desv.",
                                            "min": "mín", "max": "máx", "25%": "Q1",
                                            "50%": "mediana", "75%": "Q3"})
desc["varianza"] = PJ[NUM].var()
tabla(desc.reset_index().rename(columns={"index": "Variable"})
      [["Variable", "n", "media", "desv.", "varianza", "mín", "mediana", "máx"]],
      "metricas", "Métricas por participante (68 filas).", "metricas")

VNUM = ["participantId", "oro", "dano", "cs", "vision", "nivel", "k", "d", "a", "gano"]
varc = PJ[VNUM].var().sort_values(ascending=False)
R["varianza"] = {k: float(v) for k, v in varc.items()}
R["mayor_var"] = list(varc.index[:2]); R["menor_var"] = list(varc.index[-2:][::-1])
z = (PJ[VNUM] - PJ[VNUM].mean()) / PJ[VNUM].std()
mm = (PJ[VNUM] - PJ[VNUM].min()) / (PJ[VNUM].max() - PJ[VNUM].min())
R["var_z"] = {k: float(z[k].var()) for k in VNUM}
R["var_mm"] = {k: float(mm[k].var()) for k in VNUM}
comp = pd.DataFrame({"Variable": VNUM,
                     "Varianza cruda": [f"{PJ[c].var():,.3f}" for c in VNUM],
                     "z-score": [f"{z[c].var():.3f}" for c in VNUM],
                     "min--max": [f"{mm[c].var():.4f}" for c in VNUM]})
tabla(comp, "varianza", "Varianza antes y después de normalizar (grano: participante).",
      "varianza", "%s")

fig, ax = plt.subplots(figsize=(7.4, 3.0))
cols = [AZUL if c in R["mayor_var"] else NARANJA if c in R["menor_var"] else "#b9c0c8" for c in varc.index]
ax.bar(varc.index, varc.values, color=cols, width=.62)
ax.set_yscale("log"); ax.set_ylabel("varianza (log)")
for i, v in enumerate(varc.values):
    ax.text(i, v * 1.4, f"{v:,.2f}", ha="center", fontsize=7.5, color=TINTA)
ax.set_ylim(0.05, varc.max() * 20)
ax.set_title("El daño domina por unidades, no por importancia", loc="left", fontsize=10.5, pad=10)
guardar(fig, "varianza")

fig, ax = plt.subplots(figsize=(7.4, 3.0))
x = np.arange(len(VNUM)); w = .27
ax.bar(x - w, [PJ[c].var() for c in VNUM], w, label="cruda", color="#b9c0c8")
ax.bar(x, [z[c].var() for c in VNUM], w, label="z-score", color=AZUL)
ax.bar(x + w, [mm[c].var() for c in VNUM], w, label="min–max", color=NARANJA)
ax.set_yscale("log"); ax.set_xticks(x, VNUM, rotation=20, ha="right")
ax.set_ylabel("varianza (log)"); ax.legend(ncols=3)
ax.set_title("Normalizar iguala las escalas: el z-score deja toda varianza en 1",
             loc="left", fontsize=10.5, pad=10)
guardar(fig, "normalizacion")

# ═══════════════════════════════════════════ 5 · SEÑAL POR MINUTO (ruido)
filas = []
for mid in VALIDAS:
    d = curva(mid); gan = P.loc[P["matchId"] == mid, "ganador"].iloc[0]
    for mn, val in d.items():
        filas.append({"matchId": mid, "minuto": int(mn), "dif": float(val),
                      "acierta": int((val > 0) == (gan == 100))})
S = pd.DataFrame(filas)
acc = S.groupby("minuto")["acierta"].agg(["mean", "count"])
acc = acc[acc["count"] >= 4]
R["acierto_por_minuto"] = {int(k): float(v) for k, v in acc["mean"].items()}
for mn in (5, 10, 15, 20, 25):
    if mn in acc.index:
        R[f"acierto_min{mn}"] = float(acc.loc[mn, "mean"])

fig, ax = plt.subplots(figsize=(7.4, 2.9))
ax.plot(acc.index, 100 * acc["mean"], color=AZUL, linewidth=2, marker="o", markersize=3.5)
ax.axhline(50, color=SUAVE, linestyle="--", linewidth=1)
ax.text(acc.index.max(), 51.5, "azar", ha="right", fontsize=8, color=SUAVE)
ax.set_ylim(0, 105); ax.set_xlabel("minuto"); ax.set_ylabel("% de partidas donde el signo acierta")
ax.set_title("Cuándo empieza a informar el signo de la diferencia de oro",
             loc="left", fontsize=10.5, pad=10)
guardar(fig, "senal")

# ═══════════════════════════════════════════ 6 · DISTRIBUCIONES MUESTRALES
rng = np.random.default_rng(20240224)
B, N = 5000, 30
def boot(serie, n=N, b=B):
    v = pd.Series(serie).dropna().to_numpy()
    return rng.choice(v, size=(b, n), replace=True).mean(axis=1)

fig, axes = plt.subplots(1, 3, figsize=(7.6, 2.6))
R["sd"] = {}
for ax, (col, nom, color) in zip(axes, [("oro", "Oro por jugador", AZUL),
                                        ("dano", "Daño a campeones", NARANJA),
                                        ("gano", "Proporción que gana", AQUA)]):
    ms = boot(PJ[col])
    ax.hist(ms, bins=45, color=color, edgecolor="white", linewidth=.3, density=True)
    ax.axvline(PJ[col].mean(), color=TINTA, linestyle="--", linewidth=1.2)
    ee = ms.std(ddof=1)
    ax.set_title(f"{nom}\nEE = {ee:,.3f}", fontsize=9, loc="left"); ax.set_yticks([])
    ax.set_xlabel(f"media de n={N}")
    R["sd"][col] = {"media": float(ms.mean()), "ee": float(ee),
                    "ic95": [float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))]}
fig.suptitle(f"Distribuciones muestrales de la media ({B:,} remuestreos, n={N} participantes)",
             fontsize=10.5, x=.005, ha="left", y=1.06)
guardar(fig, "sampling")

# ═══════════════════════════════════════════ 7 · LAS REGLAS DE ARQUETIPO
VENT, DECIS, PISO, RACHA, TARDE = 5.0, 10.0, 1500, 3, 15
def clasifica(mid):
    c = CF[CF["matchId"] == mid]
    piv = c.pivot_table(index="minuto", columns="teamId", values="oroTotal", aggfunc="sum")
    tot = piv.sum(axis=1)
    gan = P.loc[P["matchId"] == mid, "ganador"].iloc[0]
    adv = (piv[100] - piv[200]) * (1 if gan == 200 else -1)
    v = 100 * adv / tot
    n = len(v)
    real = [(v.iloc[i] >= VENT and adv.iloc[i] >= PISO) for i in range(n)]
    a4 = (any(v.iloc[i] <= -DECIS for i in range(min(TARDE + 1, n)))
          and all(v.iloc[i] <= -VENT for i in range(min(TARDE, n), n)))
    racha = mejor = 0; tarde = False
    for i in range(n):
        if real[i]:
            racha += 1; mejor = max(mejor, racha)
            if i >= TARDE: tarde = True
        else: racha = 0
    a2 = mejor >= RACHA and tarde
    a1 = (TARDE < n and v.iloc[TARDE] <= -VENT and adv.iloc[TARDE] <= -PISO
          and all(adv.iloc[i] <= 0 for i in range(TARDE, n)))
    # A3 tal como se publica en la lámina: partida pareja hasta la mayor caída de v,
    # Y esa caída a +-1 minuto de un objetivo mayor tomado por el RIVAL (el que ganó).
    # Sin la segunda mitad esto no estaría probando la regla que la lámina promete.
    caidas = [(v.iloc[i] - v.iloc[i - 1], i) for i in range(1, n)]
    _, pm = min(caidas)
    pareja = all(abs(v.iloc[i]) < VENT for i in range(pm))
    obj = EV[(EV["matchId"] == mid)
             & (EV["tipo"] == "ELITE_MONSTER_KILL")
             & (EV["killerTeamId"] == gan)
             & ((EV["minuto"] - pm).abs() <= 1)]
    a3 = pareja and len(obj) > 0
    for k, ok in (("A4", a4), ("A2", a2), ("A1", a1), ("A3", a3)):
        if ok: return k, mejor
    return "sin clasificar", mejor

cls = {mid: clasifica(mid) for mid in VALIDAS}
R["clasificacion"] = {k: v[0] for k, v in cls.items()}
R["conteo_arquetipos"] = dict(Counter(v[0] for v in cls.values()))
CL = pd.DataFrame([{"matchId": m, "cola": int(P.loc[P.matchId == m, "cola"].iloc[0]),
                    "Racha con ventaja real (min)": v[1], "Arquetipo": v[0]}
                   for m, v in cls.items()])
tabla(CL, "arquetipos", "Las reglas con umbral aplicadas a las seis partidas 5v5 del corpus.",
      "arquetipos", "%.0f")

fig, ax = plt.subplots(figsize=(7.4, 2.4))
cc = Counter(v[0] for v in cls.values())
orden = ["A1", "A2", "A3", "A4", "sin clasificar"]
vals = [cc.get(k, 0) for k in orden]
ax.bar(orden, vals, color=[AZUL if v else "#e4e7ea" for v in vals], width=.55)
for i, v in enumerate(vals):
    ax.text(i, v + .06, str(v), ha="center", fontsize=10, color=TINTA)
ax.set_ylabel("partidas"); ax.set_ylim(0, max(vals) + .8)
ax.set_title("Con n=6 el reparto no significa nada — lo que se prueba es que las reglas corren",
             loc="left", fontsize=10.5, pad=10)
guardar(fig, "arquetipos")

# ═══════════════════════════════════════════ salida
(DAT / "resultados.json").write_text(json.dumps(R, indent=2, ensure_ascii=False, default=str),
                                     encoding="utf-8")
print(f"\ngranos: {len(P)} partidas · {len(PJ)} participantes · {len(CF):,} cuadros-jugador · {len(EV):,} eventos")
print(f"validas 5v5: {len(VALIDAS)}   cola 420: {R['n_cola420']}   arquetipos: {R['conteo_arquetipos']}")
print(f"acierto del signo del oro: min 10 = {R.get('acierto_min10', float('nan')):.0%}, "
      f"min 20 = {R.get('acierto_min20', float('nan')):.0%}")
