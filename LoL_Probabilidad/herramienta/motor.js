// Motor del modelo: la misma fórmula que LoL_Probabilidad/scripts/exportar.py.
//   logit = A(t) + sum_j x_j * B_j(t), con A y B_j rectas entre t = 1 y t = 40 (t recortado).
// Cada parámetro guarda [valor en t = 1, valor en t = 40].
window.Motor = (function () {
  "use strict";
  const T0 = 1, T1 = 40;

  function variable(nombre, e) {
    if (nombre.startsWith("dif_")) {
      const c = nombre.slice(4);
      return (e[c + "_p"] || 0) - (e[c + "_r"] || 0);
    }
    if (nombre === "v") return e.v;
    if (nombre === "oro_dif") return e.oro_dif / 1000;     // en miles de oro, como al ajustar
    throw new Error("variable desconocida: " + nombre);
  }

  function logit(param, nombres, e) {
    const tt = (Math.min(T1, Math.max(T0, e.minuto)) - T0) / (T1 - T0);
    const recta = (p) => p[0] + (p[1] - p[0]) * tt;
    let z = recta(param[0]);
    for (let j = 0; j < nombres.length; j++) z += variable(nombres[j], e) * recta(param[j + 1]);
    return z;
  }
  const sigmoide = (z) => 1 / (1 + Math.exp(-z));

  function prob(spec, e) {
    return sigmoide(logit(spec.param, spec.variables, e));
  }

  // Rango del 95 %: la estimación con cada uno de los 200 ajustes de partidas remuestreadas.
  function rango(spec, e) {
    const ps = spec.bootstrap.map((p) => sigmoide(logit(p, spec.variables, e))).sort((a, b) => a - b);
    const q = (f) => {
      const i = f * (ps.length - 1), a = Math.floor(i), b = Math.ceil(i);
      return ps[a] + (ps[b] - ps[a]) * (i - a);
    };
    return [q(0.025), q(0.975)];
  }

  // Avisos cuando el estado es raro en mis partidas: la estimación se vuelve una extrapolación.
  function aviso(spec, e, meta) {
    const t = Math.min(meta.minuto_max, Math.max(1, Math.round(e.minuto)));
    const n = meta.en_juego[t];
    if (n < 60) return `Solo ${n} de mis partidas seguían en juego en el minuto ${t}: tómalo con cuidado.`;
    for (const nombre of spec.variables) {
      const r = meta.rangos[nombre];
      if (!r) continue;
      const x = nombre === "v" ? e.v : variable(nombre, e);
      if (x < r[0][t - 1] || x > r[1][t - 1]) {
        return "Un marcador así casi no aparece en mis partidas a este minuto: la estimación es una extrapolación.";
      }
    }
    return "";
  }

  return { prob, rango, aviso };
})();
