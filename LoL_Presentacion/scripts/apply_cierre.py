r"""Añade la lámina final de agradecimiento a los dos mazos.

Hace de contraparte de la portada: mismo tratamiento a sangre, sin riel, y el
crédito de herramienta al pie.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAZOS = [ROOT / "presentacion.html", ROOT / "presentacion_5min.html"]

CIERRE = """
    <!-- ══════════════════════════════════════════════════════ cierre ═══ -->
    <section class="slide bare" id="s-thanks">
      <div style="margin:auto 0; display:flex; flex-direction:column; gap:34px">
        <h1 style="font-size:132px; font-weight:900; line-height:.95; letter-spacing:-.04em;
                   font-variation-settings:'wdth' 118; color:var(--parchment); margin:0">
          Gracias
        </h1>
        <p class="lead" style="color:var(--muted); max-width:48ch; font-size:26px; margin:0">
          ¿En qué minuto se perdió la partida?<br>
          Quedo atento a sus preguntas.
        </p>
      </div>
      <div class="footer">
        <div>Héctor Manuel Morán Maldonado · Especialidad en Ciencia de Datos</div>
        <div>Presentación elaborada con la asistencia de Claude (Anthropic)</div>
      </div>
    </section>
"""

ANCLA = "\n  </div>\n</div>\n\n<div id=\"blank\"></div>"
ok, bad = [], []

for p in MAZOS:
    s = p.read_text(encoding="utf-8")
    if 's id="s-thanks"' in s:
        bad.append(f"{p.name}: la lámina de cierre ya existe")
        continue
    if s.count(ANCLA) != 1:
        bad.append(f"{p.name}: el ancla de cierre aparece {s.count(ANCLA)} veces")
        continue
    p.write_text(s.replace(ANCLA, CIERRE + ANCLA), encoding="utf-8")
    ok.append(f"{p.name}: {s.count('class=\"slide')} -> {s.count('class=\"slide') + 1} láminas")

for line in ok:
    print("  +", line)
if bad:
    print("\nFALLARON:")
    for b in bad:
        print("  !", b)
    sys.exit(1)
print("\nlámina de cierre añadida a los dos mazos")
