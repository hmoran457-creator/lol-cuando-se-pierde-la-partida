r"""Captura la cortina a media pasada, que es lo único que dice si se lee.

Una animación puede estar "corriendo" y aun así no comunicar nada. Estas capturas
muestran lo que la sala ve realmente a los 500 / 900 / 1400 ms.
"""
import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "shots" / "motion"
OUT.mkdir(parents=True, exist_ok=True)
BASE = (ROOT / "presentacion.html").as_uri()

SLIDES = {4: "reveal", 5: "rewind", 6: "break"}
STOPS = [500, 900, 1500]

JS = """() => {
  const s = document.querySelector('.slide.active');
  const cr = s.querySelector('clipPath rect');
  if (!cr) return null;
  const svg = s.querySelector('svg.chart');
  const sb = svg.getBoundingClientRect();
  const scale = sb.width / svg.viewBox.baseVal.width;
  const box = cr.getBoundingClientRect();
  // borde derecho de la cortina, en unidades de la grafica
  const edge = (box.right - sb.left) / scale;
  return { id: s.id, edgeUser: +edge.toFixed(1) };
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1600, "height": 950})
    for n, name in SLIDES.items():
        pg.goto(BASE)
        pg.evaluate(f"location.hash = 'd{n}'")
        pg.reload()
        prev = 0
        for ms in STOPS:
            pg.wait_for_timeout(ms - prev)
            prev = ms
            st = pg.evaluate(JS)
            pg.locator("#stage").screenshot(path=str(OUT / f"{name}-{ms}ms.png"))
            print(f"  {name:<8} t={ms:>5}ms  borde de la cortina en x={st['edgeUser'] if st else '?'}")
    b.close()
print(f"\ncapturas en {OUT}")
