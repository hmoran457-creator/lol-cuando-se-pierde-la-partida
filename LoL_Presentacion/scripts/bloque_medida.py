r"""Parte el bloque «La medida» en líneas.

Estaba escrito como un párrafo corrido donde los tres umbrales iban separados
sólo por puntos, así que había que leerlo entero para encontrar cualquiera de
ellos. Pasa a tres piezas: la definición, los tres umbrales en bandas paralelas,
y la advertencia de por qué la medida es relativa.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def medida(sangria: str, cierre: str = "") -> str:
    i = sangria
    return (
        f'{i}<div class="medida">\n'
        f'{i}  <p class="def"><strong>La medida:</strong> <code>v</code> = diferencia de oro\n'
        f'{i}    ÷ oro total en el mapa, cuadro por cuadro.</p>\n'
        f'{i}  <div class="bandas">\n'
        f'{i}    <div><span class="et">Ventaja real</span><code>v ≥ 5 %</code> y al menos 1,500 de oro</div>\n'
        f'{i}    <div><span class="et">Decisiva</span><code>|v| ≥ 10 %</code></div>\n'
        f'{i}    <div><span class="et">Sostenida</span><code>≥ 3 minutos</code> seguidos</div>\n'
        f'{i}  </div>\n'
        f'{i}  <p class="pie">Es relativa a propósito: 2,467 de oro son el 7.7 % del mapa en el\n'
        f'{i}    minuto 10, y solo el 2.3 % en el minuto 28.{cierre}</p>\n'
        f'{i}</div>'
    )


CAMBIOS = [
    # ── mazo completo ────────────────────────────────────────────────────────
    (ROOT / "presentacion.html",
     """        <div class="panel" style="border-left:3px solid var(--blue); padding:12px 16px">
          <p style="max-width:none; margin:0; font-size:16px">
            <strong>La medida:</strong> <code>v</code> = diferencia de oro del equipo ÷ oro total
            de los diez jugadores, cuadro por cuadro. <strong>Ventaja real:</strong>
            <code>v ≥ 5 %</code> y al menos 1,500 de oro. <strong>Decisiva:</strong>
            <code>|v| ≥ 10 %</code>. Es relativa a propósito: 2,467 de oro son el 7.7 % del mapa
            en el minuto 10, y en el minuto 28 una ventaja mayor (2,565) es solo el 2.3 %.
          </p>
        </div>""",
     '        <div class="panel" style="border-left:3px solid var(--blue); padding:14px 18px">\n'
     + medida("          ") + "\n        </div>"),

    # ── mazo de 5 min: la nota lleva ademas el orden de evaluacion ───────────
    (ROOT / "presentacion_5min.html",
     """        <p class="note" style="max-width:none; margin:0">
          <strong>La medida:</strong> <code>v</code> = diferencia de oro ÷ oro total en el mapa,
          cuadro por cuadro. <strong>Ventaja real:</strong> <code>v ≥ 5 %</code> y ≥ 1,500 de oro.
          <strong>Decisiva:</strong> <code>|v| ≥ 10 %</code>. Relativa a propósito: 2,467 de oro
          son el 7.7 % del mapa en el minuto 10 y solo el 2.3 % en el 28.
          Se aplican en orden <em>A4 → A2 → A1 → A3</em>; el resto queda <em>sin clasificar</em>.
        </p>""",
     medida("        ",
            " Se aplican en orden <em>A4 → A2 → A1 → A3</em>; el resto queda <em>sin clasificar</em>.")),

    # ── mazo narrado: mismo bloque, dentro del panel del paso 1 ──────────────
    (ROOT / "presentacion_story.html",
     """        <div class="panel" data-step="1"
             style="border-left:3px solid var(--blue); padding:12px 16px">
          <p style="max-width:none; margin:0; font-size:16px">
            <strong>La medida:</strong> <code>v</code> = diferencia de oro ÷ oro total en el mapa,
            cuadro por cuadro. <strong>Ventaja real:</strong> <code>v ≥ 5 %</code> y ≥ 1,500 de oro.
            <strong>Decisiva:</strong> <code>|v| ≥ 10 %</code>. Relativa a propósito: 2,467 de oro
            son el 7.7 % del mapa en el minuto 10 y solo el 2.3 % en el 28.
          </p>
        </div>""",
     '        <div class="panel" data-step="1"\n'
     '             style="border-left:3px solid var(--blue); padding:14px 18px">\n'
     + medida("          ") + "\n        </div>"),
]

fallos = []
for archivo, viejo, nuevo in CAMBIOS:
    s = archivo.read_text(encoding="utf-8")
    if s.count(viejo) != 1:
        fallos.append(f"{archivo.name}: {s.count(viejo)} coincidencias")
        continue
    archivo.write_text(s.replace(viejo, nuevo), encoding="utf-8")
    print(f"  + {archivo.name}")

if fallos:
    print("\nPROBLEMAS:")
    for f in fallos:
        print("  !", f)
    sys.exit(1)

# ── estilos del bloque ───────────────────────────────────────────────────────
CSS = ROOT / "assets" / "deck.css"
c = CSS.read_text(encoding="utf-8")
ancla = "/* =========================================================================\n   Fichas de hipotesis"
bloque = """/* =========================================================================
   Bloque «La medida»: definicion, umbrales y advertencia, cada cosa en su linea.
   Los tres umbrales van en bandas paralelas y no en prosa corrida: asi se puede
   buscar uno solo sin leer el parrafo entero.
   ========================================================================= */

.medida { display: flex; flex-direction: column; gap: 10px; }
.medida .def { font-size: 16px; max-width: none; margin: 0; line-height: 1.45; }
.medida .bandas { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--s3); }
.medida .bandas > div {
  font-size: 15px; line-height: 1.4; color: var(--ink);
  border-left: 2px solid var(--line); padding-left: 12px;
}
.medida .et {
  display: block; color: var(--gold-lit); font-weight: 700;
  font-size: 12.5px; letter-spacing: .01em; margin-bottom: 3px;
}
.medida .pie { font-size: 13.5px; color: var(--muted); max-width: none; margin: 0; line-height: 1.45; }

/* =========================================================================
   Fichas de hipotesis"""
if c.count(ancla) != 1:
    print(f"\n! ancla de CSS: {c.count(ancla)} coincidencias")
    sys.exit(1)
CSS.write_text(c.replace(ancla, bloque), encoding="utf-8")
print("  + deck.css: estilos de .medida")
print("\nbloque «La medida» partido en líneas")
