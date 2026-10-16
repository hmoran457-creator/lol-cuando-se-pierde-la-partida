r"""Screenshot every slide and check it for real problems.

A deck that "looks fine" in source can overflow its stage, drop a font, or throw a
console error that silently kills an animation. This drives the actual file:// page
the way the classroom projector will, and asserts on what it finds.

    python scripts/shoot.py            # all slides
    python scripts/shoot.py 5          # just slide 5
"""
from __future__ import annotations

import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

# Acepta cualquiera de los dos mazos:
#   python scripts/shoot.py                       -> presentacion.html
#   python scripts/shoot.py presentacion_5min.html
#   python scripts/shoot.py presentacion_5min.html 3
_args = sys.argv[1:]
_deck = next((a for a in _args if a.endswith(".html")), "presentacion.html")
_nums = [a for a in _args if a.isdigit()]

DECK = ROOT / _deck
# ?todo revela todos los pasos: el arnes valida la lamina COMPLETA, que es
# lo que hay que revisar; a medio revelar cualquier hueco parece un defecto.
URL = DECK.as_uri() + "?todo"
SHOTS = ROOT / ("shots" if DECK.name == "presentacion.html"
                else "shots_" + DECK.stem.split("_")[-1])
SHOTS.mkdir(exist_ok=True)

# how long each slide's own animation needs before it is worth photographing
# Deben cubrir retraso + duracion de la animacion mas lenta de cada lamina, o la
# captura sale a media animacion y parece un defecto de maquetacion.
SETTLE = {
    "s-defeat": 1700,     # subtitulo: 900 + 520
    "s-reveal": 2400,
    "s-rewind": 2400,
    "s-break": 1600,
    "s-partida": 2400,    # cortina 260+1400, nota 1700+420
    "s-timeline": 2000,   # resaltado del timestamp: 1150 + 560
    "s-arch": 1600,
}
DEFAULT_SETTLE = 900


def main() -> None:
    print(f"mazo: {DECK.name}  ->  {SHOTS.name}/\n")
    only = int(_nums[0]) if _nums else None
    errors: list[str] = []
    problems: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 950})
        page.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

        page.goto(URL)
        page.wait_for_timeout(1200)  # fonts + boot

        n = page.evaluate("document.querySelectorAll('.slide').length")
        print(f"{n} diapositivas\n")

        # El escenario debe caber ENTERO en pantallas mas chicas que el, que es el
        # caso normal de un proyector. Esta prueba existe porque las capturas se
        # toman a 1600x950 -- mas ALTO que el escenario -- y por eso no veian el
        # recorte del 28% que sufria una pantalla de 1024x768.
        for vw, vh in [(1024, 768), (1280, 720), (1366, 768)]:
            probe = browser.new_page(viewport={"width": vw, "height": vh})
            probe.goto(URL)
            probe.wait_for_timeout(400)
            r = probe.evaluate(
                "() => { const b = document.getElementById('stage').getBoundingClientRect();"
                "  return [b.left, b.top, b.right, b.bottom]; }"
            )
            lost = max(0, -r[0]) + max(0, -r[1]) + max(0, r[2] - vw) + max(0, r[3] - vh)
            print(f"encuadre {vw}x{vh}: {'OK' if lost < 2 else f'RECORTA {lost:.0f}px'}")
            if lost >= 2:
                problems.append(f"a {vw}x{vh} el escenario se sale de la pantalla ({lost:.0f}px)")
            probe.close()
        print()

        # Confirm the vendored fonts are really on disk and valid. document.fonts.check()
        # alone is NOT the test: webfonts load lazily, so a face is "unloaded" simply
        # because no slide has used it yet. Force the load, then check.
        fonts = page.evaluate(
            """async () => {
                 const want = ['700 52px Archivo', '400 13px "JetBrains Mono"'];
                 const out = {};
                 for (const w of want) {
                   try { await document.fonts.load(w, 'Aág0'); out[w] = document.fonts.check(w); }
                   catch (e) { out[w] = 'error: ' + e.message; }
                 }
                 return out;
               }"""
        )
        print(f"fuentes locales: {fonts}")
        for face, ok in fonts.items():
            if ok is not True:
                problems.append(f"la fuente local {face} NO cargo (se usaria una de respaldo)")

        for i in range(1, n + 1):
            if only and i != only:
                continue
            page.evaluate(f"location.hash='d{i}'")
            page.reload()
            page.wait_for_timeout(700)

            sid = page.evaluate("document.querySelector('.slide.active')?.id || ''")
            page.wait_for_timeout(SETTLE.get(sid, DEFAULT_SETTLE))

            # --- desbordamiento: nada debe salirse del escenario de 1600x900
            over = page.evaluate(
                """() => {
                  const s = document.querySelector('.slide.active');
                  if (!s) return [];
                  const bad = [];
                  const sr = { w: 1600, h: 900 };
                  s.querySelectorAll('*').forEach(el => {
                    const r = el.getBoundingClientRect();
                    const st = getComputedStyle(el);
                    if (st.display === 'none' || st.visibility === 'hidden') return;
                    if (r.width === 0 || r.height === 0) return;
                    // el escenario esta escalado; comparar en coordenadas del escenario
                    const stage = document.getElementById('stage').getBoundingClientRect();
                    const scale = stage.width / sr.w;
                    const x = (r.left - stage.left) / scale;
                    const y = (r.top - stage.top) / scale;
                    const w = r.width / scale, h = r.height / scale;
                    if (x < -1 || y < -1 || x + w > sr.w + 1 || y + h > sr.h + 1) {
                      bad.push({
                        tag: el.tagName.toLowerCase(),
                        cls: (el.className || '').toString().slice(0, 44),
                        box: [Math.round(x), Math.round(y), Math.round(w), Math.round(h)],
                        txt: (el.textContent || '').trim().slice(0, 42)
                      });
                    }
                  });
                  return bad;
                }"""
            )
            # solo el contenedor mas externo de cada desbordamiento importa
            if over:
                worst = over[0]
                problems.append(
                    f"[{sid}] desbordamiento: <{worst['tag']} class='{worst['cls']}'> "
                    f"box={worst['box']} \"{worst['txt']}\" (+{len(over)-1} mas)"
                )

            # --- un bloque cuyo contenido se derrama sobre el siguiente. Mide el
            # DANO (texto encima de texto), no la causa: en la lamina de arquetipos
            # .row.grow media 36px con 196px dentro, y lo que sobresalia caia sobre
            # los dos paneles tapando las reglas A2 y A4. Ni el desbordamiento del
            # escenario ni el choque con el pie lo veian.
            spill = page.evaluate(
                """() => {
                  const kids = [...document.querySelectorAll('.slide.active .body > *')];
                  const ext = el => {
                    let b = el.getBoundingClientRect().bottom;
                    for (const d of el.querySelectorAll('*')) {
                      const r = d.getBoundingClientRect();
                      if (r.height) b = Math.max(b, r.bottom);
                    }
                    return b;
                  };
                  for (let i = 0; i < kids.length - 1; i++) {
                    const over = ext(kids[i]) - kids[i + 1].getBoundingClientRect().top;
                    if (over > 4) {
                      return { a: (kids[i].className || '').toString().slice(0, 30),
                               b: (kids[i + 1].className || '').toString().slice(0, 30),
                               over: Math.round(over) };
                    }
                  }
                  return null;
                }"""
            )
            if spill:
                problems.append(
                    f"[{sid}] <{spill['a']}> se derrama {spill['over']}px sobre <{spill['b']}>"
                )

            # --- el pie va posicionado en absoluto, asi que un texto que se le
            # encima NO desborda el escenario y el chequeo anterior no lo ve.
            hit = page.evaluate(
                """() => {
                  const s = document.querySelector('.slide.active');
                  const f = s && s.querySelector('.footer');
                  if (!f) return null;
                  const fr = f.getBoundingClientRect();
                  let worst = null;
                  // Se miran TODOS los descendientes, no solo las hojas: un <p> que
                  // contiene un <em> tiene hijos, y filtrar por hoja lo dejaba pasar
                  // -- que fue exactamente como este chequeo dio un falso OK.
                  for (const el of s.querySelectorAll('.body *')) {
                    const txt = (el.textContent || '').trim();
                    if (!txt) continue;
                    const r = el.getBoundingClientRect();
                    if (!r.width || !r.height) continue;
                    if (r.bottom > fr.top + 2 && r.top < fr.bottom
                        && r.right > fr.left && r.left < fr.right) {
                      const over = Math.round(r.bottom - fr.top);
                      if (!worst || over > worst.overlap) {
                        worst = { txt: txt.slice(0, 46), overlap: over };
                      }
                    }
                  }
                  return worst;
                }"""
            )
            if hit:
                problems.append(
                    f"[{sid}] el contenido se encima con el pie ({hit['overlap']}px): \"{hit['txt']}\""
                )

            # --- el grafico debe haber dibujado algo
            if sid in ("s-reveal", "s-rewind", "s-break"):
                pts = page.evaluate(
                    "document.querySelector('.slide.active .adv-line')?.getAttribute('d')?.length || 0"
                )
                if pts < 50:
                    problems.append(f"[{sid}] la linea del grafico no se dibujo (d={pts})")

            if sid == "s-board":
                rows = page.evaluate("document.querySelectorAll('.slide.active .board tbody tr').length")
                imgs = page.evaluate(
                    """() => [...document.querySelectorAll('.slide.active .board img')]
                            .filter(i => !i.complete || i.naturalWidth === 0).length"""
                )
                if rows != 10:
                    problems.append(f"[{sid}] el marcador tiene {rows} filas, se esperaban 10")
                if imgs:
                    problems.append(f"[{sid}] {imgs} retratos de campeon no cargaron")

            if sid == "s-map":
                dots = page.evaluate("document.querySelectorAll('.slide.active .rift-kill').length")
                if dots < 30:
                    problems.append(f"[{sid}] solo {dots} posiciones de asesinato en el mapa")

            out = SHOTS / f"{i:02d}-{sid}.png"
            page.locator("#stage").screenshot(path=str(out))
            print(f"  {i:02d} {sid:<12} -> {out.name}")

        browser.close()

    print("\n" + "=" * 70)
    if errors:
        print(f"ERRORES DE CONSOLA ({len(errors)}):")
        for e in dict.fromkeys(errors):
            print("  -", e)
    else:
        print("errores de consola: ninguno")

    if problems:
        print(f"\nPROBLEMAS ({len(problems)}):")
        for pr in problems:
            print("  -", pr)
    else:
        print("problemas de maquetacion: ninguno")

    (ROOT / "data" / "shoot_report.json").write_text(
        json.dumps({"errors": errors, "problems": problems}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
