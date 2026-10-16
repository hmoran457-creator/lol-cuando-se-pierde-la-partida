r"""El barrido de fugas con fugas plantadas a propósito. Todos los nombres son inventados."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import anonimizar as a  # noqa: E402

IDS = {"puuid": {"Xk3pQ9-ficticio-puuid-7HbL2w"}, "summonerId": set(),
       "riotId": {"SombraDelNorte", "Ahr"}, "matchId": {"LA1_1488203317"}, "gameId": set()}


def _salida(tmp_path, filas: str) -> str:
    (tmp_path / "participantes.csv").write_text("partida,campeon,nota\n" + filas, encoding="utf-8")
    return a.valores_salida(tmp_path)


def test_una_salida_limpia_no_reporta_nada(tmp_path):
    assert sum(a.barrer(_salida(tmp_path, "24f61cd6497b,Ahri,12840\n"), IDS).values()) == 0


def test_un_nombre_plantado_como_celda_se_detecta(tmp_path):
    hallados = a.barrer(_salida(tmp_path, "24f61cd6497b,Ahri,SombraDelNorte\n"), IDS)
    assert hallados["riotId"] == 1


def test_un_nombre_dentro_de_un_texto_se_detecta(tmp_path):
    hallados = a.barrer(_salida(tmp_path, "24f61cd6497b,Ahri,jugó con SombraDelNorte ayer\n"), IDS)
    assert hallados["riotId"] == 1


def test_un_matchid_y_un_puuid_plantados_se_detectan(tmp_path):
    texto = _salida(tmp_path, "LA1_1488203317,Ahri,Xk3pQ9-ficticio-puuid-7HbL2w\n")
    hallados = a.barrer(texto, IDS)
    assert hallados["matchId"] == 1 and hallados["puuid"] == 1


def test_un_nombre_que_es_fragmento_de_un_campeon_no_es_fuga(tmp_path):
    """Medido en la muestra propia: un nombre de 3 letras dentro de un campeón."""
    assert a.barrer(_salida(tmp_path, "24f61cd6497b,Ahri,1\n"), IDS)["riotId"] == 0
