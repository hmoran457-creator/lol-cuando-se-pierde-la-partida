r"""Descarga MIS partidas clasificatorias (cola 420) con registro y línea temporal.

Lo que hace, y por qué (ver LoL_Presentacion/VALIDACION.md):

* Pide la lista COMPLETA de partidas y, aparte, la de cola 420 explícita: las dos
  cifras son el primer escalón del embudo de filtrado (E0).
* Descarga de la MÁS VIEJA a la más nueva. La retención borra primero las viejas;
  si la llave caduca a la mitad, lo que se perdería es lo más reciente, que sigue
  disponible mañana.
* Guarda el JSON crudo tal cual (getMatch_<id>.json / getTimeline_<id>.json) y
  retoma: lo que ya está en disco no se vuelve a pedir. Volver a descargar no da la
  misma muestra, así que el crudo guardado es lo que hace repetible el estudio.
* Un 404 en la línea temporal NO es un error: es la retención. Se registra en el
  manifiesto y se sigue.
* Respeta los límites de una llave de desarrollo (20 por segundo, 100 cada 2 minutos)
  y obedece Retry-After en un 429.

La llave NUNCA se imprime ni se escribe a disco. Se lee de RIOT_API_KEY o se pide
oculta en la consola.

Uso (en una terminal PowerShell, desde la carpeta Narrativa de Datos):
    python LoL_Datos/scripts/descargar_partidas.py
    python LoL_Datos/scripts/descargar_partidas.py --riot-id "Nombre#TAG" --plataforma la1
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import pathlib
import sys
import time
import urllib.parse
from collections import deque
from datetime import datetime, timezone

import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
CRUDO = ROOT / "crudo"

# plataforma -> ruta regional de match-v5 (account-v1 no existe en "sea": usa "asia")
REGION = {
    "na1": "americas", "br1": "americas", "la1": "americas", "la2": "americas",
    "euw1": "europe", "eun1": "europe", "tr1": "europe", "ru": "europe", "me1": "europe",
    "kr": "asia", "jp1": "asia",
    "oc1": "sea", "ph2": "sea", "sg2": "sea", "th2": "sea", "tw2": "sea", "vn2": "sea",
}


class LlaveInvalida(RuntimeError):
    pass


class Cliente:
    """GET con límites de una llave de desarrollo y reintento en 429 / 5xx."""

    def __init__(self, llave: str, sesion: requests.Session | None = None,
                 dormir=time.sleep, reloj=time.monotonic):
        self._sesion = sesion or requests.Session()
        self._sesion.headers["X-Riot-Token"] = llave
        self._dormir, self._reloj = dormir, reloj
        self._seg: deque[float] = deque()      # ventana de 1 s
        self._dos: deque[float] = deque()      # ventana de 120 s
        self.peticiones = 0

    def _esperar_turno(self) -> None:
        # Un poco por debajo de 20/1 s y 100/120 s: el límite exacto no se publica.
        for cola, ventana, tope in ((self._seg, 1.0, 18), (self._dos, 120.0, 95)):
            ahora = self._reloj()
            while cola and ahora - cola[0] >= ventana:
                cola.popleft()
            if len(cola) >= tope:
                self._dormir(ventana - (ahora - cola[0]) + 0.05)
        t = self._reloj()
        self._seg.append(t)
        self._dos.append(t)

    def get(self, url: str, params: dict | None = None) -> requests.Response:
        for intento in range(6):
            self._esperar_turno()
            try:
                r = self._sesion.get(url, params=params, timeout=30)
            except (requests.ConnectionError, requests.Timeout):
                # Un corte de red (pasó: DNS caído a media descarga) se reintenta con
                # espera creciente; si persiste, main() lo reporta y se retoma después.
                if intento == 5:
                    raise
                print(f"    sin conexión; espero {2 ** (intento + 1)} s y reintento", flush=True)
                self._dormir(2 ** (intento + 1))
                continue
            self.peticiones += 1
            if r.status_code in (401, 403):
                raise LlaveInvalida(
                    f"HTTP {r.status_code}: la llave caducó o no es válida. La de desarrollo "
                    "dura 24 h; genera otra en developer.riotgames.com y vuelve a correr "
                    "este script: retoma donde se quedó.")
            if r.status_code == 429 or r.status_code >= 500:
                espera = float(r.headers.get("Retry-After", 2 ** intento))
                print(f"    HTTP {r.status_code}; espero {espera:.0f} s y reintento", flush=True)
                self._dormir(espera)
                continue
            return r
        return r


def escribir_json(ruta: pathlib.Path, datos) -> None:
    """Escritura atómica: un corte a medio archivo no deja un JSON roto que el
    reanudado tomaría por descargado."""
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    tmp.replace(ruta)


def listar_ids(cli: Cliente, region: str, puuid: str, cola: int | None) -> list[str]:
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    ids: list[str] = []
    while True:
        params = {"start": len(ids), "count": 100}
        if cola is not None:
            params["queue"] = cola
        r = cli.get(url, params)
        r.raise_for_status()
        pagina = r.json()
        ids.extend(pagina)
        if len(pagina) < 100:
            return ids


def utc(ms: int | None) -> str | None:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat() if ms else None


def cargar_manifiesto(destino: pathlib.Path) -> dict:
    """Varias cuentas del mismo jugador comparten la carpeta: el manifiesto guarda una
    entrada por cuenta, con sus partidas. Un manifiesto de una sola cuenta (el formato
    anterior) se migra: todas las partidas en disco eran de esa cuenta."""
    rmanif = destino / "manifiesto.json"
    manif = json.loads(rmanif.read_text(encoding="utf-8")) if rmanif.exists() else {}
    if "puuid" in manif and "cuentas" not in manif:
        manif["cuentas"] = [{
            "puuid": manif.pop("puuid"), "plataforma": manif.pop("plataforma", None),
            "ids_todas": manif.pop("ids_todas", None), "ids_420": manif.pop("ids_420", None),
            "lista_consultada": manif.pop("lista_consultada", None),
            "partidas": sorted(f.stem.removeprefix("getMatch_")
                               for f in destino.glob("getMatch_*.json")),
        }]
        manif.pop("region", None)
    manif.setdefault("cuentas", [])
    return manif


def descargar(cli: Cliente, plataforma: str, puuid: str, destino: pathlib.Path) -> dict:
    region = REGION[plataforma]
    destino.mkdir(parents=True, exist_ok=True)
    rmanif = destino / "manifiesto.json"
    manif = cargar_manifiesto(destino)
    cuenta = next((c for c in manif["cuentas"] if c["puuid"] == puuid), None)
    if cuenta is None:
        cuenta = {"puuid": puuid}
        manif["cuentas"].append(cuenta)
    sin_timeline = set(manif.get("timeline_404", []))

    print("Contando la lista completa de partidas (todas las colas)...", flush=True)
    todas = listar_ids(cli, region, puuid, None)
    print(f"  {len(todas)} partidas en total en la lista")
    print("Contando las de cola 420 (clasificatoria individual)...", flush=True)
    ids = listar_ids(cli, region, puuid, 420)
    print(f"  {len(ids)} partidas de cola 420")
    cuenta.update({"plataforma": plataforma, "ids_todas": len(todas), "ids_420": len(ids),
                   "partidas": ids, "lista_consultada": datetime.now(timezone.utc).isoformat()})

    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches"
    pendientes = list(reversed(ids))          # la API las da de la más nueva a la más vieja
    for n, mid in enumerate(pendientes, 1):
        fm, ft = destino / f"getMatch_{mid}.json", destino / f"getTimeline_{mid}.json"
        if fm.exists() and (ft.exists() or mid in sin_timeline):
            continue
        if not fm.exists():
            r = cli.get(f"{url}/{mid}")
            if r.status_code == 404:
                manif.setdefault("partida_404", []).append(mid)
                continue
            r.raise_for_status()
            escribir_json(fm, r.json())
        if not ft.exists() and mid not in sin_timeline:
            r = cli.get(f"{url}/{mid}/timeline")
            if r.status_code == 404:
                sin_timeline.add(mid)
            else:
                r.raise_for_status()
                escribir_json(ft, r.json())
        manif["timeline_404"] = sorted(sin_timeline)
        escribir_json(rmanif, manif)          # el progreso sobrevive a cualquier corte
        if n % 10 == 0 or n == len(pendientes):
            print(f"  {n}/{len(pendientes)} · {len(sin_timeline)} sin línea temporal", flush=True)

    # Cifras del embudo y de la retención, desde lo que quedó en disco.
    creaciones = []
    for f in destino.glob("getMatch_*.json"):
        info = json.loads(f.read_text(encoding="utf-8"))["info"]
        mid = f.stem.removeprefix("getMatch_")
        creaciones.append((info.get("gameCreation"), (destino / f"getTimeline_{mid}.json").exists()))
    con_tl = [c for c, tl in creaciones if tl and c]
    sin_tl = [c for c, tl in creaciones if not tl and c]
    propias = set(ids)
    manif.update({
        "partidas_descargadas": len(creaciones),
        "con_timeline": len(con_tl),
        "timeline_404": sorted(sin_timeline),
        "mas_vieja_con_timeline": utc(min(con_tl)) if con_tl else None,
        "mas_nueva_sin_timeline": utc(max(sin_tl)) if sin_tl else None,
        "terminada": datetime.now(timezone.utc).isoformat(),
    })
    cuenta.update({
        "descargadas": sum((destino / f"getMatch_{m}.json").exists() for m in propias),
        "con_timeline": sum((destino / f"getTimeline_{m}.json").exists() for m in propias),
    })
    escribir_json(rmanif, manif)
    return {**manif, "cuenta": cuenta, "n_cuenta": manif["cuentas"].index(cuenta) + 1}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--riot-id", help='tu Riot ID, p. ej. "Nombre#TAG"')
    ap.add_argument("--plataforma", choices=sorted(REGION), help="servidor; LAN es la1")
    ap.add_argument("--destino", type=pathlib.Path, default=CRUDO)
    args = ap.parse_args()

    riot_id = args.riot_id or input("Tu Riot ID (Nombre#TAG): ").strip()
    if "#" not in riot_id:
        sys.exit("El Riot ID lleva '#', por ejemplo Nombre#LAN.")
    plataforma = (args.plataforma or input("Servidor [la1 = LAN]: ").strip() or "la1").lower()
    if plataforma not in REGION:
        sys.exit(f"Servidor desconocido. Opciones: {', '.join(sorted(REGION))}")
    llave = os.environ.get("RIOT_API_KEY") or getpass.getpass("Llave de la API (no se muestra): ")
    llave = llave.strip()
    if not llave.startswith("RGAPI-"):
        sys.exit("Esa no parece una llave de Riot: empiezan con RGAPI-.")

    cli = Cliente(llave)
    nombre, tag = riot_id.rsplit("#", 1)
    region_cuenta = "asia" if REGION[plataforma] == "sea" else REGION[plataforma]
    try:
        r = cli.get(f"https://{region_cuenta}.api.riotgames.com/riot/account/v1/accounts/"
                    f"by-riot-id/{urllib.parse.quote(nombre)}/{urllib.parse.quote(tag)}")
        if r.status_code == 404:
            sys.exit("No existe ese Riot ID. Revisa mayúsculas, espacios y la etiqueta después del #.")
        r.raise_for_status()
        puuid = r.json()["puuid"]
        print("Cuenta encontrada.")
        m = descargar(cli, plataforma, puuid, args.destino)
    except LlaveInvalida as e:
        print(f"\n{e}")
        return 2
    except KeyboardInterrupt:
        print("\nInterrumpido. Lo descargado se conserva; vuelve a correr para retomar.")
        return 130
    except (requests.ConnectionError, requests.Timeout):
        print("\nSe perdió la conexión a internet. Lo descargado se conserva; cuando "
              "vuelva la conexión, corre el mismo comando para retomar.")
        return 3

    c = m["cuenta"]
    print(f"\nListo en {cli.peticiones} peticiones. Esta es la cuenta C{m['n_cuenta']} "
          f"de {len(m['cuentas'])}.")
    print(f"  Esta cuenta · lista completa: {c['ids_todas']} · cola 420: {c['ids_420']}"
          f" · descargadas: {c['descargadas']} · con línea temporal: {c['con_timeline']}")
    print(f"  Todas las cuentas · descargadas: {m['partidas_descargadas']} · con línea temporal:"
          f" {m['con_timeline']} · sin ella (404): {len(m['timeline_404'])}")
    print(f"  Línea temporal más vieja disponible: {m['mas_vieja_con_timeline']}")
    print(f"  Carpeta: {args.destino}")
    if m["con_timeline"] < 150:
        print("  AVISO: menos de 150 con línea temporal. Según el planteamiento, se baja a "
              "tres arquetipos antes de escribir reglas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
