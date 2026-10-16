r"""Escribe los umbrales numéricos de los arquetipos en los dos mazos.

Las reglas quedaban en prosa ("ventaja sostenida durante varios minutos") mientras
el subtítulo prometía "con su umbral numérico". Esto cierra esa brecha.
Los umbrales están comprobados en scripts/probe_umbrales.py: clasifican la partida
de ejemplo como A2, que es lo que la lámina afirma.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LARGO, CORTO = ROOT / "presentacion.html", ROOT / "presentacion_5min.html"
ok: list[str] = []
bad: list[str] = []


def sub(p: pathlib.Path, old: str, new: str, tag: str) -> None:
    s = p.read_text(encoding="utf-8")
    n = s.count(old)
    if n != 1:
        bad.append(f"[{tag}] {p.name}: {n} coincidencias :: {old[:64]!r}")
        return
    p.write_text(s.replace(old, new), encoding="utf-8")
    ok.append(f"{p.name} · {tag}")


MEDIDA = """        <div class="panel" style="border-left:3px solid var(--blue); padding:12px 16px">
          <p style="max-width:none; margin:0; font-size:16px">
            <strong>La medida:</strong> <code>v</code> = diferencia de oro del equipo ÷ oro total
            de los diez jugadores, cuadro por cuadro. <strong>Ventaja real:</strong>
            <code>v ≥ 5 %</code> y al menos 1,500 de oro. <strong>Decisiva:</strong>
            <code>|v| ≥ 10 %</code>. Es relativa a propósito: 2,467 de oro son el 7.7 % del mapa
            en el minuto 10, y en el minuto 28 una ventaja mayor (2,565) es solo el 2.3 %.
          </p>
        </div>
"""

# ── reglas con umbral, iguales en los dos mazos ──────────────────────────────
REGLAS = [
    ("A1",
     "<span class=\"test\">La desventaja de oro aparece antes del minuto 15 y nunca se revierte.</span>",
     "<span class=\"test\"><code>v ≤ −5 %</code> en el minuto 15, y la ventaja nunca vuelve a ser positiva.</span>"),
    ("A2",
     "<span class=\"test\">Ventaja sostenida durante varios minutos y derrota igual — la partida del inicio.</span>",
     "<span class=\"test\">Ventaja real durante <code>≥ 3 minutos</code> seguidos, alguno en el minuto 15 o "
     "después, y derrota igual. La partida del inicio cae aquí: 12 minutos seguidos.</span>"),
    ("A4",
     "<span class=\"test\">Desventaja grande desde los primeros minutos, sin ventana de remontada.</span>",
     "<span class=\"test\"><code>v ≤ −10 %</code> antes del minuto 15, y nunca se recupera por encima de <code>−5 %</code>.</span>"),
]

# A3 tiene redacción distinta en cada mazo
A3_LARGO = ("""<span class="test">Partida pareja hasta que la mayor caída de oro coincide con un objetivo mayor:
              barón, dragón, heraldo, larvas del vacío o Atakhan.</span>""",
            """<span class="test"><code>|v| &lt; 5 %</code> hasta la mayor caída de <code>v</code>, y esa caída a
              ±1 minuto de un objetivo mayor del rival: barón, dragón, heraldo, larvas o Atakhan.</span>""")
A3_CORTO = ("""<span class="test">Partida pareja hasta que la mayor caída coincide con barón, dragón,
              heraldo, larvas o Atakhan.</span>""",
            """<span class="test"><code>|v| &lt; 5 %</code> hasta la mayor caída de <code>v</code>, y esa caída a
              ±1 minuto de un objetivo mayor del rival.</span>""")

# ═══════════════════════════════════════════════════════ mazo largo
sub(LARGO, """      <div class="body">
        <div class="row grow" style="gap:var(--s5)">
          <div class="col half">
            <div class="hyp"><div class="id">A1</div><div class="txt">Derrota desde línea""",
    """      <div class="body">
""" + MEDIDA + """        <div class="row grow" style="gap:var(--s5)">
          <div class="col half">
            <div class="hyp"><div class="id">A1</div><div class="txt">Derrota desde línea""",
    "medida")

for tag, old, new in REGLAS:
    sub(LARGO, old, new, f"regla {tag}")
sub(LARGO, *A3_LARGO, "regla A3")

# el orden ahora es completo, y se suma la prueba de sensibilidad
sub(LARGO, """        <p class="note" style="margin:2px 0 10px">Se aplican en orden: A4 se evalúa antes que A1,
          y lo que no cumple ninguna queda <em>sin clasificar</em>.</p>""",
    """        <p class="note" style="margin:2px 0 10px">Se aplican en este orden —
          <em>A4 → A2 → A1 → A3</em> — y lo que no cumple ninguna queda <em>sin clasificar</em>.</p>""",
    "orden")

sub(LARGO, """        <p class="note">
          Habrá una categoría <em>“sin clasificar”</em>, y su tamaño se reporta. Un conjunto de
          reglas que acomoda el 100&nbsp;% de las partidas es la señal de que se ajustaron
          después de ver los datos.
        </p>""",
    """        <p class="note">
          El tamaño de <em>“sin clasificar”</em> se reporta: un conjunto de reglas que acomoda el
          100&nbsp;% de las partidas es la señal de que se ajustaron después de ver los datos.
          Y reporto cuántas partidas cambian de arquetipo si el 5&nbsp;% se mueve a 4&nbsp;% o a
          6&nbsp;% — si apenas se mueven, el umbral no está haciendo trabajo sospechoso.
        </p>""", "sensibilidad")

# ═══════════════════════════════════════════════════════ mazo de 5 min
sub(CORTO, """      <div class="body">
        <div class="row grow" style="gap:var(--s5)">
          <div class="col half">
            <div class="hyp"><div class="id">A1</div><div class="txt">Derrota desde línea""",
    """      <div class="body">
        <p class="note" style="max-width:none; margin:0">
          <strong>La medida:</strong> <code>v</code> = diferencia de oro ÷ oro total en el mapa,
          cuadro por cuadro. <strong>Ventaja real:</strong> <code>v ≥ 5 %</code> y ≥ 1,500 de oro.
          <strong>Decisiva:</strong> <code>|v| ≥ 10 %</code>. Relativa a propósito: 2,467 de oro
          son el 7.7 % del mapa en el minuto 10 y solo el 2.3 % en el 28.
          Se aplican en orden <em>A4 → A2 → A1 → A3</em>; el resto queda <em>sin clasificar</em>.
        </p>
        <div class="row grow" style="gap:var(--s5)">
          <div class="col half">
            <div class="hyp"><div class="id">A1</div><div class="txt">Derrota desde línea""",
    "medida")

sub(CORTO, "<span class=\"test\">La desventaja aparece antes del minuto 15 y nunca se revierte.</span>",
    "<span class=\"test\"><code>v ≤ −5 %</code> en el minuto 15, y nunca vuelve a ser positiva.</span>",
    "regla A1")
sub(CORTO, "<span class=\"test\">Ventaja sostenida y derrota igual — la partida del inicio.</span>",
    "<span class=\"test\">Ventaja real <code>≥ 3 minutos</code> seguidos, alguno en el 15 o después. "
    "La partida del inicio: 12 seguidos.</span>", "regla A2")
sub(CORTO, "<span class=\"test\">Desventaja grande desde el principio, sin ventana de remontada.</span>",
    "<span class=\"test\"><code>v ≤ −10 %</code> antes del minuto 15, y nunca se recupera sobre <code>−5 %</code>.</span>",
    "regla A4")
sub(CORTO, *A3_CORTO, "regla A3")

# ═══════════════════════════════════════════════════════ informe
print("=" * 62)
for a in ok:
    print("  +", a)
if bad:
    print(f"\nFALLARON ({len(bad)}):")
    for m in bad:
        print("  !", m)
    sys.exit(1)
print(f"\n{len(ok)} reemplazos aplicados en los dos mazos")
