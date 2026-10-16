r"""Rehace la lámina «Cuatro formas de perder» y afina la trampa de H1.

Layout: los cuatro arquetipos estaban en dos columnas de fichas compactas —unos
44 px cada una— con la regla en letra chica debajo del nombre, y sobraba hasta
300 px al pie de la lámina. Pasan al formato ancho que ya usan las hipótesis:
nombre a la izquierda, regla a la derecha, separados por un filete, repartidos en
el alto disponible. Es la misma pieza `.hyp.wide` / `.hyplist` ya probada.

Trampa de H1: «no se puede probar» se cambia por «nunca podría salir falsa», que
enlaza con el subtítulo de la propia lámina («escritas para poder salir falsas»)
y dice con precisión cuál es el defecto: es infalsable, no indemostrable.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAZOS = [ROOT / "presentacion.html", ROOT / "presentacion_5min.html",
         ROOT / "presentacion_story.html"]

FICHA = re.compile(
    r'<div class="hyp"(?P<attrs>[^>]*)><div class="id">(?P<id>A\d)</div>'
    r'<div class="txt">(?P<nombre>.*?)\s*<span class="test">(?P<regla>.*?)</span>'
    r'</div></div>', re.S)

fallos: list[str] = []

for mazo in MAZOS:
    s = mazo.read_text(encoding="utf-8")

    # ── 1 · trampa de H1 ────────────────────────────────────────────────────
    for viejo, nuevo in [
        ('<b>Trampa:</b> “las perdí por no convertir” no se puede probar: toda ventaja',
         '<b>Trampa:</b> “las perdí por no convertir” nunca podría salir falsa: toda ventaja'),
    ]:
        if s.count(viejo) == 1:
            s = s.replace(viejo, nuevo)
        else:
            fallos.append(f"{mazo.name}: trampa H1 aparece {s.count(viejo)} veces")

    # ── 2 · las cuatro fichas de arquetipo pasan a formato ancho ────────────
    fichas = list(FICHA.finditer(s))
    if len(fichas) != 4:
        fallos.append(f"{mazo.name}: se encontraron {len(fichas)} fichas de arquetipo, se esperaban 4")
        continue

    nuevas = []
    for m in fichas:
        attrs = m.group("attrs")           # conserva data-step en la version narrada
        nuevas.append(
            f'          <div class="hyp wide"{attrs}>\n'
            f'            <div class="id">{m.group("id")}</div>\n'
            f'            <div class="txt">{" ".join(m.group("nombre").split())}</div>\n'
            f'            <div class="test">{" ".join(m.group("regla").split())}</div>\n'
            f'          </div>\n'
        )

    ini, fin = fichas[0].start(), fichas[-1].end()
    # el contenedor de dos columnas que las envuelve
    abre = s.rindex('<div class="row grow"', 0, ini)
    cierra = s.index("</div>", s.index("</div>", fin) + 6) + 6   # cierra .col y .row

    bloque = '<div class="hyplist">\n' + "".join(nuevas) + "        </div>"
    s = s[:abre] + bloque + s[cierra:]

    mazo.write_text(s, encoding="utf-8")
    print(f"  + {mazo.name}: 4 arquetipos a formato ancho")

if fallos:
    print("\nPROBLEMAS:")
    for f in fallos:
        print("  !", f)
    sys.exit(1)
print("\nlisto")
