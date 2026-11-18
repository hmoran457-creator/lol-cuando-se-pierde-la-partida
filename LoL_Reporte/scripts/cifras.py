r"""Genera las cifras y tablas del reporte final desde los archivos de resultados.

Ningún número del reporte se escribe a mano: todos salen de aquí, como \macro{} en
tablas/cifras.tex o como tablas en tablas/*.tex. Si se vuelve a correr el análisis,
este script actualiza el reporte sin tocar el texto.

Fuentes, en el orden del flujo (todas van en el repositorio público):
    LoL_Datos/anonimizado/resumen_descarga.json   (conteos agregados de lo local:
                                                   listas por cuenta, dúos, eventos)
    LoL_Datos/anonimizado/resultados.json         (barrido de fugas y riesgo)
    LoL_Datos/anonimizado/publico/partidas.csv
    LoL_Analisis/resultados/{e1,e2_e4,e5_e8,v1}.json
    Trabajo complementario (sección del mismo nombre):
    LoL_Dimensionalidad/reduccion_dimensionalidad.ipynb   (salidas del notebook ejecutado)
    LoL_Exploratorio/analisis_exploratorio.ipynb          (ídem; sus salidas son agregados)
    LoL_Probabilidad/herramienta/modelo.json y LoL_Probabilidad/resultados/*.json

Uso:  python LoL_Reporte/scripts/cifras.py
"""
from __future__ import annotations

import json
import pathlib
import re
from html.parser import HTMLParser

import pandas as pd

RAIZ = pathlib.Path(__file__).resolve().parent.parent.parent
RES = RAIZ / "LoL_Analisis" / "resultados"
TAB = RAIZ / "LoL_Reporte" / "tablas"


def leer(ruta: pathlib.Path) -> dict:
    # Si falta una fuente se detiene: antes devolvía {} y el reporte se recompilaba con
    # ceros («0 cuentas propias») sin ningún aviso.
    if not ruta.exists():
        raise SystemExit(f"Falta {ruta.relative_to(RAIZ)}. Corre primero el análisis "
                         "(LoL_Analisis/scripts, en el orden del README).")
    return json.loads(ruta.read_text(encoding="utf-8"))


def es(x, dec: int = 1) -> str:
    """Formato del proyecto: espacio fino para miles y coma decimal."""
    if isinstance(x, bool):
        return "sí" if x else "no"
    if isinstance(x, int):
        return f"{x:,}".replace(",", "\\,")
    if isinstance(x, float):
        return f"{x:,.{dec}f}".replace(",", "\\,").replace(".", "{,}")
    return str(x)


def pct(x: float, dec: int = 0) -> str:
    return es(100 * x, dec)


def pval(x: float) -> str:
    """«p = 0,177» o «p < 0,001» (un p de permutación nunca es exactamente 0)."""
    return "\\(p < 0{,}001\\)" if x < 0.001 else f"\\(p = {es(x, 3)}\\)"


def tabla(nombre: str, titulo: str, etiqueta: str, columnas: str, encabezado: list[str],
          filas: list[list[str]], pie: list[str] | None = None) -> None:
    cuerpo = " \\\\\n".join(" & ".join(f) for f in filas) + " \\\\\n"
    extra = ("\\midrule\n" + " & ".join(pie) + " \\\\\n") if pie else ""
    (TAB / f"{nombre}.tex").write_text(
        "\\begin{table}[H]\n\\centering\\small\n"
        f"\\caption{{{titulo}}}\n\\label{{tab:{etiqueta}}}\n"
        f"\\begin{{tabular}}{{{columnas}}}\n\\toprule\n" + " & ".join(encabezado) + " \\\\\n"
        "\\midrule\n" + cuerpo + extra + "\\bottomrule\n\\end{tabular}\n\\end{table}\n",
        encoding="utf-8")


class _Tablas(HTMLParser):
    """Filas de las tablas HTML que pandas escribe en un notebook (celdas th y td, en orden)."""

    def __init__(self):
        super().__init__()
        self.filas: list[list[str]] = []
        self._fila: list[str] | None = None
        self._celda: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._fila = []
        elif tag in ("th", "td") and self._fila is not None:
            self._celda = ""

    def handle_endtag(self, tag):
        if tag in ("th", "td") and self._celda is not None and self._fila is not None:
            self._fila.append(self._celda.strip())
            self._celda = None
        elif tag == "tr" and self._fila is not None:
            self.filas.append(self._fila)
            self._fila = None

    def handle_data(self, data):
        if self._celda is not None:
            self._celda += data


def salidas(ruta: pathlib.Path) -> tuple[str, list[list[list[str]]]]:
    """El texto impreso y las tablas de un notebook ya ejecutado.

    En las tablas con índice de dos niveles, pandas no repite el primer nivel en las filas que
    lo comparten; aquí se rellena con el de la fila anterior para que cada fila sea completa.
    """
    if not ruta.exists():
        raise SystemExit(f"Falta {ruta.relative_to(RAIZ)}: ejecuta su construir_notebook.py.")
    nb = json.loads(ruta.read_text(encoding="utf-8"))
    texto, tablas = "", []
    for celda in nb["cells"]:
        for o in celda.get("outputs", []):
            if o.get("output_type") == "stream":
                texto += "".join(o["text"])
            html = o.get("data", {}).get("text/html")
            if html:
                p = _Tablas()
                p.feed("".join(html))
                ancho = max(len(f) for f in p.filas)
                filas, previa = [], []
                for f in p.filas:
                    if len(f) < ancho and previa:
                        f = previa[:ancho - len(f)] + f
                    filas.append(f)
                    previa = f
                tablas.append(filas)
    return texto, tablas


def buscar(tablas: list[list[list[str]]], encabezado: str) -> dict[tuple[str, ...], dict[str, str]]:
    """La tabla cuyo encabezado contiene `encabezado`, como {índice: {columna: valor}}."""
    for t in tablas:
        if encabezado in t[0]:
            cols = t[0]
            n_ind = sum(1 for c in cols if c == "")
            # La fila con los nombres del índice (p. ej. «minuto») no trae datos: se salta.
            return {tuple(f[:n_ind]): dict(zip(cols[n_ind:], f[n_ind:])) for f in t[1:]
                    if any(x != "" for x in f[n_ind:])}
    raise SystemExit(f"No se encontró la tabla con «{encabezado}» en el notebook")


def dato(texto: str, patron: str) -> float:
    m = re.search(patron, texto)
    if not m:
        raise SystemExit(f"No se encontró «{patron}» en las salidas del notebook")
    return float(m.group(1).replace(",", ""))


def numero(celda: str) -> float:
    """«13%», «40% [35%–47%]», «1.30» o «-1776» -> el primer número."""
    m = re.match(r"\s*(-?[\d.]+)", celda)
    if not m:
        raise SystemExit(f"Celda sin número en el notebook: «{celda}»")
    return float(m.group(1))


def complementario(c: dict[str, str]) -> None:
    """Cifras de la sección «Trabajo complementario», leídas de lo que cada trabajo generó."""
    # Reducción de dimensionalidad
    texto, tablas = salidas(RAIZ / "LoL_Dimensionalidad" / "reduccion_dimensionalidad.ipynb")
    c["drN"] = es(int(dato(texto, r"Matriz de datos: ([\d,]+) partidas")))
    c["drPcaDos"] = es(dato(texto, r"PC1\+PC2, el ([\d.]+)%"), 1)
    c["drPcUnoCorr"] = es(dato(texto, r"ventaja promedio de los 20 minutos: ([\d.]+)"), 3)
    c["drLda"] = es(dato(texto, r"5 pliegues\): ([\d.]+)%"), 1)
    c["drVveinte"] = es(dato(texto, r"si v\(20\) > 0 acierta el ([\d.]+)%"), 1)
    comp = buscar(tablas, "silueta victoria/derrota")
    sil = [numero(f["silueta victoria/derrota"]) for f in comp.values()]
    c["drSilMin"], c["drSilMax"] = es(min(sil), 2), es(max(sil), 2)

    # Análisis exploratorio
    texto, tablas = salidas(RAIZ / "LoL_Exploratorio" / "analisis_exploratorio.ipynb")
    parte = buscar(tablas, "parte BOTTOM")
    c["eaDefQuince"] = es(int(abs(numero(parte[("15", "Derrota")]["diferencia del equipo (oro)"]))))
    c["eaBotDer"] = es(int(numero(parte[("15", "Derrota")]["parte BOTTOM"])))
    c["eaMidDer"] = es(int(numero(parte[("15", "Derrota")]["parte MIDDLE"])))
    c["eaBotVic"] = es(int(numero(parte[("15", "Victoria")]["parte BOTTOM"])))
    antes = buscar(tablas, "va abajo")
    c["eaAbajoN"] = es(int(dato(texto, r"en las (\d+) restantes")))
    c["eaAbajoYo"] = es(int(numero(antes[("BOTTOM (yo)",)]["va abajo"])))
    c["eaAbajoMid"] = es(int(numero(antes[("MIDDLE",)]["va abajo"])))
    razon = buscar(tablas, "razón")
    c["eaMuerteContra"] = es(numero(razon[("muerte|en contra",)]["razón"]), 2)
    c["eaMuerteFavor"] = es(numero(razon[("muerte|a favor",)]["razón"]), 2)
    c["eaMiMuerte"] = es(numero(razon[("mi muerte",)]["razón"]), 2)
    c["eaBaronContra"] = es(numero(razon[("barón|en contra",)]["razón"]), 2)
    camino = buscar(tablas, "M2 − M1")
    c["eaCaminoMax"] = es(max(abs(numero(f["M2 − M1"])) for f in camino.values()), 3)
    veinte = buscar(tablas, "minuto 15")
    c["eaMenosCincoQuince"] = veinte[("v = −5 %",)]["minuto 15"].split()[0]
    muertes = buscar(tablas, "en campo rival")
    der, vic = muertes[("Derrota", "15 en adelante")], muertes[("Victoria", "15 en adelante")]
    c["eaMuerteDer"], c["eaMuerteVic"] = es(numero(der["por cada 10 min"]), 2), es(numero(vic["por cada 10 min"]), 2)
    c["eaCampoDer"], c["eaCampoVic"] = es(int(numero(der["en campo rival"]))), es(int(numero(vic["en campo rival"])))

    # Modelo de probabilidad de ganar
    base = RAIZ / "LoL_Probabilidad"
    m = leer(base / "herramienta" / "modelo.json")
    met, meta = m["meta"]["metricas"], m["meta"]
    res = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in (base / "resultados").glob("*.json")}
    perd = lambda n: res[n]["perdida_log"]  # noqa: E731
    elegido_m, elegido_o = m["marcador"]["nombre"], m["marcador_oro"]["nombre"]
    antes_m, antes_o = "fin_m_sin_baron_hl", "fin_mo_sin_baron_hl"
    numeros = lambda spec: sum(1 if abs(a - b) < 1e-12 else 2 for a, b in spec["param"])  # noqa: E731
    c["pgPartidas"], c["pgPrueba"] = es(meta["partidas"]), es(meta["partidas_prueba"])
    c["pgNumMarc"], c["pgNumOro"] = es(numeros(m["marcador"])), es(numeros(m["marcador_oro"]))
    c["pgAntesMarc"], c["pgElegMarc"] = es(perd(antes_m), 3), es(perd(elegido_m), 3)
    c["pgAntesOro"], c["pgElegOro"] = es(perd(antes_o), 3), es(perd(elegido_o), 3)
    c["pgSoloOro"] = es(perd("base_oro_interaccion"), 3)
    c["pgXpDif"] = es(abs(perd("nv_m_xp_tv") - perd("nv_m_tv")), 3)
    ob = [perd(n) - perd(elegido_m) for n in res if n.startswith("ob_")]
    c["pgObjDifMax"] = es(max(abs(x) for x in ob), 4)
    cal = meta["calibracion"]["marcador"]
    c["pgCalMax"] = es(int(round(100 * max(abs(a - b) for a, b in cal))))
    pr = res["prueba_temporal"]
    c["pgPruebaAntesMarc"], c["pgPruebaMarc"] = es(pr[antes_m]["perdida_log"], 3), es(pr[elegido_m]["perdida_log"], 3)
    c["pgPruebaOro"] = es(pr[elegido_o]["perdida_log"], 3)
    fam = met["familias"]
    f3 = lambda x: es(x, 3)  # noqa: E731
    tabla("probabilidad", "Modelo de probabilidad de ganar: pérdida logarítmica en validación cruzada "
          "por partida (menor es mejor).", "probabilidad", "lrr",
          ["Modelo", "Solo el marcador", "Marcador y oro"],
          [["No saber nada (la proporción de victorias)", f3(perd("base_proporcion")), "—"],
           ["Logística simple (con oro: solo el oro)", f3(perd("base_marcador_dif")), f3(perd("base_oro_interaccion"))],
           ["Mejor árbol combinado", f3(fam["arboles_marcador"]["perdida_log"]), f3(fam["arboles_oro"]["perdida_log"])],
           ["Mejor de las otras familias", f3(fam["otros_marcador"]["perdida_log"]), f3(fam["otros_oro"]["perdida_log"])],
           ["Logística con efectos por minuto", f3(perd(antes_m)), f3(perd(antes_o))],
           ["\\textbf{La misma, con los niveles (elegida)}", f"\\textbf{{{f3(perd(elegido_m))}}}",
            f"\\textbf{{{f3(perd(elegido_o))}}}"]])


def main() -> int:
    TAB.mkdir(parents=True, exist_ok=True)
    resumen = leer(RAIZ / "LoL_Datos" / "anonimizado" / "resumen_descarga.json")
    anon = leer(RAIZ / "LoL_Datos" / "anonimizado" / "resultados.json")
    e1, e24, e58, v1 = (leer(RES / f"{n}.json") for n in ("e1", "e2_e4", "e5_e8", "v1"))
    # `parche` como texto: leído como número, «15.10» se vuelve 15.1 y se junta con el
    # parche 15.1 (pasó: daba 42 parches en vez de 46).
    partidas = pd.read_csv(RAIZ / "LoL_Datos" / "anonimizado" / "publico" / "partidas.csv",
                           dtype={"parche": str})
    p = partidas
    final = p[(p["cola"] == 420) & (p["jugadores"] == 10)
              & (p["rendicionTemprana"] == 0) & (p["duracionMin"] >= 5)
              & ~((p["rendicion"] == 1) & (p["duracionMin"] < 10))
              & p["equipoPropio"].notna()]
    assert len(final) == e1["partidas"], "la muestra pública no coincide con la del análisis"

    c: dict[str, str] = {}
    cuentas = resumen["cuentas"]
    c["nCuentas"] = es(len(cuentas))
    c["listaTotal"] = es(sum(x.get("ids_todas") or 0 for x in cuentas))
    c["listaCola"] = es(sum(x.get("ids_420") or 0 for x in cuentas))
    c["nUnicas"] = es(e1["embudo"][0]["n"])
    c["nFinal"] = es(e1["partidas"])
    c["nDerrotas"] = es(e1["derrotas"])
    c["nVictorias"] = es(e1["victorias"])
    c["nQuitadas"] = es(e1["embudo"][0]["n"] - e1["partidas"])
    c["nDuo"] = es(resumen["duo_cuentas_propias"])
    # La primera cuenta sola: el plan pedía unas 150 partidas para continuar
    uno = final[final["cuentaPropia"] == "C1"]
    c["nCuentaUno"], c["derCuentaUno"] = es(len(uno)), es(int((uno["gane"] == 0).sum()))
    c["nBottom"] = es(int((final["rolPropio"] == "BOTTOM").sum()))
    c["pctBottom"] = pct((final["rolPropio"] == "BOTTOM").mean())
    c["nParches"] = es(final["parche"].nunique())
    c["mesInicio"], c["mesFin"] = final["mes"].min(), final["mes"].max()
    c["nPuuid"] = es(anon.get("barrido_crudo", {}).get("puuid", 0))
    c["nNombres"] = es(anon.get("barrido_crudo", {}).get("riotId", 0))
    c["nFugas"] = es(anon.get("fugas", 0))
    # eventos y cuadros de la MUESTRA FINAL (van junto a \nFinal en la portada)
    c["nEventos"] = es(resumen["eventos_muestra"])
    c["nCuadros"] = es(resumen["cuadros_muestra"])
    riesgo = {r["Nivel"]: r for r in anon.get("k_participante", [])}
    c["pctUnicosSinCampeon"] = es(riesgo.get("Sin campeón", {}).get("pct_unicas", 0.0))
    # Riesgo residual de la tabla PÚBLICA de partidas: mes + cuenta + duración al segundo
    # casi siempre señalan una sola partida. Se dice en el reporte, en vez de darlo por resuelto.
    todas = p[p["equipoPropio"].notna()]
    clave = todas.groupby(["mes", "cuentaPropia", "duracionMin"])["partida"].transform("size")
    c["pctPartidaUnica"] = pct((clave == 1).mean())
    c["nPartidasPublicas"] = es(len(todas))
    c["nEventosPublicos"] = es(len(pd.read_csv(RAIZ / "LoL_Datos" / "anonimizado" / "publico"
                                               / "eventos_equipo.csv", usecols=["partida"])))

    # E1
    x = e1["e1"]
    c["eUnoPct"] = es(x["pct_desacuerdo"], 0)
    c["eUnoLo"], c["eUnoHi"] = es(x["ic95_wilson"][0], 0), es(x["ic95_wilson"][1], 0)
    c["eUnoConDdos"] = es(x["derrotas_con_d2"])
    c["eUnoDesac"] = es(x["desacuerdo_mas_de_2_min"])
    c["eUnoMedDif"] = es(int(x["mediana_abs_dif"]))
    c["dUnoMedDer"] = es(int(e1["d1"]["mediana_derrotas"]))
    c["dUnoMedVic"] = es(int(e1["d1"]["mediana_victorias"]))
    c["dUnoAntesCincoDer"] = es(e1["d1"]["pct_d1_antes_min5_derrotas"], 0)
    c["dUnoAntesCincoVic"] = es(e1["d1"]["pct_d1_antes_min5_victorias"], 0)
    c["dDosMed"] = es(int(e1["d2"]["mediana_derrotas"]))
    c["derrotasArriba"] = es(e1["derrotas_terminan_arriba"])
    c["derrotasNuncaDetras"] = es(e1["derrotas_nunca_detras"])

    # E2
    h1 = e24["e2_h1"]
    c["hUnoDerTasa"], c["hUnoVicTasa"] = es(h1["derrotas"]["tasa"], 2), es(h1["victorias"]["tasa"], 2)
    c["hUnoDerPartidas"], c["hUnoVicPartidas"] = es(h1["derrotas"]["partidas"]), es(h1["victorias"]["partidas"])
    c["hUnoMenos"] = pct(1 - h1["razon_der_entre_vic"])
    filas = []
    for f, etq in (("<15", "Antes del minuto 15"), ("15-25", "Minutos 15 a 25"), (">=25", "Minuto 25 o después")):
        d, v = h1["por_fase"][f]["derrotas"], h1["por_fase"][f]["victorias"]
        filas.append([etq, f"{es(d['tasa'], 2)} [{es(d['ic95'][0], 2)}; {es(d['ic95'][1], 2)}]",
                      es(d["partidas"]), f"{es(v['tasa'], 2)} [{es(v['ic95'][0], 2)}; {es(v['ic95'][1], 2)}]",
                      es(v["partidas"])])
    tabla("h1_fases", "H1: objetivos propios por minuto con ventaja real, por fase (IC 95\\,\\% bootstrap por partida).",
          "h1fases", "lrrrr", ["Fase", "Derrotas", "n", "Victorias", "n"], filas)
    for f, k in (("<15", "A"), ("15-25", "B"), (">=25", "C")):
        c[f"hUnoDer{k}"] = es(h1["por_fase"][f]["derrotas"]["tasa"], 2)
        c[f"hUnoVic{k}"] = es(h1["por_fase"][f]["victorias"]["tasa"], 2)

    # E3
    h2 = e24["e3_h2"]
    for g, k in (("derrotas", "Der"), ("victorias", "Vic")):
        c[f"hDosObs{k}"] = pct(h2[g]["observado"], 1)
        c[f"hDosReg{k}"] = pct(h2[g]["nula_registrada"]["media"], 1)
        c[f"hDosCor{k}"] = pct(h2[g]["nula_corregida"]["media"], 1)
        c[f"hDosPCor{k}"] = es(h2[g]["nula_corregida"]["p_mayor"], 3)
        c[f"hDosPReg{k}"] = es(h2[g]["nula_registrada"]["p_menor"], 3)
    # La rama con la definición REGISTRADA (D1, la mayor caída)
    for g, k in (("derrotas", "Der"), ("victorias", "Vic")):
        d1 = h2["con_d1"][g]
        c[f"hDosUnoObs{k}"] = pct(d1["observado"], 1)
        c[f"hDosUnoReg{k}"] = pct(d1["nula_registrada"]["media"], 1)
        c[f"hDosUnoCor{k}"] = pct(d1["nula_corregida"]["media"], 1)
        c[f"hDosUnoPCor{k}"] = pval(d1["nula_corregida"]["p_mayor"])
        c[f"hDosUnoPReg{k}"] = pval(d1["nula_registrada"]["p_menor"])
    c["alfaBonf"] = es(h2["alfa_bonferroni"], 4)
    c["hDosPasaBonf"] = "sí" if h2["derrotas"]["nula_corregida"]["p_mayor"] < h2["alfa_bonferroni"] else "no"
    c["hDosAntesCinco"] = es(h2["derrotas"]["quiebres_antes_min5"])
    c["hDosPrimerObj"] = es(h2["primer_objetivo_mayor_min"], 1)
    c["neutrales"] = es(e24["objetivos_neutrales_excluidos"])

    # E4
    h3 = e24["e4_h3"]
    tabla("h3_curva", "H3: de las partidas que van abajo con \\(v \\le -5\\)\\,\\% en el minuto \\(t\\), cuántas terminaron ganando.",
          "h3curva", "rrrr", ["Minuto", "En riesgo", "Remontaron", "\\% (IC 95\\,\\% Wilson)"],
          [[k.split("_")[1], es(int(v["en_riesgo"])), es(int(v["remontaron"])),
            f"{pct(v['p'])} [{pct(v['lo'])}; {pct(v['hi'])}]"] for k, v in h3.items()])
    for m in (5, 10, 15, 20, 25, 30):
        c[f"hTres{['Cinco','Diez','Quince','Veinte','Veinticinco','Treinta'][[5,10,15,20,25,30].index(m)]}"] = pct(h3[f"min_{m}"]["p"])
    c["hTresRiesgoTreinta"] = es(int(h3["min_30"]["en_riesgo"]))
    # El punto sin regreso (umbral principal 5 %, sensibilidad 3 % y 10 %)
    ps = e24["e4_punto_sin_regreso"]
    u = ps["por_umbral"][f"{ps['umbral_principal']:.2f}"]
    c["hTresUmbral"] = pct(ps["umbral_principal"])
    c["hTresPunto"] = es(u["minuto"])
    c["hTresPuntoP"], c["hTresPuntoLo"], c["hTresPuntoHi"] = pct(u["p"], 1), pct(u["lo"], 1), pct(u["hi"], 1)
    c["hTresPuntoRiesgo"], c["hTresPuntoRemontaron"] = es(u["en_riesgo"]), es(u["remontaron"])
    for clave, k in (("0.10", "Diez"), ("0.03", "Tres")):
        s = ps["por_umbral"].get(clave)
        c[f"hTresPunto{k}"] = es(s["minuto"]) if s else "—"
        c[f"hTresPunto{k}Riesgo"] = es(s["en_riesgo"]) if s else "—"

    # E5–E8
    nombres = {"A1": "A1 · Derrota desde línea", "A2": "A2 · Ventaja desperdiciada",
               "A3": "A3 · Decidida en un objetivo", "A4": "A4 · Muy desigual",
               "Sin clasificar": "Sin clasificar"}
    filas = []
    for r in e58["e5"]:
        filas.append([nombres[r["arquetipo"]], es(r["n"]), f"{pct(r['p'])} [{pct(r['lo'])}; {pct(r['hi'])}]"])
        k = {"A1": "AUno", "A2": "ADos", "A3": "ATres", "A4": "ACuatro", "Sin clasificar": "SinClas"}[r["arquetipo"]]
        c[f"pct{k}"], c[f"n{k}"] = pct(r["p"]), es(r["n"])
        if r["arquetipo"] == "Sin clasificar":
            c["pctClas"] = pct(1 - r["p"])   # las cuatro reglas juntas (no solo A1+A2+A4)
        c[f"lo{k}"], c[f"hi{k}"] = pct(r["lo"]), pct(r["hi"])
    tabla("arquetipos", f"E5: arquetipos de las {e58['derrotas']} derrotas (IC 95\\,\\% de Wilson).",
          "arquetipos", "lrr", ["Arquetipo", "Derrotas", "\\% [IC 95\\,\\%]"], filas)
    e6 = e58["e6"]
    tabla("sensibilidad", "E6: derrotas por arquetipo al mover el umbral de 5\\,\\%.", "sensibilidad",
          "lrrrrr", ["Umbral", "A1", "A2", "A3", "A4", "Sin clasificar"],
          [[f"{es(float(u), 0)}\\,\\%"] + [es(int(n)) for n in fila.values()] for u, fila in e6["conteos"].items()])
    c["eSeisCuatro"], c["eSeisSeis"] = es(e6["cambian_con_4"]), es(e6["cambian_con_6"])
    c["eSeisCuatroPct"] = pct(e6["cambian_con_4"] / e58["derrotas"])
    c["eSeisSeisPct"] = pct(e6["cambian_con_6"] / e58["derrotas"])
    e7 = e58["e7"]
    c["eSieteCorte"] = e7["corte_mes"]
    c["eSieteUno"], c["eSieteDos"] = es(e7["derrotas_primera"]), es(e7["derrotas_segunda"])
    c["eSieteMedUno"], c["eSieteMedDos"] = es(int(e7["mediana_d2_primera"])), es(int(e7["mediana_d2_segunda"]))
    c["eSieteP"] = es(e7["chi2_p"], 2)
    e8 = e58["e8_cuentas"]
    c["eOchoP"], c["eOchoPAprox"] = es(e8["p_permutacion"], 2), es(e8["chi2_p_aprox"], 2)
    c["eOchoEspMin"] = es(e8["esperado_min"], 1)
    b = e58["e8_bottom"]
    c["botPartidas"], c["botDerrotas"] = es(b["partidas"]), es(b["derrotas"])
    c["botHDosP"] = es(b["h2_derrotas"]["p_mayor"], 3)
    c["botHTresTreinta"] = pct(b["h3"]["30"])
    for f, k in (("<15", "A"), ("15-25", "B"), (">=25", "C")):
        c[f"botHUnoDer{k}"] = es(b["h1_por_fase"][f]["derrotas"], 2)
        c[f"botHUnoVic{k}"] = es(b["h1_por_fase"][f]["victorias"], 2)
    ex = e58["exploratorio_sin_clasificar"]
    c["exTranquilo"] = es(ex["mediana_pct_partida_con_abs_v_menor_5"], 0)
    c["exNuncaDiez"] = es(ex["pct_nunca_bajo_menos_10"], 0)
    c["exDdos"] = es(int(ex["mediana_d2"]))
    c["exDur"], c["exDurClas"] = es(int(ex["mediana_duracion"])), es(int(ex["mediana_duracion_clasificadas"]))

    # tabla por cuenta, desde la tabla pública
    filas, tot = [], [0, 0, 0, 0]
    for cu in sorted(final["cuentaPropia"].dropna().unique()):
        s = final[final["cuentaPropia"] == cu]
        ids = next((x.get("ids_420") for x in cuentas if x["cuenta"] == cu), None)
        fila = [ids or 0, len(s), int(s["gane"].sum()), int((s["gane"] == 0).sum())]
        tot = [a + b_ for a, b_ in zip(tot, fila)]
        filas.append([cu] + [es(int(v)) for v in fila])
    tabla("cuentas", "La muestra por cuenta, después del filtrado.", "cuentas", "lrrrr",
          ["Cuenta", "Cola 420 en la lista", "Muestra final", "Victorias", "Derrotas"], filas,
          ["\\textbf{Total}"] + [f"\\textbf{{{es(int(v))}}}" for v in tot])
    tabla("embudo", "Embudo de filtrado, rehecho desde la tabla pública de partidas.", "embudo", "lrr",
          ["Paso", "Partidas", "Quita"],
          [[p["paso"], es(p["n"]), "—" if i == 0 else es(e1["embudo"][i - 1]["n"] - p["n"])]
           for i, p in enumerate(e1["embudo"])])

    # V1
    c["vUnoArq"], c["vUnoN"] = v1["arquetipo"], es(v1["derrotas_en_el_arquetipo"])
    c["vUnoDur"] = es(v1["duracion_min"], 1)
    c["vUnoMax"], c["vUnoMaxOro"] = es(v1["ventaja_max_pct"], 1), es(v1["ventaja_max_oro"])
    c["vUnoMaxMin"], c["vUnoDdos"] = es(v1["minuto_ventaja_max"]), es(v1["d2"])
    c["vUnoArribaHasta"] = es(v1["d2"] - 1)
    c["vUnoArriba"], c["vUnoDurMin"] = es(v1["minutos_arriba"]), es(int(v1["duracion_min"]))
    abajo = [m for m in v1["minutos_abajo"] if m < v1["d2"]]
    c["vUnoAbajoAntes"] = ", ".join(str(m) for m in abajo) if abajo else "ninguno"
    c["vUnoAntesRemate"], c["vUnoMinAntesRemate"] = es(v1["v_antes_del_remate_pct"], 1), es(v1["minuto_antes_del_remate"])
    c["vUnoRemateRival"], c["vUnoRematePropio"] = es(v1["objetivos_rival_remate"]), es(v1["objetivos_propios_remate"])
    c["vUnoPerdido"] = pct(1 - v1["v_antes_del_remate_pct"] / v1["ventaja_max_pct"])
    c["vUnoFinal"] = es(v1["v_final_pct"], 1)
    c["vUnoObjPropios"], c["vUnoObjRival"] = es(v1["objetivos_propios"]), es(v1["objetivos_rival"])

    complementario(c)

    (TAB / "cifras.tex").write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in c.items()),
                                    encoding="utf-8")
    print(f"{len(c)} cifras y {len(list(TAB.glob('*.tex'))) - 1} tablas en {TAB}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
