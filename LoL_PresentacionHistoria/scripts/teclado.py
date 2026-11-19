r"""Recorre la presentacion con el teclado, como en clase, y revisa que nada se rompa.

    python LoL_PresentacionHistoria/scripts/teclado.py

Comprueba, con movimiento normal y con «reducir movimiento»:
  * avanzar paso por paso por todas las laminas sin errores de consola;
  * que al terminar cada lamina todos sus pasos esten a la vista y cada contador
    haya llegado a su cifra;
  * que al REGRESAR a una lamina ya vista aparezca completa;
  * que R la repita desde el paso 0 y que P (modo cine) avance solo.
"""
from __future__ import annotations

import pathlib
import sys

from playwright.sync_api import sync_playwright

DECK = pathlib.Path(__file__).resolve().parent.parent / "presentacion_historia.html"

ESTADO = """() => {
  const s = document.querySelector('.slide.active');
  const pasos = [...s.querySelectorAll('[data-step]')];
  const dig = x => String(x).replace(/[^0-9]/g, '');
  const malos = [...s.querySelectorAll('[data-count]')].filter(e => {
    const st = e.closest('[data-step]');
    if (st && !st.classList.contains('mostrado')) return false;
    const n = Number(String(e.dataset.count).replace(/[^0-9.\\-]/g, ''));
    const d = +(e.dataset.dec || 0);
    return dig(e.textContent) !== dig(n.toLocaleString('es-MX', {minimumFractionDigits: d, maximumFractionDigits: d}));
  }).length;
  return { id: s.id, total: pasos.length, vistos: pasos.filter(p => p.classList.contains('mostrado')).length,
           contadores_malos: malos };
}"""


def recorrido(nav, reducir: bool) -> list[str]:
    ctx = nav.new_context(viewport={"width": 1600, "height": 900},
                          reduced_motion="reduce" if reducir else "no-preference")
    pg = ctx.new_page()
    errores: list[str] = []
    pg.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errores.append(str(e)))
    pg.goto(DECK.as_uri())
    pg.wait_for_timeout(800)
    problemas: list[str] = []
    n = pg.evaluate("document.querySelectorAll('.slide').length")
    vistas = []
    for _ in range(200):                      # avanzar todo, un paso a la vez
        st = pg.evaluate(ESTADO)
        maxp = pg.evaluate("Math.max(0, ...[...document.querySelectorAll('.slide.active [data-step]')].map(e => +e.dataset.step))")
        paso = pg.evaluate("document.querySelector('.slide.active')._paso || 0")
        if paso >= maxp:                      # lamina completa: esperar animaciones y revisar
            pg.wait_for_timeout(300 if reducir else 6500)
            st = pg.evaluate(ESTADO)
            if st["vistos"] != st["total"] or st["contadores_malos"]:
                problemas.append(f"{st['id']}: {st['vistos']}/{st['total']} pasos, {st['contadores_malos']} contadores sin llegar")
            vistas.append(st["id"])
            if len(vistas) == n:
                break
        pg.keyboard.press("ArrowRight")
        pg.wait_for_timeout(120 if reducir else 900)
    if len(vistas) != n:
        problemas.append(f"solo se recorrieron {len(vistas)} de {n} laminas")
    for _ in range(3):                        # regresar: debe aparecer completa
        pg.keyboard.press("ArrowLeft")
        pg.wait_for_timeout(400)
        st = pg.evaluate(ESTADO)
        if st["vistos"] != st["total"] or st["contadores_malos"]:
            problemas.append(f"al regresar a {st['id']}: {st['vistos']}/{st['total']} pasos, "
                             f"{st['contadores_malos']} contadores mal")
    pg.keyboard.press("r")                    # R: desde el paso 0
    pg.wait_for_timeout(200)
    st = pg.evaluate(ESTADO)
    if st["total"] and st["vistos"] == st["total"]:
        problemas.append(f"R no reinicio {st['id']}")
    antes = pg.evaluate("location.hash")      # P: modo cine avanza solo
    pg.keyboard.press("p")
    pg.wait_for_timeout(16000)
    if pg.evaluate("location.hash") == antes and pg.evaluate("document.querySelector('.slide.active')._paso || 0") == 0:
        problemas.append("P (modo cine) no avanzo")
    pg.keyboard.press("p")
    ctx.close()
    return [f"consola: {e}" for e in dict.fromkeys(errores)] + problemas


def main() -> int:
    total = []
    with sync_playwright() as p:
        nav = p.chromium.launch()
        for reducir in (False, True):
            r = recorrido(nav, reducir)
            print(f"{'movimiento reducido' if reducir else 'movimiento normal':>20}: "
                  f"{'sin problemas' if not r else str(len(r)) + ' problemas'}")
            for x in r:
                print("   -", x)
            total += r
        nav.close()
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
