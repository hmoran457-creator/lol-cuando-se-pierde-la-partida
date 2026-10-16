r"""¿Se está recortando el JSON de la lámina 10?

Los bloques .code llevan overflow:auto, así que si el contenedor los aplasta las
últimas líneas del payload desaparecen sin aviso -- y esa lámina existe justamente
para enseñar el payload.
"""
import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = (ROOT / "presentacion.html").as_uri() + "#d10"

JS = """() => {
  const out = [];
  document.querySelectorAll('.slide.active .code').forEach((el, i) => {
    const b = el.getBoundingClientRect();
    const lines = el.textContent.replace(/\\s+$/, '').split(String.fromCharCode(10));
    out.push({
      i: i,
      h: Math.round(b.height),
      scrollH: el.scrollHeight,
      hidden: el.scrollHeight - Math.ceil(b.height),
      lines: lines.length,
      last: lines[lines.length - 1].trim().slice(0, 44)
    });
  });
  const row = document.querySelector('.slide.active .row.grow');
  return { codes: out, rowH: Math.round(row.getBoundingClientRect().height), rowNeed: row.scrollHeight };
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1600, "height": 950})
    pg.goto(URL)
    pg.wait_for_timeout(1000)
    r = pg.evaluate(JS)
    print(f"row.grow: {r['rowH']}px de alto para {r['rowNeed']}px de contenido")
    for c in r["codes"]:
        flag = "OCULTA CONTENIDO" if c["hidden"] > 2 else "ok"
        print(f"  bloque {c['i']}: caja {c['h']}px | contenido {c['scrollH']}px | "
              f"oculto {c['hidden']}px | {c['lines']} lineas | {flag}")
        print(f"      ultima linea: {c['last']!r}")
    b.close()
