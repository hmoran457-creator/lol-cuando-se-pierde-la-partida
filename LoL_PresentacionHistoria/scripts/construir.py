r"""Construye presentacion_historia.html desde plantilla.html.

    {{clave}}     -> cifra calculada aquí desde los resultados del análisis
    <!--datos--> -> window.HISTORIA: las series que historia.js anima en el navegador

Todas las gráficas se dibujan en el navegador (no son imágenes), para poder animarlas
paso a paso. Ninguna cifra está escrita a mano, y el script falla si queda una
{{clave}} sin valor.

Uso:  python LoL_PresentacionHistoria/scripts/construir.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import numpy as np
import pandas as pd

AQUI = pathlib.Path(__file__).resolve().parent
BASE = AQUI.parent
RAIZ = BASE.parent
sys.path.insert(0, str(RAIZ / "LoL_Analisis" / "scripts"))
import e1_quiebre as e1  # noqa: E402
import e2_e4 as e24  # noqa: E402
import v1_partida as v1mod  # noqa: E402

ETIQUETA = {"DRAGON": "Dragón", "HORDE": "Larvas", "RIFTHERALD": "Heraldo",
            "BARON_NASHOR": "Barón", "ATAKHAN": "Atakhan"}


def mil(n: float) -> str:
    return f"{int(round(n)):,}"


def pct(x: float) -> str:
    return f"{100 * x:.0f}"


def de_cada(p: float, n: int = 20) -> int:
    """«De cada 20»: cuántas figuras se pintan. Nunca 0 si p > 0, para no esconder lo raro."""
    k = int(round(p * n))
    return max(k, 1) if p > 0 else 0


def main() -> int:
    leer = lambda n: json.loads((e1.RES / f"{n}.json").read_text(encoding="utf-8"))  # noqa: E731
    r1, r24, r58 = leer("e1"), leer("e2_e4"), leer("e5_e8")
    muestra, v, obj, _ = e24.cargar()
    q = e1.quiebres(v)
    arq = pd.read_csv(e1.RES / "arquetipos_por_derrota.csv")
    # Los campeones propios, contados sobre la MUESTRA FINAL (1,195), ya agregados en el
    # resumen publicado: antes se contaban sobre las 1,241 descargadas y el orden salía al revés.
    resumen = json.loads((RAIZ / "LoL_Datos" / "anonimizado" / "resumen_descarga.json").read_text(encoding="utf-8"))
    top = pd.Series(resumen["campeones_propios_muestra"]).sort_values(ascending=False, kind="stable")

    # --- el caso: la mediana de A2 (misma regla que V1 del reporte)
    pid, _, n_a2 = v1mod.elegir(v, arq, "A2")
    g = v[v["partida"] == pid].sort_values("minuto")
    o = obj[obj["partida"] == pid].copy()
    o["min"] = o["ms"] / 60000
    qq = e1.quiebres(g).iloc[0]
    vv = g["v"].to_numpy() * 100
    dif = (g["oroPropio"] - g["oroRival"]).to_numpy()
    i_max = int(vv.argmax())
    dur = float(muestra.loc[muestra["partida"] == pid, "duracionMin"].iloc[0])
    # umbral de fases de la pista 1 («15-25»): la franja del caso y el cierre lo usan
    umbral = int(next(k for k in r24["e2_h1"]["por_fase"] if "-" in k).split("-")[0])
    tarde = o[o["min"] >= umbral]
    # Los cuadros van cada minuto, salvo el último, que cae en el fin real de la partida
    # (34.13, no «35»): así la línea y los objetivos comparten el mismo reloj.
    mins = [float(m) for m in g["minuto"]]
    if mins[-1] > dur:
        mins[-1] = round(dur, 2)
    # el remate: lo que pasó en los últimos 2 minutos, y cuánta ventaja quedaba antes
    t_remate = dur - 2
    remate = o[o["min"] >= t_remate]
    v_antes = float(vv[int(t_remate)])
    caso = {
        "serie": [{"min": m, "v": round(float(x), 2)} for m, x in zip(mins, vv)],
        "objetivos": [{"min": round(float(r["min"]), 2), "propio": bool(r["propio"]),
                       "monstruo": r["tipo"] == "ELITE_MONSTER_KILL",
                       "nombre": ETIQUETA.get(r["monsterType"], "Torre")
                       if r["tipo"] == "ELITE_MONSTER_KILL" else "Torre"} for _, r in o.iterrows()],
        "duracion": round(dur, 2), "d2": int(qq["d2"]), "min_max": int(g["minuto"].iloc[i_max]),
        "v_max": round(float(vv[i_max]), 1),
        # el oro real de cada equipo en el minuto de mayor ventaja (lámina «el oro»)
        "oroMax": {"propio": int(g["oroPropio"].iloc[i_max]), "rival": int(g["oroRival"].iloc[i_max])},
        # la carrera del oro hasta ese minuto (la lámina la anima minuto a minuto)
        "oroSerie": [{"min": int(m), "p": int(a), "r": int(b)} for m, a, b in
                     zip(g["minuto"], g["oroPropio"], g["oroRival"]) if m <= g["minuto"].iloc[i_max]],
        "umbral": umbral,
    }

    # --- ejemplo de la medida: 2,000 de oro sobre el oro total típico del mapa
    oro = pd.read_csv(e1.PUBLICO / "oro_equipo.csv")
    oro = oro[oro["partida"].isin(muestra["partida"])]
    total = oro.groupby(["partida", "minuto"])["oroTotal"].sum().reset_index()
    t5 = float(total[total["minuto"] == 5]["oroTotal"].median())
    t30 = float(total[total["minuto"] == 30]["oroTotal"].median())
    ejemplo = {"ventaja": 2000, "total5": round(t5), "total30": round(t30)}

    # --- tropiezo: minuto de la mayor caída, derrotas y victorias (en %)
    d1 = {}
    for gane, k in ((0, "derrotas"), (1, "victorias")):
        s = q[q["gane"] == gane]["d1"].clip(upper=30)
        d1[k] = [round(100 * float((s == m).mean()), 2) for m in range(0, 31)]

    # --- pista 3: curva y figuras «de cada 20»
    c4 = pd.read_csv(e1.RES / "e4_remontada_por_minuto.csv")
    c4 = c4[c4["en_riesgo"] >= 30]
    curva = [{"min": int(r["minuto"]), "p": round(float(r["p"]) * 100, 1)} for _, r in c4.iterrows()]
    h3 = r24["e4_h3"]

    # --- formas de perder: mediana de v por minuto en cada arquetipo
    formas = {}
    for a in ["A1", "A2", "A3", "A4", "Sin clasificar"]:
        ps = arq.loc[arq["arquetipo"] == a, "partida"]
        sub = v[v["partida"].isin(ps)]
        n_min = sub.groupby("minuto")["partida"].nunique()
        med = sub.groupby("minuto")["v"].median()[n_min >= max(10, len(ps) // 5)] * 100
        formas[a] = [{"min": int(m), "v": round(float(x), 2)} for m, x in med.items()]

    e5 = {r["arquetipo"]: r for r in r58["e5"]}
    h1 = r24["e2_h1"]["por_fase"]
    h2 = r24["e3_h2"]
    # cada tarjeta lleva el arte de SU campeón (por nombre, no por posición)
    for camp in top.index[:2]:
        if not (BASE / "assets" / "img" / f"{camp}_splash.jpg").exists():
            raise SystemExit(f"falta assets/img/{camp}_splash.jpg (arte de Data Dragon)")
    ps = r24["e4_punto_sin_regreso"]
    punto = ps["por_umbral"][f"{ps['umbral_principal']:.2f}"]
    datos = {
        "caso": caso, "ejemplo": ejemplo, "d1": d1, "curva": curva, "formas": formas,
        "punto": {"minuto": punto["minuto"], "umbral": ps["umbral_principal"]},
        "h1": {f: {"der": round(h1[f]["derrotas"]["tasa"], 5), "vic": round(h1[f]["victorias"]["tasa"], 5),
                   # ¿se enciman los intervalos? entonces la diferencia no se distingue del azar
                   "empate": bool(h1[f]["derrotas"]["ic95"][1] >= h1[f]["victorias"]["ic95"][0])}
               for f in ("<15", "15-25", ">=25")},
        "h2": {"obsDer": round(100 * h2["derrotas"]["observado"], 1),
               "azarDer": round(100 * h2["derrotas"]["nula_corregida"]["media"], 1),
               "obsVic": round(100 * h2["victorias"]["observado"], 1),
               "azarVic": round(100 * h2["victorias"]["nula_corregida"]["media"], 1)},
        "figuras": {m: de_cada(h3[f"min_{m}"]["p"]) for m in (5, 15, 30)},
        "pctFormas": {k: round(100 * e5[k]["p"], 1) for k in e5},
    }

    # periodo cubierto, desde la columna «mes» (AAAA-MM) de la muestra final
    MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre"]
    ini, fin = muestra["mes"].min(), muestra["mes"].max()
    n_meses = (int(fin[:4]) - int(ini[:4])) * 12 + int(fin[5:]) - int(ini[5:])
    anios = n_meses / 12
    nombre_mes = lambda s: f"{MESES[int(s[5:]) - 1]} de {s[:4]}"  # noqa: E731

    c = {
        "nUnicas": mil(r1["embudo"][0]["n"]), "nFinal": mil(r1["partidas"]),
        "nFinalNum": str(int(r1["partidas"])),
        "periodoAnios": f"{anios:.0f}" if abs(anios - round(anios)) < 0.09 else f"{anios:.1f}",
        "periodoTexto": f"de {nombre_mes(ini)} a {nombre_mes(fin)}",
        "umbral": str(umbral),
        "nDerrotas": mil(r1["derrotas"]), "nVictorias": mil(r1["victorias"]),
        "nQuitadas": str(r1["embudo"][0]["n"] - r1["partidas"]),
        "nCuentas": str(muestra["cuentaPropia"].nunique()),
        "campUno": top.index[0], "campUnoN": str(int(top.iloc[0])),
        "campDos": top.index[1], "campDosN": str(int(top.iloc[1])),
        "hTresPunto": str(punto["minuto"]),
        "hTresPuntoDiez": str(ps["por_umbral"]["0.10"]["minuto"]),
        "pctBottom": pct((muestra["rolPropio"] == "BOTTOM").mean()),
        "casoDur": f"{int(dur)}:{round((dur - int(dur)) * 60):02d}",
        "casoArriba": str(int((vv > 0).sum())), "casoD2": str(int(qq["d2"])),
        "casoMaxOro": mil(dif[i_max]), "casoMaxMin": str(int(g["minuto"].iloc[i_max])),
        "casoProp15": str(int(tarde["propio"].sum())), "casoRiv15": str(int((~tarde["propio"]).sum())),
        "casoNA2": str(n_a2),
        "casoDurMin": str(int(dur)),
        "casoDurTexto": f"{int(dur)} minutos y {round((dur - int(dur)) * 60)} segundos",
        "casoVmax": f"{vv[i_max]:.1f}", "casoVantes": f"{v_antes:.1f}",
        "casoMinAntes": str(int(t_remate)),
        "casoPctPerdido": f"{100 * (1 - v_antes / vv[i_max]):.0f}",
        "casoRivRemate": str(int((~remate["propio"]).sum())),
        "casoPropRemate": str(int(remate["propio"].sum())),
        "casoDeCada": f"{100 / (100 * e5['A2']['p']):.0f}",
        "ejTotal5": mil(t5), "ejTotal30": mil(t30),
        "ejPct5": f"{100 * 2000 / t5:.0f}", "ejPct30": f"{100 * 2000 / t30:.0f}",
        "d1Med": str(int(r1["d1"]["mediana_derrotas"])), "d2Med": str(int(r1["d2"]["mediana_derrotas"])),
        "eUnoPct": f"{r1['e1']['pct_desacuerdo']:.0f}",
        "h1DerA": f"{h1['<15']['derrotas']['tasa']:.2f}", "h1VicA": f"{h1['<15']['victorias']['tasa']:.2f}",
        "h1DerB": f"{h1['15-25']['derrotas']['tasa']:.2f}", "h1VicB": f"{h1['15-25']['victorias']['tasa']:.2f}",
        "h1Der10": f"{10 * h1['15-25']['derrotas']['tasa']:.0f}",
        "h1Vic10": f"{10 * h1['15-25']['victorias']['tasa']:.0f}",
        "h2ObsDer": f"{100 * h2['derrotas']['observado']:.0f}",
        "h2AzarDer": f"{100 * h2['derrotas']['nula_corregida']['media']:.0f}",
        "h2ObsVic": f"{100 * h2['victorias']['observado']:.0f}",
        "h2AzarVic": f"{100 * h2['victorias']['nula_corregida']['media']:.0f}",
        "h2P": f"{h2['derrotas']['nula_corregida']['p_mayor']:.3f}",
        # brechas sobre el azar, con las mismas cifras redondeadas que muestran las barras
        "h2BrechaDer": str(round(100 * h2["derrotas"]["observado"]) - round(100 * h2["derrotas"]["nula_corregida"]["media"])),
        "h2BrechaVic": str(round(100 * h2["victorias"]["observado"]) - round(100 * h2["victorias"]["nula_corregida"]["media"])),
        "replicas": mil(r24["replicas"]),
        "h3Cinco": pct(h3["min_5"]["p"]), "h3Quince": pct(h3["min_15"]["p"]),
        "h3Treinta": pct(h3["min_30"]["p"]), "h3Riesgo30": str(int(h3["min_30"]["en_riesgo"])),
        "fig5": str(datos["figuras"][5]), "fig15": str(datos["figuras"][15]), "fig30": str(datos["figuras"][30]),
        "pA1": pct(e5["A1"]["p"]), "pA2": pct(e5["A2"]["p"]), "pA3": pct(e5["A3"]["p"]),
        "pA4": pct(e5["A4"]["p"]), "pSin": pct(e5["Sin clasificar"]["p"]),
        "pClas": pct(1 - e5["Sin clasificar"]["p"]),
        "sinTranquilo": f"{r58['exploratorio_sin_clasificar']['mediana_pct_partida_con_abs_v_menor_5']:.0f}",
        "sinDdos": str(int(r58["exploratorio_sin_clasificar"]["mediana_d2"])),
        "eOchoP": f"{r58['e8_cuentas']['p_permutacion']:.2f}",
    }

    html = (BASE / "plantilla.html").read_text(encoding="utf-8")
    html = re.sub(r"\{\{(\w+)\}\}", lambda m: c.get(m.group(1), m.group(0)), html)
    html = html.replace("<!--datos-->", "window.HISTORIA = " + json.dumps(datos, ensure_ascii=False) + ";")
    sin = sorted(set(re.findall(r"\{\{(\w+)\}\}", html)))
    if sin:
        raise SystemExit(f"cifras sin valor en la plantilla: {sin}")
    (BASE / "presentacion_historia.html").write_text(html, encoding="utf-8")
    print(f"presentacion_historia.html: {len(c)} cifras, {html.count('<section')} láminas, "
          f"{len(html) // 1024} KB")
    print({k: c[k] for k in ("ejTotal5", "ejTotal30", "ejPct5", "ejPct30", "fig5", "fig15", "fig30",
                              "h1Der10", "h1Vic10", "campUno", "campDos")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
