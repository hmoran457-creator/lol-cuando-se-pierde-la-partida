r"""Tabla de entrenamiento del modelo de probabilidad de ganar: una fila por partida y minuto.

    python LoL_Probabilidad/scripts/datos.py

Cada fila describe el estado de una partida en el cuadro t (el minuto t:00), contado desde mi
lado, y la etiqueta es si mi equipo ganó. Se usan las 1,195 partidas del embudo del proyecto y
los minutos 1 .. último − 1 (el último cuadro es el final de la partida).

Lo que ya pasó en el cuadro t son los eventos con floor(ms / 60000) < t: la convención de E2-E4
(un evento del minuto m ocurre entre los cuadros m y m + 1).

Columnas (sufijo _p = mi equipo, _r = el rival):
  marcador, lo que se ve dentro de la partida:
    asesinatos, estructuras (torres e inhibidores), dragones, larvas, heraldos, barones,
    atakhan, baron_activo (barón tomado hace menos de 3 minutos: la mejora dura 3 min)
  oro, lo que NO se ve en una partida clasificatoria (solo en repeticiones o como espectador):
    oro_dif (oro propio − rival) y v (oro_dif / oro total × 100); oro_total no es variable de
    ningún modelo, solo sirve para la mediana del oro por minuto de la página
  placas (oro de placas de torre: tampoco está en el marcador)
  nivel, suma de los niveles de los cinco jugadores (se ve con la tecla Tab), y xp, la
    experiencia sumada (no se ve; sirve solo para medir cuánto se pierde por usar el nivel)
  detalle de objetivos, del JSON crudo (se ve en el juego): torre, inhibidor, torre_nexo,
    dragon_elem (dragones sin el ancestral), ancestral, alma, inhib_abiertos (inhibidores del
    rival caídos ahora) y ancestral_activo (mejora del ancestral)

Lee tablas por participante que no se publican; la salida va a LoL_Probabilidad/datos/, que
está en .gitignore. Lo único que sale de esa carpeta son métricas y coeficientes agregados.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
sys.path.insert(0, str(RAIZ / "LoL_Analisis" / "scripts"))
import e1_quiebre as e1  # noqa: E402

PRIVADO = RAIZ / "LoL_Datos" / "anonimizado"
SALIDA = AQUI.parent / "datos" / "estado_por_minuto.parquet"
MONSTRUOS = {"DRAGON": "dragones", "HORDE": "larvas", "RIFTHERALD": "heraldos",
             "BARON_NASHOR": "barones", "ATAKHAN": "atakhan"}
# Prueba temporal: las partidas de estos meses nunca se usan para elegir el modelo.
MES_PRUEBA = "2026-05"


CRUDO = RAIZ / "LoL_Datos" / "crudo"


def huellas_anonimas(ev: pd.DataFrame) -> dict[tuple, str]:
    """Huella de cada partida anonimizada: los milisegundos exactos de sus asesinatos."""
    k = ev[ev["tipo"] == "CHAMPION_KILL"].sort_values("ms")
    return {tuple(g["ms"].astype(int)): p for p, g in k.groupby("partida")}


def detalle_objetivos(ev: pd.DataFrame, muestra: pd.DataFrame) -> pd.DataFrame:
    """Detalle de objetivos que la anonimización no guardó, leído del JSON crudo (local).

    La llave de los seudónimos fue efímera, así que cada línea de tiempo cruda se enlaza con su
    partida anonimizada por la huella de sus asesinatos (los ms exactos). El enlace vive solo en
    memoria: la salida va por seudónimo y no guarda ningún matchId.

    Devuelve un evento por fila: partida, m (minuto del evento), equipo que se lo lleva (100/200)
    y clase: torre, inhibidor, torre_nexo, dragon_elem, ancestral o alma.
    """
    import json

    huellas = huellas_anonimas(ev)
    filas, sin_par = [], 0
    for f in sorted(CRUDO.glob("getTimeline_*.json")):
        t = json.loads(f.read_text(encoding="utf-8"))
        eventos = [e for fr in t["info"]["frames"] for e in fr.get("events", [])]
        huella = tuple(sorted(int(e["timestamp"]) for e in eventos if e["type"] == "CHAMPION_KILL"))
        partida = huellas.get(huella)
        if partida is None:
            sin_par += 1
            continue
        for e in eventos:
            m = int(e["timestamp"]) // 60000
            if e["type"] == "BUILDING_KILL" and e.get("teamId") in (100, 200):
                quien = 300 - e["teamId"]                      # teamId es el equipo que perdió el edificio
                if e.get("buildingType") == "INHIBITOR_BUILDING":
                    filas.append((partida, m, quien, "inhibidor"))
                else:
                    filas.append((partida, m, quien, "torre"))
                    if e.get("towerType") == "NEXUS_TURRET":
                        filas.append((partida, m, quien, "torre_nexo"))
            elif e["type"] == "ELITE_MONSTER_KILL" and e.get("monsterType") == "DRAGON" \
                    and e.get("killerTeamId") in (100, 200):
                clase = "ancestral" if e.get("monsterSubType") == "ELDER_DRAGON" else "dragon_elem"
                filas.append((partida, m, e["killerTeamId"], clase))
            elif e["type"] == "DRAGON_SOUL_GIVEN" and e.get("teamId") in (100, 200):
                filas.append((partida, m, e["teamId"], "alma"))
    out = pd.DataFrame(filas, columns=["partida", "m", "equipo", "clase"])
    enlazadas = out["partida"].nunique() if len(out) else 0
    print(f"detalle de objetivos: {enlazadas:,} partidas enlazadas por huella; {sin_par} líneas de "
          f"tiempo sin pareja (fuera del embudo o sin asesinatos)")
    faltan = set(muestra["partida"]) - set(out["partida"])
    assert len(faltan) <= 5, f"{len(faltan)} partidas de la muestra sin detalle de objetivos"
    return out[out["partida"].isin(muestra["partida"])]


def construir() -> pd.DataFrame:
    partidas = pd.read_csv(e1.PUBLICO / "partidas.csv", dtype={"parche": str})
    muestra, _ = e1.filtrar(partidas)
    v = e1.medida_v(pd.read_csv(e1.PUBLICO / "oro_equipo.csv"), muestra)
    ultimo = v.groupby("partida")["minuto"].max()
    v = v[(v["minuto"] >= 1) & (v["minuto"] < v["partida"].map(ultimo))].copy()
    lado = muestra.set_index("partida")["equipoPropio"]

    ev = pd.read_csv(PRIVADO / "eventos.csv",
                     usecols=["partida", "tipo", "ms", "equipoAutor", "equipoVictima", "killerId", "monsterType"])
    ev = ev[ev["partida"].isin(muestra["partida"])].copy()
    ev["m"] = ev["ms"] // 60000

    # Quién se lleva cada evento, desde mi lado. Las ejecuciones (muertes ante una torre o los
    # súbditos, killerId 0) no suman al marcador del juego, que es lo que se escribe en la página.
    k = ev[(ev["tipo"] == "CHAMPION_KILL") & (ev["killerId"] > 0)].copy()
    k["quien"] = np.where(k["equipoVictima"] == k["partida"].map(lado), "r", "p")   # muere uno mío: punto del rival
    k["clase"] = "asesinatos"
    o = ev[ev["tipo"].isin(["BUILDING_KILL", "TURRET_PLATE_DESTROYED", "ELITE_MONSTER_KILL"])
           & ev["equipoAutor"].isin([100, 200])].copy()
    o["quien"] = np.where(o["equipoAutor"] == o["partida"].map(lado), "p", "r")
    o["clase"] = np.select([o["tipo"] == "BUILDING_KILL", o["tipo"] == "TURRET_PLATE_DESTROYED"],
                           ["estructuras", "placas"], o["monsterType"].map(MONSTRUOS).fillna(""))
    todos = pd.concat([k, o])
    todos = todos[todos["clase"] != ""]
    todos["col"] = todos["clase"] + "_" + todos["quien"]

    # Conteo por minuto y acumulado: en el cuadro t cuentan los eventos con m < t.
    por_min = todos.groupby(["partida", "m", "col"]).size().unstack(fill_value=0)
    cols = sorted(por_min.columns)
    filas = v[["partida", "minuto"]].copy()
    filas["m"] = filas["minuto"] - 1                       # acumulado hasta el minuto t − 1
    rejilla = pd.MultiIndex.from_frame(filas[["partida", "m"]])
    completo = por_min.reindex(
        pd.MultiIndex.from_tuples([(p, m) for p, u in ultimo.items() for m in range(int(u) + 1)],
                                  names=["partida", "m"]), fill_value=0)
    acumulado = completo.groupby(level="partida").cumsum()
    estado = acumulado.reindex(rejilla).fillna(0).astype(int).reset_index(drop=True)

    # Barón activo: tomado en los minutos t − 3 .. t − 1.
    bar = todos[todos["clase"] == "barones"]
    for q in ("p", "r"):
        b = bar[bar["quien"] == q].groupby(["partida", "m"]).size()
        activo = np.zeros(len(filas), dtype=int)
        for atras in (1, 2, 3):
            idx = pd.MultiIndex.from_arrays([filas["partida"], filas["minuto"] - atras])
            activo += b.reindex(idx).fillna(0).to_numpy(dtype=int)
        estado[f"baron_activo_{q}"] = (activo > 0).astype(int)

    tabla = pd.concat([filas[["partida", "minuto"]].reset_index(drop=True), estado], axis=1)

    # Detalle de objetivos (JSON crudo): conteos acumulados hasta el cuadro t, más dos estados que
    # duran: inhibidores rivales caídos ahora (reaparecen a los 5 minutos) y la mejora del dragón
    # ancestral (dura 2.5 minutos; con cuadros por minuto, los 2 minutos anteriores).
    det = detalle_objetivos(ev, muestra)
    det["quien"] = np.where(det["equipo"] == det["partida"].map(lado), "p", "r")
    det["col"] = det["clase"] + "_" + det["quien"]
    por_min_det = det.groupby(["partida", "m", "col"]).size().unstack(fill_value=0)
    acum_det = por_min_det.reindex(completo.index, fill_value=0).groupby(level="partida").cumsum()
    estado_det = acum_det.reindex(rejilla).fillna(0).astype(int).reset_index(drop=True)
    for clase in ["torre", "inhibidor", "torre_nexo", "dragon_elem", "ancestral", "alma"]:
        for q in ("p", "r"):
            col = f"{clase}_{q}"
            tabla[col] = estado_det[col].to_numpy() if col in estado_det else 0
    for clase, nombre, minutos in [("inhibidor", "inhib_abiertos", 5), ("ancestral", "ancestral_activo", 2)]:
        for q in ("p", "r"):
            b = det[det["col"] == f"{clase}_{q}"].groupby(["partida", "m"]).size()
            activo = np.zeros(len(filas), dtype=int)
            for atras in range(1, minutos + 1):
                idx = pd.MultiIndex.from_arrays([filas["partida"], filas["minuto"] - atras])
                activo += b.reindex(idx).fillna(0).to_numpy(dtype=int)
            tabla[f"{nombre}_{q}"] = np.minimum(activo, 3 if clase == "inhibidor" else 1)
    # Comprobación: torres + inhibidores del crudo = estructuras de la tabla anonimizada.
    dif = (tabla["torre_p"] + tabla["inhibidor_p"] - tabla["estructuras_p"]).abs()
    print(f"torres + inhibidores = estructuras en el {(dif == 0).mean():.2%} de las filas")
    # Niveles y experiencia de cada equipo en el cuadro t (suma de sus cinco jugadores). El nivel
    # se ve en el marcador del juego (tecla Tab); la experiencia no.
    cu = pd.read_csv(PRIVADO / "cuadros.csv", usecols=["partida", "minuto", "teamId", "nivel", "xp"])
    cu = cu[cu["partida"].isin(muestra["partida"])]
    cu["quien"] = np.where(cu["teamId"] == cu["partida"].map(lado), "p", "r")
    suma = cu.groupby(["partida", "minuto", "quien"])[["nivel", "xp"]].sum().unstack("quien")
    suma.columns = [f"{c}_{q}" for c, q in suma.columns]
    suma = suma.reindex(pd.MultiIndex.from_frame(filas[["partida", "minuto"]]))
    assert suma.notna().all().all(), "faltan niveles en algún cuadro"
    for c in suma.columns:
        tabla[c] = suma[c].astype(int).to_numpy()

    tabla["oro_dif"] = (v["oroPropio"] - v["oroRival"]).to_numpy()
    tabla["oro_total"] = (v["oroPropio"] + v["oroRival"]).to_numpy()     # solo para agregados
    tabla["v"] = (v["v"] * 100).to_numpy()
    tabla["azul"] = (tabla["partida"].map(lado) == 100).astype(int).to_numpy()
    info = muestra.set_index("partida")
    tabla["gane"] = tabla["partida"].map(info["gane"]).astype(int)
    tabla["mes"] = tabla["partida"].map(info["mes"])
    tabla["prueba_temporal"] = (tabla["mes"] >= MES_PRUEBA).astype(int)
    for c in cols:
        tabla[c] = tabla[c].astype(int)
    return tabla


def main() -> int:
    tabla = construir()
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    tabla.to_parquet(SALIDA, index=False)
    n = tabla.groupby("prueba_temporal")["partida"].nunique()
    print(f"{len(tabla):,} filas · {tabla['partida'].nunique():,} partidas "
          f"({n.get(0, 0)} para elegir el modelo, {n.get(1, 0)} de prueba temporal desde {MES_PRUEBA})")
    print("columnas:", ", ".join(tabla.columns))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
