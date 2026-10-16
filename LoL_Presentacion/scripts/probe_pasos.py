r"""¿La revelación por pasos se comporta como necesita un presentador?

Seis cosas, cada una capaz de fallar sola:
  A · la flecha avanza PASOS dentro de la lámina, y sólo al agotarlos cambia de lámina
  B · el clic hace lo mismo que la flecha
  C · los puntos del riel muestran cuántos pasos faltan
  D · volver atrás muestra la lámina entera (para responder una pregunta)
  E · la tecla A revela todo de golpe
  F · ?todo desactiva el sistema, y los otros dos mazos siguen pasando de lámina
      de un solo clic
"""
from __future__ import annotations

import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORY = (ROOT / "presentacion_story.html").as_uri()
CORTO = (ROOT / "presentacion_5min.html").as_uri()

ESTADO = """() => {
  const s = document.querySelector('.slide.active');
  const vis = [...s.querySelectorAll('[data-step]')]
    .filter(e => e.classList.contains('mostrado')).length;
  return { id: s.id, pasos: s.querySelectorAll('[data-step]').length, vistos: vis,
           pips: document.querySelectorAll('#pasos i').length,
           pipsOn: document.querySelectorAll('#pasos i.on').length };
}"""


def abre(pg, url, n=None):
    pg.goto(url)
    if n:
        pg.evaluate(f"location.hash = 'd{n}'")
        pg.reload()
    pg.wait_for_timeout(900)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1600, "height": 950})

    print("A · la flecha avanza pasos y luego de lámina (lámina 3, «Lo primero que miramos»)")
    abre(pg, STORY, 3)
    for i in range(5):
        e = pg.evaluate(ESTADO)
        print(f"  clic {i}: {e['id']:<12} pasos vistos {e['vistos']}/{e['pasos']}"
              f"   pips {e['pipsOn']}/{e['pips']}")
        pg.keyboard.press("ArrowRight")
        pg.wait_for_timeout(520)
    fin = pg.evaluate(ESTADO)
    print(f"  al final: {fin['id']}   {'PASA DE LAMINA AL AGOTARSE' if fin['id'] != 's-facil' else 'NO AVANZO'}")

    print("\nB · el clic del ratón hace lo mismo")
    abre(pg, STORY, 3)
    antes = pg.evaluate(ESTADO)["vistos"]
    pg.mouse.click(1200, 500)
    pg.wait_for_timeout(520)
    print(f"  vistos {antes} -> {pg.evaluate(ESTADO)['vistos']}")

    print("\nD · volver atrás muestra la lámina entera")
    abre(pg, STORY, 3)
    for _ in range(4):
        pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(420)
    pg.keyboard.press("ArrowLeft"); pg.wait_for_timeout(500)
    e = pg.evaluate(ESTADO)
    print(f"  {e['id']}: {e['vistos']}/{e['pasos']} "
          f"{'ENTERA' if e['vistos'] == e['pasos'] else 'A MEDIAS'}")

    print("\nE · la tecla A revela todo")
    abre(pg, STORY, 9)
    pg.keyboard.press("a"); pg.wait_for_timeout(500)
    e = pg.evaluate(ESTADO)
    print(f"  {e['id']}: {e['vistos']}/{e['pasos']} {'TODO' if e['vistos'] == e['pasos'] else 'NO'}")

    print("\nF · ?todo, y los otros mazos")
    pg.goto(STORY + "?todo")
    pg.evaluate("location.hash='d9'")
    pg.reload(); pg.wait_for_timeout(900)
    e = pg.evaluate(ESTADO)
    print(f"  story ?todo d9: {e['vistos']}/{e['pasos']} {'TODO VISIBLE' if e['vistos'] == e['pasos'] else 'NO'}")

    abre(pg, CORTO, 3)
    a = pg.evaluate("document.querySelector('.slide.active').id")
    pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(500)
    c = pg.evaluate("document.querySelector('.slide.active').id")
    print(f"  mazo de 5 min: {a} -> {c}   {'PASA DE UN CLIC' if a != c else 'SE ATORO'}")
    b.close()
