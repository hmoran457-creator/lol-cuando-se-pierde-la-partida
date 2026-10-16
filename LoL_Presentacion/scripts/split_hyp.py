r"""Parte la lámina de hipótesis en dos, de tres en tres.

Las seis fichas se extraen del HTML actual y se reusan literalmente: no se
reescribe el texto, solo se saca el <span class="test"> fuera del .txt para
que la trampa ocupe su propia columna al lado del enunciado.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
H = ROOT / "presentacion.html"
src = H.read_text(encoding="utf-8")

start = src.index('    <section class="slide" id="s-hyp" data-sec="3">')
end = src.index("    </section>", start) + len("    </section>\n")
block = src[start:end]

cards = re.findall(
    r'<div class="hyp"><div class="id">(H\d)</div><div class="txt">(.*?)</div></div>',
    block, re.S,
)
if len(cards) != 6:
    sys.exit(f"se esperaban 6 fichas, se encontraron {len(cards)}")

split_re = re.compile(r'(.*?)<span class="test">(.*?)</span>\s*$', re.S)
parsed = []
for hid, body in cards:
    m = split_re.match(body.strip())
    if not m:
        sys.exit(f"{hid}: no se pudo separar el enunciado de la trampa")
    claim = " ".join(m.group(1).split())
    trap = " ".join(m.group(2).split())
    if not trap.startswith("Trampa:"):
        sys.exit(f"{hid}: la trampa no empieza como se esperaba: {trap[:40]!r}")
    parsed.append((hid, claim, trap.removeprefix("Trampa:").strip()))

# la nota de encuadre que ya vivía al pie de la lámina original
panel = block[block.index('<div class="panel" style="border-left:3px solid var(--gold);'):
              block.index("      </div>\n      <div class=\"footer\">") if '<div class="footer">' in block
              else block.rindex("      </div>")]
panel = panel[:panel.rindex("</div>") + len("</div>")]


def card(hid: str, claim: str, trap: str) -> str:
    return (
        f'          <div class="hyp wide">\n'
        f'            <div class="id">{hid}</div>\n'
        f'            <div class="txt">{claim}</div>\n'
        f'            <div class="test"><b>Trampa:</b> {trap}</div>\n'
        f'          </div>\n'
    )


slide_a = (
    '    <section class="slide" id="s-hyp-a" data-sec="3">\n'
    '      <div class="kicker">3 · Hipótesis · la ventaja y los objetivos</div>\n'
    '      <h2>Tres hipótesis sobre la ventaja\n'
    '        <span class="sub">Cada una está escrita para poder salir falsa, y al lado va lo que\n'
    '          podría arruinarla. Nombrar la trampa es parte de la hipótesis.</span></h2>\n'
    '      <div class="body">\n'
    '        <div class="hyplist">\n'
    + "".join(card(*p) for p in parsed[:3])
    + '        </div>\n'
    '      </div>\n'
    '      <div class="footer">\n'
    '        <div>H1 no necesita línea temporal, así que puede correr sobre una ventana más larga</div>\n'
    '      </div>\n'
    '    </section>\n'
)

slide_b = (
    '    <section class="slide" id="s-hyp-b" data-sec="3">\n'
    '      <div class="kicker">3 · Hipótesis · qué explica el resultado</div>\n'
    '      <h2>Tres hipótesis sobre la explicación\n'
    '        <span class="sub">Las tres se comparan contra mis propias victorias. La última es la\n'
    '          más frágil, y es la que da título al proyecto.</span></h2>\n'
    '      <div class="body">\n'
    '        <div class="hyplist">\n'
    + "".join(card(*p) for p in parsed[3:])
    + '        </div>\n'
    f'        {panel}\n'
    '      </div>\n'
    '    </section>\n'
)

H.write_text(src[:start] + slide_a + "\n" + slide_b + src[end:], encoding="utf-8")

print(f"fichas reusadas: {[p[0] for p in parsed]}")
print(f"s-hyp-a: {[p[0] for p in parsed[:3]]}")
print(f"s-hyp-b: {[p[0] for p in parsed[3:]]}  + panel de encuadre ({len(panel)} car.)")
print("s-hyp original eliminada:", 'id="s-hyp"' not in H.read_text(encoding="utf-8"))
