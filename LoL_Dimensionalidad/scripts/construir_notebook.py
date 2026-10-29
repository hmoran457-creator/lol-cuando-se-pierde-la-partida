r"""Arma, ejecuta y exporta el notebook de reducción de dimensionalidad.

    python LoL_Dimensionalidad/scripts/construir_notebook.py

1. Escribe LoL_Dimensionalidad/reduccion_dimensionalidad.ipynb desde las celdas de abajo.
2. Lo ejecuta completo (nbclient), de modo que el .ipynb entregado trae todas sus salidas.
3. Lo exporta a HTML y de ahí a PDF con Chromium (playwright).

El texto de las celdas vive aquí y no en el .ipynb para poder regenerarlo de punta a punta.
"""
from __future__ import annotations

import pathlib
import sys

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

AQUI = pathlib.Path(__file__).resolve().parent
BASE = AQUI.parent
NB = BASE / "reduccion_dimensionalidad.ipynb"
HTML = BASE / "reduccion_dimensionalidad.html"
PDF = BASE / "reduccion_dimensionalidad.pdf"
sys.path.insert(0, str(AQUI))
from celdas import CELDAS  # noqa: E402


def main() -> int:
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.metadata["language_info"] = {"name": "python"}
    for tipo, texto in CELDAS:
        texto = texto.strip("\n")
        nb.cells.append(nbformat.v4.new_markdown_cell(texto) if tipo == "md" else nbformat.v4.new_code_cell(texto))

    print("ejecutando el notebook…", flush=True)
    NotebookClient(nb, timeout=1200, kernel_name="python3",
                   resources={"metadata": {"path": str(BASE)}}).execute()
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
