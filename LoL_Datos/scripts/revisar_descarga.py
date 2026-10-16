r"""Revisa la descarga en LoL_Datos/crudo: integridad, filtros y calidad.

Imprime solo conteos y rangos. Nunca un nombre, un Riot ID ni un identificador.
Escribe el embudo en crudo/revision.json para el reporte (E0).

Uso:  python LoL_Datos/scripts/revisar_descarga.py
"""
from __future__ import annotations

import json
import pathlib
from collections import Counter
from datetime import datetime, timezone

CRUDO = pathlib.Path(__file__).resolve().parent.parent / "crudo"


def leer(ruta: pathlib.Path):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def main() -> int:
    man = leer(CRUDO / "manifiesto.json") or {}
    cuentas = man.get("cuentas") or [{"puuid": man.get("puuid", ""), "ids_todas": man.get("ids_todas"),
                                      "ids_420": man.get("ids_420")}]
    etiqueta = {c["puuid"]: f"C{i}" for i, c in enumerate(cuentas, 1)}
    matches = sorted(CRUDO.glob("getMatch_*.json"))
    print("== Integridad")
    print(f"  registros: {len(matches)} · líneas temporales: {len(list(CRUDO.glob('getTimeline_*.json')))}"
          f" · .tmp sueltos: {len(list(CRUDO.glob('*.tmp')))}")

    malos, filas = 0, []
    for fm in matches:
        mid = fm.stem.removeprefix("getMatch_")
        m, t = leer(fm), leer(CRUDO / f"getTimeline_{mid}.json")
        if not m or not t:
            malos += 1
            continue
        info, tinfo = m["info"], t["info"]
        parts = info["participants"]
        mias = [p for p in parts if p.get("puuid") in etiqueta]
        # Dos cuentas propias en la misma partida = otra persona jugaba una de ellas en
        # dúo conmigo (confirmado por el jugador). Yo soy la de BOTTOM.
        yo = next((p for p in mias if p.get("teamPosition") == "BOTTOM"), mias[0] if mias else None)
        # gameDuration: segundos si viene gameEndTimestamp, milisegundos si no (parche 11.20)
        dur_s = info["gameDuration"] if "gameEndTimestamp" in info else info["gameDuration"] / 1000
        equipo = {p["participantId"]: p["teamId"] for p in parts}
        # torres por equipo atribuidas por killerId (no por teamId), contra el registro
        torres = {100: 0, 200: 0}
        tipos, monstruos = Counter(), Counter()
        for fr in tinfo["frames"]:
            for e in fr.get("events", []):
                tipos[e["type"]] += 1
                if e["type"] == "ELITE_MONSTER_KILL":
                    monstruos[e.get("monsterType")] += 1
                if e["type"] == "BUILDING_KILL" and e.get("buildingType") == "TOWER_BUILDING":
                    a = e.get("killerTeamId") or equipo.get(e.get("killerId"))
                    if a is None and e.get("teamId") in (100, 200):
                        a = 300 - e["teamId"]
                    if a in torres:
                        torres[a] += 1
        oficial = {x["teamId"]: x["objectives"]["tower"]["kills"] for x in info["teams"]}
        filas.append({
            "cola": info.get("queueId"), "jugadores": len(parts),
            "parche": ".".join(str(info.get("gameVersion")).split(".")[:2]),
            "mes": datetime.fromtimestamp(info["gameCreation"] / 1000, tz=timezone.utc).strftime("%Y-%m"),
            "dur_min": dur_s / 60, "cuadros": len(tinfo["frames"]),
            "intervalo": tinfo.get("frameInterval"),
            "ids_coinciden": t["metadata"]["matchId"] == m["metadata"]["matchId"],
            "mid": mid,
            "rendicion_temprana": any(p.get("gameEndedInEarlySurrender") for p in parts),
            "rendicion": any(p.get("gameEndedInSurrender") for p in parts),
            "estoy": yo is not None, "gane": bool(yo and yo.get("win")),
            "cuenta": etiqueta.get((yo or {}).get("puuid"), "?"),
            # Dos cuentas propias en la misma partida romperían la idea de «mi equipo».
            "cuentas_propias": len(mias),
            "rol": (yo or {}).get("teamPosition") or "?",
            "torres_cuadran": torres == oficial,
            "end_result": info.get("endOfGameResult"),
            "tipos": tipos, "monstruos": monstruos,
        })
    print(f"  JSON ilegibles o sin pareja: {malos}")
    print(f"  matchId del registro = el de la línea temporal: "
          f"{sum(f['ids_coinciden'] for f in filas)} de {len(filas)}")
    print(f"  estoy entre los participantes: {sum(f['estoy'] for f in filas)} de {len(filas)}")

    print("\n== Embudo (E0)")
    n0 = len(filas)
    p1 = [f for f in filas if f["cola"] == 420]
    p2 = [f for f in p1 if f["jugadores"] == 10]
    p3 = [f for f in p2 if not f["rendicion_temprana"]]
    p4 = [f for f in p3 if f["dur_min"] >= 5]
    # Rendición antes del minuto 10: casi siempre alguien abandonó. No es un remake (ese
    # lo marca gameEndedInEarlySurrender) y pasa el filtro de 5 min, pero la partida no
    # se jugó: se trata como atípica y se excluye, reportando cuántas.
    abandonadas = [f for f in p4 if f["rendicion"] and f["dur_min"] < 10]
    p4 = [f for f in p4 if f not in abandonadas]
    print(f"  partidas con dos cuentas propias (dúo; yo = la de BOTTOM): "
          f"{sum(f['cuentas_propias'] > 1 for f in filas)}")
    suma = lambda k: sum(c.get(k) or 0 for c in cuentas)  # noqa: E731
    # Una partida en dúo entre dos cuentas propias está en las dos listas; y la lista de
    # una cuenta se recorre con el tiempo, así que una partida ya descargada puede no
    # estar en la lista de la última corrida. Se cuentan partidas únicas.
    unicas = set().union(*(set(c.get("partidas") or []) for c in cuentas),
                         {f["mid"] for f in filas})
    embudo = [("lista completa (todas las colas, suma)", suma("ids_todas")),
              ("cola 420 (suma de listas)", suma("ids_420")),
              ("cola 420, partidas únicas", len(unicas)),
              ("con registro y línea temporal", n0),
              ("cola 420 confirmada en el registro", len(p1)),
              ("10 participantes", len(p2)),
              ("sin rendición temprana (remake)", len(p3)),
              ("duración >= 5 min", len(p4) + len(abandonadas)),
              ("sin rendición antes del min 10 (abandono)", len(p4))]
    for etq, n in embudo:
        print(f"  {etq:<38} {n}")
    g = sum(f["gane"] for f in p4)
    print(f"  -> muestra final: {len(p4)} partidas · {g} victorias · {len(p4) - g} derrotas")

    print("\n== Por cuenta")
    por_cuenta = {}
    for c in cuentas:
        e = etiqueta[c["puuid"]]
        fs = [f for f in p4 if f["cuenta"] == e]
        gc = sum(f["gane"] for f in fs)
        rol = Counter(f["rol"] for f in fs).most_common(1)
        meses = sorted(f["mes"] for f in fs)
        por_cuenta[e] = {"cola420": c.get("ids_420"), "final": len(fs), "victorias": gc,
                         "derrotas": len(fs) - gc}
        print(f"  {e} ({c.get('plataforma') or '?'}): cola 420 {c.get('ids_420')} · final {len(fs)}"
              f" · {gc} V / {len(fs) - gc} D · rol principal "
              f"{rol[0][0] if rol else '?'} · {meses[0] if meses else '?'} a {meses[-1] if meses else '?'}")

    print("\n== Calidad")
    print(f"  frameInterval: {dict(Counter(f['intervalo'] for f in filas))}")
    malos_cuadros = sum(1 for f in p4 if abs(f["cuadros"] - (int(f["dur_min"]) + 2)) > 1)
    print(f"  cuadros vs duración fuera de ±1: {malos_cuadros}")
    print(f"  torres por killerId cuadran con el registro: {sum(f['torres_cuadran'] for f in p4)} de {len(p4)}")
    print(f"  endOfGameResult: {dict(Counter(f['end_result'] for f in filas))}  (no se filtra por él)")
    dur = sorted(f["dur_min"] for f in p4)
    if dur:
        print(f"  duración (min): mín {dur[0]:.1f} · mediana {dur[len(dur) // 2]:.1f} · máx {dur[-1]:.1f}")
        print(f"  partidas que llegan al minuto 30: {sum(d >= 30 for d in dur)} (denominador de H3)")
    print(f"  parches ({len(set(f['parche'] for f in p4))}): "
          f"{dict(sorted(Counter(f['parche'] for f in p4).items()))}")
    print(f"  meses: {dict(sorted(Counter(f['mes'] for f in p4).items()))}")
    print(f"  mi rol: {dict(Counter(f['rol'] for f in p4).most_common())}")
    mon = sum((f["monstruos"] for f in p4), Counter())
    print(f"  monsterType observados: {dict(mon.most_common())}")
    tipos = sum((f["tipos"] for f in p4), Counter())
    print(f"  tipos de evento: {len(tipos)}")

    rev = {"embudo": [{"paso": e, "n": n} for e, n in embudo],
           "victorias": g, "derrotas": len(p4) - g, "por_cuenta": por_cuenta,
           "duo_cuentas_propias": sum(f["cuentas_propias"] > 1 for f in filas),
           "rol": dict(Counter(f["rol"] for f in p4)),
           "duracion_mediana": dur[len(dur) // 2] if dur else None,
           "meses": dict(Counter(f["mes"] for f in p4)),
           # La lista que el análisis debe usar; vive en crudo/, fuera del repositorio.
           "muestra_final": sorted(f["mid"] for f in p4),
           "excluidas_abandono": sorted(f["mid"] for f in abandonadas),
           "llegan_min30": sum(d >= 30 for d in dur),
           "parches": dict(Counter(f["parche"] for f in p4)),
           "torres_cuadran": sum(f["torres_cuadran"] for f in p4),
           "monsterType": dict(mon), "tipos_evento": dict(tipos)}
    (CRUDO / "revision.json").write_text(json.dumps(rev, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
