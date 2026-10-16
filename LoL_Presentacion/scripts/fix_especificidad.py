r"""Corrige los dos errores de especificidad que encontró probe_animado.py.

1. Las reglas puntuales no llevaban `:not(.visto)`, así que al retroceder la
   lámina volvía a animarse aunque la cascada sí se callara.
2. El bloque de `prefers-reduced-motion` era MENOS específico que las reglas
   animadas (`:not()` cuenta como clase), así que perdía: la cascada seguía
   corriendo con movimiento reducido puesto.

Cada reemplazo afirma cuántas veces debe aparecer su ancla. El intento anterior
falló justamente por eso: un ancla aparecía dos veces y se reemplazaron ambas.
"""
from __future__ import annotations

import pathlib
import sys

CSS = pathlib.Path(__file__).resolve().parent.parent / "assets" / "deck.css"
s = CSS.read_text(encoding="utf-8")
fallos: list[str] = []


def cambia(old: str, new: str, veces: int, tag: str) -> None:
    global s
    n = s.count(old)
    if n != veces:
        fallos.append(f"[{tag}] aparece {n} veces, se esperaban {veces}")
        return
    s = s.replace(old, new)
    print("  +", tag)


# ── 1 · las puntuales se callan al retroceder ────────────────────────────────
cambia(".animado #s-defeat .defeat-sub { animation: llega 520ms var(--ease) 900ms backwards; }",
       ".animado #s-defeat.slide:not(.visto) .defeat-sub { animation: llega 520ms var(--ease) 900ms backwards; }",
       1, "defeat-sub")

cambia(".animado #s-timeline .code .hl {\n  background-color: transparent;",
       ".animado #s-timeline.slide:not(.visto) .code .hl {\n  background-color: transparent;",
       1, "timestamp")

cambia(".animado #s-partida .body > .note { animation: llega 420ms var(--ease) 1700ms backwards; }",
       ".animado #s-partida.slide:not(.visto) .body > .note { animation: llega 420ms var(--ease) 1700ms backwards; }",
       1, "nota-partida")

cambia(".animado #s-defeat .defeat-word { animation: aterriza 600ms var(--ease) backwards; }",
       ".animado #s-defeat.slide:not(.visto) .defeat-word { animation: aterriza 600ms var(--ease) backwards; }",
       1, "defeat-word")

# ── 2 · el bloque de movimiento reducido iguala la especificidad ─────────────
VIEJO = """  /* las extras del mazo corto: se apagan, pero su ESTADO FINAL se queda puesto
     -- el resaltado del timestamp es contenido, no adorno */
  .animado #s-defeat .defeat-sub,
  .animado #s-partida .body > .note { animation: none; }
  .animado #s-timeline .code .hl { animation: none; background-size: 100% 100%; }
  /* la cascada completa se apaga; el contenido queda tal cual, visible */
  .animado .slide.active .kicker,
  .animado .slide.active h2,
  .animado .slide.active .footer,
  .animado .slide.active .body > *,
  .animado .slide.bare.active > div > *,
  .animado .slide.active :is(.ticks li, .srcitem, .hyp),
  .animado #s-defeat .defeat-word { animation: none; }"""

NUEVO = """  /* Estos selectores REPITEN el `:not(.visto)` de las reglas que apagan. Sin el,
     la regla animada es mas especifica y gana, y la cascada seguia corriendo con
     prefers-reduced-motion puesto. El estado FINAL siempre queda visible: el
     resaltado del timestamp es contenido, no adorno. */
  .animado #s-defeat.slide:not(.visto) .defeat-sub,
  .animado #s-defeat.slide:not(.visto) .defeat-word,
  .animado #s-partida.slide:not(.visto) .body > .note,
  .animado .slide.active:not(.visto) .kicker,
  .animado .slide.active:not(.visto) h2,
  .animado .slide.active:not(.visto) .footer,
  .animado .slide.active:not(.visto) .body > *,
  .animado .slide.bare.active:not(.visto) > div > *,
  .animado .slide.active:not(.visto) :is(.ticks li, .srcitem, .hyp) { animation: none; }
  .animado #s-timeline.slide:not(.visto) .code .hl {
    animation: none; background-size: 100% 100%;
  }"""

cambia(VIEJO, NUEVO, 1, "bloque-movimiento-reducido")

if fallos:
    print("\nFALLARON, no se escribio nada:")
    for f in fallos:
        print("  !", f)
    sys.exit(1)

CSS.write_text(s, encoding="utf-8")
print("\ndeck.css actualizado")
