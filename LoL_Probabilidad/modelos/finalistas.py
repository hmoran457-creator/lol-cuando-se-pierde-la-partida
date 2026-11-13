r"""Elección final del modelo de probabilidad de ganar.

    python LoL_Probabilidad/modelos/finalistas.py variantes   # 1. variantes legibles (desarrollo)
    python LoL_Probabilidad/modelos/finalistas.py prueba      # 2. prueba temporal, UNA vez

Regla fijada antes de ver la prueba temporal: en cada modo se elige el modelo más simple cuya
pérdida en validación cruzada queda dentro del intervalo del mejor (comparar(), bootstrap por
partida). La prueba temporal (partidas de 2026-05 en adelante) solo confirma que el elegido no
se degrada fuera de la época en que se ajustó; no se usa para escoger entre finalistas.

Las variantes "legibles" existen por la herramienta: en glm_m_lineal_t el número de barones ya
sin mejora activa tiene coeficiente negativo (su valor ya está en torres y oro), así que sumar
un barón en la página BAJARÍA la probabilidad. Se prueba quitar ese término (el barón entra
solo por su mejora activa) y quitar además heraldo y larvas, que no aportan.
"""
from __future__ import annotations

import json
import pathlib
import sys

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "scripts"))
sys.path.insert(0, str(AQUI))
from evaluar import MARCADOR, MARCADOR_ORO, RESULTADOS, comparar, evaluar, prueba_final  # noqa: E402
import arboles  # noqa: E402
import base  # noqa: E402
import glm  # noqa: E402
import otros  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import FunctionTransformer, StandardScaler  # noqa: E402

SIN_BARON = [d for d in glm.DIF if d != "dif_barones"]
SIN_BARON_HL = [d for d in SIN_BARON if d not in ("dif_heraldos", "dif_larvas")]

VARIANTES = {
    "fin_m_sin_baron": (glm.glm(C=0.03, tv=SIN_BARON[:2], fijas=SIN_BARON[2:], forma="lineal"), MARCADOR,
                        "glm_m_lineal_t sin el conteo de barones (el barón entra por su mejora activa)"),
    "fin_m_sin_baron_hl": (glm.glm(C=0.03, tv=SIN_BARON_HL[:2], fijas=SIN_BARON_HL[2:], forma="lineal"), MARCADOR,
                           "además sin heraldo ni larvas"),
    "fin_mo_sin_baron": (glm.glm(C=0.1, tv=["v"], fijas=["oro_dif"] + SIN_BARON, forma="lineal"), MARCADOR_ORO,
                         "glm_mo_lineal sin el conteo de barones"),
    "fin_mo_sin_baron_hl": (glm.glm(C=0.1, tv=["v"], fijas=["oro_dif"] + SIN_BARON_HL, forma="lineal"), MARCADOR_ORO,
                            "además sin heraldo ni larvas"),
}


# Segunda ronda: ¿agrega algo el nivel (visible con Tab)? Regla fijada antes de correrla: el
# nivel entra a la herramienta solo si mejora al elegido con un intervalo que excluye el cero.
# La experiencia (xp) no se ve en la partida: se prueba solo como techo de lo que se pierde.
NIVEL = ["nivel_p", "nivel_r"]
XP = ["xp_p", "xp_r"]
TV_M, FIJAS_M = SIN_BARON_HL[:2], SIN_BARON_HL[2:]
VARIANTES_NIVEL = {
    "nv_m_fijo": (glm.glm(C=0.03, tv=TV_M, fijas=FIJAS_M + ["dif_nivel"], forma="lineal"), MARCADOR + NIVEL,
                  "elegido sin oro + diferencia de niveles con efecto fijo"),
    "nv_m_tv": (glm.glm(C=0.03, tv=TV_M + ["dif_nivel"], fijas=FIJAS_M, forma="lineal"), MARCADOR + NIVEL,
                "elegido sin oro + diferencia de niveles con efecto que cambia con el minuto"),
    "nv_m_xp_tv": (glm.glm(C=0.03, tv=TV_M + ["dif_xp"], fijas=FIJAS_M, forma="lineal"), MARCADOR + XP,
                   "techo: diferencia de experiencia (no visible) con efecto que cambia con el minuto"),
    "nv_mo_fijo": (glm.glm(C=0.1, tv=["v"], fijas=["oro_dif"] + SIN_BARON_HL + ["dif_nivel"], forma="lineal"),
                   MARCADOR_ORO + NIVEL, "elegido con oro + diferencia de niveles con efecto fijo"),
    "nv_mo_tv": (glm.glm(C=0.1, tv=["v", "dif_nivel"], fijas=["oro_dif"] + SIN_BARON_HL, forma="lineal"),
                 MARCADOR_ORO + NIVEL, "elegido con oro + diferencia de niveles que cambia con el minuto"),
}
# Con el nivel, Atakhan y la mejora del barón quedan con coeficientes negativos (sin significancia):
# su valor ya está en niveles y torres, y en la página "tomar Atakhan" bajaría la probabilidad.
# Variante legible sin ellos; entra si no pierde contra la versión completa (intervalo con el 0).
LEGIBLES = ["dif_dragones", "dif_nivel"]
VARIANTES_NIVEL.update({
    "nv2_m": (glm.glm(C=0.03, tv=TV_M, fijas=LEGIBLES, forma="lineal"), MARCADOR + NIVEL,
              "nv_m_fijo sin Atakhan ni mejora del barón"),
    "nv2_mo": (glm.glm(C=0.1, tv=["v"], fijas=["oro_dif"] + TV_M + LEGIBLES, forma="lineal"),
               MARCADOR_ORO + NIVEL, "nv_mo_fijo sin Atakhan ni mejora del barón"),
})
VARIANTES.update(VARIANTES_NIVEL)


def nivel():
    for n, (f, cols, notas) in VARIANTES_NIVEL.items():
        evaluar(n, f, cols, notas)
    for a, b in [("fin_m_sin_baron_hl", "nv_m_fijo"), ("fin_m_sin_baron_hl", "nv_m_tv"),
                 ("fin_m_sin_baron_hl", "nv_m_xp_tv"), ("nv_m_tv", "nv_m_xp_tv"),
                 ("fin_mo_sin_baron_hl", "nv_mo_fijo"), ("fin_mo_sin_baron_hl", "nv_mo_tv"),
                 ("nv_m_fijo", "nv2_m"), ("fin_m_sin_baron_hl", "nv2_m"),
                 ("nv_mo_fijo", "nv2_mo"), ("fin_mo_sin_baron_hl", "nv2_mo")]:
        c = comparar(a, b)
        print(f"  {b} − {a}: {c['b_menos_a']:+.4f} [{c['ic95'][0]:+.4f}, {c['ic95'][1]:+.4f}]")


def fabrica(nombre):
    """La fábrica y las columnas de cualquier modelo, venga del script que venga."""
    if nombre in VARIANTES:
        return VARIANTES[nombre][:2]
    if nombre in glm.EXPERIMENTOS:
        return glm.EXPERIMENTOS[nombre][:2]
    if nombre in arboles.EXPERIMENTOS:
        return arboles.EXPERIMENTOS[nombre][:2]
    for n, f, cols, *_ in otros.EXPERIMENTOS:
        if n == nombre:
            return f, cols
    bases = {
        "base_proporcion": (base.Proporcion, ["minuto"]),
        "base_marcador_dif": (lambda: make_pipeline(FunctionTransformer(base.diferencias), StandardScaler(),
                                                    LogisticRegression(max_iter=2000)), MARCADOR),
    }
    return bases[nombre]


def variantes():
    for n, (f, cols, notas) in VARIANTES.items():
        evaluar(n, f, cols, notas)
    for a, b in [("glm_m_lineal_t", "fin_m_sin_baron"), ("glm_m_lineal_t", "fin_m_sin_baron_hl"),
                 ("glm_m_tv1_c001", "fin_m_sin_baron_hl"),
                 ("glm_mo_lineal", "fin_mo_sin_baron"), ("glm_mo_lineal", "fin_mo_sin_baron_hl"),
                 ("glm_mo_min_c001", "fin_mo_sin_baron_hl")]:
        c = comparar(a, b)
        print(f"  {b} − {a}: {c['b_menos_a']:+.4f} [{c['ic95'][0]:+.4f}, {c['ic95'][1]:+.4f}]")


# Finalistas para la prueba temporal: el elegido de cada modo, las referencias y el mejor modelo
# de cada familia en validación cruzada (se buscan en resultados/, no se escriben a mano).
# Elegidos tras la segunda ronda: con el nivel, y sin Atakhan ni la mejora del barón (variante
# legible, empata con la completa). Los dos mejoran a los de la primera ronda con intervalos que
# excluyen el cero; esos quedan como referencia en la prueba temporal y en la nota de la página.
ELEGIDOS = {"marcador": "nv2_m", "marcador_oro": "nv2_mo"}
ANTERIORES = {"marcador": "fin_m_sin_baron_hl", "marcador_oro": "fin_mo_sin_baron_hl"}


def finalistas():
    todos = [json.loads(f.read_text(encoding="utf-8")) for f in RESULTADOS.glob("*.json")
             if f.name != "prueba_temporal.json"]
    out = {}
    for modo, con_oro in [("marcador", False), ("marcador_oro", True)]:
        nombres = ["base_proporcion", "base_marcador_dif"] if not con_oro else []
        nombres += [ANTERIORES[modo], ELEGIDOS[modo]]
        for pre in ("glm_", "otr_", "arb_"):
            cands = [r for r in todos if r["nombre"].startswith(pre) and "asesinatos_p" in r["columnas"]
                     and ("v" in r["columnas"]) == con_oro]
            nombres.append(min(cands, key=lambda r: r["perdida_log"])["nombre"])
        out[modo] = nombres
    return out


def prueba():
    salida = {}
    for modo, nombres in finalistas().items():
        print(f"--- {modo}")
        for n in nombres:
            f, cols = fabrica(n)
            salida[n] = prueba_final(n, f, cols)
    (RESULTADOS / "prueba_temporal.json").write_text(json.dumps(salida, indent=1, ensure_ascii=False),
                                                     encoding="utf-8")


if __name__ == "__main__":
    {"variantes": variantes, "nivel": nivel, "prueba": prueba}[sys.argv[1]]()
