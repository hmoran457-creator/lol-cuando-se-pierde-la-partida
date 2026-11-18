r"""Exporta la presentación narrada a PDF, una lámina por página, como respaldo.

    python LoL_PresentacionHistoria/scripts/exportar_pdf.py

La presentación es HTML con animaciones; el PDF es para cuando no se pueda abrir (otra
computadora, una plataforma que solo acepta PDF). Cada lámina se captura completa, con
todos sus pasos revelados (?todo, como en shoot.py) y sus animaciones terminadas, a doble
resolución para que se vea nítida en un proyector. El texto del PDF no es seleccionable:
son imágenes de las láminas.
"""
from __future__ import annotations

import io
import pathlib

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
DECK = ROOT / "presentacion_historia.html"
SALIDA = ROOT / "presentacion_historia.pdf"
# Los mismos tiempos de shoot.py: cubren la animación más lenta de cada lámina.
ESPERA = {"h-caso": 3200, "h-respuesta": 3000, "h-pista3": 2800, "h-pruebas": 2600}
ESPERA_BASE = 2000


def main() -> int:
    paginas = []
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pag = nav.new_page(viewport={"width": 1600, "height": 950}, device_scale_factor=2)
        errores = []
        pag.on("pageerror", lambda e: errores.append(str(e)))
        pag.goto(DECK.as_uri() + "?todo")
        pag.wait_for_timeout(1200)                                  # fuentes y arranque
        n = pag.evaluate("document.querySelectorAll('.slide').length")
        for i in range(1, n + 1):
            # La lámina se lee de la dirección (#dN) al cargar: se recarga, como en shoot.py.
            pag.evaluate(f"location.hash='d{i}'")
            pag.reload()
            pag.wait_for_timeout(700)
            sid = pag.evaluate("document.querySelector('.slide.active')?.id || ''")
            pag.wait_for_timeout(ESPERA.get(sid, ESPERA_BASE))
            png = pag.locator("#stage").screenshot()
            paginas.append(Image.open(io.BytesIO(png)).convert("RGB"))
            print(f"  {i:02d} {sid}")
        nav.close()
    assert not errores, f"errores en la página: {errores}"
    paginas[0].save(SALIDA, save_all=True, append_images=paginas[1:], resolution=200)
    print(f"{SALIDA.name}: {len(paginas)} páginas, {SALIDA.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
