// Interfaz de la herramienta. El modelo vive en motor.js (Motor.prob, Motor.rango, Motor.aviso)
// y sus parámetros en window.MODELOS, que escribe construir.py.
(function () {
  "use strict";
  const M = window.MODELOS;
  const META = M.meta;

  // Filas del marcador: clave de la variable, nombre, aclaración, tope y mínimo. El barón,
  // Atakhan, el heraldo y las larvas no entran: no cambian la estimación (ver la nota).
  const FILAS = [
    ["asesinatos", "Asesinatos", "", 80, 0],
    ["estructuras", "Torres e inhibidores", "destruidos", 25, 0],
    ["dragones", "Dragones", "incluye el ancestral", 6, 0],
    ["nivel", "Niveles", "suma de los cinco, con Tab", 90, 5],
  ];
  // Los niveles arrancan en "automático" (null): la suma típica de un equipo en ese minuto, igual
  // para los dos. Al tocarlos quedan fijos en lo que se escribió.
  const tipico = (t) => META.nivel_mediana[Math.min(META.minuto_max, Math.max(0, t))];
  const INICIAL = () => {
    const e = { minuto: 15, usarOro: false, oro_p: null, oro_r: null };
    for (const [k] of FILAS) { e[k + "_p"] = 0; e[k + "_r"] = 0; }
    e.nivel_p = null; e.nivel_r = null;
    return e;
  };
  let estado = leerHash() || INICIAL();

  const $ = (id) => document.getElementById(id);
  const pct = (x) => Math.round(100 * x) + " %";
  const reloj = (m) => m + ":00";

  // ---------- construir el marcador ----------
  function stepper(lado, clave, tope, minimo) {
    const cont = document.createElement("div");
    cont.className = "contador";
    const menos = boton("−", `Quitar uno: ${clave} de ${lado === "p" ? "mi equipo" : "el rival"}`);
    const mas = boton("+", `Sumar uno: ${clave} de ${lado === "p" ? "mi equipo" : "el rival"}`);
    const val = document.createElement("span");
    val.className = "valor";
    val.id = `v-${clave}_${lado}`;
    menos.onclick = () => cambiar(`${clave}_${lado}`, -1, tope, minimo);
    mas.onclick = () => cambiar(`${clave}_${lado}`, +1, tope, minimo);
    // Mi equipo: el número queda pegado al centro, como en el marcador del juego.
    if (lado === "p") cont.append(menos, mas, val); else cont.append(val, menos, mas);
    return cont;
  }
  function boton(texto, etiqueta) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "paso"; b.textContent = texto;
    b.setAttribute("aria-label", etiqueta);
    return b;
  }
  function armar() {
    const raiz = $("filas");
    for (const [clave, nombre, nota, tope, minimo] of FILAS) {
      const fila = document.createElement("div");
      fila.className = "fila";
      const p = document.createElement("div"); p.className = "lado p"; p.append(stepper("p", clave, tope, minimo));
      const n = document.createElement("div"); n.className = "nombre";
      n.innerHTML = nombre + (nota ? `<small>${nota}</small>` : "");
      const r = document.createElement("div"); r.className = "lado r"; r.append(stepper("r", clave, tope, minimo));
      fila.append(p, n, r);
      raiz.append(fila);
    }
  }

  // Valor que se muestra y que ve el modelo (los niveles en automático valen lo típico).
  const valor = (e, k, t) => (e[k] == null ? tipico(t ?? e.minuto) : e[k]);

  function cambiar(k, d, tope, minimo) {
    estado[k] = Math.max(minimo, Math.min(tope, valor(estado, k) + d));
    // Al fijar los niveles de un lado, el otro también deja el automático en su valor actual.
    if (k.startsWith("nivel")) for (const l of ["p", "r"]) estado[`nivel_${l}`] = valor(estado, `nivel_${l}`);
    pintar();
  }

  // ---------- el estado que ve el modelo ----------
  function entrada(e, minuto) {
    const x = Object.assign({}, e, { minuto: minuto ?? e.minuto });
    for (const l of ["p", "r"]) x[`nivel_${l}`] = valor(e, `nivel_${l}`, x.minuto);
    let modo = "marcador";
    if (e.usarOro && e.oro_p > 0 && e.oro_r > 0) {
      modo = "marcador_oro";
      x.v = 100 * (e.oro_p - e.oro_r) / (e.oro_p + e.oro_r);
      // En otro minuto se conserva la ventaja relativa y se escala el oro total típico; en el
      // minuto actual se usa el oro escrito, para que el punto quede sobre su curva.
      const otro = minuto != null && minuto !== e.minuto;
      const total = otro ? META.oro_total_mediana[minuto] : e.oro_p + e.oro_r;
      x.oro_dif = x.v / 100 * total;
    }
    return [modo, x];
  }

  // ---------- pintar ----------
  function pintar() {
    $("minuto").value = estado.minuto;
    $("reloj-texto").textContent = reloj(estado.minuto);
    for (const [clave, , , tope, minimo] of FILAS) {
      for (const lado of ["p", "r"]) {
        const k = `${clave}_${lado}`;
        const n = valor(estado, k);
        $(`v-${k}`).textContent = n;
        $(`v-${k}`).classList.toggle("auto", estado[k] == null);
        $(`v-${k}`).title = estado[k] == null ? "Valor típico en este minuto: cámbialo con − y +" : "";
        const caja = $(`v-${k}`).parentElement.querySelectorAll("button");
        caja.forEach((b) => {
          b.disabled = b.textContent === "−" ? n <= minimo : n >= tope;
        });
      }
    }
    $("oro").classList.toggle("activo", estado.usarOro);
    $("usar-oro").setAttribute("aria-pressed", estado.usarOro ? "true" : "false");
    if (estado.usarOro) {
      if (document.activeElement !== $("oro-p")) $("oro-p").value = estado.oro_p ?? "";
      if (document.activeElement !== $("oro-r")) $("oro-r").value = estado.oro_r ?? "";
    }

    const [modo, x] = entrada(estado);
    const spec = M[modo];
    const p = Motor.prob(spec, x);
    const [lo, hi] = Motor.rango(spec, x);
    $("prob-p").textContent = pct(p);
    $("prob-r").textContent = pct(1 - p);
    $("cuerda-azul").style.width = (100 * p).toFixed(1) + "%";
    $("cuerda-rango").style.left = (100 * lo).toFixed(1) + "%";
    $("cuerda-rango").style.width = (100 * (hi - lo)).toFixed(1) + "%";
    $("cuerda").setAttribute("aria-label", `Probabilidad de ganar de mi equipo: ${pct(p)}`);
    const k = Math.round(20 * p);
    $("de-veinte").innerHTML = `Partidas así: gané <strong>${k} de cada 20</strong>`;
    $("rango-texto").textContent = `Rango del modelo: ${pct(lo)} a ${pct(hi)}`;
    const avisos = [];
    if (estado.usarOro && modo === "marcador") avisos.push("Escribe el oro de los dos equipos para usarlo.");
    const a = Motor.aviso(spec, x, META);
    if (a) avisos.push(a);
    $("aviso").textContent = avisos.join(" ");

    pintarMueve(modo, x, p);
    pintarCurva(p);
    escribirHash();
  }

  function pintarMueve(modo, x, p) {
    // Cada caso suma uno a un conteo. Con el oro escrito, un asesinato o una torre ya no se
    // muestran: el oro que dan está en el oro escrito, y sumarlos con el oro fijo daría un
    // engañoso "±0".
    const conOro = modo === "marcador_oro";
    const casos = [
      ["Un asesinato más de mi equipo", "asesinatos_p", 80, !conOro],
      ["Una torre más de mi equipo", "estructuras_p", 25, !conOro],
      ["Un dragón más de mi equipo", "dragones_p", 6, true],
      ["Un nivel más en mi equipo", "nivel_p", 90, true],
      ["Un asesinato más del rival", "asesinatos_r", 80, !conOro],
      ["Una torre más del rival", "estructuras_r", 25, !conOro],
      ["Un dragón más del rival", "dragones_r", 6, true],
      ["Un nivel más en el rival", "nivel_r", 90, true],
    ];
    const filas = casos.filter(([, clave, tope, ver]) => ver && x[clave] < tope)
      .map(([texto, clave]) => {
        const y = Object.assign({}, x);
        y[clave] = y[clave] + 1;
        return [texto, Motor.prob(M[modo], y) - p];
      });
    $("mueve-nota").textContent = conOro
      ? "Con el oro escrito, un asesinato o una torre mueven la probabilidad por el oro que dan: cambia el oro para verlo."
      : "";
    const tope = Math.max(0.01, ...filas.map(([, d]) => Math.abs(d)));
    $("mueve").innerHTML = filas.map(([texto, d]) => {
      const pp = Math.round(100 * d);
      const signo = pp > 0 ? "+" : pp < 0 ? "−" : "±";
      const ancho = (50 * Math.abs(d) / tope).toFixed(1);
      const izq = d >= 0 ? 50 : 50 - ancho;
      const color = d >= 0 ? "var(--blue)" : "var(--red)";
      return `<li><span>${texto}</span><span class="delta ${d >= 0 ? "sube" : "baja"}">${signo}${Math.abs(pp)} pts</span>` +
        `<span class="barra"><span style="left:${izq}%;width:${ancho}%;background:${color}"></span></span></li>`;
    }).join("");
  }

  function pintarCurva(pActual) {
    const W = 520, H = 230, I = 34, D = 10, A = 10, B = 28;
    const tmax = META.minuto_max;
    const xs = (t) => I + (W - I - D) * (t - 1) / (tmax - 1);
    const ys = (q) => A + (H - A - B) * (1 - q);
    const puntos = [], banda = [];
    for (let t = 1; t <= tmax; t++) {
      const [modo, x] = entrada(estado, t);
      const q = Motor.prob(M[modo], x);
      const [lo, hi] = Motor.rango(M[modo], x);
      puntos.push([xs(t), ys(q)]);
      banda.push([xs(t), ys(lo), ys(hi)]);
    }
    const linea = puntos.map(([a, b], i) => (i ? "L" : "M") + a.toFixed(1) + " " + b.toFixed(1)).join("");
    const area = banda.map(([a, , h], i) => (i ? "L" : "M") + a.toFixed(1) + " " + h.toFixed(1)).join("") +
      banda.slice().reverse().map(([a, l]) => "L" + a.toFixed(1) + " " + l.toFixed(1)).join("") + "Z";
    let marcas = "";
    for (const q of [0, .25, .5, .75, 1]) {
      marcas += `<line class="eje" x1="${I}" x2="${W - D}" y1="${ys(q)}" y2="${ys(q)}" ${q === .5 ? "" : 'stroke-dasharray="2 4"'}/>` +
        `<text x="${I - 6}" y="${ys(q) + 4}" text-anchor="end">${Math.round(q * 100)}</text>`;
    }
    for (let t = 5; t <= tmax; t += 5) {
      marcas += `<text x="${xs(t)}" y="${H - 8}" text-anchor="middle">${t}</text>`;
    }
    const cx = xs(estado.minuto), cy = ys(pActual);
    $("curva").innerHTML =
      `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Probabilidad de ganar con el mismo marcador en cada minuto">` +
      marcas +
      `<path d="${area}" fill="rgba(220,230,240,.10)"/>` +
      `<path d="${linea}" fill="none" stroke="var(--ink)" stroke-width="2"/>` +
      `<line x1="${cx}" x2="${cx}" y1="${A}" y2="${H - B}" stroke="var(--gold)" stroke-width="1" stroke-dasharray="3 3"/>` +
      `<circle cx="${cx}" cy="${cy}" r="6" fill="${pActual >= .5 ? "var(--blue)" : "var(--red)"}" stroke="var(--void)" stroke-width="2"/>` +
      `<text x="${W - D}" y="${H - 8}" text-anchor="end" opacity="0">minuto</text>` +
      `</svg>` +
      `<p style="margin:4px 0 0;color:var(--muted);font-size:14px">Minuto de la partida en el eje horizontal; la franja es el rango del modelo.</p>`;
  }

  // ---------- estado en la dirección (para no perderlo al recargar) ----------
  function escribirHash() {
    try { history.replaceState(null, "", "#" + encodeURIComponent(JSON.stringify(estado))); } catch (e) { /* file:// sin historial */ }
  }
  function leerHash() {
    // Solo se copian las claves conocidas, convertidas a número y acotadas: la dirección la
    // puede escribir cualquiera.
    try {
      const e = JSON.parse(decodeURIComponent(location.hash.slice(1)));
      const base = INICIAL();
      const num = (v, lo, hi, def = lo) => {
        const n = Math.round(Number(v));
        return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : def;
      };
      base.minuto = num(e.minuto, 1, META.minuto_max, 15);
      for (const [k, , , tope, minimo] of FILAS) {
        for (const l of ["p", "r"]) {
          const v = e[`${k}_${l}`];
          base[`${k}_${l}`] = k === "nivel" && v == null ? null : num(v, minimo, tope);
        }
      }
      base.usarOro = e.usarOro === true;
      base.oro_p = e.oro_p == null ? null : num(e.oro_p, 0, 200000) || null;
      base.oro_r = e.oro_r == null ? null : num(e.oro_r, 0, 200000) || null;
      return base;
    } catch (e) { return null; }
  }

  // ---------- eventos ----------
  armar();
  $("minuto").addEventListener("input", (ev) => { estado.minuto = +ev.target.value; pintar(); });
  $("usar-oro").onclick = () => {
    estado.usarOro = !estado.usarOro;
    if (estado.usarOro && !(estado.oro_p > 0)) {
      const mitad = Math.round(META.oro_total_mediana[estado.minuto] / 2 / 100) * 100;
      estado.oro_p = mitad; estado.oro_r = mitad;
    }
    pintar();
  };
  for (const lado of ["p", "r"]) {
    $(`oro-${lado}`).addEventListener("input", (ev) => {
      const n = parseFloat(ev.target.value);
      estado[`oro_${lado}`] = Number.isFinite(n) && n > 0 ? n : null;
      pintar();
    });
  }
  $("reiniciar").onclick = () => { estado = INICIAL(); pintar(); };
  pintar();
})();
