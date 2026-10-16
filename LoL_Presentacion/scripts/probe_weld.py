r"""¿La gráfica ocupa los MISMOS píxeles en las láminas 04, 05 y 06?

El borde de la cortina solo es "el reloj" si el minuto 22 cae en la misma x en las
tres láminas. Antes de soldarla la curva saltaba 32px entre láminas y cambiaba de
escala, así que el presentador señalaba tres sitios distintos para el mismo minuto.
"""
import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = (ROOT / "presentacion.html").as_uri()

JS = """() => {
  const s = document.querySelector('.slide.active');
  const line = s.querySelector('.adv-line');
  const svg = s.querySelector('svg.chart');
  if (!line || !svg) return null;
  const lb = line.getBoundingClientRect();
  const sb = svg.getBoundingClientRect();
  return {
    id: s.id,
    scale: +(sb.width / svg.viewBox.baseVal.width).toFixed(4),
    lineX: +lb.left.toFixed(1), lineY: +lb.top.toFixed(1),
    lineW: +lb.width.toFixed(1), lineH: +lb.height.toFixed(1)
  };
}"""

rows = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1600, "height": 950})
    for n in (4, 5, 6):
        # goto a un fragmento del MISMO documento no vuelve a arrancar la pagina:
        # sin este reload el sondeo medía tres veces la misma lámina y decía SOLDADA.
        pg.goto(BASE)
        pg.evaluate(f"location.hash = 'd{n}'")
        pg.reload()
        pg.wait_for_timeout(2600)          # deja terminar la cortina
        rows.append(pg.evaluate(JS))
    b.close()

print(f"{'lamina':<12}{'escala':<10}{'x':<10}{'y':<10}{'ancho':<10}{'alto':<10}")
print("-" * 62)
for r in rows:
    print(f"{r['id']:<12}{r['scale']:<10}{r['lineX']:<10}{r['lineY']:<10}{r['lineW']:<10}{r['lineH']:<10}")

keys = ["scale", "lineX", "lineY", "lineW", "lineH"]
drift = {k: max(r[k] for r in rows) - min(r[k] for r in rows) for k in keys}
print("\ndesviacion entre laminas:", {k: round(v, 2) for k, v in drift.items()})
print("SOLDADA" if all(v <= 0.5 for v in drift.values()) else "NO SOLDADA -- revisar")
