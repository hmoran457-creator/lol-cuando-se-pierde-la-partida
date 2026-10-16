r"""Reduce las hipótesis de seis a tres en los dos mazos existentes.

Se conservan las tres que corren sobre la línea temporal y forman un solo hilo:
convertir la ventaja, qué marca el quiebre, y si hay un punto sin retorno.
Se van la de primera sangre (no necesita timeline, otra ventana de datos), la de
modelo equipo-contra-individual y la de campeones (a la que ya se le había
cortado la mitad por no ser medible).

Efecto secundario que vale la pena: tres pruebas al 5 % dan 14 % de probabilidad
de al menos un falso positivo, contra 26 % con seis.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LARGO, CORTO = ROOT / "presentacion.html", ROOT / "presentacion_5min.html"

FICHAS = """          <div class="hyp wide">
            <div class="id">H1</div>
            <div class="txt">Con la misma ventaja temprana, en las partidas que pierdo mi equipo
              toma menos objetivos por minuto que en las que gana.</div>
            <div class="test"><b>Trampa:</b> decir “las perdí por no convertir” es circular —
              toda ventaja perdida fue, por definición, no convertida. Solo se prueba si
              “convertir” se define sin mirar el resultado.</div>
          </div>
          <div class="hyp wide">
            <div class="id">H2</div>
            <div class="txt">La ventana donde más cambia el oro contiene un objetivo con más
              frecuencia de la esperada por azar.</div>
            <div class="test"><b>Trampa:</b> la pelea ocurre <em>antes</em> que el objetivo, así que
              el objetivo marca el momento, no lo causa. Y los cambios tardíos son mecánicamente
              más grandes: hay que normalizar.</div>
          </div>
          <div class="hyp wide">
            <div class="id">H3</div>
            <div class="txt">Existe un minuto a partir del cual la probabilidad de remontar cae
              de forma marcada.</div>
            <div class="test"><b>Trampa:</b> supervivencia. Un minuto crítico en el 30 solo existe
              en partidas que llegaron al 30, y el denominador se encoge justo donde afirmo el
              efecto. Espero intervalos demasiado anchos para ubicarlo — y ese sería el resultado.</div>
          </div>
"""

PANEL = """        <div class="panel" style="border-left:3px solid var(--gold); background:rgba(188,139,44,.06); padding:14px var(--s3)">
          <p style="max-width:none; font-size:16.5px">
            <strong>Son tres y no seis a propósito.</strong> Las tres corren sobre la línea
            temporal y forman un solo hilo: convertir la ventaja, qué marca el quiebre, y si hay
            un punto sin retorno. Además, tres pruebas al 5&nbsp;% dan un 14&nbsp;% de
            probabilidad de al menos un falso positivo; con seis eran 26&nbsp;%.
          </p>
        </div>
"""

NUEVA = ('    <section class="slide" id="s-hyp" data-sec="3">\n'
         '      <div class="kicker">3 · Hipótesis</div>\n'
         '      <h2>Tres hipótesis, y la trampa de cada una\n'
         '        <span class="sub">Todas están escritas para poder salir falsas, y al lado va lo\n'
         '          que podría arruinarlas. Se comparan contra mis propias victorias.</span></h2>\n'
         '      <div class="body">\n'
         '        <div class="hyplist">\n'
         + FICHAS +
         '        </div>\n'
         + PANEL +
         '      </div>\n'
         '    </section>')


def seccion(texto: str, sid: str) -> tuple[int, int]:
    a = texto.index(f'<section class="slide" id="{sid}"')
    a = texto.rindex("\n", 0, a) + 1
    fin = "    </section>"
    b = texto.index(fin, a) + len(fin)
    return a, b


fallos = []

# ── mazo largo: s-hyp-a y s-hyp-b se funden en una sola ─────────────────────
s = LARGO.read_text(encoding="utf-8")
try:
    a1, b1 = seccion(s, "s-hyp-a")
    a2, b2 = seccion(s, "s-hyp-b")
    assert a2 > b1, "s-hyp-b deberia ir despues de s-hyp-a"
    s = s[:a1] + NUEVA + s[b2:]
    LARGO.write_text(s, encoding="utf-8")
    print(f"  + {LARGO.name}: s-hyp-a + s-hyp-b -> s-hyp   ({s.count('class=\"slide')} láminas)")
except Exception as e:  # noqa: BLE001
    fallos.append(f"{LARGO.name}: {e}")

# ── mazo de 5 min: la lamina de hipotesis se reemplaza entera ────────────────
c = CORTO.read_text(encoding="utf-8")
try:
    a, b = seccion(c, "s-hyp")
    c = c[:a] + NUEVA + c[b:]
    CORTO.write_text(c, encoding="utf-8")
    print(f"  + {CORTO.name}: 6 -> 3 hipótesis   ({c.count('class=\"slide')} láminas)")
except Exception as e:  # noqa: BLE001
    fallos.append(f"{CORTO.name}: {e}")

for f in (LARGO, CORTO):
    t = f.read_text(encoding="utf-8")
    ids = re.findall(r'class="id">(H\d)', t)
    print(f"    {f.name}: {ids}")
    if ids != ["H1", "H2", "H3"]:
        fallos.append(f"{f.name}: quedaron {ids}")

if fallos:
    print("\nPROBLEMAS:")
    for x in fallos:
        print("  !", x)
    sys.exit(1)
print("\ntres hipótesis en los dos mazos")
