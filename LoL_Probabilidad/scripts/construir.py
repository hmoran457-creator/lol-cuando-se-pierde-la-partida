r"""Construye la herramienta: LoL_Probabilidad/probabilidad.html, un solo archivo sin internet.

    python LoL_Probabilidad/scripts/exportar.py     # modelo.json (necesita los datos locales)
    python LoL_Probabilidad/scripts/construir.py    # la página (solo necesita modelo.json)

Incrusta en herramienta/plantilla.html el modelo (modelo.json), el motor y la interfaz (JS), la
fuente Archivo (la de las presentaciones) y la nota de cómo se hizo. Ninguna cifra de la nota
está escrita a mano: salen de modelo.json. Falla si queda alguna {{llave}} sin rellenar.
"""
from __future__ import annotations

import base64
import json
import math
import pathlib
import re

BASE = pathlib.Path(__file__).resolve().parent.parent
RAIZ = BASE.parent
HERR = BASE / "herramienta"
SALIDA = BASE / "probabilidad.html"
FUENTE = RAIZ / "LoL_PresentacionFinal" / "assets" / "fonts" / "archivo-2.woff2"


def mil(n: float) -> str:
    return f"{int(round(n)):,}"


def recta(p, t):
    tt = (min(40, max(1, t)) - 1) / 39
    return p[0] + (p[1] - p[0]) * tt


def puntos(beta: float) -> int:
    """Cuántos puntos mueve un logit de beta a una partida que va 50 / 50."""
    return round(100 * (1 / (1 + math.exp(-beta)) - .5))


def numeros(spec: dict) -> int:
    """Parámetros del modelo: dos por recta que cambia con el minuto, uno por coeficiente fijo."""
    return sum(1 if abs(a - b) < 1e-12 else 2 for a, b in spec["param"])


def nota(m: dict) -> str:
    meta, met = m["meta"], m["meta"]["metricas"]
    ref = met["referencias"]
    mc, mo = m["marcador"], m["marcador_oro"]
    idx = lambda spec, v: spec["variables"].index(v) + 1  # noqa: E731
    pm = lambda spec, v, t: puntos(recta(spec["param"][idx(spec, v)], t))  # noqa: E731
    cal = "".join(f"<tr><td>{100 * a:.0f} %</td><td>{100 * b:.0f} %</td></tr>"
                  for a, b in meta["calibracion"]["marcador"])
    fam, pr = met["familias"], met["prueba"]
    arb_m, arb_o = fam["arboles_marcador"], fam["arboles_oro"]
    return f"""
<p><strong>Qué es.</strong> Dos regresiones logísticas entrenadas con mis {mil(meta['partidas'])}
partidas clasificatorias (gané el {100 * meta['victorias']:.0f} %), una fila por partida y minuto.
<em>Sin el oro</em>, el modelo usa el minuto y las diferencias del marcador: asesinatos, torres e
inhibidores, dragones, Atakhan y la mejora del barón. El efecto de los asesinatos y de las torres
cambia con el minuto; el de lo demás es fijo. <em>Con el oro</em>, el modelo usa además la
diferencia de oro, en oro y en proporción del oro total; esa proporción es lo único cuyo efecto
cambia con el minuto. Los asesinatos cuentan como en el marcador del juego: sin las ejecuciones
(muertes ante una torre o los súbditos).</p>

<p><strong>Qué pesa</strong> (puntos que mueve en una partida que va pareja):
un asesinato, {pm(mc, 'dif_asesinatos', 5)} puntos al minuto 5 y {pm(mc, 'dif_asesinatos', 30)}
al 30; una torre, {pm(mc, 'dif_estructuras', 5)} y {pm(mc, 'dif_estructuras', 30)}; un dragón,
{pm(mc, 'dif_dragones', 15)} a cualquier minuto; la mejora del barón,
{pm(mc, 'dif_baron_activo', 25)}. Cuando se conoce el oro, los asesinatos y las torres casi dejan
de pesar (su valor ya está en el oro), pero los dragones no ({pm(mo, 'dif_dragones', 15)} puntos):
sus mejoras no se ven en el oro.</p>

<p><strong>Cómo se eligió.</strong> Se compararon tres familias de modelos con las mismas
reglas: regresiones logísticas con efectos que cambian con el minuto, árboles de decisión
combinados (<em>gradient boosting</em> y bosques aleatorios) y otras (redes neuronales pequeñas,
un modelo por minuto, vecinos cercanos). La medida es la pérdida logarítmica (menor es mejor) en
validación cruzada que nunca mezcla minutos de una misma partida entre el entrenamiento y la
prueba. Se eligió el modelo más simple dentro del margen de error del mejor.</p>
<table>
<tr><th>Modelo, sin el oro</th><th>Pérdida</th></tr>
<tr><td>No saber nada (siempre la proporción de victorias)</td><td>{ref['base_proporcion']:.3f}</td></tr>
<tr><td>Logística simple sobre las diferencias</td><td>{ref['base_marcador_dif']:.3f}</td></tr>
<tr><td>Mejor árbol combinado</td><td>{arb_m['perdida_log']:.3f}</td></tr>
<tr><td>Mejor de las otras familias (red neuronal, un modelo por minuto…)</td><td>{fam['otros_marcador']['perdida_log']:.3f}</td></tr>
<tr><td><strong>Elegido</strong> ({numeros(mc)} números)</td><td><strong>{met['marcador']['cv']['perdida_log']:.3f}</strong></td></tr>
<tr><th>Con el oro</th><th></th></tr>
<tr><td>Solo el oro</td><td>{ref['base_oro_interaccion']:.3f}</td></tr>
<tr><td>Mejor árbol combinado</td><td>{arb_o['perdida_log']:.3f}</td></tr>
<tr><td>Mejor de las otras familias</td><td>{fam['otros_oro']['perdida_log']:.3f}</td></tr>
<tr><td><strong>Elegido</strong> ({numeros(mo)} números)</td><td><strong>{met['marcador_oro']['cv']['perdida_log']:.3f}</strong></td></tr>
</table>
<p>Ningún árbol ni red superó a la logística por más que el margen de error: con unas mil
partidas no hay datos para aprender más que eso. Al final se midieron los finalistas con las
partidas de mayo de 2026 en adelante, que no se usaron para elegir. Ahí la pérdida subió para
todos: el elegido marcó {met['marcador']['prueba']['perdida_log']:.3f} sin el oro y
{met['marcador_oro']['prueba']['perdida_log']:.3f} con el oro; el mejor árbol,
{pr[arb_m['nombre']]:.3f} y {pr[arb_o['nombre']]:.3f}. Con solo
{meta['partidas_prueba']} partidas esas diferencias no son significativas, pero la calibración en esos meses fue
peor (error de {100 * met['marcador']['prueba']['ece']:.0f} puntos contra
{100 * met['marcador']['cv']['ece']:.0f} en la validación): en partidas recientes, toma la cifra
como aproximada.</p>

<p><strong>Calibración.</strong> Cuando el modelo dice cierto porcentaje, ¿gané ese porcentaje?
Los minutos de partida, agrupados en diez grupos según lo que predijo (sin el oro, fuera de
muestra):</p>
<table><tr><th>Predijo</th><th>Gané</th></tr>{cal}</table>

<p><strong>El rango</strong> es cuánto cambiaría la estimación si el modelo se hubiera entrenado
con otra muestra de mis partidas (95 % de 200 remuestreos). No es la incertidumbre del juego:
esa ya está en la probabilidad.</p>

<p><strong>Límites.</strong> Describe mis partidas, no las de cualquier jugador; jugué casi
siempre de tirador. Son asociaciones: un dragón «vale» lo que valieron mis partidas con un dragón
más, no lo que causa. Los parches cambian el juego. Y más allá del minuto 40 los efectos dejan de
cambiar: hay pocas partidas tan largas.</p>
"""


def main() -> int:
    m = json.loads((HERR / "modelo.json").read_text(encoding="utf-8"))
    html = (HERR / "plantilla.html").read_text(encoding="utf-8")
    valores = {
        "fuente": base64.b64encode(FUENTE.read_bytes()).decode("ascii"),
        "partidas": mil(m["meta"]["partidas"]),
        "minuto_max": str(m["meta"]["minuto_max"]),
        "modelos": json.dumps(m, ensure_ascii=False, separators=(",", ":")),
        "motor": (HERR / "motor.js").read_text(encoding="utf-8"),
        "interfaz": (HERR / "interfaz.js").read_text(encoding="utf-8"),
        "nota": nota(m),
    }
    html = re.sub(r"\{\{(\w+)\}\}", lambda g: valores[g.group(1)], html)
    sobran = re.findall(r"\{\{\w+\}\}", html)
    assert not sobran, f"llaves sin rellenar: {sobran}"
    SALIDA.write_text(html, encoding="utf-8")
    print(f"{SALIDA.name}: {SALIDA.stat().st_size / 1e3:.0f} kB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
