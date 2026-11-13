r"""Familia logística (GLM / GAM sencillo) para la probabilidad de ganar en el minuto t.

    python LoL_Probabilidad/modelos/glm.py              # todos los experimentos + comparaciones
    python LoL_Probabilidad/modelos/glm.py glm_m_tv1    # solo los nombrados
    python LoL_Probabilidad/modelos/glm.py --comparar   # solo la tabla de comparaciones
    python LoL_Probabilidad/modelos/glm.py --exportar   # coeficientes de los recomendados

Idea: logit P(gano) = b0 + f(t) + sum_j x_j * beta_j(t), donde t es el minuto y cada beta_j(t)
es un coeficiente que cambia con el minuto. f y beta_j se escriben en una base de splines del
minuto con nudos FIJOS (no dependen de los datos de cada pliegue):

  * grado 1: funciones "sombrero" (interpolación lineal entre nudos). En JS basta con
    np.interp: el coeficiente en t es la interpolación lineal de los coeficientes en los nudos.
  * grado 3: B-splines cúbicos (SplineTransformer con esos nudos); el minuto se recorta al
    rango de los nudos antes de la base, así que no hay extrapolación que portar.

Cada variable x se divide entre su desviación estándar (calculada al ajustar) UNA vez, antes de
multiplicarla por la base; las columnas x*B_k(t) ya no se reescalan. Con forma "efecto+desvio"
entra x sola más x*B_k(t): la penalización L2 encoge hacia un coeficiente constante en el tiempo.
Con forma "rampa" la base son rampas R_k(t) (sumas acumuladas de los sombreros): la misma recta
por tramos, pero la L2 cae sobre los saltos entre nudos vecinos y suaviza la curva. Con forma
"lineal" no hay nudos: minuto y x*minuto (minuto recortado a [1, 40]).

Unidades de exportación (las de variables()): diferencias en conteos, v en %, oro_dif en miles
de oro. exportar() reescribe cualquier modelo de grado 1 como tablas de coeficientes en los
nudos, y verifica que la interpolación de esas tablas reproduce el pipeline.

Ninguna llamada a la prueba temporal aquí: eso lo hace el autor con los finalistas.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from evaluar import MARCADOR, MARCADOR_ORO, ORO, RESULTADOS, cargar, comparar, evaluar  # noqa: E402

NUDOS = (1, 5, 10, 15, 20, 25, 30, 40)
CONTEOS = ["asesinatos", "estructuras", "dragones", "larvas", "heraldos", "barones",
           "baron_activo", "atakhan"]


# ---------------------------------------------------------------- variables derivadas
def variables(X: pd.DataFrame, lista: list[str]) -> dict[str, np.ndarray]:
    """Construye las variables base pedidas (sin escalar) a partir de las columnas crudas."""
    g = lambda c: X[c].to_numpy(dtype=float)  # noqa: E731
    out = {}
    for nombre in lista:
        if nombre.startswith("dif_"):                 # propio − rival
            c = nombre[4:]
            out[nombre] = g(f"{c}_p") - g(f"{c}_r")
        elif nombre.startswith("raiz_"):              # sqrt(propio) − sqrt(rival)
            c = nombre[5:]
            out[nombre] = np.sqrt(g(f"{c}_p")) - np.sqrt(g(f"{c}_r"))
        elif nombre.startswith("p_") or nombre.startswith("r_"):   # conteo de un solo lado
            out[nombre] = g(f"{nombre[2:]}_{nombre[0]}")
        elif nombre == "ases_rel":                    # diferencia de asesinatos / total
            out[nombre] = (g("asesinatos_p") - g("asesinatos_r")) / (g("asesinatos_p") + g("asesinatos_r") + 10)
        elif nombre == "ases_tot":                    # ritmo de la partida
            out[nombre] = g("asesinatos_p") + g("asesinatos_r")
        elif nombre == "alma":                        # 4+ dragones ~ alma del dragón
            out[nombre] = (g("dragones_p") >= 4).astype(float) - (g("dragones_r") >= 4).astype(float)
        elif nombre == "punto_alma":                  # 3+ dragones: a uno del alma
            out[nombre] = (g("dragones_p") >= 3).astype(float) - (g("dragones_r") >= 3).astype(float)
        elif nombre == "v":
            out[nombre] = g("v")
        elif nombre == "v3":                          # saturación del oro relativo
            out[nombre] = g("v") ** 3 / 100
        elif nombre == "oro_dif":
            out[nombre] = g("oro_dif") / 1000
        elif nombre == "azul":
            out[nombre] = g("azul") * 2 - 1
        else:
            raise KeyError(nombre)
    return out


def base_minuto(t: np.ndarray, grado: int, spl: SplineTransformer | None) -> np.ndarray:
    t = np.clip(t, NUDOS[0], NUDOS[-1])
    if grado == 1:
        eye = np.eye(len(NUDOS))
        return np.column_stack([np.interp(t, NUDOS, eye[k]) for k in range(len(NUDOS))])
    return spl.transform(t.reshape(-1, 1))


class Disenio(BaseEstimator, TransformerMixin):
    """Matriz del GLM: base del minuto + variables con coeficiente variable en el tiempo.

    tv: variables con coeficiente que cambia con el minuto.  fijas: coeficiente constante.
    forma: "completo" (solo x*B_k), "efecto+desvio" (x + x*B_k), "rampa" (x + x*R_k, R_k
    rampas entre nudos vecinos) o "lineal" (x + x*minuto, sin nudos).
    """

    def __init__(self, tv=(), fijas=(), grado=1, forma="efecto+desvio"):
        self.tv, self.fijas, self.grado, self.forma = tv, fijas, grado, forma

    def fit(self, X, y=None):
        v = variables(X, list(self.tv) + list(self.fijas))
        self.escala_ = {k: (float(np.std(a)) or 1.0) for k, a in v.items()}
        self.spl_ = None
        if self.grado != 1:
            self.spl_ = SplineTransformer(knots=np.array(NUDOS, dtype=float).reshape(-1, 1),
                                          degree=self.grado, extrapolation="constant")
            self.spl_.fit(np.array(NUDOS, dtype=float).reshape(-1, 1))
        return self

    def transform(self, X):
        v = variables(X, list(self.tv) + list(self.fijas))
        return self.matriz(v, X["minuto"].to_numpy(dtype=float))

    def matriz(self, v: dict, t: np.ndarray) -> np.ndarray:
        if self.forma == "rampa":
            # Rampas: R_k(t) = recorte((t − n_{k−1}) / (n_k − n_{k−1}), 0, 1), k = 1..K−1.
            # beta(t) = c + sum_k delta_k R_k(t) es la misma recta por tramos que con
            # sombreros, pero la L2 cae sobre los saltos delta_k entre nudos vecinos
            # (penalización de primeras diferencias): encoge hacia curvas suaves.
            n = np.array(NUDOS, dtype=float)
            tc = np.clip(t, n[0], n[-1])
            B = np.column_stack([np.clip((tc - n[k - 1]) / (n[k] - n[k - 1]), 0, 1) for k in range(1, len(n))])
        elif self.forma == "lineal":      # sin nudos: minuto recortado, x y x*minuto
            B = (np.clip(t, NUDOS[0], NUDOS[-1]) / NUDOS[-1])[:, None]
        else:
            B = base_minuto(t, self.grado, self.spl_)
        cols = [B]
        for k in self.tv:
            x = v[k] / self.escala_[k]
            if self.forma in ("efecto+desvio", "rampa", "lineal"):
                cols.append(x[:, None])
            cols.append(x[:, None] * B)
        for k in self.fijas:
            cols.append((v[k] / self.escala_[k])[:, None])
        return np.hstack(cols)


def glm(C=1.0, **kw):
    return lambda: make_pipeline(Disenio(**kw), LogisticRegression(C=C, max_iter=5000))


# ---------------------------------------------------------------- experimentos
DIF = [f"dif_{c}" for c in CONTEOS]
ORO_V = ["v", "oro_dif"]

EXPERIMENTOS = {
    # --- MARCADOR
    "glm_m_lineal": (glm(tv=(), fijas=DIF), MARCADOR,
                     "diferencias con coeficiente fijo + base del minuto (grado 1)"),
    "glm_m_tv1_completo": (glm(tv=DIF, forma="completo"), MARCADOR,
                           "diferencias x B(t) grado 1, solo interacciones"),
    "glm_m_tv1": (glm(tv=DIF), MARCADOR, "diferencias x B(t) grado 1, efecto + desvío"),
    "glm_m_tv3": (glm(tv=DIF, grado=3), MARCADOR, "diferencias x B(t) cúbico, efecto + desvío"),
    "glm_m_alma": (glm(tv=DIF + ["alma", "punto_alma"]), MARCADOR,
                   "tv1 + indicadores 4+ y 3+ dragones (propio − rival)"),
    "glm_m_rel": (glm(tv=DIF + ["ases_rel"]), MARCADOR,
                  "tv1 + asesinatos relativos al total (dif / (total + 10))"),
    "glm_m_raiz": (glm(tv=[d.replace("dif_", "raiz_") if d in ("dif_asesinatos", "dif_estructuras") else d
                           for d in DIF]), MARCADOR,
                   "tv1 con sqrt(propio) − sqrt(rival) para asesinatos y estructuras"),
    "glm_m_sep": (glm(tv=[f"{s}_{c}" for c in CONTEOS for s in ("p", "r")]), MARCADOR,
                  "tv1 con conteos propios y rivales por separado"),
    "glm_m_tv1_c01": (glm(C=0.1, tv=DIF), MARCADOR, "tv1 con C = 0.1"),
    "glm_m_tv1_c001": (glm(C=0.01, tv=DIF), MARCADOR, "tv1 con C = 0.01"),
    "glm_m_tv_min": (glm(tv=DIF[:2], fijas=DIF[2:]), MARCADOR,
                     "solo asesinatos y estructuras cambian con el minuto; el resto fijo"),
    "glm_m_tv_min_c003": (glm(C=0.03, tv=DIF[:2], fijas=DIF[2:]), MARCADOR, "tv_min con C = 0.03"),
    # --- ORO
    "glm_o_v": (glm(tv=["v"]), ORO, "v x B(t) grado 1 + base del minuto"),
    "glm_o_v_dif": (glm(tv=ORO_V), ORO, "v y oro_dif, ambos x B(t)"),
    "glm_o_v3": (glm(tv=ORO_V + ["v3"]), ORO, "v, oro_dif y v^3 (saturación), todos x B(t)"),
    # --- MARCADOR + ORO
    "glm_mo_tv_c01": (glm(C=0.1, tv=DIF + ORO_V), MARCADOR_ORO, "diferencias del marcador, v y oro_dif x B(t); C = 0.1"),
    "glm_mo_tv_c001": (glm(C=0.01, tv=DIF + ORO_V), MARCADOR_ORO, "igual con C = 0.01"),
    "glm_mo_min": (glm(C=0.1, tv=ORO_V + DIF[:2], fijas=DIF[2:]), MARCADOR_ORO,
                   "v, oro_dif, asesinatos y estructuras x B(t); resto del marcador fijo; C = 0.1"),
    "glm_mo_min_c001": (glm(C=0.01, tv=ORO_V + DIF[:2], fijas=DIF[2:]), MARCADOR_ORO, "mo_min con C = 0.01"),
    "glm_mo_vtv": (glm(C=0.1, tv=["v"], fijas=["oro_dif"] + DIF), MARCADOR_ORO,
                   "solo v cambia con el minuto; oro_dif y marcador con coeficiente fijo; C = 0.1"),
    "glm_mo_min_azul": (glm(C=0.1, tv=ORO_V + DIF[:2], fijas=DIF[2:] + ["azul"]), MARCADOR_ORO + ["azul"],
                        "mo_min + lado azul"),
    # --- rampas: misma recta por tramos, pero la L2 suaviza (primeras diferencias entre nudos)
    "glm_m_rampa": (glm(C=0.03, tv=DIF[:2], fijas=DIF[2:], forma="rampa"), MARCADOR,
                    "tv_min_c003 con rampas (penaliza saltos entre nudos)"),
    "glm_mo_rampa": (glm(C=0.1, tv=["v"], fijas=["oro_dif"] + DIF, forma="rampa"), MARCADOR_ORO,
                     "mo_vtv con rampas"),
    "glm_o_rampa": (glm(C=0.1, tv=["v"], forma="rampa"), ORO, "o_v con rampas, C = 0.1"),
    "glm_mo_lineal": (glm(C=0.1, tv=["v"], fijas=["oro_dif"] + DIF, forma="lineal"), MARCADOR_ORO,
                      "sin nudos: minuto, v, v x minuto, oro_dif y las 8 diferencias fijas; C = 0.1"),
    "glm_m_lineal_t": (glm(C=0.03, tv=DIF[:2], fijas=DIF[2:], forma="lineal"), MARCADOR,
                       "sin nudos: minuto, asesinatos y estructuras con x minuto, resto fijo; C = 0.03"),
}


def correr(nombres):
    for n in nombres:
        fab, cols, notas = EXPERIMENTOS[n]
        r = evaluar(n, fab, cols, notas)
        print("    tramos:", {k: round(x, 3) for k, x in r["por_tramo"].items()})


def referencia(columnas):
    return "base_marcador_dif" if "v" not in columnas else "base_oro_interaccion"


def tabla_comparar():
    for n, (_, cols, _) in EXPERIMENTOS.items():
        f = RESULTADOS / f"{n}.json"
        if not f.exists():
            continue
        r = json.loads(f.read_text(encoding="utf-8"))
        ref = referencia(cols)
        c = comparar(ref, n)
        print(f"{n:<28} {r['perdida_log']:.4f}±{r['perdida_log_ee']:.4f} brier {r['brier']:.4f} "
              f"auc {r['auc']:.4f} ece {r['ece']:.4f} | vs {ref}: {c['b_menos_a']:+.4f} "
              f"[{c['ic95'][0]:+.4f}, {c['ic95'][1]:+.4f}]")


# Recomendados: el más simple dentro del IC del mejor de su conjunto.
# ORO: ningún GLM supera a base_oro_interaccion (3 coeficientes); ese es el recomendado.
RECOMENDADOS = {"MARCADOR": "glm_m_lineal_t", "MARCADOR_ORO": "glm_mo_lineal", "ORO": "base_oro_interaccion"}
# Pares (simple, complejo) del mismo conjunto para la regla "el más simple dentro del IC".
PARES = [("glm_m_lineal_t", "glm_m_rampa"), ("glm_m_lineal_t", "glm_m_tv1_c001"),
         ("glm_mo_lineal", "glm_mo_rampa"), ("glm_mo_lineal", "glm_mo_min_c001"),
         ("base_oro_interaccion", "glm_o_rampa"), ("base_oro_interaccion", "glm_o_v_dif")]
EXPORTAR = ["glm_m_lineal_t", "glm_m_rampa", "glm_mo_lineal", "glm_mo_rampa", "glm_o_rampa"]


def dentro_del_conjunto():
    """comparar(simple, complejo): negativo = el complejo es mejor."""
    for simple, complejo in PARES:
        c = comparar(simple, complejo)
        print(f"{complejo} − {simple}: {c['b_menos_a']:+.4f} "
              f"[{c['ic95'][0]:+.4f}, {c['ic95'][1]:+.4f}]")


def informe():
    tabla_comparar()
    dentro_del_conjunto()
    for n in list(RECOMENDADOS.values()) + ["glm_m_rampa", "glm_mo_rampa", "base_marcador_dif"]:
        calibracion(n)


def calibracion(nombre):
    """Observado vs predicho promedio por tramo de minutos (solo agregados)."""
    d, _ = cargar()
    p = pd.read_parquet(RESULTADOS.parent / "datos" / "oof" / f"{nombre}.parquet")["p"].to_numpy()
    tramo = pd.cut(d["minuto"], [0, 5, 10, 15, 20, 25, 30, 99])
    t = pd.DataFrame({"obs": d["gane"], "pred": p, "tramo": tramo}).groupby("tramo", observed=True).mean()
    print(f"  calibración {nombre}: " + "  ".join(
        f"{str(i)}: {r.obs:.3f}/{r.pred:.3f}" for i, r in t.iterrows()))


def exportar(nombre):
    """Ajusta con todo el desarrollo y escribe el modelo como tablas en los nudos (grado 1).

    Como la base de grado 1 suma 1 en cada minuto, logit = interp(t, NUDOS, a0)
    + sum_j x_j * interp(t, NUDOS, a_j) (coeficiente fijo = tabla constante), con x_j en sus
    unidades originales (variables() sin escalar). t se recorta a [NUDOS[0], NUDOS[-1]].
    """
    fab, cols, _ = EXPERIMENTOS[nombre]
    d, _ = cargar()
    modelo = fab().fit(d[cols], d["gane"].to_numpy())
    dis, lr = modelo[0], modelo[-1]
    assert dis.grado == 1
    K, t = len(NUDOS), np.array(NUDOS, dtype=float)
    nombres = list(dis.tv) + list(dis.fijas)
    cero = {k: np.zeros(K) for k in nombres}
    logit = lambda v: dis.matriz(v, t) @ lr.coef_[0] + lr.intercept_[0]  # noqa: E731
    tablas = {"(minuto)": logit(cero)}
    for k in nombres:   # efecto de una unidad de x_k en cada nudo (el modelo es lineal en x)
        tablas[k] = logit({**cero, k: np.ones(K)}) - tablas["(minuto)"]
    # Verificación: la fórmula de tablas + interpolación reproduce el pipeline en los datos.
    v = variables(d[cols], nombres)
    tt = np.clip(d["minuto"].to_numpy(dtype=float), t[0], t[-1])
    z = np.interp(tt, t, tablas["(minuto)"]) + sum(v[k] * np.interp(tt, t, tablas[k]) for k in nombres)
    p_pipe = modelo.predict_proba(d[cols])[:, 1]
    print(f"  máx |p_tablas − p_pipeline| = {np.abs(1 / (1 + np.exp(-z)) - p_pipe).max():.2e}")
    por_curva = 2 if dis.forma == "lineal" else K      # recta: 2 números; tabla: K
    n_par = por_curva * (1 + len(dis.tv)) + len(dis.fijas)
    print(f"\n{nombre}: {n_par} números (tablas en los nudos {NUDOS}; fijas = una sola cifra)")
    for k, a in tablas.items():
        print(f"  {k:<18}" + " ".join(f"{x:+8.4f}" for x in (a if k in dis.tv or k == '(minuto)' else a[:1])))


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["--comparar"]:
        informe()
    elif args == ["--exportar"]:
        for n in EXPORTAR:
            exportar(n)
    elif args:
        correr(args)
    else:
        correr(list(EXPERIMENTOS))
        informe()
        for n in EXPORTAR:
            exportar(n)
