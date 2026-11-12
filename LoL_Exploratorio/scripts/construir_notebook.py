r"""Arma, ejecuta, revisa y exporta el notebook de análisis exploratorio.

    python LoL_Exploratorio/scripts/construir_notebook.py

1. Escribe LoL_Exploratorio/analisis_exploratorio.ipynb desde las celdas de celdas.py.
2. Lo ejecuta completo (nbclient), de modo que el .ipynb entregado trae todas sus salidas.
3. REVISA LAS SALIDAS: el notebook lee tablas por participante que nunca van al repositorio
   (LoL_Datos/anonimizado/*.csv), así que sus salidas son la frontera de privacidad. Si
   alguna salida de texto contiene el id de una partida, el id de un jugador o el campeón
   de otro jugador, se detiene sin escribir nada.
4. Lo exporta a HTML y de ahí a PDF con Chromium (playwright).
"""
from __future__ import annotations

import pathlib
import re
import sys

import nbformat
import pandas as pd
from nbclient import NotebookClient
from nbconvert import HTMLExporter

AQUI = pathlib.Path(__file__).resolve().parent
BASE = AQUI.parent
RAIZ = BASE.parent
NB = BASE / "analisis_exploratorio.ipynb"
HTML = BASE / "analisis_exploratorio.html"
PDF = BASE / "analisis_exploratorio.pdf"
PRIVADO = RAIZ / "LoL_Datos" / "anonimizado"
sys.path.insert(0, str(AQUI))
from celdas import CELDAS  # noqa: E402


def textos_de_salida(nb) -> list[str]:
    """Todo el texto que el notebook guarda como salida (no las imágenes)."""
    textos = []
    for c in nb.cells:
        for o in c.get("outputs", []):
            if "text" in o:
                textos.append(o["text"])
            for tipo, valor in o.get("data", {}).items():
                if tipo.startswith("text/"):
                    textos.append(valor if isinstance(valor, str) else "".join(valor))
            if o.get("output_type") == "error":
                textos.append("\n".join(o.get("traceback", [])))
    return textos


def revisar_fugas(nb) -> list[str]:
    part = pd.read_csv(PRIVADO / "participantes.csv", usecols=["partida", "jugador", "es_propio",
                                                                "campeon"])
    ids = set(part["partida"].astype(str)) | set(part["jugador"].dropna().astype(str))
    propios = set(part.loc[part["es_propio"] == 1, "campeon"])
    ajenos = set(part.loc[part["es_propio"] == 0, "campeon"]) - propios
    patron = re.compile(r"\b(" + "|".join(sorted(map(re.escape, ajenos), key=len, reverse=True))
                        + r")\b")
    hallazgos = []
    for texto in textos_de_salida(nb):
        for token in re.findall(r"\b[0-9a-f]{12}\b", texto):
            if token in ids:
                hallazgos.append(f"id de partida o jugador: {token}")
        for m in patron.finditer(texto):
            hallazgos.append(f"campeón de otro jugador: {m.group(0)}")
    return hallazgos


def main() -> int:
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.metadata["language_info"] = {"name": "python"}
    for tipo, texto in CELDAS:
        texto = texto.strip("\n")
        nb.cells.append(nbformat.v4.new_markdown_cell(texto) if tipo == "md" else nbformat.v4.new_code_cell(texto))

    print("ejecutando el notebook…", flush=True)
    NotebookClient(nb, timeout=1800, kernel_name="python3",
                   resources={"metadata": {"path": str(BASE)}}).execute()

    fugas = revisar_fugas(nb)
    if fugas:
        print("SALIDAS CON DATOS PRIVADOS; no se escribe nada:")
        for f in sorted(set(fugas)):
            print("  ", f)
        return 1
    print("revisión de privacidad: ninguna salida trae ids ni campeones ajenos")
    nbformat.write(nb, NB)
    print("notebook:", NB.name)

    cuerpo, _ = HTMLExporter(template_name="classic").from_notebook_node(nb)
    # Al imprimir: que ninguna gráfica ni tabla quede partida entre dos páginas.
    impresion = ("<style>@media print { .output_png, .output_html, .output_text, .text_cell_render"
                 " { break-inside: avoid; } div.output_area img { max-width: 100%; } }</style>")
    cuerpo = cuerpo.replace("</head>", impresion + "</head>", 1)
    HTML.write_text(cuerpo, encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pag = nav.new_page()
        pag.goto(HTML.as_uri(), wait_until="networkidle")      # MathJax llega de un CDN
        pag.wait_for_timeout(3000)                               # y tarda en componer las fórmulas
        pag.pdf(path=str(PDF), format="Letter", print_background=True,
                margin={"top": "14mm", "bottom": "14mm", "left": "12mm", "right": "12mm"})
        nav.close()
    HTML.unlink()
    print("pdf:", PDF.name, f"{PDF.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
