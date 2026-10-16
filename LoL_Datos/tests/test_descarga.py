r"""El descargador contra una API simulada: ninguna prueba toca la red ni usa llave."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import descargar_partidas as d  # noqa: E402

TODAS = [f"LA1_{i}" for i in range(250, 0, -1)]          # de la más nueva a la más vieja
COLA420 = [m for m in TODAS if int(m[4:]) % 10 != 0]     # 225 de cola 420
VIEJAS_SIN_TL = {f"LA1_{i}" for i in (1, 2, 3)}          # la retención ya las borró


class Resp:
    def __init__(self, status, datos=None, headers=None):
        self.status_code, self._datos, self.headers = status, datos, headers or {}

    def json(self):
        return self._datos

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class APIFalsa:
    def __init__(self, caduca_tras=None, un_429=False):
        self.headers, self.pedidas, self.caduca_tras, self.un_429 = {}, [], caduca_tras, un_429

    def get(self, url, params=None, timeout=None):
        self.pedidas.append(url)
        if self.caduca_tras is not None and len(self.pedidas) > self.caduca_tras:
            return Resp(401)
        if self.un_429:
            self.un_429 = False
            return Resp(429, headers={"Retry-After": "1"})
        if url.endswith("/ids"):
            fuente = COLA420 if params.get("queue") == 420 else TODAS
            if "/by-puuid/otra/" in url:                      # segunda cuenta: otras partidas
                fuente = [f"LA1_{int(m[4:]) + 1000}" for m in fuente[:40]]
            return Resp(200, fuente[params["start"]:params["start"] + params["count"]])
        mid = url.rsplit("/", 2)[-2] if url.endswith("/timeline") else url.rsplit("/", 1)[-1]
        if url.endswith("/timeline"):
            return Resp(404) if mid in VIEJAS_SIN_TL else Resp(200, {"info": {"frames": []}})
        return Resp(200, {"info": {"gameCreation": 1_700_000_000_000 + int(mid[4:]) * 60_000}})


def cliente(api):
    return d.Cliente("RGAPI-falsa", sesion=api, dormir=lambda s: None)


def test_pagina_hasta_agotar_y_cuenta_las_dos_listas(tmp_path):
    m = d.descargar(cliente(APIFalsa()), "la1", "p", tmp_path)
    assert m["cuenta"]["ids_todas"] == 250 and m["cuenta"]["ids_420"] == 225
    assert m["partidas_descargadas"] == 225 and m["con_timeline"] == 222
    assert m["timeline_404"] == sorted(VIEJAS_SIN_TL)


def test_descarga_de_la_mas_vieja_a_la_mas_nueva(tmp_path):
    api = APIFalsa()
    d.descargar(cliente(api), "la1", "p", tmp_path)
    partidas = [u.rsplit("/", 1)[-1] for u in api.pedidas
                if "/matches/LA1_" in u and not u.endswith("/timeline")]
    assert partidas[0] == "LA1_1" and partidas[-1] == "LA1_249"


def test_si_la_llave_caduca_retoma_sin_repetir(tmp_path):
    with pytest.raises(d.LlaveInvalida):
        d.descargar(cliente(APIFalsa(caduca_tras=60)), "la1", "p", tmp_path)
    a_medias = len(list(tmp_path.glob("getMatch_*.json")))
    assert 0 < a_medias < 225
    api = APIFalsa()
    m = d.descargar(cliente(api), "la1", "p", tmp_path)
    assert m["partidas_descargadas"] == 225
    ya_estaban = {f"LA1_{i}" for i in range(1, 30)} & set(COLA420)
    repetidas = [u for u in api.pedidas if u.rsplit("/", 1)[-1] in ya_estaban
                 and not u.endswith("/timeline")]
    assert not repetidas, "una partida ya en disco se volvió a pedir"
    cuentas = json.loads((tmp_path / "manifiesto.json").read_text(encoding="utf-8"))["cuentas"]
    assert [c["puuid"] for c in cuentas] == ["p"], "retomar no debe duplicar la cuenta"


def test_una_segunda_cuenta_se_suma_sin_pisar_a_la_primera(tmp_path):
    d.descargar(cliente(APIFalsa()), "la1", "p", tmp_path)
    m = d.descargar(cliente(APIFalsa()), "la1", "otra", tmp_path)
    assert [c["puuid"] for c in m["cuentas"]] == ["p", "otra"] and m["n_cuenta"] == 2
    assert m["cuentas"][0]["descargadas"] == 225 and m["cuenta"]["descargadas"] == 40
    assert m["partidas_descargadas"] == 225 + 40
    assert not set(m["cuentas"][0]["partidas"]) & set(m["cuentas"][1]["partidas"])


def test_el_manifiesto_de_una_sola_cuenta_se_migra(tmp_path):
    (tmp_path / "getMatch_LA1_7.json").write_text("{}", encoding="utf-8")
    (tmp_path / "manifiesto.json").write_text(json.dumps(
        {"puuid": "p", "plataforma": "la1", "region": "americas", "ids_todas": 9, "ids_420": 1}),
        encoding="utf-8")
    manif = d.cargar_manifiesto(tmp_path)
    assert "puuid" not in manif and "region" not in manif
    assert manif["cuentas"] == [{"puuid": "p", "plataforma": "la1", "ids_todas": 9,
                                 "ids_420": 1, "lista_consultada": None,
                                 "partidas": ["LA1_7"]}]


def test_un_429_se_reintenta(tmp_path):
    m = d.descargar(cliente(APIFalsa(un_429=True)), "la1", "p", tmp_path)
    assert m["partidas_descargadas"] == 225


def test_un_corte_de_red_breve_se_reintenta(tmp_path):
    import requests

    class APIConCorte(APIFalsa):
        cortes = 2

        def get(self, url, params=None, timeout=None):
            if self.cortes:
                self.cortes -= 1
                raise requests.ConnectionError("getaddrinfo failed")
            return super().get(url, params, timeout)

    m = d.descargar(cliente(APIConCorte()), "la1", "p", tmp_path)
    assert m["partidas_descargadas"] == 225


def test_el_limitador_no_pasa_de_95_en_dos_minutos():
    reloj, dormido = [0.0], []

    def dormir(s):
        dormido.append(s)
        reloj[0] += s

    cli = d.Cliente("RGAPI-falsa", sesion=APIFalsa(), dormir=dormir, reloj=lambda: reloj[0])
    for _ in range(96):
        cli._esperar_turno()
    assert reloj[0] >= 119, "la petición 96 salió antes de que se abriera la ventana de 2 min"
