r"""Otras familias de modelos y preguntas de estructura (prefijo otr_).

    python LoL_Probabilidad/modelos/otros.py            # todas las corridas
    python LoL_Probabilidad/modelos/otros.py mlp knn    # solo las que contienen esas palabras

Familias: red neuronal pequeña (MLP), vecinos más cercanos, una logística por minuto o por
tramo frente a una sola logística, peso 1/(filas de la partida), promedio y apilamiento de un
modelo de oro con uno de marcador, y una logística estructurada a(t) + g(t)·(w·diferencias).

Cómo se pesan las partidas sin la columna `partida`: `evaluar` entrega X[ent] con una máscara
booleana, que conserva el orden original (partida, minuto) y cada partida empieza en el minuto 1
y avanza de uno en uno. Así que `partidas(X)` = suma acumulada de (minuto == 1) reconstruye la
partida de cada fila. `partidas` verifica esa estructura y falla si el orden cambia algún día.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.neighbors import NearestNeighbors
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from evaluar import MARCADOR, MARCADOR_ORO, ORO, comparar, evaluar  # noqa: E402

SEMILLA = 7


# ----------------------------------------------------------------------------- utilidades
def partidas(X) -> np.ndarray:
    """Número de partida de cada fila, deducido del minuto (ver docstring del módulo)."""
    m = X["minuto"].to_numpy()
    assert m[0] == 1 and np.all((m[1:] == m[:-1] + 1) | (m[1:] == 1)), \
        "las filas no vienen en orden (partida, minuto) con minutos consecutivos desde 1"
    return np.cumsum(m == 1)


def pesos_partida(X) -> np.ndarray:
    """1/(filas de su partida), reescalado a media 1: cada partida pesa lo mismo."""
    g = partidas(X)
    w = 1.0 / np.bincount(g)[g]
    return w / w.mean()


def rasgos(X, oro: bool = True, interaccion: bool = False, minuto: bool = True) -> np.ndarray:
    """Diferencias propio − rival del marcador, minuto, v (y v×minuto si se pide)."""
    cols = [c[:-2] for c in X.columns if c.endswith("_p")]
    out = [X[f"{c}_p"].to_numpy() - X[f"{c}_r"].to_numpy() for c in cols]
    if minuto:
        out.append(X["minuto"].to_numpy().astype(float))
    if oro and "v" in X.columns:
        out.append(X["v"].to_numpy())
        if interaccion:
            out.append(X["v"].to_numpy() * X["minuto"].to_numpy())
    return np.column_stack(out).astype(float)


def r_lineal(X):  # para la logística conjunta (como base_oro_interaccion + diferencias)
    return rasgos(X, interaccion=True)


def r_red(X):  # la red aprende la interacción sola
    return rasgos(X, interaccion=False)


def r_oro_lineal(X):  # exactamente base_oro_interaccion: v, v×minuto, minuto
    return np.column_stack([X["v"], X["v"] * X["minuto"], X["minuto"]]).astype(float)


def r_marcador(X):  # exactamente base_marcador_dif: diferencias + minuto
    return rasgos(X, oro=False)


def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


# ----------------------------------------------------------------------------- estimadores
class Escalado(BaseEstimator, ClassifierMixin):
    """rasgos -> StandardScaler -> clasificador, con peso por partida opcional."""

    def __init__(self, f=r_lineal, clf=None, pesar: bool = False):
        self.f, self.clf, self.pesar = f, clf, pesar

    def fit(self, X, y):
        Z = self.f(X)
        self.esc_ = StandardScaler().fit(Z)
        clf = clone(self.clf) if self.clf is not None else LogisticRegression(max_iter=2000)
        w = pesos_partida(X) if self.pesar else None
        self.clf_ = clf.fit(self.esc_.transform(Z), y, sample_weight=w)
        return self

    def predict_proba(self, X):
        return self.clf_.predict_proba(self.esc_.transform(self.f(X)))


def red(capas, alpha, semilla=SEMILLA):
    # lbfgs y sin early_stopping: la validación interna de sklearn parte por fila y filtraría
    # minutos de la misma partida.
    return MLPClassifier(hidden_layer_sizes=capas, alpha=alpha, solver="lbfgs", max_iter=3000,
                         random_state=semilla)


class Bolsa(BaseEstimator, ClassifierMixin):
    """Promedio (en logit) de varias redes con distinta semilla: menos varianza, sigue exportable."""

    def __init__(self, f=r_red, capas=(8,), alpha=10.0, n=5, pesar=False):
        self.f, self.capas, self.alpha, self.n, self.pesar = f, capas, alpha, n, pesar

    def fit(self, X, y):
        self.redes_ = [Escalado(self.f, red(self.capas, self.alpha, SEMILLA + i), self.pesar).fit(X, y)
                       for i in range(self.n)]
        return self

    def predict_proba(self, X):
        p = expit(np.mean([_logit(r.predict_proba(X)[:, 1]) for r in self.redes_], axis=0))
        return np.column_stack([1 - p, p])


class Vecinos(BaseEstimator, ClassifierMixin):
    """k vecinos en rasgos estandarizados; p = (victorias + a·p0) / (k + a) para no dar 0 ni 1."""

    def __init__(self, f=r_red, k=200, a=2.0, peso_minuto=1.0):
        self.f, self.k, self.a, self.peso_minuto = f, k, a, peso_minuto

    def _z(self, X):
        Z = self.esc_.transform(self.f(X))
        Z[:, self.col_min_] *= self.peso_minuto
        return Z

    def fit(self, X, y):
        Z = self.f(X)
        self.esc_ = StandardScaler().fit(Z)
        n_dif = sum(c.endswith("_p") for c in X.columns)
        self.col_min_ = n_dif  # el minuto va justo después de las diferencias
        self.y_, self.p0_ = np.asarray(y, float), float(np.mean(y))
        self.nn_ = NearestNeighbors(n_neighbors=self.k).fit(self._z(X))
        return self

    def predict_proba(self, X):
        _, idx = self.nn_.kneighbors(self._z(X))
        p = (self.y_[idx].sum(axis=1) + self.a * self.p0_) / (self.k + self.a)
        return np.column_stack([1 - p, p])


class PorMinuto(BaseEstimator, ClassifierMixin):
    """Una logística por tramo de minutos (tramo de ancho 1 = una por minuto).

    `cortes` son los inicios de tramo; el último tramo es abierto. Dentro de un tramo de ancho
    mayor a 1 el minuto entra como variable; en tramos de un minuto no.
    """

    def __init__(self, f_sin_minuto=None, cortes=tuple(range(1, 36)), C=1.0):
        self.f_sin_minuto, self.cortes, self.C = f_sin_minuto, cortes, C

    def _tramo(self, m):
        return np.searchsorted(np.asarray(self.cortes), m, side="right") - 1

    def _z(self, X, t):
        Z = self.f_sin_minuto(X)
        ancho = (self.cortes[t + 1] - self.cortes[t]) if t + 1 < len(self.cortes) else 99
        if ancho > 1:
            Z = np.column_stack([Z, X["minuto"].to_numpy()])
        return Z

    def fit(self, X, y):
        y = np.asarray(y)
        tr = self._tramo(X["minuto"].to_numpy())
        self.modelos_ = {}
        for t in range(len(self.cortes)):
            s = tr == t
            if s.sum() == 0:
                continue
            if len(np.unique(y[s])) < 2:
                self.modelos_[t] = float(y[s].mean())
                continue
            Z = self._z(X[s], t)
            esc = StandardScaler().fit(Z)
            lr = LogisticRegression(C=self.C, max_iter=2000).fit(esc.transform(Z), y[s])
            self.modelos_[t] = (esc, lr)
        return self

    def predict_proba(self, X):
        tr = self._tramo(X["minuto"].to_numpy())
        p = np.zeros(len(X))
        disponibles = np.array(sorted(self.modelos_))
        for t in np.unique(tr):
            s = tr == t
            tt = disponibles[np.argmin(np.abs(disponibles - t))]  # tramo sin datos: el más cercano
            mod = self.modelos_[tt]
            if isinstance(mod, float):
                p[s] = mod
            else:
                esc, lr = mod
                p[s] = lr.predict_proba(esc.transform(self._z(X[s], tt)))[:, 1]
        return np.column_stack([1 - p, p])


def sm_oro(X):
    return X[["v"]].to_numpy().astype(float)


def sm_marcador(X):
    return rasgos(X, oro=False, minuto=False)


def sm_marcador_oro(X):
    return rasgos(X, oro=True, minuto=False)


class Estructurado(BaseEstimator, ClassifierMixin):
    """logit P = a0 + a1·t + g(t)·(w·z),  g(t) = exp(c1·log t + c2·t/10 + c3·(t/10)²).

    z = diferencias estandarizadas (y v). Un solo índice de ventaja cuyo peso cambia con el
    minuto: 8–9 pesos + 5 números, en vez de una pendiente por variable y por minuto.
    Penalización L2 `lam` sobre w y c. Se exporta como fórmula cerrada.
    """

    def __init__(self, f_sin_minuto=sm_marcador_oro, lam=1e-3, pesar=False):
        self.f_sin_minuto, self.lam, self.pesar = f_sin_minuto, lam, pesar

    def _bases(self, X):
        t = X["minuto"].to_numpy().astype(float)
        A = np.column_stack([np.ones_like(t), t / 10])
        B = np.column_stack([np.log(t), t / 10, (t / 10) ** 2])
        return A, B

    def _eta(self, th, A, B, Z):
        na, nw = A.shape[1], Z.shape[1]
        a, w, c = th[:na], th[na:na + nw], th[na + nw:]
        g = np.exp(B @ c)
        s = Z @ w
        return A @ a + g * s, g, s

    def fit(self, X, y):
        y = np.asarray(y, float)
        Z0 = self.f_sin_minuto(X)
        self.esc_ = StandardScaler().fit(Z0)
        Z = self.esc_.transform(Z0)
        A, B = self._bases(X)
        pw = pesos_partida(X) if self.pesar else np.ones(len(y))
        pw = pw / pw.sum()
        na, nw, nc = A.shape[1], Z.shape[1], B.shape[1]
        w0 = LogisticRegression(max_iter=2000).fit(Z, y).coef_[0]
        th0 = np.r_[np.zeros(na), w0, np.zeros(nc)]
        lam = self.lam

        def obj(th):
            eta, g, s = self._eta(th, A, B, Z)
            loss = np.sum(pw * (np.logaddexp(0, eta) - y * eta))
            r = pw * (expit(eta) - y)
            ga = A.T @ r
            gw = Z.T @ (r * g)
            gc = B.T @ (r * g * s)
            reg = th[na:]
            loss += 0.5 * lam * reg @ reg
            return loss, np.r_[ga, gw + lam * reg[:nw], gc + lam * reg[nw:]]

        res = minimize(obj, th0, jac=True, method="L-BFGS-B", options={"maxiter": 5000})
        self.th_, self.convergio_ = res.x, bool(res.success)
        return self

    def predict_proba(self, X):
        A, B = self._bases(X)
        eta, _, _ = self._eta(self.th_, A, B, self.esc_.transform(self.f_sin_minuto(X)))
        p = expit(eta)
        return np.column_stack([1 - p, p])


class Combinado(BaseEstimator, ClassifierMixin):
    """Un modelo de oro y uno de marcador, combinados.

    modo="promedio": promedio de logits, sin ajustar nada.
    modo="apilado": logística sobre [l_oro, l_marcador, l_oro·t, l_marcador·t, t], con los logits
    de primer nivel fuera de muestra (GroupKFold por partida dentro del entrenamiento).
    """

    def __init__(self, modo="apilado", pesar=False):
        self.modo, self.pesar = modo, pesar

    def _base(self):
        return (Escalado(r_oro_lineal, pesar=self.pesar), Escalado(r_marcador, pesar=self.pesar))

    @staticmethod
    def _meta_x(lo, lm, t):
        t = t / 10
        return np.column_stack([lo, lm, lo * t, lm * t, t])

    def fit(self, X, y):
        y = np.asarray(y)
        self.oro_, self.marc_ = [m.fit(X, y) for m in self._base()]
        if self.modo == "apilado":
            g = partidas(X)
            lo, lm = np.zeros(len(y)), np.zeros(len(y))
            for ent, pru in GroupKFold(n_splits=5).split(X, y, g):
                # .iloc conserva el orden; cada pliegue interno sigue siendo partidas completas
                Xe = X.iloc[ent]
                mo, mm = self._base()
                lo[pru] = _logit(mo.fit(Xe, y[ent]).predict_proba(X.iloc[pru])[:, 1])
                lm[pru] = _logit(mm.fit(Xe, y[ent]).predict_proba(X.iloc[pru])[:, 1])
            self.meta_ = LogisticRegression(max_iter=2000).fit(
                self._meta_x(lo, lm, X["minuto"].to_numpy()), y)
        return self

    def predict_proba(self, X):
        lo = _logit(self.oro_.predict_proba(X)[:, 1])
        lm = _logit(self.marc_.predict_proba(X)[:, 1])
        if self.modo == "promedio":
            p = expit((lo + lm) / 2)
        else:
            p = self.meta_.predict_proba(self._meta_x(lo, lm, X["minuto"].to_numpy()))[:, 1]
        return np.column_stack([1 - p, p])


# ----------------------------------------------------------------------------- corridas
# Exploración previa (MARCADOR, una red, guardar=False; mismos pliegues, así que es optimista):
#   8 ocultas: alpha 1 0.5644, 10 0.5621, 30 0.5553, 100 0.5482, 300 0.5532
#   16 ocultas: alpha 10 0.5691, 300 0.5531;  4 ocultas: alpha 10 0.5555, 50 0.5515
#   vecinos: k=100 0.5608, k=400 0.5601 (se quedó k=200)
# Pérdida promediando primero dentro de cada partida (la métrica que optimiza el peso 1/filas):
#   el peso gana ~0.001 en los tres conjuntos, y pierde ~0.001 por fila; el ECE empeora.
CINCO = (1, 6, 11, 16, 21, 26, 31, 36)  # tramos de 5 minutos, último abierto (36+)
EXPERIMENTOS = [
    # --- ORO: ¿una logística por minuto (como el cuaderno) o una sola? ¿pesar partidas?
    ("otr_oro_porminuto", lambda: PorMinuto(sm_oro), ORO,
     "una logística sobre v por cada minuto 1..34, la última para 35+"),
    ("otr_oro_portramo", lambda: PorMinuto(sm_oro, CINCO), ORO,
     "una logística sobre v y minuto por tramo de 5 minutos (36+ junto)"),
    ("otr_oro_peso", lambda: Escalado(r_oro_lineal, pesar=True), ORO,
     "base_oro_interaccion con peso 1/(filas de la partida)"),
    ("otr_oro_red", lambda: Bolsa(r_oro_lineal, (8,), 100.0), ORO,
     "5 redes (8 ocultas, alpha 100) sobre v, v×minuto, minuto; promedio de logits"),
    # --- MARCADOR
    ("otr_m_porminuto", lambda: PorMinuto(sm_marcador), MARCADOR,
     "una logística sobre las diferencias por cada minuto 1..34, la última para 35+"),
    ("otr_m_portramo", lambda: PorMinuto(sm_marcador, CINCO), MARCADOR,
     "una logística sobre diferencias y minuto por tramo de 5 minutos"),
    ("otr_m_peso", lambda: Escalado(r_marcador, pesar=True), MARCADOR,
     "base_marcador_dif con peso 1/(filas de la partida)"),
    ("otr_m_red", lambda: Bolsa(r_red, (8,), 100.0), MARCADOR,
     "5 redes (8 ocultas, alpha 100) sobre diferencias y minuto"),
    ("otr_m_knn", lambda: Vecinos(r_red, k=200), MARCADOR,
     "200 vecinos en diferencias + minuto estandarizados, suavizado (v+2·p0)/(k+2)"),
    ("otr_m_estructurado", lambda: Estructurado(sm_marcador), MARCADOR,
     "a0+a1·t + g(t)·(w·z), g = exp(c1 log t + c2 t + c3 t²)"),
    # --- MARCADOR + ORO
    ("otr_mo_lineal", lambda: Escalado(r_lineal), MARCADOR_ORO,
     "referencia conjunta: logística sobre diferencias, minuto, v, v×minuto"),
    ("otr_mo_peso", lambda: Escalado(r_lineal, pesar=True), MARCADOR_ORO,
     "otr_mo_lineal con peso 1/(filas de la partida)"),
    ("otr_mo_portramo", lambda: PorMinuto(sm_marcador_oro, CINCO), MARCADOR_ORO,
     "una logística sobre diferencias, v y minuto por tramo de 5 minutos"),
    ("otr_mo_red", lambda: Bolsa(r_red, (8,), 100.0), MARCADOR_ORO,
     "5 redes (8 ocultas, alpha 100) sobre diferencias, minuto y v"),
    ("otr_mo_knn", lambda: Vecinos(r_red, k=200), MARCADOR_ORO,
     "200 vecinos en diferencias + minuto + v estandarizados, suavizado"),
    ("otr_mo_estructurado", lambda: Estructurado(sm_marcador_oro), MARCADOR_ORO,
     "a0+a1·t + g(t)·(w·z) con z = diferencias y v"),
    ("otr_mo_promedio", lambda: Combinado("promedio"), MARCADOR_ORO,
     "promedio de logits de base_oro_interaccion y base_marcador_dif"),
    ("otr_mo_apilado", lambda: Combinado("apilado"), MARCADOR_ORO,
     "apilamiento: logística sobre los dos logits, sus productos con t, y t"),
]

REFERENCIA = {"otr_oro": "base_oro_interaccion", "otr_m_": "base_marcador_dif",
              "otr_mo": "base_oro_interaccion"}


def referencia(nombre: str) -> str:
    return next(v for k, v in sorted(REFERENCIA.items(), key=lambda kv: -len(kv[0]))
                if nombre.startswith(k))


if __name__ == "__main__":
    filtros = sys.argv[1:]
    hechos = []
    for nombre, fabrica, columnas, notas in EXPERIMENTOS:
        if filtros and not any(f in nombre for f in filtros):
            continue
        evaluar(nombre, fabrica, columnas, notas)
        hechos.append(nombre)
    print()
    for nombre in hechos:
        ref = referencia(nombre)
        c = comparar(ref, nombre)
        print(f"{nombre:<24} vs {ref:<22} b−a {c['b_menos_a']:+.4f}  "
              f"IC95 [{c['ic95'][0]:+.4f}, {c['ic95'][1]:+.4f}]")
