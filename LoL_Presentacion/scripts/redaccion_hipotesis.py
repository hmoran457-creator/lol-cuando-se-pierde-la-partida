r"""Reescribe las tres hipótesis para que suenen a español dicho en voz alta.

Qué estaba mal:
  H1 · «en las partidas que pierdo mi equipo toma» se lee un instante como «que
       pierdo mi equipo», y la persona salta a media frase: pierdo (yo) ->
       mi equipo toma (él). Se unifica el sujeto con perdemos/ganamos.
  H2 · «la ventana donde más cambia el oro» es abstracto y «con más frecuencia de
       la esperada por azar» suena a resumen traducido. Se concreta y se nombra
       el objetivo.
  H3 · «cae de forma marcada» es un calco duro; la trampa abría con un sustantivo
       suelto («supervivencia.») y cerraba con una compresión ilegible.

El contenido no cambia: siguen definiendo la conversión sin mirar el resultado,
siguen diciendo que el objetivo marca y no causa, y siguen nombrando el sesgo de
supervivencia.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAZOS = [ROOT / "presentacion.html", ROOT / "presentacion_5min.html",
         ROOT / "presentacion_story.html"]

# ── enunciados: idénticos en los tres mazos ──────────────────────────────────
TXT = [
    ("""Con la misma ventaja temprana, en las partidas que pierdo mi equipo
              toma menos objetivos por minuto que en las que gana.""",
     """Con la misma ventaja temprana, mi equipo toma menos objetivos por minuto
              en las partidas que perdemos que en las que ganamos."""),

    ("""La ventana donde más cambia el oro contiene un objetivo con más
              frecuencia de la esperada por azar.""",
     """El minuto en que más cae la ventaja coincide con un objetivo —barón,
              dragón o heraldo— más seguido de lo que explicaría el azar."""),

    ("""Existe un minuto a partir del cual la probabilidad de remontar cae
              de forma marcada.""",
     """Existe un punto de no retorno: un minuto a partir del cual mis derrotas
              ya casi nunca se revierten."""),
]

# ── trampas: versión larga (completa y 5 min) ────────────────────────────────
TRAP_LARGA = [
    ("""<b>Trampa:</b> decir “las perdí por no convertir” es circular —
              toda ventaja perdida fue, por definición, no convertida. Solo se prueba si
              “convertir” se define sin mirar el resultado.""",
     """<b>Trampa:</b> “las perdí por no convertir” no se puede probar: toda ventaja
              perdida fue, por definición, no convertida. Por eso mido la conversión sin mirar el
              resultado — objetivos por minuto mientras íbamos arriba."""),

    ("""<b>Trampa:</b> la pelea ocurre <em>antes</em> que el objetivo, así que
              el objetivo marca el momento, no lo causa. Y los cambios tardíos son mecánicamente
              más grandes: hay que normalizar.""",
     """<b>Trampa:</b> el objetivo marca el momento, no lo causa: la pelea ocurre
              <em>antes</em>. Y como el oro crece con la partida, las caídas tardías son mayores
              por sí solas — hay que normalizar."""),

    ("""<b>Trampa:</b> supervivencia. Un minuto crítico en el 30 solo existe
              en partidas que llegaron al 30, y el denominador se encoge justo donde afirmo el
              efecto. Espero intervalos demasiado anchos para ubicarlo — y ese sería el resultado.""",
     """<b>Trampa:</b> sesgo de supervivencia. Un punto de no retorno en el minuto 30
              solo se puede ver en las partidas que llegaron al 30, y a esa altura quedan pocas: el
              denominador se encoge justo donde digo que está el efecto. Espero intervalos
              demasiado anchos para ubicarlo — y ese sería el resultado."""),
]

# ── trampas: versión corta (narrada) ─────────────────────────────────────────
TRAP_CORTA = [
    ("""<b>Trampa:</b> decir “las perdí por no convertir” es circular —
              toda ventaja perdida fue, por definición, no convertida.""",
     """<b>Trampa:</b> “las perdí por no convertir” no se puede probar: toda ventaja
              perdida fue, por definición, no convertida."""),

    ("""<b>Trampa:</b> la pelea ocurre <em>antes</em> que el objetivo, así que
              el objetivo marca el momento, no lo causa.""",
     """<b>Trampa:</b> el objetivo marca el momento, no lo causa: la pelea ocurre
              <em>antes</em>."""),

    ("""<b>Trampa:</b> supervivencia. Un minuto crítico en el 30 solo existe
              en partidas que llegaron al 30, justo donde afirmo el efecto.""",
     """<b>Trampa:</b> sesgo de supervivencia. Un punto de no retorno en el minuto 30
              solo se ve en las partidas que llegaron al 30, y a esa altura quedan pocas."""),
]

fallos: list[str] = []

for mazo in MAZOS:
    s = mazo.read_text(encoding="utf-8")
    hechos = 0
    grupos = TXT + (TRAP_CORTA if "story" in mazo.name else TRAP_LARGA)
    for old, new in grupos:
        n = s.count(old)
        if n != 1:
            fallos.append(f"{mazo.name}: {n} coincidencias de {old[:44]!r}")
            continue
        s = s.replace(old, new)
        hechos += 1
    if hechos == len(grupos):
        mazo.write_text(s, encoding="utf-8")
        print(f"  + {mazo.name}: {hechos} reemplazos")
    else:
        fallos.append(f"{mazo.name}: solo {hechos}/{len(grupos)}, no se escribio")

if fallos:
    print("\nPROBLEMAS:")
    for f in fallos:
        print("  !", f)
    sys.exit(1)
print("\nredacción actualizada en los tres mazos")
