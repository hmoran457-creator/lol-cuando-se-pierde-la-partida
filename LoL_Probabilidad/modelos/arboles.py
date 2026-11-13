r"""Modelos de árboles (ensambles) para la probabilidad de ganar en el minuto t.

    python LoL_Probabilidad/modelos/arboles.py                 # todos los experimentos
    python LoL_Probabilidad/modelos/arboles.py arb_x arb_y     # solo esos
    python LoL_Probabilidad/modelos/arboles.py --comparar      # bootstrap contra la base
    python LoL_Probabilidad/modelos/arboles.py --diag arb_x    # monotonía, importancia, tamaño

Familias: HistGradientBoosting (con y sin restricciones monótonas), GradientBoosting,
RandomForest y ExtraTrees. La ingeniería de variables (diferencias propio − rival) va dentro
del estimador. Restricción monótona: más conteos propios (o más oro a favor) nunca bajan la
probabilidad; más conteos del rival nunca la suben; el minuto queda libre.

Notas:
* early_stopping=False en todos los HGB: su validación interna separa filas, no partidas, y
  filtraría minutos de la misma partida. El número de iteraciones se fija a mano.
* min_samples_leaf está en filas; una partida aporta ~30 filas, así que 300 filas son ~10
  partidas como mínimo por hoja.
"""
from __future__ import annotations

import json
import pathlib
import sys
from functools import partial

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import (ExtraTreesClassifier, GradientBoostingClassifier,
                              HistGradientBoostingClassifier, RandomForestClassifier)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from evaluar import (MARCADOR, MARCADOR_ORO, OOF, ORO, RESULTADOS, SEMILLA,  # noqa: E402
                     TRAMOS, cargar, comparar, evaluar, pliegues)

SEM = SEMILLA % (2**31)


# ---------------------------------------------------------------- representaciones
def crudo(X: pd.DataFrame) -> pd.DataFrame:
    return X.copy()


def diferencias(X: pd.DataFrame) -> pd.DataFrame:
    """minuto, d_<conteo> = propio − rival, y v / oro_dif / azul si vienen."""
    out = {"minuto": X["minuto"].to_numpy()}
    for c in X.columns:
        if c.endswith("_p"):
            b = c[:-2]
            out[f"d_{b}"] = X[c].to_numpy() - X[f"{b}_r"].to_numpy()
    for c in ("v", "oro_dif", "azul"):
        if c in X.columns:
            out[c] = X[c].to_numpy()
    return pd.DataFrame(out, index=X.index)


def diferencias_total(X: pd.DataFrame) -> pd.DataFrame:
    """Diferencias más el total de asesinatos (ritmo de la partida, sin restricción)."""
    out = diferencias(X)
    out["asesinatos_tot"] = X["asesinatos_p"].to_numpy() + X["asesinatos_r"].to_numpy()
    return out


REPS = {"crudo": crudo, "dif": diferencias, "dif_tot": diferencias_total}


def signo(col: str) -> int:
    if col.startswith("d_") or col.endswith("_p") or col in ("v", "oro_dif"):
        return 1
    if col.endswith("_r"):
        return -1
    return 0  # minuto, azul, totales


def columnas_salida(rep: str, columnas: list[str]) -> list[str]:
    muestra = pd.DataFrame(np.zeros((1, len(columnas))), columns=columnas)
    return list(REPS[rep](muestra).columns)


# ---------------------------------------------------------------- fábricas
def hgb(rep: str, columnas: list[str], mono: bool = True, lr: float = 0.05, it: int = 300,
        hojas: int = 15, prof=None, msl: int = 300, l2: float = 1.0):
    cst = None
    if mono:
        cst = {c: signo(c) for c in columnas_salida(rep, columnas)}
    return make_pipeline(
        FunctionTransformer(REPS[rep]),
        HistGradientBoostingClassifier(learning_rate=lr, max_iter=it, max_leaf_nodes=hojas,
                                       max_depth=prof, min_samples_leaf=msl, l2_regularization=l2,
                                       monotonic_cst=cst, early_stopping=False, random_state=SEM))


def gbc(rep: str, columnas: list[str], lr: float = 0.05, n: int = 200, prof: int = 3,
        msl: int = 300, sub: float = 0.8):
    return make_pipeline(
        FunctionTransformer(REPS[rep]),
        GradientBoostingClassifier(learning_rate=lr, n_estimators=n, max_depth=prof,
                                   min_samples_leaf=msl, subsample=sub, random_state=SEM))


def bosque(clase, rep: str, columnas: list[str], mono: bool = True, n: int = 300, msl: int = 300,
           mf=0.5, ms=0.3, calibrar: bool = False):
    cst = [signo(c) for c in columnas_salida(rep, columnas)] if mono else None
    kw = dict(n_estimators=n, min_samples_leaf=msl, max_features=mf, monotonic_cst=cst,
              n_jobs=-1, random_state=SEM)
    if clase is RandomForestClassifier:
        kw["max_samples"] = ms
    est = clase(**kw)
    if calibrar:
        # Ojo: CalibratedClassifierCV separa filas, no partidas (fuga leve entre minutos).
        est = CalibratedClassifierCV(est, method="sigmoid", cv=3)
    return make_pipeline(FunctionTransformer(REPS[rep]), est)


# ---------------------------------------------------------------- experimentos
M, MO, O = MARCADOR, MARCADOR_ORO, ORO
EXPERIMENTOS: dict[str, tuple] = {
    # --- MARCADOR: representación y monotonía con una configuración conservadora
    "arb_hgb_marc_crudo_libre": (partial(hgb, "crudo", M, mono=False), M,
                                 "HGB columnas crudas, sin restricciones; lr .05, 300 it, 15 hojas, msl 300, l2 1"),
    "arb_hgb_marc_crudo_mono": (partial(hgb, "crudo", M), M,
                                "HGB columnas crudas, monótono (_p +, _r −)"),
    "arb_hgb_marc_dif_libre": (partial(hgb, "dif", M, mono=False), M,
                               "HGB sobre diferencias + minuto, sin restricciones"),
    "arb_hgb_marc_dif_mono": (partial(hgb, "dif", M), M,
                              "HGB sobre diferencias + minuto, monótono (+ en diferencias)"),
    # --- MARCADOR: los libres sobreajustan; menos capacidad
    "arb_hgb_marc_crudo_mono_suave": (partial(hgb, "crudo", M, lr=0.03, it=200, hojas=7, msl=600, l2=5.0), M,
                                      "HGB crudo monótono, suave: lr .03, 200 it, 7 hojas, msl 600, l2 5"),
    "arb_hgb_marc_dif_mono_suave": (partial(hgb, "dif", M, lr=0.03, it=200, hojas=7, msl=600, l2=5.0), M,
                                    "HGB diferencias monótono, suave: lr .03, 200 it, 7 hojas, msl 600, l2 5"),
    "arb_hgb_marc_crudo_mono_corto": (partial(hgb, "crudo", M, it=100), M,
                                      "HGB crudo monótono, 100 it (lr .05, 15 hojas, msl 300)"),
    # --- MARCADOR: árboles poco profundos (interacciones de a pares) y más iteraciones
    "arb_hgb_marc_crudo_mono_p2": (partial(hgb, "crudo", M, it=500, hojas=None, prof=2), M,
                                   "HGB crudo monótono, profundidad 2, 500 it, lr .05, msl 300"),
    "arb_hgb_marc_dif_mono_p2": (partial(hgb, "dif", M, it=500, hojas=None, prof=2), M,
                                 "HGB diferencias monótono, profundidad 2, 500 it, lr .05, msl 300"),
    # --- MARCADOR: otras familias de árboles
    "arb_gbc_marc_dif_p2": (partial(gbc, "dif", M, n=300, prof=2), M,
                            "GradientBoosting (árboles públicos) sobre diferencias, prof 2, 300 árboles, "
                            "lr .05, msl 300, subsample .8; sin restricción monótona (no la admite)"),
    "arb_rf_marc_crudo_mono": (partial(bosque, RandomForestClassifier, "crudo", M), M,
                               "RandomForest monótono, 300 árboles, msl 300, max_features .5, max_samples .3"),
    "arb_et_marc_crudo_mono": (partial(bosque, ExtraTreesClassifier, "crudo", M, msl=150), M,
                               "ExtraTrees monótono, 300 árboles, msl 150, max_features .5"),
    "arb_rf_marc_crudo_cal": (partial(bosque, RandomForestClassifier, "crudo", M, mono=False, msl=100,
                                      calibrar=True), M,
                              "RandomForest libre msl 100 + calibración sigmoide (CalibratedClassifierCV cv=3 "
                              "separa filas, no partidas: fuga leve)"),
    # --- MARCADOR_ORO
    "arb_hgb_mo_crudo_mono": (partial(hgb, "crudo", MO), MO,
                              "HGB crudo + v + oro_dif, monótono; lr .05, 300 it, 15 hojas, msl 300"),
    "arb_hgb_mo_crudo_mono_p2": (partial(hgb, "crudo", MO, it=500, hojas=None, prof=2), MO,
                                 "HGB crudo + v + oro_dif, monótono, prof 2, 500 it"),
    "arb_hgb_mo_dif_mono_p2": (partial(hgb, "dif", MO, it=500, hojas=None, prof=2), MO,
                               "HGB diferencias + v + oro_dif, monótono, prof 2, 500 it"),
    "arb_gbc_mo_dif_p2": (partial(gbc, "dif", MO, n=300, prof=2), MO,
                          "GradientBoosting sobre diferencias + v + oro_dif, prof 2, 300 árboles"),
    # --- ORO
    "arb_hgb_oro_mono": (partial(hgb, "crudo", O), O,
                         "HGB minuto, v, oro_dif, monótono; lr .05, 300 it, 15 hojas, msl 300"),
    "arb_hgb_oro_mono_p2": (partial(hgb, "crudo", O, it=500, hojas=None, prof=2), O,
                            "HGB minuto, v, oro_dif, monótono, prof 2, 500 it"),
    "arb_gbc_oro_p2": (partial(gbc, "crudo", O, n=300, prof=2), O,
                       "GradientBoosting minuto, v, oro_dif, prof 2, 300 árboles"),
}


def correr(nombres: list[str]) -> None:
    for n in nombres:
        fab, cols, notas = EXPERIMENTOS[n]
        evaluar(n, fab, cols, notas)


def base_de(cols: list[str]) -> str:
    return "base_oro_interaccion" if "v" in cols else "base_marcador_dif"


def tabla_comparar() -> None:
    filas = []
    for f in sorted(RESULTADOS.glob("arb_*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        b = base_de(r["columnas"])
        c = comparar(b, r["nombre"])
        filas.append((r["nombre"], r["perdida_log"], r["perdida_log_ee"], r["brier"], r["auc"],
                      r["ece"], b, c["b_menos_a"], c["ic95"][0], c["ic95"][1]))
    for x in filas:
        print(f"{x[0]:<34} {x[1]:.4f}±{x[2]:.4f} brier {x[3]:.4f} auc {x[4]:.4f} ece {x[5]:.4f} | "
              f"vs {x[6]}: {x[7]:+.4f} [{x[8]:+.4f}, {x[9]:+.4f}]")


def diagnostico(nombre: str) -> None:
    """Agregados solamente: monotonía, importancia por permutación, calibración por tramo, tamaño."""
    from sklearn.inspection import permutation_importance
    fab, cols, _ = EXPERIMENTOS[nombre]
    d, _ = cargar()
    plg = pliegues(d)
    X, y = d[cols], d["gane"].to_numpy()
    ent, pru = plg != 0, plg == 0
    mod = fab().fit(X[ent], y[ent])
    p0 = mod.predict_proba(X[pru])[:, 1]
    for c in cols:
        s = signo(c)
        if s == 0:
            continue
        Xb = X[pru].copy()
        Xb[c] = Xb[c] + 1
        p1 = mod.predict_proba(Xb)[:, 1]
        malas = int(np.sum(s * (p1 - p0) < -1e-9))
        print(f"  monotonía {c:<16} +1 → filas que se mueven al revés: {malas}")
    pi = permutation_importance(mod, X[pru], y[pru], scoring="neg_log_loss", n_repeats=3,
                                random_state=SEM, n_jobs=1)
    orden = np.argsort(-pi.importances_mean)
    print("  importancia por permutación (aumento de pérdida log, pliegue 0):")
    for i in orden:
        print(f"    {cols[i]:<16} {pi.importances_mean[i]:+.4f}")
    # calibración por tramo, con las predicciones fuera de muestra
    oof = pd.read_parquet(OOF / f"{nombre}.parquet")["p"].to_numpy()
    for a, b in TRAMOS:
        m = (d["minuto"] >= a) & (d["minuto"] <= b)
        print(f"  tramo {a}-{b if b < 99 else '+'}: predicho {oof[m].mean():.3f}  observado {y[m].mean():.3f}")
    # tamaño con todo el desarrollo
    mod = fab().fit(X, y)
    est = mod[-1]
    if isinstance(est, HistGradientBoostingClassifier):
        hojas = sum(int(pr[0].nodes["is_leaf"].sum()) for pr in est._predictors)
        print(f"  tamaño: {len(est._predictors)} árboles, {hojas} hojas en total")
    elif isinstance(est, GradientBoostingClassifier):
        hojas = sum(int(t[0].tree_.n_leaves) for t in est.estimators_)
        print(f"  tamaño: {len(est.estimators_)} árboles, {hojas} hojas en total")
    elif hasattr(est, "estimators_"):
        hojas = sum(int(t.tree_.n_leaves) for t in est.estimators_)
        print(f"  tamaño: {len(est.estimators_)} árboles, {hojas} hojas en total")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--comparar"]:
        tabla_comparar()
    elif args[:1] == ["--diag"]:
        for n in args[1:]:
            print(n)
            diagnostico(n)
    else:
        correr(args or list(EXPERIMENTOS))
