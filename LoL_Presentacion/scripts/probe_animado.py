r"""Comprueba TODO el movimiento del mazo corto, y que no se filtre al largo.

Cinco preguntas, cada una capaz de fallar por su cuenta:
  A · las tres animaciones puntuales corren
  B · la cascada de entrada corre y se escalona
  C · los contadores cuentan
  D · al RETROCEDER no se repite nada (clase .visto)
  E · el mazo largo sigue sin nada de esto, y con menos movimiento todo el
      contenido queda visible
"""
from __future__ import annotations

import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORTO = (ROOT / "presentacion_5min.html").as_uri()
LARGO = (ROOT / "presentacion.html").as_uri()

OPACIDAD = ("() => { const s=document.querySelector('.slide.active');"
            " const g=x=>{const e=s.querySelector(x);"
            "   return e?+(+getComputedStyle(e).opacity).toFixed(2):null;};"
            " return {kicker:g('.kicker'), h2:g('h2'),"
            "         b1:g('.body > *:nth-child(1)'), b2:g('.body > *:nth-child(2)'),"
            "         pie:g('.footer')}; }")


def ir(pg, base, n, espera):
    pg.goto(base)
    pg.evaluate(f"location.hash = 'd{n}'")
    pg.reload()
    pg.wait_for_timeout(espera)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1600, "height": 950})

    print("A · animaciones puntuales del mazo corto")
    for n, sel, prop, ts in [
        (2, "#s-defeat .defeat-sub", "opacity", (400, 2000)),
        (6, "#s-timeline .code .hl", "backgroundSize", (1250, 2400)),
        (3, "#s-partida .body > .note", "opacity", (900, 2600)),
    ]:
        v = []
        for t in ts:
            ir(pg, CORTO, n, t)
            v.append(pg.evaluate(
                "([s,p])=>{const e=document.querySelector(s);"
                " return e?getComputedStyle(e)[p]:null;}", [sel, prop]))
        print(f"  d{n} {sel:<30} {v[0]}  ->  {v[1]}   {'CORRE' if v[0]!=v[1] else 'NO CORRE'}")

    print("\nB · cascada de entrada (lámina 5, Fuentes de datos)")
    ir(pg, CORTO, 5, 120)
    pronto = pg.evaluate(OPACIDAD)
    ir(pg, CORTO, 5, 1100)
    tarde = pg.evaluate(OPACIDAD)
    print(f"  a 120 ms : {pronto}")
    print(f"  a 1100 ms: {tarde}")
    escalona = pronto["kicker"] is not None and pronto["kicker"] > (pronto["b2"] or 0)
    todo_ok = all(v == 1 for v in tarde.values() if v is not None)
    print(f"  se escalona (kicker antes que el cuerpo): {escalona}")
    print(f"  todo visible al asentarse: {todo_ok}")

    print("\nC · contadores (lámina 3)")
    vals = []
    for t in (500, 800, 1700):
        ir(pg, CORTO, 3, t)
        vals.append(pg.evaluate(
            "()=>document.querySelector('[data-count]')?.textContent"))
    print(f"  +8,052 a 500/800/1700 ms: {vals}   "
          f"{'CUENTA' if len(set(vals)) > 1 and vals[-1] == '+8,052' else 'REVISAR'}")

    print("\nD · al retroceder no se repite")
    pg.goto(CORTO); pg.wait_for_timeout(700)
    pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(1200)   # -> 2
    pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(2600)   # -> 3
    pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(900)    # -> 4
    pg.keyboard.press("ArrowLeft");  pg.wait_for_timeout(120)    # vuelve a 3
    r = pg.evaluate("""() => { const s=document.querySelector('.slide.active');
      return { id:s.id, visto:s.classList.contains('visto'),
               nota:+(+getComputedStyle(s.querySelector('.body > .note')).opacity).toFixed(2),
               cifra:s.querySelector('[data-count]').textContent }; }""")
    print(f"  {r}   {'SIN REPETIR' if r['visto'] and r['nota']==1 and r['cifra']=='+8,052' else 'SE REPITE'}")
    pg.close()

    print("\nE · el mazo largo, y menos movimiento")
    pg = b.new_page(viewport={"width": 1600, "height": 950})
    ir(pg, LARGO, 9, 1200)
    lg = pg.evaluate(OPACIDAD)
    anim = pg.evaluate("()=>getComputedStyle(document.querySelector('.slide.active .kicker')).animationName")
    print(f"  largo d9: opacidades {lg} · animation-name del kicker: {anim}")
    pg.close()

    pg = b.new_page(viewport={"width": 1600, "height": 950}, reduced_motion="reduce")
    ir(pg, CORTO, 5, 200)
    rm = pg.evaluate(OPACIDAD)
    ir(pg, CORTO, 3, 200)
    cifra = pg.evaluate("()=>document.querySelector('[data-count]').textContent")
    print(f"  menos movimiento: opacidades {rm} · cifra {cifra}")
    print(f"  {'TODO VISIBLE DE INMEDIATO' if all(v==1 for v in rm.values() if v is not None) and cifra=='+8,052' else 'REVISAR'}")
    pg.close()
    b.close()
