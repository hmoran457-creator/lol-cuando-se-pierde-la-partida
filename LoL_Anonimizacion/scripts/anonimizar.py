r"""Anonimización del corpus de League of Legends (match-v5 + timeline).

Convierte los JSON crudos de Riot en las cuatro tablas del proyecto (partidas,
participantes, cuadros, eventos) aplicando una política explícita por campo, y luego
MIDE el resultado en vez de afirmarlo:

1. Barrido de fugas: busca en los CSV de salida cada identificador original
   (puuid, summonerId, Riot ID, matchId, gameId). Se corre también sobre el JSON crudo
   como control negativo: un barrido que no encuentra nada en el crudo no prueba nada.
2. Riesgo de reidentificación: tamaño de clase de equivalencia (k) sobre los
   cuasi-identificadores, en tres niveles de generalización.

Nunca imprime un valor de identificador: un reporte de fuga que cita la fuga es otra fuga.

Uso:
    python scripts/anonimizar.py                       # corpus de LoL_EDA/datos
    python scripts/anonimizar.py --datos <carpeta>     # otro corpus (p. ej. el propio)

La llave HMAC de los seudónimos se genera al azar en cada corrida y no se guarda, salvo
que se defina la variable de entorno LOL_ANON_KEY (necesaria si hay que unir corridas).
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import pathlib
import secrets
from datetime import datetime, timezone

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATOS_DEFECTO = ROOT.parent / "LoL_EDA" / "datos"
SALIDA, TAB, FIG = ROOT / "salida", ROOT / "tablas", ROOT / "figuras"

# ─────────────────────────────────────────── la política, campo por campo
# Una sola fuente de verdad: el reporte imprime esta tabla, no una copia a mano.
POLITICA = [
    # (campo en el JSON, nivel, técnica, destino)
    ("riotIdGameName / riotIdName", "participante", "Supresión", "—"),
    ("riotIdTagline", "participante", "Supresión", "—"),
    ("summonerName", "participante", "Supresión", "—"),
    ("summonerId", "participante", "Supresión", "—"),
    ("profileIcon", "participante", "Supresión", "—"),
    ("puuid", "participante", "Seudonimización (HMAC-SHA256)", "jugador, es_propio, cuenta"),
    ("metadata.participants", "partida", "Supresión", "—"),
    ("matchId", "partida", "Seudonimización (HMAC-SHA256)", "partida"),
    ("gameId", "partida y eventos", "Supresión", "—"),
    ("gameName, tournamentCode", "partida", "Supresión", "—"),
    ("gameCreation", "partida", "Generalización (fecha → mes)", "mes"),
    ("gameStartTimestamp, gameEndTimestamp", "partida", "Supresión", "—"),
    ("gameVersion", "partida", "Generalización (versión → parche)", "parche"),
    ("summonerLevel", "participante", "Generalización (bandas)", "bandaNivel"),
    ("victimDamage*[].name", "eventos", "Supresión (no se exporta)", "—"),
    ("championName, teamPosition", "participante", "Se conserva (análisis)", "campeon, rol"),
    ("timestamp de cuadros y eventos", "cuadros, eventos", "Se conserva (relativo al inicio)", "ms, minuto"),
    ("position {x, y}", "cuadros, eventos", "Se conserva", "x, y"),
    ("oro, xp, KDA, daño, visión, objetivos", "todos", "Se conserva (no identifica)", "—"),
    ("eventos de la tabla pública", "eventos (público)",
     "Minimización: solo torres y monstruos épicos; sin posición ni víctima", "eventos_equipo"),
]

# Lo único que el análisis lee de los eventos (e2_e4.cargar). Publicar más (compras, guardianes,
# posiciones x/y, milisegundos de cada jugada) no agrega reproducibilidad y sí huella.
EVENTOS_PUBLICOS = ["BUILDING_KILL", "ELITE_MONSTER_KILL"]
COLUMNAS_EVENTOS_PUBLICOS = ["partida", "tipo", "ms", "equipoAutor", "monsterType"]

BANDAS_NIVEL = [(1, 100, "1–99"), (100, 300, "100–299"), (300, 600, "300–599"), (600, 10**6, "600+")]


def seudonimo(valor: object, llave: bytes, largo: int = 12) -> str:
    """Clave estable y no reversible. HMAC y no un hash simple: un matchId tiene
    pocos dígitos variables y sha256(matchId) se revierte enumerando."""
    if valor in (None, ""):
        return ""
    return hmac.new(llave, str(valor).encode("utf-8"), hashlib.sha256).hexdigest()[:largo]


def banda_nivel(nivel: object) -> str:
    try:
        n = int(nivel)
    except (TypeError, ValueError):
        return "*"
    return next((etq for lo, hi, etq in BANDAS_NIVEL if lo <= n < hi), "*")


def mes(ms_epoch: object) -> str:
    if not ms_epoch:
        return "*"
    return datetime.fromtimestamp(int(ms_epoch) / 1000, tz=timezone.utc).strftime("%Y-%m")


def dia(ms_epoch: object) -> str:
    if not ms_epoch:
        return "*"
    return datetime.fromtimestamp(int(ms_epoch) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def cargar(datos: pathlib.Path):
    for f in sorted(datos.glob("getMatch_*.json")):
        m = json.loads(f.read_text(encoding="utf-8"))
        t = json.loads((datos / f.name.replace("getMatch", "getTimeline")).read_text(encoding="utf-8"))
        yield m, t


def identificadores(m: dict, campeones: set[str]) -> dict[str, set[str]]:
    """Los valores que NUNCA deben aparecer en la salida, por tipo.

    Los nombres cortos, puramente numéricos o iguales a un campeón se excluyen del
    barrido: un tagline «1234» choca con cualquier cifra de oro y uno igual a un
    campeón choca con la columna `campeon` (ambas colisiones se midieron en el corpus).
    """
    ids: dict[str, set[str]] = {"puuid": set(), "summonerId": set(), "riotId": set(),
                                "matchId": {m["metadata"]["matchId"]},
                                "gameId": {str(m["info"]["gameId"])}}
    for p in m["info"]["participants"]:
        for k in ("puuid", "summonerId"):
            if p.get(k):
                ids[k].add(str(p[k]))
        for k in ("riotIdGameName", "riotIdName", "summonerName"):
            v = str(p.get(k) or "")
            if len(v) >= 3 and not v.isdigit() and v not in campeones:
                ids["riotId"].add(v)
    return ids


def tablas(datos: pathlib.Path, llave: bytes, propios: dict[str, str] | None = None):
    propios = propios or {}
    partidas, participantes, cuadros, eventos = [], [], [], []
    crudo_qi, ids_todos = [], {}
    for m, t in cargar(datos):
        info = m["info"]
        mid = m["metadata"]["matchId"]
        pid = seudonimo(mid, llave)
        campeones = {p["championName"] for p in info["participants"]}
        for k, v in identificadores(m, campeones).items():
            ids_todos.setdefault(k, set()).update(v)
        ganador = next((x["teamId"] for x in info["teams"] if x.get("win")), None)
        # Si dos cuentas propias están en la misma partida, otra persona jugaba una en dúo
        # conmigo: yo soy la de BOTTOM y la otra cuenta se trata como un compañero más.
        mias = [p for p in info["participants"] if p.get("puuid") in propios]
        yo = next((p for p in mias if p.get("teamPosition") == "BOTTOM"), mias[0] if mias else None)
        yo_puuid = yo.get("puuid") if yo else None
        ps = info["participants"]
        partidas.append({
            "partida": pid, "parche": ".".join(str(info.get("gameVersion")).split(".")[:2]),
            "cola": info.get("queueId"), "mes": mes(info.get("gameCreation")),
            "duracionMin": round(info.get("gameDuration", 0) / 60, 2),
            "jugadores": len(ps), "ganador": ganador,
            # Lo necesario para rehacer el filtro y la medida v(t) desde las tablas
            # PÚBLICAS: de qué lado jugué y cómo terminó. El lado (100/200) no identifica.
            "equipoPropio": yo["teamId"] if yo else None,
            "rolPropio": (yo.get("teamPosition") or "") if yo else "",
            "cuentaPropia": propios.get(yo_puuid, "") if yo else "",
            "gane": int(bool(yo.get("win"))) if yo else None,
            "rendicionTemprana": int(any(p.get("gameEndedInEarlySurrender") for p in ps)),
            "rendicion": int(any(p.get("gameEndedInSurrender") for p in ps)),
        })
        equipo = {p["participantId"]: p["teamId"] for p in ps}
        for p in info["participants"]:
            participantes.append({
                "partida": pid, "participantId": p["participantId"],
                "jugador": seudonimo(p.get("puuid"), llave),
                # Se decide ANTES del HMAC: con llave efímera, después ya no se puede.
                "es_propio": int(yo_puuid is not None and p.get("puuid") == yo_puuid),
                "cuenta": propios.get(p.get("puuid"), "") if p.get("puuid") == yo_puuid else "",
                "teamId": p["teamId"],
                "campeon": p.get("championName"), "rol": p.get("teamPosition") or "",
                "gano": int(bool(p.get("win"))), "k": p.get("kills"), "d": p.get("deaths"),
                "a": p.get("assists"), "oro": p.get("goldEarned"),
                "dano": p.get("totalDamageDealtToChampions"), "vision": p.get("visionScore"),
                "bandaNivel": banda_nivel(p.get("summonerLevel")),
            })
            # Los cuasi-identificadores tal como llegan, solo en memoria, para medir k.
            crudo_qi.append({
                "partida": pid, "campeon": p.get("championName"), "rol": p.get("teamPosition") or "",
                "parche": partidas[-1]["parche"], "cola": info.get("queueId"),
                "dia": dia(info.get("gameCreation")), "mes": partidas[-1]["mes"],
                "nivel": p.get("summonerLevel"), "bandaNivel": banda_nivel(p.get("summonerLevel")),
                "teamId": p["teamId"], "gano": int(bool(p.get("win"))),
            })
        for i, fr in enumerate(t["info"]["frames"]):
            for k, pf in fr["participantFrames"].items():
                pos = pf.get("position") or {}
                cuadros.append({
                    "partida": pid, "minuto": i, "participantId": int(k),
                    "teamId": equipo.get(int(k)), "oroTotal": pf.get("totalGold"),
                    "xp": pf.get("xp"), "nivel": pf.get("level"),
                    "x": pos.get("x"), "y": pos.get("y"),
                })
            for e in fr.get("events", []):
                pos = e.get("position") or {}
                # Equipo del autor: killerTeamId en monstruos; en lo demás, el equipo de
                # killerId. NO teamId: en BUILDING_KILL nombra al equipo que perdió la torre.
                autor = e.get("killerTeamId") or equipo.get(e.get("killerId"))
                if autor is None and e["type"] in ("BUILDING_KILL", "TURRET_PLATE_DESTROYED") \
                        and e.get("teamId") in (100, 200):
                    autor = 300 - e["teamId"]   # la derribaron súbditos: el otro equipo
                eventos.append({
                    "partida": pid, "tipo": e["type"], "ms": e.get("timestamp"),
                    "equipoAutor": autor, "equipoVictima": equipo.get(e.get("victimId")),
                    "killerId": e.get("killerId"), "victimId": e.get("victimId"),
                    "nAsistencias": len(e.get("assistingParticipantIds") or []),
                    "killerTeamId": e.get("killerTeamId"), "monsterType": e.get("monsterType"),
                    "x": pos.get("x"), "y": pos.get("y"),
                })
    return ({"partidas": pd.DataFrame(partidas), "participantes": pd.DataFrame(participantes),
             "cuadros": pd.DataFrame(cuadros), "eventos": pd.DataFrame(eventos)},
            pd.DataFrame(crudo_qi), sin_campeones(ids_todos, participantes))


def sin_campeones(ids: dict[str, set[str]], participantes: list[dict]) -> dict[str, set[str]]:
    """Quita de los nombres a barrer los que son nombre de campeón en CUALQUIER partida.

    `identificadores` solo ve los campeones de su propia partida, pero la columna
    `campeon` de la salida tiene los de todas: un jugador llamado como un campeón que se
    jugó en otra partida chocaba ahí (medido en la muestra propia). Ninguna columna de
    salida lleva nombres de jugador, así que esa exclusión no esconde una fuga real.
    """
    todos = {p["campeon"] for p in participantes}
    return {**ids, "riotId": ids.get("riotId", set()) - todos}


def valores_salida(carpeta: pathlib.Path) -> str:
    """Los valores DISTINTOS de texto de todos los CSV de salida, uno por renglón.

    Barrer el texto completo no escala: con ~1,200 partidas son cientos de MB y miles de
    nombres. Un identificador que se fugara aparecería como valor de una celda (o dentro
    de una), así que basta con los valores distintos. Las celdas puramente numéricas se
    omiten: ningún identificador barrido es solo dígitos.
    """
    vistos: set[str] = set()
    for ruta in sorted(carpeta.rglob("*.csv")):
        df = pd.read_csv(ruta, dtype=str, keep_default_na=False)
        for col in df.columns:
            vistos.update(v for v in df[col].unique()
                          if v and not v.replace(".", "", 1).lstrip("-").isdigit())
    return "\n".join(sorted(vistos))


def valores_crudo(datos: pathlib.Path) -> str:
    """Control negativo: los valores distintos de los registros crudos, uno por renglón.
    Los registros traen los cinco tipos de identificador; las líneas temporales solo
    repiten puuid y gameId, que ya están aquí."""
    vistos: set[str] = set()

    def caminar(o) -> None:
        if isinstance(o, dict):
            for v in o.values():
                caminar(v)
        elif isinstance(o, list):
            for v in o:
                caminar(v)
        elif isinstance(o, (str, int)) and not isinstance(o, bool):
            vistos.add(str(o))

    for f in sorted(datos.glob("getMatch_*.json")):
        caminar(json.loads(f.read_text(encoding="utf-8")))
    return "\n".join(sorted(vistos))


def barrer(texto: str, ids: dict[str, set[str]]) -> dict[str, int]:
    """Cuántos identificadores de cada tipo aparecen en `texto`. Sin valores.

    Los nombres se buscan como palabra completa: un nombre de tres letras aparece como
    fragmento dentro del nombre de algún campeón (medido en la muestra propia), y eso
    no es una fuga. Los demás identificadores son largos y se buscan tal cual.
    """
    def palabra(c: str) -> bool:
        return c.isalnum() or c == "_"

    def hay(tipo: str, v: str) -> bool:
        # str.find y no una regex: el control negativo barre ~80 MB de JSON crudo y una
        # regex por nombre (cientos de nombres) tardaba minutos.
        i = texto.find(v)
        if tipo != "riotId":
            return i >= 0
        while i >= 0:
            antes = texto[i - 1] if i > 0 else " "
            despues = texto[i + len(v)] if i + len(v) < len(texto) else " "
            if not palabra(antes) and not palabra(despues):
                return True
            i = texto.find(v, i + 1)
        return False
    return {k: sum(1 for v in vals if hay(k, v)) for k, vals in ids.items()}


def riesgo(qi: pd.DataFrame, columnas: list[str]) -> dict:
    tam = qi.groupby(columnas, dropna=False)[columnas[0]].transform("size")
    return {"filas": len(qi), "clases": int(qi.groupby(columnas, dropna=False).ngroups),
            "k_min": int(tam.min()), "unicas": int((tam == 1).sum()),
            "pct_unicas": round(100 * (tam == 1).mean(), 1)}


def a_latex(df: pd.DataFrame, nombre: str, titulo: str, etiqueta: str, columnas: str) -> None:
    cuerpo = df.to_latex(index=False, escape=True, column_format=columnas)
    (TAB / f"{nombre}.tex").write_text(
        "\\begin{table}[H]\n\\centering\n\\small\n"
        f"\\caption{{{titulo}}}\n\\label{{tab:{etiqueta}}}\n{cuerpo}\\end{{table}}\n",
        encoding="utf-8")


def figura_riesgo(k_part: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.4, 2.4))
    etiquetas = [r["Nivel"] for r in k_part][::-1]
    valores = [r["pct_unicas"] for r in k_part][::-1]
    ax.barh(etiquetas, valores, color=["#2a78d6" if v < 100 else "#eb6834" for v in valores],
            height=.6)
    for i, v in enumerate(valores):
        ax.text(v + 1, i, f"{v:.1f} %".replace(".", ","), va="center", fontsize=8.5,
                color="#1a1a19")
    ax.set_xlim(0, 112)
    ax.set_xlabel("% de participantes únicos (k = 1)")
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.grid(axis="x", color="#d9d8d4", linewidth=.7)
    ax.set_axisbelow(True)
    ax.set_title("Quitar los nombres no basta: casi todos siguen siendo únicos",
                 fontsize=10, loc="left")
    FIG.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIG / "riesgo.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--datos", type=pathlib.Path, default=DATOS_DEFECTO)
    ap.add_argument("--mi-puuid", action="append", default=[],
                    help="puuid propio (se puede repetir, una vez por cuenta); marca "
                         "es_propio=1 antes de seudonimizar")
    args = ap.parse_args()

    # tablas/, figuras/ y salida/ son las del reporte de anonimización, que describe el
    # PILOTO. Con otro corpus todo va a <datos>/../anonimizado/ para no reescribir en
    # silencio las cifras de un reporte ya entregado.
    global SALIDA, TAB, FIG
    if args.datos.resolve() != DATOS_DEFECTO.resolve():
        base = args.datos.resolve().parent / "anonimizado"
        SALIDA, TAB, FIG = base, base / "tablas", base / "figuras"
    SALIDA.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)

    # El manifiesto del descargador trae los puuid propios, uno por cuenta, en el orden
    # en que se descargaron; así no hay que copiarlos a mano. La etiqueta C1, C2, ...
    # permite comparar cuentas sin nombrarlas.
    manifiesto = args.datos / "manifiesto.json"
    puuids = list(args.mi_puuid)
    if not puuids and manifiesto.exists():
        man = json.loads(manifiesto.read_text(encoding="utf-8"))
        puuids = [c["puuid"] for c in man.get("cuentas", [])] or [man.get("puuid", "")]
    propios = {p: f"C{i}" for i, p in enumerate((p for p in puuids if p), 1)}

    llave = os.environ.get("LOL_ANON_KEY", "").encode() or secrets.token_bytes(32)
    salidas, qi, ids = tablas(args.datos, llave, propios)
    for nombre, df in salidas.items():
        df.to_csv(SALIDA / f"{nombre}.csv", index=False, encoding="utf-8")

    # Lo que va al repositorio público: solo nivel EQUIPO. La tabla de participantes
    # (campeón y rol de cada desconocido) es 100 % única y se queda local.
    publico = {
        "partidas": salidas["partidas"],
        "oro_equipo": (salidas["cuadros"].groupby(["partida", "minuto", "teamId"], as_index=False)
                       ["oroTotal"].sum()),
        "eventos_equipo": salidas["eventos"].loc[salidas["eventos"]["tipo"].isin(EVENTOS_PUBLICOS),
                                                 COLUMNAS_EVENTOS_PUBLICOS],
    }
    (SALIDA / "publico").mkdir(exist_ok=True)
    for nombre, df in publico.items():
        df.to_csv(SALIDA / "publico" / f"{nombre}.csv", index=False, encoding="utf-8")

    # 1 · barrido de fugas: la salida contra el crudo (control negativo)
    texto_salida, texto_crudo = valores_salida(SALIDA), valores_crudo(args.datos)
    en_salida, en_crudo = barrer(texto_salida, ids), barrer(texto_crudo, ids)
    assert all(v > 0 for v in en_crudo.values()), "el barrido no detecta nada en el crudo: no sirve"
    fugas = sum(en_salida.values())

    # 2 · riesgo de reidentificación (solo partidas 5v5: la de Arena no es comparable)
    qi5 = qi[qi.groupby("partida")["partida"].transform("size") == 10]
    niveles = [
        ("Crudo sin nombres", ["campeon", "rol", "parche", "cola", "dia", "nivel"]),
        ("Generalizado (mes, bandas)", ["campeon", "rol", "parche", "cola", "mes", "bandaNivel"]),
        ("Sin campeón", ["rol", "parche", "cola", "mes", "bandaNivel"]),
        ("Solo campeón", ["campeon"]),
    ]
    k_part = [{"Nivel": n, "Cuasi-identificadores": ", ".join(c), **riesgo(qi5, c)} for n, c in niveles]
    comp = (qi5.sort_values("campeon").groupby("partida")
            .agg(composicion=("campeon", lambda s: "|".join(s)), mes=("mes", "first")).reset_index())
    k_comp = riesgo(comp, ["composicion"])

    resultados = {
        "partidas": len(salidas["partidas"]), "partidas_5v5": int(qi5["partida"].nunique()),
        "participantes": len(salidas["participantes"]), "cuadros": len(salidas["cuadros"]),
        "eventos": len(salidas["eventos"]),
        "identificadores_unicos": {k: len(v) for k, v in ids.items()},
        "barrido_salida": en_salida, "barrido_crudo": en_crudo, "fugas": fugas,
        "k_participante": k_part, "k_composicion": k_comp,
        "llave": "LOL_ANON_KEY" if os.environ.get("LOL_ANON_KEY") else "efímera",
    }
    (SALIDA / "resultados.json").write_text(json.dumps(resultados, indent=1, ensure_ascii=False),
                                             encoding="utf-8")

    # tablas para el reporte
    a_latex(pd.DataFrame(POLITICA, columns=["Campo", "Nivel", "Técnica", "Columna de salida"]),
            "politica", "Política de anonimización, campo por campo (generada desde el script).",
            "politica", "p{4.2cm}p{2.3cm}p{4.6cm}p{2.4cm}")
    tipos = {"puuid": "puuid", "summonerId": "summonerId", "riotId": "Riot ID / nombre",
             "matchId": "matchId", "gameId": "gameId"}
    a_latex(pd.DataFrame([{"Identificador": tipos[k], "Valores distintos": len(ids[k]),
                           "Hallados en el JSON crudo": en_crudo[k],
                           "Hallados en la salida": en_salida[k]} for k in tipos]),
            "barrido", "Barrido de fugas: cada identificador original buscado en el crudo "
            "(control negativo) y en los CSV anonimizados.", "barrido", "lrrr")
    a_latex(pd.DataFrame([{"Nivel": r["Nivel"], "Cuasi-identificadores": r["Cuasi-identificadores"],
                           "Clases": r["clases"], "k mín.": r["k_min"],
                           "% únicos": f"{r['pct_unicas']:.1f}".replace(".", ",")} for r in k_part]),
            "riesgo", f"Riesgo de reidentificación por participante ({len(qi5)} participantes "
            f"de {qi5['partida'].nunique()} partidas 5v5).", "riesgo", "p{3.2cm}p{6.2cm}rrr")
    figura_riesgo(k_part)
    cifras = {
        "nPartidas": resultados["partidas"], "nPartidasCinco": resultados["partidas_5v5"],
        "nParticipantes": resultados["participantes"], "nCuadros": f"{resultados['cuadros']:,}",
        "nEventos": f"{resultados['eventos']:,}", "nFugas": fugas,
        "nPuuid": len(ids["puuid"]), "nRiotId": len(ids["riotId"]),
        "nCampos": len(POLITICA),
        "nSuprimidos": sum("Supresión" in p[2] for p in POLITICA),
        "nSeudo": sum("Seudonim" in p[2] for p in POLITICA),
        "nGeneral": sum("Generaliz" in p[2] for p in POLITICA),
        "pctUnicosCrudo": k_part[0]["pct_unicas"], "pctUnicosGen": k_part[1]["pct_unicas"],
        "pctUnicosSinCampeon": k_part[2]["pct_unicas"], "pctUnicosCampeon": k_part[3]["pct_unicas"],
        "kMinSinCampeon": k_part[2]["k_min"],
        "compUnicas": k_comp["unicas"], "compTotal": k_comp["filas"],
    }
    def es(v: object) -> str:
        """Formato del EDA: espacio fino para miles y coma decimal."""
        if isinstance(v, float):
            return f"{v:.1f}".replace(".", "{,}")
        if isinstance(v, int):
            return f"{v:,}".replace(",", "\\,")
        return str(v).replace(",", "\\,")

    (TAB / "cifras.tex").write_text(
        "".join(f"\\newcommand{{\\{k}}}{{{es(v)}}}\n" for k, v in cifras.items()), encoding="utf-8")

    print(f"{resultados['partidas']} partidas -> {', '.join(f'{n}: {len(d)}' for n, d in salidas.items())}")
    print("barrido crudo :", en_crudo)
    print("barrido salida:", en_salida, "-> fugas:", fugas)
    for r in k_part:
        print(f"  {r['Nivel']:<28} clases={r['clases']:>3} k_min={r['k_min']} únicos={r['pct_unicas']}%")
    print(f"  composición de 10 campeones: {k_comp['unicas']} de {k_comp['filas']} partidas únicas")
    return 1 if fugas else 0


if __name__ == "__main__":
    raise SystemExit(main())
