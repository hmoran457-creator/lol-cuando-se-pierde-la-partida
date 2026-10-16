r"""Resume en un JSON publicable los pocos conteos que solo existen en los archivos locales.

El reporte y las presentaciones citan cifras que no se pueden rehacer desde las tablas
públicas: cuántas partidas tenía cada cuenta en su lista, cuántas partidas en dúo entre
cuentas propias hubo, cuántos eventos y cuadros tiene la muestra final y cuáles son los
campeones del autor. Este script las cuenta UNA vez desde lo local y las deja en
LoL_Datos/anonimizado/resumen_descarga.json, que sí va al repositorio. Así cifras.py y los
construir.py se reproducen completos desde una copia pública.

Solo hay conteos agregados por cuenta propia (C1–C6) y campeones del propio autor: ningún
puuid, Riot ID, matchId ni dato de los otros jugadores.

Fuentes locales (no se publican):
    LoL_Datos/crudo/manifiesto.json     ids_todas e ids_420 de cada cuenta, en orden C1..C6
    LoL_Datos/crudo/revision.json       partidas en dúo entre cuentas propias
    LoL_Datos/anonimizado/{eventos,cuadros,participantes}.csv

Uso:  python LoL_Datos/scripts/resumen_publico.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import pandas as pd

RAIZ = pathlib.Path(__file__).resolve().parent.parent.parent
CRUDO = RAIZ / "LoL_Datos" / "crudo"
ANON = RAIZ / "LoL_Datos" / "anonimizado"
SALIDA = ANON / "resumen_descarga.json"
sys.path.insert(0, str(RAIZ / "LoL_Analisis" / "scripts"))
import e1_quiebre as e1  # noqa: E402  (la misma regla de filtrado que el análisis)


def main() -> int:
    faltan = [p for p in (CRUDO / "manifiesto.json", CRUDO / "revision.json",
                          ANON / "eventos.csv", ANON / "cuadros.csv", ANON / "participantes.csv")
              if not p.exists()]
    if faltan:
        raise SystemExit("Este script solo corre con los datos originales (no se publican). Faltan:\n  "
                         + "\n  ".join(str(p.relative_to(RAIZ)) for p in faltan)
                         + f"\nEl resultado ya está en {SALIDA.relative_to(RAIZ)}.")

    man = json.loads((CRUDO / "manifiesto.json").read_text(encoding="utf-8"))
    rev = json.loads((CRUDO / "revision.json").read_text(encoding="utf-8"))
    partidas = pd.read_csv(e1.PUBLICO / "partidas.csv", dtype={"parche": str})
    muestra, _ = e1.filtrar(partidas)
    ids = set(muestra["partida"])

    eventos = pd.read_csv(ANON / "eventos.csv", usecols=["partida"])
    cuadros = pd.read_csv(ANON / "cuadros.csv", usecols=["partida"])
    part = pd.read_csv(ANON / "participantes.csv", usecols=["partida", "es_propio", "campeon"])
    # El campeón propio de cada partida de la MUESTRA FINAL (no de las 1,241 descargadas).
    mios = part[(part["es_propio"] == 1) & part["partida"].isin(ids)]

    resumen = {
        "nota": "Conteos agregados de los datos locales; sin identificadores. "
                "Generado por LoL_Datos/scripts/resumen_publico.py.",
        # Las etiquetas C1..C6 siguen el orden del manifiesto, igual que anonimizar.py.
        "cuentas": [{"cuenta": f"C{i}", "ids_todas": c.get("ids_todas"), "ids_420": c.get("ids_420")}
                    for i, c in enumerate(man.get("cuentas", []), 1)],
        "duo_cuentas_propias": rev["duo_cuentas_propias"],
        "muestra_partidas": len(ids),
        "eventos_muestra": int(eventos["partida"].isin(ids).sum()),
        "cuadros_muestra": int(cuadros["partida"].isin(ids).sum()),
        "campeones_propios_muestra": {k: int(v) for k, v in mios["campeon"].value_counts().items()},
    }
    SALIDA.write_text(json.dumps(resumen, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in resumen.items() if k != "campeones_propios_muestra"},
                     indent=1, ensure_ascii=False))
    print("campeones más usados:", list(resumen["campeones_propios_muestra"].items())[:3])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
