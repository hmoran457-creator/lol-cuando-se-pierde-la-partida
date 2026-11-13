r"""Revisa la herramienta en Chromium (playwright).

    python LoL_Probabilidad/scripts/verificar.py [carpeta_de_capturas]

1. Paridad: en 500 estados al azar, la probabilidad y el rango que calcula la página (motor.js)
   son los mismos que calcula Python con los parámetros de modelo.json. La fórmula de Python ya
   se comparó contra el modelo de sklearn al exportar (exportar.py), así que esto cierra la
   cadena sklearn -> modelo.json -> página.
2. Coherencia: más asesinatos, torres o dragones propios nunca bajan la probabilidad, y del
   rival nunca la suben.
3. Sin errores de consola, y sin desbordes horizontales a 375 px (teléfono) ni a 1280 px.
4. Capturas para revisarlas a ojo (si se da una carpeta).
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

BASE = pathlib.Path(__file__).resolve().parent.parent
PAGINA = BASE / "probabilidad.html"
MODELO = BASE / "herramienta" / "modelo.json"


def p_python(spec, e):
    tt = (min(40, max(1, e["minuto"])) - 1) / 39
    recta = lambda p: p[0] + (p[1] - p[0]) * tt  # noqa: E731

    def x(nombre):
        if nombre.startswith("dif_"):
            c = nombre[4:]
            return e.get(f"{c}_p", 0) - e.get(f"{c}_r", 0)
        return e["v"] if nombre == "v" else e["oro_dif"] / 1000

    def prob(param):
        z = recta(param[0]) + sum(x(n) * recta(param[j + 1]) for j, n in enumerate(spec["variables"]))
        return 1 / (1 + np.exp(-z))

    ps = np.sort([prob(b) for b in spec["bootstrap"]])
    return prob(spec["param"]), float(np.quantile(ps, .025)), float(np.quantile(ps, .975))


def estados(n, rng):
    out = []
    for _ in range(n):
        e = {"minuto": int(rng.integers(1, 46))}
        for c, tope in [("asesinatos", 50), ("estructuras", 12), ("dragones", 5), ("atakhan", 1)]:
            e[f"{c}_p"], e[f"{c}_r"] = int(rng.integers(0, tope + 1)), int(rng.integers(0, tope + 1))
        e["baron_activo_p"], e["baron_activo_r"] = int(rng.integers(0, 2)), int(rng.integers(0, 2))
        e["v"] = float(rng.normal(0, 8))
        e["oro_dif"] = float(rng.normal(0, 4000))
        out.append(e)
    return out


def main() -> int:
    capturas = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
    modelo = json.loads(MODELO.read_text(encoding="utf-8"))
    rng = np.random.default_rng(20261010)
    casos = estados(500, rng)
    from playwright.sync_api import sync_playwright
    fallas = []
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pag = nav.new_page(viewport={"width": 1280, "height": 900})
        errores = []
        pag.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
        pag.on("pageerror", lambda e: errores.append(str(e)))
        pag.goto(PAGINA.as_uri())
        pag.wait_for_timeout(500)

        # 1. Paridad
        js = pag.evaluate("""(casos) => {
            const out = [];
            for (const e of casos) for (const modo of ["marcador", "marcador_oro"]) {
                const s = window.MODELOS[modo];
                out.push([window.Motor.prob(s, e), ...window.Motor.rango(s, e)]);
            }
            return out;
        }""", casos)
        py = [p_python(modelo[modo], e) for e in casos for modo in ("marcador", "marcador_oro")]
        dif = np.abs(np.array(js) - np.array(py)).max()
        print(f"paridad JS contra Python: diferencia máxima {dif:.1e} en {len(py)} cálculos")
        if dif > 1e-9:
            fallas.append("paridad")

        # 2. Coherencia (monotonía) en los dos modelos
        malos = pag.evaluate("""(casos) => {
            let malos = 0;
            const claves = ["asesinatos", "estructuras", "dragones", "atakhan", "baron_activo"];
            for (const e of casos) for (const modo of ["marcador", "marcador_oro"]) {
                const s = window.MODELOS[modo], p = window.Motor.prob(s, e);
                for (const c of claves) {
                    const a = Object.assign({}, e); a[c + "_p"] += 1;
                    const b = Object.assign({}, e); b[c + "_r"] += 1;
                    if (window.Motor.prob(s, a) < p - 1e-12 || window.Motor.prob(s, b) > p + 1e-12) malos++;
                }
            }
            return malos;
        }""", casos)
        print(f"coherencia: {malos} casos en que algo a favor baja la probabilidad (o en contra la sube)")
        if malos:
            fallas.append("coherencia")

        # 3. La interfaz responde: sumar un asesinato propio sube el número grande.
        antes = pag.inner_text("#prob-p")
        pag.click("button[aria-label='Sumar uno: asesinatos de mi equipo']")
        pag.wait_for_timeout(100)
        despues = pag.inner_text("#prob-p")
        print(f"interfaz: {antes} -> {despues} al sumar un asesinato propio")
        if not int(despues.split()[0]) > int(antes.split()[0]):
            fallas.append("interfaz")

        # 3b. Con el oro: la página convierte los dos totales en v y oro_dif como al entrenar.
        pag.click("#usar-oro")
        pag.fill("#oro-p", "30500")
        pag.fill("#oro-r", "28000")
        pag.wait_for_timeout(150)
        e = pag.evaluate("JSON.parse(decodeURIComponent(location.hash.slice(1)))")
        e.update({"v": 100 * (30500 - 28000) / 58500, "oro_dif": 2500})
        esperado = round(100 * p_python(modelo["marcador_oro"], e)[0])
        visto = int(pag.inner_text("#prob-p").split()[0])
        print(f"interfaz con oro: muestra {visto} %, Python da {esperado} %")
        if visto != esperado:
            fallas.append("interfaz con oro")
        pag.click("#usar-oro")

        for ancho, alto in [(1280, 900), (375, 812)]:
            pag.set_viewport_size({"width": ancho, "height": alto})
            pag.goto(PAGINA.as_uri() + "#")
            pag.wait_for_timeout(300)
            # Un estado de ejemplo: minuto 24, arriba en asesinatos y torres, el rival con barón.
            pag.evaluate("""() => {
                const e = {minuto: 24, asesinatos_p: 18, asesinatos_r: 14, estructuras_p: 5, estructuras_r: 3,
                           dragones_p: 2, dragones_r: 3, atakhan_p: 0, atakhan_r: 0,
                           baron_activo_p: 0, baron_activo_r: 1, usarOro: false};
                location.hash = encodeURIComponent(JSON.stringify(e));
            }""")
            pag.reload()
            pag.wait_for_timeout(400)
            ancho_doc = pag.evaluate("document.documentElement.scrollWidth")
            print(f"{ancho} px: ancho del documento {ancho_doc}")
            if ancho_doc > ancho:
                fallas.append(f"desborde a {ancho} px")
            if capturas:
                capturas.mkdir(parents=True, exist_ok=True)
                pag.screenshot(path=str(capturas / f"herramienta_{ancho}.png"), full_page=True)
        if capturas:
            pag.set_viewport_size({"width": 1280, "height": 900})
            pag.click("#usar-oro")
            pag.fill("#oro-p", "41200")
            pag.fill("#oro-r", "43900")
            pag.wait_for_timeout(300)
            pag.screenshot(path=str(capturas / "herramienta_oro.png"), full_page=False)
        print("errores de consola:", errores or "ninguno")
        if errores:
            fallas.append("consola")
        nav.close()
    print("TODO BIEN" if not fallas else f"FALLAS: {fallas}")
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main())
