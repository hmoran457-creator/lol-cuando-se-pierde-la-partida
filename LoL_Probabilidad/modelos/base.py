r"""Modelos de referencia: la vara que cualquier otro modelo tiene que superar.

    python LoL_Probabilidad/modelos/base.py
"""
import pathlib
import sys

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from evaluar import MARCADOR, ORO, evaluar  # noqa: E402


class Proporcion(BaseEstimator, ClassifierMixin):
    """No sabe nada de la partida: siempre predice la proporción de victorias."""

    def fit(self, X, y):
        self.p_ = float(np.mean(y))
        return self

    def predict_proba(self, X):
        return np.column_stack([np.full(len(X), 1 - self.p_), np.full(len(X), self.p_)])


def diferencias(X):
    """Diferencias propio − rival de cada conteo del marcador, más el minuto."""
    cols = [c[:-2] for c in X.columns if c.endswith("_p")]
    out = {c: X[f"{c}_p"].to_numpy() - X[f"{c}_r"].to_numpy() for c in cols}
    out["minuto"] = X["minuto"].to_numpy()
    return np.column_stack(list(out.values()))


if __name__ == "__main__":
    evaluar("base_proporcion", Proporcion, ["minuto"], "siempre la proporción de victorias")
    evaluar("base_oro_lineal", lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
            ["minuto", "v"], "logística sobre minuto y v, sin interacción")
    evaluar("base_oro_interaccion", lambda: make_pipeline(
        FunctionTransformer(lambda X: np.column_stack([X["v"], X["v"] * X["minuto"], X["minuto"]])),
        StandardScaler(), LogisticRegression(max_iter=2000)),
        ["minuto", "v"], "logística: v, v×minuto, minuto")
    evaluar("base_marcador_dif", lambda: make_pipeline(
        FunctionTransformer(diferencias), StandardScaler(), LogisticRegression(max_iter=2000)),
        MARCADOR, "logística sobre las diferencias del marcador y el minuto")
