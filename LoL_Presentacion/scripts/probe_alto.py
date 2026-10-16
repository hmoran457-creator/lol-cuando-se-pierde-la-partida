r"""¿Qué está ocupando el alto de una lámina? Uso: probe_alto.py <deck.html> <n>"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
deck = sys.argv[1] if len(sys.argv) > 1 else "presentacion.html"
n = sys.argv[2] if len(sys.argv) > 2 else "3"
BASE = (ROOT / deck).as_uri()

JS = """() => {
  const s = document.querySelector('.slide.active');
  const rows = [];
  const push = (label, el) => {
    if (!el) return;
    const r = el.getBoundingClientRect();
    rows.push({ label, top: Math.round(r.top), bot: Math.round(r.bottom), h: Math.round(r.height) });
  };
  push('kicker', s.querySelector('.kicker'));
  push('h2', s.querySelector('h2'));
  push('body', s.querySelector('.body'));
  s.querySelectorAll('.body > *').forEach((el, i) =>
    push('  body[' + i + '] .' + (el.className || el.tagName).toString().slice(0, 22), el));
  push('footer', s.querySelector('.footer'));
  const st = document.getElementById('stage').getBoundingClientRect();
  return { id: s.id, stageTop: Math.round(st.top), stageBot: Math.round(st.bottom), rows };
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1600, "height": 950})
    pg.goto(BASE)
    pg.evaluate(f"location.hash = 'd{n}'")
    pg.reload()
    pg.wait_for_timeout(2600)
    r = pg.evaluate(JS)
    print(f"{r['id']}  (escenario {r['stageTop']}..{r['stageBot']})\n")
    print(f"{'elemento':<34}{'top':>7}{'bot':>7}{'alto':>7}")
    print("-" * 55)
    for x in r["rows"]:
        print(f"{x['label']:<34}{x['top']:>7}{x['bot']:>7}{x['h']:>7}")
    b.close()
