r"""Construye presentacion_final.html desde plantilla.html.

Tres sustituciones, y ninguna cifra escrita a mano:
    {{clave}}         -> cifra calculada aquí desde los archivos de resultados
    <!--svg:nombre--> -> figuras/nombre.svg incrustada (hereda la tipografía Archivo)
    <!--datos-->      -> window.LOL_DATA con la serie de V1, para la gráfica animada

El resultado es UN archivo HTML más assets/, que funciona sin internet desde una USB
(Chrome bloquea fetch() sobre file://, por eso todo va incrustado).

Si queda algún {{...}} sin rellenar, el script falla: una lámina con una llave a la
vista es peor que no tener lámina.

Uso:  python LoL_PresentacionFinal/scripts/figuras_deck.py
      python LoL_PresentacionFinal/scripts/construir.py
"""
from __future__ import annotations

import json
import math
import pathlib
import re
import sys

import pandas as pd

AQUI = pathlib.Path(__file__).resolve().parent
BASE = AQUI.parent
RAIZ = BASE.parent
sys.path.insert(0, str(RAIZ / "LoL_Analisis" / "scripts"))
import e1_quiebre as e1  # noqa: E402
import e2_e4 as e24  # noqa: E402
import v1_partida as v1mod  # noqa: E402


def mil(n: float) -> str:
    """Convención del mazo (es-MX): coma de miles, punto decimal."""
    return f"{int(round(n)):,}"


def pct(x: float, dec: int = 0) -> str:
    return f"{100 * x:.{dec}f}"


def tramos_abajo(minutos, v, d2: int) -> dict:
    """Los tramos con v < 0, en palabras: «en el minuto 7 y desde el 34, hasta el final».
    Se dice en minutos y tramos, no en cuadros: «3 de 36» contaba cuadros, y el último
    cuadro es el fin de la partida, no un minuto."""
    tramos, ini = [], None
    for i, (m, x) in enumerate(zip(minutos, v)):
        if x < 0 and ini is None:
            ini = int(m)
        if ini is not None and (x >= 0 or i == len(v) - 1):
            fin = int(m) if x < 0 else int(minutos[i - 1])
            tramos.append((ini, fin, i == len(v) - 1 and x < 0))
            ini = None
    partes = []
    for a, b, al_final in tramos:
        if al_final:
            partes.append(f"desde el minuto {a}, hasta el final")
        elif a == b:
            partes.append(f"en el minuto {a}")
        else:
            partes.append(f"del minuto {a} al {b}")
    texto = " y ".join([", ".join(partes[:-1]), partes[-1]] if len(partes) > 1 else partes)
    return {"v1VecesAbajo": str(len(tramos)), "v1Abajo": texto}


def datos_v1() -> tuple[dict, dict]:
    muestra, v, obj, _ = e24.cargar()
    arq = pd.read_csv(e1.RES / "arquetipos_por_derrota.csv")
    pid, _, _ = v1mod.elegir(v, arq, "A2")
    g = v[v["partida"] == pid].sort_values("minuto")
    o = obj[obj["partida"] == pid].copy()
    o["min"] = o["ms"] / 60000
    q = e1.quiebres(g).iloc[0]
    dur = float(muestra.loc[muestra["partida"] == pid, "duracionMin"].iloc[0])
    vv = g["v"].to_numpy() * 100
    dif = (g["oroPropio"] - g["oroRival"]).to_numpy()
    i_max = int(vv.argmax())
    corte = 15                      # el umbral de H1, no un minuto elegido para la historia
    tarde = o[o["min"] >= corte]
    datos = {
        "duracion": round(dur, 2), "d2": int(q["d2"]), "min_max": int(g["minuto"].iloc[i_max]),
        "v_max": round(float(vv[i_max]), 1),
        "v_max_txt": f"+{vv[i_max]:.1f} % (+{mil(dif[i_max])} de oro)",
        "serie": [{"min": int(m), "v": round(float(x), 2)} for m, x in zip(g["minuto"], vv)],
        "objetivos": [{"min": round(float(r["min"]), 2), "propio": bool(r["propio"]),
                       "monstruo": r["tipo"] == "ELITE_MONSTER_KILL"} for _, r in o.iterrows()],
    }
    c = {
        "v1Dur": f"{int(dur)}:{round((dur - int(dur)) * 60):02d}",
        "v1Arriba": str(int((vv > 0).sum())),
        **tramos_abajo(g["minuto"].to_numpy(), vv, int(q["d2"])),
        "v1MaxOro": mil(dif[i_max]), "v1MaxOroN": str(int(dif[i_max])),
        "v1MinMax": str(int(g["minuto"].iloc[i_max])), "v1D2": str(int(q["d2"])),
        "v1Corte": str(corte),
        "v1ObjPropTarde": str(int(tarde["propio"].sum())),
        "v1ObjRivalTarde": str(int((~tarde["propio"]).sum())),
    }
    return datos, c


def main() -> int:
    leer = lambda n: json.loads((e1.RES / f"{n}.json").read_text(encoding="utf-8"))  # noqa: E731
    r1, r24, r58 = leer("e1"), leer("e2_e4"), leer("e5_e8")
    anon = json.loads((RAIZ / "LoL_Datos" / "anonimizado" / "resultados.json").read_text(encoding="utf-8"))
    # conteos de lo local ya agregados (se publica; antes se leía crudo/revision.json)
    resumen = json.loads((RAIZ / "LoL_Datos" / "anonimizado" / "resumen_descarga.json").read_text(encoding="utf-8"))
    v1r = leer("v1")
    ps = r24["e4_punto_sin_regreso"]
    punto = ps["por_umbral"][f"{ps['umbral_principal']:.2f}"]
    partidas = pd.read_csv(e1.PUBLICO / "partidas.csv", dtype={"parche": str})
    final, _ = e1.filtrar(partidas)

    v1, c = datos_v1()
    e5 = {r["arquetipo"]: r for r in r58["e5"]}
    h1 = r24["e2_h1"]["por_fase"]
    h2 = r24["e3_h2"]
    h3 = r24["e4_h3"]
    c.update({
        "nFinal": mil(r1["partidas"]), "nUnicas": mil(r1["embudo"][0]["n"]),
        "nDerrotas": mil(r1["derrotas"]), "nVictorias": mil(r1["victorias"]),
        "nCuentas": str(final["cuentaPropia"].nunique()),
        "c1Derrotas": str(int(((final["cuentaPropia"] == "C1") & (final["gane"] == 0)).sum())),
        "nParches": str(final["parche"].nunique()),
        "mesInicio": final["mes"].min(), "mesFin": final["mes"].max(),
        "nPuuid": mil(anon["barrido_crudo"]["puuid"]), "nFugas": str(anon["fugas"]),
        "nDuo": str(resumen["duo_cuentas_propias"]),
        "dUnoMed": str(int(r1["d1"]["mediana_derrotas"])), "dDosMed": str(int(r1["d2"]["mediana_derrotas"])),
        "eUnoPct": f"{r1['e1']['pct_desacuerdo']:.0f}",
        "eUnoLo": f"{r1['e1']['ic95_wilson'][0]:.0f}", "eUnoHi": f"{r1['e1']['ic95_wilson'][1]:.0f}",
        "hDosObs": pct(h2["derrotas"]["observado"], 1),
        "hDosP": f"{h2['derrotas']['nula_corregida']['p_mayor']:.3f}",
        "hDosAntesCinco": str(h2["derrotas"]["quiebres_antes_min5"]),
        "hDosObsVic": pct(h2["victorias"]["observado"]),
        "hDosCorVic": pct(h2["victorias"]["nula_corregida"]["media"]),
        "hTresCinco": pct(h3["min_5"]["p"]), "hTresQuince": pct(h3["min_15"]["p"]),
        "hTresTreinta": pct(h3["min_30"]["p"]), "hTresRiesgo": str(int(h3["min_30"]["en_riesgo"])),
        # H3: el punto sin regreso (umbral principal) y la sensibilidad al umbral
        "hTresPunto": str(punto["minuto"]), "hTresPuntoP": f"{100 * punto['p']:.0f}",
        "hTresPuntoRiesgo": str(punto["en_riesgo"]), "hTresUmbral": f"{100 * ps['umbral_principal']:.0f}",
        "hTresPuntoDiez": str(ps["por_umbral"]["0.10"]["minuto"]),
        # H2 con la definición registrada (D1)
        "hDosUnoP": f"{h2['con_d1']['derrotas']['nula_corregida']['p_mayor']:.2f}",
        "hDosUnoObs": pct(h2["con_d1"]["derrotas"]["observado"]),
        "hDosUnoCor": pct(h2["con_d1"]["derrotas"]["nula_corregida"]["media"]),
        # V1: la ventaja se encoge y luego el remate
        "v1VMax": f"{v1r['ventaja_max_pct']:.1f}", "v1VAntes": f"{v1r['v_antes_del_remate_pct']:.1f}",
        "v1MinAntes": str(v1r["minuto_antes_del_remate"]), "v1RemateRival": str(v1r["objetivos_rival_remate"]),
        "pctAUno": pct(e5["A1"]["p"]), "pctADos": pct(e5["A2"]["p"]), "pctATres": pct(e5["A3"]["p"]),
        "pctACuatro": pct(e5["A4"]["p"]), "pctSinClas": pct(e5["Sin clasificar"]["p"]),
        "pctClas": pct(1 - e5["Sin clasificar"]["p"]),
        "exTranquilo": f"{r58['exploratorio_sin_clasificar']['mediana_pct_partida_con_abs_v_menor_5']:.0f}",
        "eOchoP": f"{r58['e8_cuentas']['p_permutacion']:.2f}",
    })
    for f, k in (("<15", "A"), ("15-25", "B"), (">=25", "C")):
        c[f"hUnoDer{k}"] = f"{h1[f]['derrotas']['tasa']:.2f}"
        c[f"hUnoVic{k}"] = f"{h1[f]['victorias']['tasa']:.2f}"

    html = (BASE / "plantilla.html").read_text(encoding="utf-8")
    html = re.sub(r"\{\{(\w+)\}\}", lambda m: c[m.group(1)] if m.group(1) in c else m.group(0), html)

    def svg(m):
        texto = (BASE / "figuras" / f"{m.group(1)}.svg").read_text(encoding="utf-8")
        texto = re.sub(r"<\?xml[^>]*\?>|<!DOCTYPE[^>]*>", "", texto)
        texto = re.sub(r"<metadata>.*?</metadata>", "", texto, flags=re.S)   # sin fechas
        # ids únicos por figura: matplotlib repite los mismos (clip paths) en cada SVG
        return texto.replace('id="', f'id="{m.group(1)}-').replace("url(#", f"url(#{m.group(1)}-") \
                    .replace('xlink:href="#', f'xlink:href="#{m.group(1)}-')
    html = re.sub(r"<!--svg:(\w+)-->", svg, html)
    html = html.replace("<!--datos-->", "window.LOL_DATA = " + json.dumps({"v1": v1}, ensure_ascii=False) + ";")

    sin = sorted(set(re.findall(r"\{\{(\w+)\}\}", html)))
    if sin:
        raise SystemExit(f"cifras sin valor en la plantilla: {sin}")
    (BASE / "presentacion_final.html").write_text(html, encoding="utf-8")
    print(f"presentacion_final.html: {len(c)} cifras, "
          f"{len(re.findall('<section', html))} láminas, {len(html) // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
