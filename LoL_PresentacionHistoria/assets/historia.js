/* =========================================================================
   Presentacion narrada - motor, graficas y movimiento
   ---------------------------------------------------------------------------
   * Navegacion (teclas, pasos, pantalla en negro) heredada del mazo original.
   * Todas las graficas se dibujan aqui, desde window.HISTORIA: ninguna cifra
     esta escrita a mano.
   * Movimiento en dos capas:
       - CSS: entradas, apariciones por paso ([data-step] + .mostrado), pulsos;
       - JS: «efectos» atados a un paso que necesitan coordinar varias piezas
         (la linea del caso con su cabezal, la carrera del oro, el rebobinado).
     Cada efecto sabe ponerse (on) y quitarse (off); si la lamina ya se vio,
     o en ?todo, o con movimiento reducido, se pone de golpe en su estado final.
   * ?video: la presentacion avanza sola (tambien con la tecla P, «modo cine»).
     scripts/video.py la graba cuadro por cuadro con un reloj virtual, asi que
     todo el tiempo aqui sale de requestAnimationFrame / setTimeout.
   ========================================================================= */
(function () {
  "use strict";

  var H = window.HISTORIA || {};
  var stage = document.getElementById("stage");
  var slides = [], idx = 0;
  var TODO = /[?&]todo\b/.test(location.search);
  var VIDEO = /[?&]video\b/.test(location.search);
  var MENOS_MOV = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };
  var quieto = function () { return TODO || MENOS_MOV.matches; };

  /* ============================================================ tema claro / oscuro */
  // El tema inicial lo pone un script en el <head> (antes de pintar): ?tema=claro|oscuro,
  // si no lo que se eligio la vez pasada, y si no el claro de la plantilla. Aqui solo se
  // alterna (tecla T o boton del riel) y se recuerda; localStorage puede fallar sin romper nada.
  var TEMA_CLAVE = "lol-historia-tema";
  function claro() { return document.documentElement.getAttribute("data-theme") !== "dark"; }
  function etiquetaTema() {
    var b = document.getElementById("tema-btn");
    if (!b) return;
    var txt = claro() ? "Cambiar a tema oscuro (T)" : "Cambiar a tema claro (T)";
    b.setAttribute("aria-label", txt); b.title = txt;
  }
  function alternaTema() {
    var t = claro() ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", t);
    try { localStorage.setItem(TEMA_CLAVE, t); } catch (e) { /* sin almacenamiento: solo esta vez */ }
    etiquetaTema();
    if (stage._repinta) stage._repinta();
  }

  function fitStage() {
    var s = Math.min(window.innerWidth / 1600, window.innerHeight / 900);
    stage.style.transform = "scale(" + s + ")";
  }
  window.addEventListener("resize", fitStage);

  /* ============================================================ tiempo */
  var CURVA = {
    sale: function (p) { return 1 - Math.pow(1 - p, 3); },
    suave: function (p) { return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; },
    lineal: function (p) { return p; }
  };
  // Interpolacion atada a una lamina: si se sale de ella, se detiene.
  function tween(s, dur, fn, o) {
    o = o || {};
    var ease = CURVA[o.ease || "sale"], t0 = null, h = { vivo: true };
    (s._tw = s._tw || []).push(h);
    fn(0);
    requestAnimationFrame(function f(ts) {
      if (!h.vivo) return;
      if (t0 === null) t0 = ts + (o.delay || 0);
      var p = (ts - t0) / dur;
      if (p < 0) { requestAnimationFrame(f); return; }
      if (p >= 1) { h.vivo = false; fn(1); if (o.fin) o.fin(); return; }
      fn(ease(p));
      requestAnimationFrame(f);
    });
    return h;
  }
  function corre(s, rapido, dur, fn, o) {
    if (rapido) { fn(1); if (o && o.fin) o.fin(); return; }
    tween(s, dur, fn, o);
  }
  function detener(s) { (s._tw || []).forEach(function (h) { h.vivo = false; }); s._tw = []; }

  /* ============================================================ efectos */
  function efecto(s, paso, on, off) {
    (s._ef = s._ef || []).push({ paso: paso, on: on, off: off || function () {}, activo: false });
  }
  function aplicaEfectos(s, n, rapido) {
    (s._ef || []).forEach(function (e) {
      var ver = e.paso <= n;
      if (ver && !e.activo) { e.activo = true; e.on(rapido); }
      else if (!ver && e.activo) { e.activo = false; e.off(); }
    });
  }
  function reinicia(s) {
    detener(s);
    (s._ef || []).forEach(function (e) { if (e.activo) { e.activo = false; e.off(); } });
    s.querySelectorAll("[data-count]").forEach(function (x) { x._contado = false; });
  }

  /* ============================================================ contadores */
  // data-count admite «1,195»: se queda solo con los digitos (y el punto decimal).
  function contar(root, rapido) {
    Array.prototype.forEach.call(root.querySelectorAll("[data-count]"), function (el) {
      var st = el.closest("[data-step]");
      if (st && !st.classList.contains("mostrado")) return;
      if (el._contado) return;
      el._contado = true;
      var fin = parseFloat(String(el.dataset.count).replace(/[^\d.\-]/g, ""));
      var dec = parseInt(el.dataset.dec || "0", 10), pre = el.dataset.prefix || "", suf = el.dataset.suffix || "";
      var pinta = function (v) {
        return pre + v.toLocaleString("es-MX", { minimumFractionDigits: dec, maximumFractionDigits: dec }) + suf;
      };
      if (isNaN(fin)) return;
      corre(root, rapido, parseInt(el.dataset.dur || "1300", 10), function (p) { el.textContent = pinta(fin * p); },
        { delay: parseInt(el.dataset.delay || "0", 10) });
    });
  }

  /* ============================================================ navegacion */
  var RAIL = [
    { id: 1, label: "El misterio" }, { id: 2, label: "Las pistas" },
    { id: 3, label: "Las pruebas" }, { id: 4, label: "Lo que encontré" },
    { id: 5, label: "La respuesta" }
  ];
  function buildRail() {
    var rail = document.getElementById("rail"), h = "";
    RAIL.forEach(function (r) {
      h += '<div class="rail-item" data-sec="' + r.id + '"><span class="num">' + r.id +
        "</span><span>" + r.label + "</span></div>";
    });
    h += '<div class="rail-item spacer"></div><div class="counter"><span id="pageno">1</span> / ' +
      '<span id="pagetot">1</span><span class="pasos" id="pasos"></span></div>' +
      '<button type="button" id="tema-btn" class="tema-btn">&#9680;</button>';
    rail.innerHTML = h;
    var b = document.getElementById("tema-btn");
    // mousedown sin foco: si el boton se quedara con el foco, la barra espaciadora lo pulsaria
    b.addEventListener("mousedown", function (e) { e.preventDefault(); });
    b.addEventListener("click", function () { alternaTema(); });
    etiquetaTema();
  }
  function updateRail() {
    var sec = parseInt(slides[idx].dataset.sec || "0", 10);
    document.querySelectorAll(".rail-item[data-sec]").forEach(function (el) {
      var n = parseInt(el.dataset.sec, 10);
      el.classList.toggle("on", n === sec);
      el.classList.toggle("done", n < sec);
    });
    document.getElementById("pageno").textContent = String(idx + 1);
    document.getElementById("progress").style.width = ((idx + 1) / slides.length) * 100 + "%";
    var cur = slides[idx], mx = maxPaso(cur), h = "";
    for (var q = 1; q <= mx; q++) h += "<i class='" + (q <= (cur._paso || 0) ? "on" : "") + "'></i>";
    document.getElementById("pasos").innerHTML = h;
  }

  function pasosDe(s) { return Array.prototype.slice.call(s.querySelectorAll("[data-step]")); }
  function maxPaso(s) {
    return pasosDe(s).reduce(function (m, e) { return Math.max(m, parseInt(e.dataset.step, 10) || 0); }, 0);
  }
  function pintaPasos(s, n, rapido) {
    s._paso = n;
    pasosDe(s).forEach(function (e) { e.classList.toggle("mostrado", (parseInt(e.dataset.step, 10) || 0) <= n); });
    aplicaEfectos(s, n, rapido);
    contar(s, rapido);
    updateRail();
    programa();
  }

  // Color del resplandor de fondo segun el acto (azul = mi equipo, rojo = derrota, oro = hallazgo).
  var TONO = { 0: [188, 139, 44], 1: [14, 158, 180], 2: [188, 139, 44], 3: [74, 110, 150], 4: [188, 139, 44], 5: [232, 200, 122] };
  function tonoDe(s) { return s.id === "h-derrota" ? [222, 67, 97] : TONO[parseInt(s.dataset.sec || "0", 10)]; }

  function barrido(atras) {
    var b = document.getElementById("barrido");
    if (!b || quieto()) return;
    b.classList.remove("va", "vuelve");
    void b.offsetWidth;
    b.classList.add(atras ? "vuelve" : "va");
  }

  function show(n, back) {
    if (n < 0 || n >= slides.length) return;
    var viejo = slides[idx], s = slides[n];
    if (viejo !== s) {
      detener(viejo);
      viejo.classList.remove("active", "enter", "enter-back", "sale", "sale-back");
      if (!quieto()) {
        viejo.classList.add(back ? "sale-back" : "sale");
        clearTimeout(viejo._salida);
        viejo._salida = setTimeout(function () { viejo.classList.remove("sale", "sale-back"); }, 820);
      }
      barrido(back);
    }
    idx = n;
    var visto = s._seen === true;
    clearTimeout(s._salida);
    s.classList.remove("sale", "sale-back", "enter", "enter-back");
    s.classList.toggle("visto", visto);
    void s.offsetWidth;
    s.classList.add("active", back ? "enter-back" : "enter");
    medirTrazos(s);
    var completa = TODO || back || visto;
    if (visto) reinicia(s);
    pintaPasos(s, completa ? maxPaso(s) : 0, completa || MENOS_MOV.matches);
    s._seen = true;
    if (stage._tono) stage._tono(tonoDe(s));
    location.replace(location.pathname + location.search + "#d" + (idx + 1));
  }
  function next() {
    var s = slides[idx];
    if (!TODO && s._paso < maxPaso(s)) { pintaPasos(s, s._paso + 1, MENOS_MOV.matches); return; }
    show(idx + 1, false);
  }
  function prev() {
    var s = slides[idx], mx = maxPaso(s);
    if (!TODO && mx && s._paso > 0 && s._paso < mx) { pintaPasos(s, s._paso - 1, true); return; }
    show(idx - 1, true);
  }
  function repite() {
    var s = slides[idx];
    reinicia(s);
    s.classList.remove("visto", "active", "enter", "enter-back");
    pasosDe(s).forEach(function (x) { x.classList.remove("mostrado"); });
    void s.offsetWidth;                 // reinicia tambien las animaciones CSS de entrada
    s.classList.add("active", "enter");
    pintaPasos(s, 0, MENOS_MOV.matches);
  }

  /* ---------------------------------------------------- modo cine (P, ?video) */
  // Cuanto se sostiene cada paso: lo que tarda en leerse lo que aparece (≈230
  // palabras por minuto) y nunca menos de lo que dura su animacion.
  // Al entrar basta con alcanzar el titular (sigue en pantalla toda la lamina); el tiempo
  // se lo llevan los pasos, y sobre todo el ULTIMO de cada lamina, que trae la conclusion.
  var MINIMO = {
    "h-portada": [6200], "h-derrota": [4200, 3600, 4400], "h-juego": [2400, 4800, 3600, 4400, 5600],
    "h-yo": [2400, 5000, 5200], "h-caso": [2200, 7000, 4800, 4800, 8600],
    "h-pregunta": [2200, 4600, 5600, 4800], "h-pruebas": [2400, 6000, 4800, 5400], "h-medida": [2400, 4600, 4600, 5400],
    "h-pista1": [2400, 3600, 3600, 3600, 7800], "h-pista2": [2400, 4800, 5000, 8000],
    "h-pista3": [2400, 4800, 4400, 4400, 8200], "h-veredicto": [2200, 5200, 5200, 6000],
    "h-respuesta": [5400, 7000, 8000], "h-gracias": [9500]
  };
  function palabras(e) { return (e.textContent || "").trim().split(/\s+/).filter(Boolean).length; }
  function espera(s, paso) {
    var w = 0;
    if (paso === 0) {
      s.querySelectorAll("h1, h2, .kicker, .cierre-grande, .defeat-word, p, .closer").forEach(function (e) {
        if (!e.closest("[data-step]")) w += palabras(e);
      });
    } else {
      pasosDe(s).forEach(function (e) {
        if (parseInt(e.dataset.step, 10) !== paso || e.closest("svg")) return;
        var padre = e.parentElement && e.parentElement.closest("[data-step]");
        if (padre && parseInt(padre.dataset.step, 10) === paso) return;
        w += palabras(e);
      });
    }
    // El titular sigue en pantalla durante toda la lamina: al entrar basta con
    // alcanzar a leerlo por encima; lo que trae cada paso si se lee completo.
    var leer = paso === 0 ? Math.min(3000, 1200 + w * 80) : 2000 + w * 290;
    return Math.max(leer, (MINIMO[s.id] || [])[paso] || 2800);
  }
  var auto = VIDEO, autoT = null;
  function programa() {
    clearTimeout(autoT);
    if (!auto || TODO) return;
    var s = slides[idx];
    autoT = setTimeout(function () {
      if (idx === slides.length - 1 && s._paso >= maxPaso(s)) {
        auto = false;
        if (VIDEO) {                     // el video termina con un fundido a negro, no en seco
          document.body.classList.add("fundido");
          setTimeout(function () { window.__fin = true; }, 1600);
        }
        return;
      }
      next();
    }, espera(s, s._paso || 0));
  }

  var blanked = false;
  function setBlank(v) { blanked = v; document.body.classList.toggle("blank", v); }
  document.addEventListener("keydown", function (e) {
    var k = e.key;
    if (k === "b" || k === "B" || k === ".") { e.preventDefault(); setBlank(!blanked); return; }
    if (blanked) { e.preventDefault(); setBlank(false); return; }
    if (e.repeat) return;
    if (k === "ArrowRight" || k === "ArrowDown" || k === "PageDown" || k === " " || k === "Enter") { e.preventDefault(); next(); }
    else if (k === "ArrowLeft" || k === "ArrowUp" || k === "PageUp" || k === "Backspace") { e.preventDefault(); prev(); }
    else if (k === "Home") { e.preventDefault(); show(0, true); }
    else if (k === "End") { e.preventDefault(); show(slides.length - 1, false); }
    else if (k === "f" || k === "F") {
      if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen();
    }
    else if (k === "r" || k === "R") { e.preventDefault(); repite(); }
    else if (k === "t" || k === "T") { e.preventDefault(); alternaTema(); }
    else if (k === "p" || k === "P") {
      e.preventDefault(); auto = !auto; document.body.classList.toggle("cine", auto); programa();
    }
    else if (/^[1-5]$/.test(k)) {
      e.preventDefault();
      for (var q = 0; q < slides.length; q++) if (slides[q].dataset.sec === k) { show(q, q < idx); break; }
    }
    else if (k === "a" || k === "A") { e.preventDefault(); pintaPasos(slides[idx], maxPaso(slides[idx]), true); }
    else if (k === "?" || k === "h" || k === "H") { e.preventDefault(); flashHelp(); }
  });
  var dnX = 0, dnY = 0;
  document.addEventListener("mousedown", function (e) { dnX = e.clientX; dnY = e.clientY; });
  document.addEventListener("click", function (e) {
    if (e.target.closest("a, button")) return;   // el boton de tema no avanza la lamina
    if (Math.abs(e.clientX - dnX) > 5 || Math.abs(e.clientY - dnY) > 5) return;
    if (e.clientX < window.innerWidth * 0.22) prev(); else next();
  });
  var tx = 0;
  document.addEventListener("touchstart", function (e) { tx = e.changedTouches[0].clientX; }, { passive: true });
  document.addEventListener("touchend", function (e) {
    var dx = e.changedTouches[0].clientX - tx;
    if (Math.abs(dx) > 55) { if (dx < 0) next(); else prev(); }
  }, { passive: true });
  var helpT;
  function flashHelp() {
    var h = document.getElementById("help");
    // ?todo es para leer o exportar (PDF, capturas): la ayuda de teclas saldria en la imagen
    if (!h || VIDEO || TODO) return;
    h.classList.add("show");
    clearTimeout(helpT);
    helpT = setTimeout(function () { h.classList.remove("show"); }, 2600);
  }

  /* ================================================================ SVG util */
  var NS = "http://www.w3.org/2000/svg", nId = 0;
  function uid() { return "u" + (++nId); }
  function el(name, attrs, padre) {
    var e = document.createElementNS(NS, name);
    for (var k in attrs) if (attrs[k] !== undefined && attrs[k] !== null) e.setAttribute(k, attrs[k]);
    if (padre) padre.appendChild(e);
    return e;
  }
  function txt(attrs, s, padre) { var t = el("text", attrs, padre); t.textContent = s; return t; }
  // texto con partes: ["fijo", {n: 1234, dec: 0, delay: 0}, "fijo"] -> los numeros cuentan
  function txtCuenta(attrs, partes, padre) {
    var t = el("text", attrs, padre);
    partes.forEach(function (p) {
      var sp = el("tspan", {}, t);
      if (typeof p === "string") { sp.textContent = p; return; }
      sp.setAttribute("data-count", p.n);
      if (p.dec) sp.setAttribute("data-dec", p.dec);
      if (p.delay) sp.setAttribute("data-delay", p.delay);
      sp.textContent = p.n.toLocaleString("es-MX", { minimumFractionDigits: p.dec || 0, maximumFractionDigits: p.dec || 0 });
    });
    return t;
  }
  function lienzo(host, w, h) {
    host.innerHTML = "";
    return el("svg", { viewBox: "0 0 " + w + " " + h, preserveAspectRatio: "xMidYMid meet" }, host);
  }
  function camino(puntos) {
    return puntos.map(function (p, i) { return (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1); }).join(" ");
  }
  function medirTrazos(s) {
    s.querySelectorAll("path.trazo, path.trazo-js").forEach(function (p) {
      if (p._largo) return;
      var L = Math.ceil(p.getTotalLength()) + 2;
      if (L < 4) return;                    // aun sin geometria (lamina oculta)
      p._largo = L;
      // Sin --len el patron de guiones es invalido y la linea se ve COMPLETA; al fijarlo, la
      // transicion del desfase corria de 0 a L y la linea se «borraba» sola al abrir la lamina.
      // Se fija sin transicion y se fuerza el estilo antes de devolverla.
      p.style.transition = "none";
      p.style.setProperty("--len", L);
      if (p.classList.contains("trazo-js")) { p.style.strokeDasharray = L; p.style.strokeDashoffset = p._dibujado ? 0 : L; }
      p.getBoundingClientRect();
      getComputedStyle(p).strokeDashoffset;
      p.style.transition = "";
      p.classList.add("medido");
    });
  }
  var mil = function (n) { return Math.round(n).toLocaleString("es-MX"); };
  var slideDe = function (host) { return host.closest(".slide"); };
  // Trazo dibujado por JS (cuando algo mas tiene que seguir la punta de la linea)
  function dibujaJS(p, f) {
    if (!p._largo) { var L = Math.ceil(p.getTotalLength()) + 2; if (L > 4) { p._largo = L; p.style.strokeDasharray = L; p.classList.add("medido"); } }
    p._dibujado = f >= 1;
    if (p._largo) p.style.strokeDashoffset = p._largo * (1 - f);
  }
  // Area entre la curva y el cero, azul arriba y roja abajo (recortes)
  function areas(svg, padre, pts, y0, W, Hh, attrs) {
    var u = uid(), d = "M" + pts[0][0] + " " + y0 + " " + camino(pts).replace(/^M/, "L") +
      " L" + pts[pts.length - 1][0] + " " + y0 + "Z";
    var cA = el("clipPath", { id: u + "a" }, svg); el("rect", { x: -10, y: -10, width: W + 20, height: y0 + 10 }, cA);
    var cB = el("clipPath", { id: u + "b" }, svg); el("rect", { x: -10, y: y0, width: W + 20, height: Hh }, cB);
    var a = el("path", Object.assign({ class: "area-azul", d: d, "clip-path": "url(#" + u + "a)" }, attrs || {}), padre);
    var b = el("path", Object.assign({ class: "area-roja", d: d, "clip-path": "url(#" + u + "b)" }, attrs || {}), padre);
    return [a, b];
  }

  /* ===================================================== portada / cierre: el eco */
  // La linea del caso, enorme y tenue, se dibuja detras del titulo: la historia
  // empieza y termina con la misma partida.
  function eco(host) {
    var s = slideDe(host), c = H.caso, W = 1600, Hh = 900, svg = lienzo(host, W, Hh);
    svg.setAttribute("preserveAspectRatio", "none");
    var n = c.serie.length - 1, tope = 9;
    var pts = c.serie.map(function (p) { return [40 + (p.min / c.serie[n].min) * 1520, 450 - (p.v / tope) * 380]; });
    el("line", { class: "eco-cero", x1: 40, x2: 1560, y1: 450, y2: 450 }, svg);
    var g = el("g", { class: "eco-areas" }, svg);
    areas(svg, g, pts, 450, W, Hh);
    var linea = el("path", { class: "eco-linea trazo-js", d: camino(pts) }, svg);
    efecto(s, 0, function (rapido) {
      g.classList.remove("ve");
      corre(s, rapido, parseInt(host.dataset.dur || "5200", 10), function (p) { dibujaJS(linea, p); }, {
        ease: "suave", delay: 300, fin: function () { g.classList.add("ve"); } });
    }, function () { dibujaJS(linea, 0); g.classList.remove("ve"); });
  }

  /* ===================================================== 1 · el mapa */
  function mapa(host) {
    var s = slideDe(host), S = 520, svg = lienzo(host, S, S);
    el("rect", { class: "mapa-fondo", x: 10, y: 10, width: S - 20, height: S - 20, rx: 18 }, svg);
    el("line", { class: "mapa-rio", x1: 70, y1: 70, x2: S - 70, y2: S - 70 }, svg);
    var carriles = el("g", {}, svg);
    el("path", { class: "mapa-carril", d: "M70 450 L70 110 Q70 70 110 70 L450 70" }, carriles);
    el("path", { class: "mapa-carril", d: "M70 450 L450 70" }, carriles);
    el("path", { class: "mapa-carril", d: "M70 450 L410 450 Q450 450 450 410 L450 70" }, carriles);
    // paso 3: torres en los tres caminos
    var torres = [[70, 330], [70, 220], [180, 340], [270, 250], [190, 450], [320, 450],
                  [450, 190], [450, 300], [340, 180], [250, 270], [330, 70], [200, 70]];
    torres.forEach(function (p, i) {
      el("rect", { class: (i < 6 ? "torre-azul" : "torre-roja") + " pop", x: p[0] - 8, y: p[1] - 8, width: 16, height: 16,
        "data-step": 3, style: "--delay:" + (i % 6) * 110 + "ms" }, svg);
    });
    // paso 2: las bases (el Nexo de cada equipo), con ondas
    var bases = el("g", { "data-step": 2 }, svg);
    [["azul", 70, 450], ["roja", 450, 70]].forEach(function (b) {
      el("circle", { class: "onda " + b[0], cx: b[1], cy: b[2], r: 26 }, bases);
      el("circle", { class: "onda " + b[0], cx: b[1], cy: b[2], r: 26, style: "animation-delay:1.1s" }, bases);
      el("circle", { class: "base-" + b[0], cx: b[1], cy: b[2], r: 26 }, bases);
    });
    txt({ class: "etq", x: 104, y: 494 }, "base azul", bases);
    txt({ class: "etq", x: 340, y: 36 }, "base roja", bases);
    // paso 3 (con las torres): los monstruos neutrales junto al rio; el paso 4 es el oro, sin dibujo
    var m = el("g", { "data-step": 3 }, svg);
    [[376, 358, 0, "dragones", 404, 392], [144, 162, 260, "el Barón", 52, 128]].forEach(function (q) {
      el("circle", { class: "onda oro", cx: q[0], cy: q[1], r: 18, style: "animation-delay:" + (q[2] + 1000) + "ms" }, m);
      el("path", { class: "monstruo pop", "data-step": 3, style: "--delay:" + (q[2] + 700) + "ms",
        d: "M" + (q[0] - 18) + " " + q[1] + " l18 -18 l18 18 l-18 18 z" }, m);
      txt({ class: "etq oro", x: q[4], y: q[5] }, q[3], m);
    });
    // paso 1: los diez jugadores salen de su base y caminan a su camino
    var azul = [[[70, 450], [70, 236]], [[70, 450], [206, 314]], [[70, 450], [118, 384], [150, 300]],
                [[70, 450], [300, 450]], [[70, 450], [268, 450], [272, 434]]];
    var rojo = azul.map(function (r, i) {
      return i === 2 ? [[450, 70], [384, 118], [372, 214]] : r.map(function (p) { return [p[1], p[0]]; });
    });
    var jug = [];
    [[azul, "jugador-azul", 0], [rojo, "jugador-rojo", 380]].forEach(function (eq) {
      eq[0].forEach(function (ruta, i) {
        var c = el("circle", { class: eq[1] + " jugador", cx: ruta[0][0], cy: ruta[0][1], r: 9 }, svg);
        jug.push({ c: c, ruta: ruta, delay: eq[2] + i * 120 });
      });
    });
    function sobre(ruta, f) {
      var L = [], tot = 0;
      for (var i = 1; i < ruta.length; i++) { var d = Math.hypot(ruta[i][0] - ruta[i - 1][0], ruta[i][1] - ruta[i - 1][1]); L.push(d); tot += d; }
      var obj = f * tot;
      for (var j = 0; j < L.length; j++) {
        if (obj <= L[j] || j === L.length - 1) {
          var q = L[j] ? Math.min(1, obj / L[j]) : 1;
          return [ruta[j][0] + (ruta[j + 1][0] - ruta[j][0]) * q, ruta[j][1] + (ruta[j + 1][1] - ruta[j][1]) * q];
        }
        obj -= L[j];
      }
    }
    efecto(s, 1, function (rapido) {
      jug.forEach(function (j) {
        j.c.classList.add("ve");
        corre(s, rapido, 1700, function (p) {
          var xy = sobre(j.ruta, p); j.c.setAttribute("cx", xy[0].toFixed(1)); j.c.setAttribute("cy", xy[1].toFixed(1));
        }, { ease: "suave", delay: j.delay });
      });
    }, function () {
      jug.forEach(function (j) { j.c.classList.remove("ve"); j.c.setAttribute("cx", j.ruta[0][0]); j.c.setAttribute("cy", j.ruta[0][1]); });
    });
  }

  /* ===================================================== 2 · el oro: una carrera */
  function oro(host) {
    var s = slideDe(host), c = H.caso, ser = c.oroSerie, W = 680, Hh = 360, svg = lienzo(host, W, Hh);
    var max = Math.max(c.oroMax.propio, c.oroMax.rival) * 1.02, X0 = 150, AN = 520;
    var X = function (v) { return X0 + (v / max) * AN; };
    var reloj = txt({ class: "etq reloj", x: X0, y: 40 }, "", svg);
    var barras = [["Mi equipo", "p", "azul", 76], ["Rival", "r", "rojo", 172]].map(function (f) {
      txt({ class: "etq", x: 0, y: f[3] + 34, style: "font-size:21px;fill:var(--parchment)" }, f[0], svg);
      el("rect", { class: "pista-barra", x: X0, y: f[3], width: AN, height: 52, rx: 6 }, svg);
      return { r: el("rect", { class: "barra " + f[2], x: X0, y: f[3], width: 0, height: 52, rx: 6 }, svg),
               t: txt({ class: "etq grande-num", x: X0, y: f[3] + 37 }, "", svg), k: f[1] };
    });
    function pinta(mf) {
      var i = Math.min(ser.length - 1, Math.floor(mf)), j = Math.min(ser.length - 1, i + 1), q = mf - i;
      barras.forEach(function (b) {
        var v = ser[i][b.k] + (ser[j][b.k] - ser[i][b.k]) * q, w = Math.max(0, X(v) - X0);
        b.r.setAttribute("width", w.toFixed(1));
        b.t.textContent = v > 0 ? mil(v) : "";
        var dentro = w > 170;
        b.t.setAttribute("x", dentro ? X0 + w - 14 : X0 + w + 12);
        b.t.setAttribute("text-anchor", dentro ? "end" : "start");
        b.t.classList.toggle("dentro", dentro);
      });
      reloj.textContent = "minuto " + ser[i].min;
    }
    pinta(0);
    var u = ser[ser.length - 1], fin = ser.length - 1;
    efecto(s, 2, function (rapido) {
      corre(s, rapido, 3600, function (p) { pinta(p * fin); }, { ease: "suave" });
    }, function () { pinta(0); });
    var g = el("g", { "data-step": 3 }, svg);
    // guias desde el final de cada barra hasta la llave (sin cruzar los numeros)
    el("line", { class: "marca", x1: X(u.r), x2: X(u.r), y1: 228, y2: 262 }, g);
    el("line", { class: "marca", x1: X(u.p), x2: X(u.p), y1: 132, y2: 262 }, g);
    el("path", { class: "llave trazo", "data-step": 3, d: "M" + X(u.r) + " 262 l0 10 L" + X(u.p) + " 272 l0 -10" }, svg);
    txtCuenta({ class: "etq oro", x: X(u.p), y: 310, "text-anchor": "end", style: "font-size:23px", "data-step": 3 },
      ["ventaja: +", { n: u.p - u.r, delay: 300 }, " de oro"], svg);
  }

  /* ===================================================== 3 · el caso */
  function caso(host, opt) {
    opt = opt || {};
    var s = slideDe(host), c = H.caso, W = 1300, Hh = opt.alto || 430;
    var M = { t: 56, r: 100, b: 62, l: 90 }, iw = W - M.l - M.r, ih = Hh - M.t - M.b;
    var svg = lienzo(host, W, Hh), n = c.serie.length - 1, ult = c.serie[n].min;
    var fin = Math.max(c.duracion, ult);
    var tope = Math.ceil(Math.max.apply(null, c.serie.map(function (p) { return Math.abs(p.v); }))) + 2;
    var X = function (m) { return M.l + (m / fin) * iw; };
    var Y = function (v) { return M.t + (1 - (v + tope) / (2 * tope)) * ih; };
    // Objetivos sin encimarse y cerca de su minuto real: cada icono va en la primera de dos
    // filas donde cabe; solo si no cabe en ninguna se recorre unos pixeles a la derecha.
    var posiciones = function (lista, sep) {
      var pos = new Map();
      [true, false].forEach(function (lado) {
        var filas = [-1e9, -1e9];
        lista.filter(function (o) { return o.propio === lado; }).forEach(function (o) {
          var x = X(o.min);
          var f = filas[0] + sep <= x ? 0 : filas[1] + sep <= x ? 1 : (filas[0] <= filas[1] ? 0 : 1);
          x = Math.max(x, filas[f] + sep);
          filas[f] = x;
          pos.set(o, { x: x, fila: f });
        });
      });
      return pos;
    };
    var valor = function (m) {          // el ultimo cuadro no cae en minuto entero
      var i = 0;
      while (i < n - 1 && c.serie[i + 1].min < m) i++;
      var a = c.serie[i], b = c.serie[i + 1], q = Math.max(0, Math.min(1, (m - a.min) / (b.min - a.min)));
      return a.v + (b.v - a.v) * q;
    };
    // franja dorada desde la ventaja maxima: de ahi en adelante, la ventaja se encoge
    var franja = el("rect", { class: "franja", x: X(c.min_max), y: M.t - 28, width: X(fin) - X(c.min_max), height: ih + 52 }, svg);
    var franjaTxt = txt({ class: "etq oro", x: X(c.min_max) + 10, y: M.t - 36 }, "desde aquí, la ventaja se encoge", svg);
    el("line", { class: "cero", x1: M.l, x2: M.l + iw, y1: Y(0), y2: Y(0) }, svg);
    txt({ class: "etq", x: M.l + iw + 14, y: Y(tope * 0.45) }, "vamos", svg);
    txt({ class: "etq", x: M.l + iw + 14, y: Y(tope * 0.45) + 18 }, "ganando", svg);
    txt({ class: "etq", x: M.l + iw + 14, y: Y(-tope * 0.45) }, "vamos", svg);
    txt({ class: "etq", x: M.l + iw + 14, y: Y(-tope * 0.45) + 18 }, "perdiendo", svg);
    for (var m = 0; m <= fin - 3; m += 5) txt({ class: "etq", x: X(m), y: M.t + ih + 28, "text-anchor": "middle" }, "min " + m, svg);
    var seg = Math.round((c.duracion % 1) * 60);
    txt({ class: "etq", x: X(c.duracion), y: M.t + ih + 28, "text-anchor": "middle" },
      "fin " + Math.floor(c.duracion) + ":" + (seg < 10 ? "0" : "") + seg, svg);

    // la linea y sus areas se descubren con un recorte que avanza junto al cabezal
    var pts = c.serie.map(function (p) { return [X(p.min), Y(p.v)]; });
    var u = uid(), cl = el("clipPath", { id: u }, svg), cr = el("rect", { x: 0, y: 0, width: 0, height: Hh }, cl);
    var g = el("g", { "clip-path": "url(#" + u + ")" }, svg);
    areas(svg, g, pts, Y(0), W, Hh);
    el("path", { class: "linea clara", d: camino(pts) }, g);

    var cab = el("g", { class: "cabezal" }, svg);
    el("line", { class: "cabezal-linea", x1: 0, x2: 0, y1: M.t - 14, y2: M.t + ih }, cab);
    var punto = el("circle", { class: "cabezal-punto", cx: 0, cy: Y(0), r: 8 }, cab);
    var etq = txt({ class: "etq cabezal-txt", x: 12, y: M.t + ih - 10 }, "", cab);
    function cabezal(mm, texto) {
      var v = valor(mm);
      cab.setAttribute("transform", "translate(" + X(mm).toFixed(1) + ",0)");
      punto.setAttribute("cy", Y(v).toFixed(1));
      punto.classList.toggle("abajo", v < 0);
      etq.textContent = texto !== undefined ? texto : "min " + Math.floor(mm) +
        (Math.abs(v) < 0.5 ? " · parejos" : v > 0 ? " · vamos ganando" : " · vamos perdiendo");
      etq.setAttribute("text-anchor", X(mm) > W - 300 ? "end" : "start");
      etq.setAttribute("x", X(mm) > W - 300 ? -14 : 14);
    }
    function revela(p) {
      var mm = p * ult;
      cr.setAttribute("width", (X(mm) + 2).toFixed(1));
      cabezal(mm);
      cab.classList.toggle("ve", p > 0 && p < 1);
    }
    revela(0);

    if (!opt.final) {
      // paso 1: la partida se reproduce de principio a fin
      efecto(s, 1, function (rapido) { corre(s, rapido, 5600, revela, { ease: "lineal" }); }, function () { revela(0); });
      // pasos 2 y 3: objetivos en orden de tiempo, con onda; los que caen juntos se recorren
      var k = { true: 0, false: 0 }, ordenados = c.objetivos.slice().sort(function (a, b) { return a.min - b.min; });
      var px = posiciones(ordenados, 17);
      ordenados.forEach(function (o) {
        var paso = o.propio ? 2 : 3, i = k[o.propio]++;
        var pp = px.get(o), cx = pp.x;
        var cy = o.propio ? M.t + 12 + pp.fila * 19 : M.t + ih - 12 - pp.fila * 19, cls = o.propio ? "azul" : "rojo";
        var d = "--delay:" + i * 120 + "ms";
        el("circle", { class: "onda-obj " + cls, cx: cx, cy: cy, r: 10, "data-step": paso, style: d }, svg);
        var at = { class: "icono pop " + cls, "data-step": paso, style: d };
        if (o.monstruo) { at.d = "M" + cx + " " + (cy - 10) + " l10 10 l-10 10 l-10 -10z"; el("path", at, svg); }
        else { at.x = cx - 7; at.y = cy - 7; at.width = 14; at.height = 14; el("rect", at, svg); }
      });
      txt({ class: "etq azul", x: M.l - 14, y: M.t + 17, "text-anchor": "end", "data-step": 2 }, "nuestros", svg);
      txt({ class: "etq rojo", x: M.l - 14, y: M.t + ih - 7, "text-anchor": "end", "data-step": 3 }, "del rival", svg);
      franja.setAttribute("data-step", 4); franja.classList.add("barre");
      franjaTxt.setAttribute("data-step", 4);
      // el remate: llave sobre los objetivos del rival de los ultimos 2 minutos
      // la llave abarca los iconos del remate donde quedaron dibujados (se recorren si no caben)
      var yr = M.t + ih - 58, xr = X(c.duracion - 2), xd = X(c.duracion);
      ordenados.forEach(function (o) {
        if (!o.propio && o.min >= c.duracion - 2) { xr = Math.min(xr, px.get(o).x - 9); xd = Math.max(xd, px.get(o).x + 9); }
      });
      el("path", { class: "llave roja trazo", "data-step": 4, style: "--delay:900ms;--dur:700ms",
        d: "M" + xr + " " + (yr + 8) + " l0 -8 L" + xd + " " + yr + " l0 8" }, svg);
      txt({ class: "etq rojo", x: xr - 10, y: yr + 6, "text-anchor": "end", "data-step": 4 }, "el remate", svg);
      return;
    }

    // ---- cierre: la partida se repite y luego se REBOBINA hasta el umbral
    var marca = el("g", { class: "marca-d2" }, svg);
    el("line", { class: "marca", x1: X(c.d2), x2: X(c.d2), y1: M.t - 18, y2: M.t + ih }, marca);
    txt({ class: "etq oro", x: X(c.d2) - 12, y: M.t - 24, "text-anchor": "end" }, "pasamos a ir abajo: minuto " + c.d2, marca);
    franjaTxt.textContent = "aquí empezó a encogerse la ventaja";
    franjaTxt.classList.add("aparece");
    var tardios = c.objetivos.filter(function (o) { return o.min >= c.min_max; }).sort(function (a, b) { return a.min - b.min; });
    var pr = posiciones(tardios, 15);
    var objs = tardios.map(function (o) {
      var pp = pr.get(o), cx = pp.x;
      var cy = o.propio ? M.t + 14 + pp.fila * 17 : M.t + ih - 14 - pp.fila * 17, cls = "icono obj-r " + (o.propio ? "azul" : "rojo"), e;
      if (o.monstruo) e = el("path", { class: cls, d: "M" + cx + " " + (cy - 9) + " l9 9 l-9 9 l-9 -9z" }, svg);
      else e = el("rect", { class: cls, x: cx - 6, y: cy - 6, width: 12, height: 12 }, svg);
      return { e: e, min: o.min };
    });
    function franjaEn(mm) {
      var x = X(mm);
      franja.setAttribute("x", x.toFixed(1)); franja.setAttribute("width", Math.max(0, X(fin) - x).toFixed(1));
      objs.forEach(function (o) { o.e.classList.toggle("ve", o.min >= mm - 0.01); });
    }
    franjaEn(fin); franjaTxt.classList.remove("ve");
    efecto(s, 0, function (rapido) {
      marca.classList.remove("ve");
      corre(s, rapido, 2600, revela, { ease: "lineal", delay: 500, fin: function () { marca.classList.add("ve"); } });
    }, function () { revela(0); marca.classList.remove("ve"); });
    efecto(s, 1, function (rapido) {
      franjaTxt.classList.remove("ve");
      corre(s, rapido, 2800, function (p) {
        var mm = c.d2 - (c.d2 - c.min_max) * p;
        franjaEn(mm); cabezal(mm, "min " + Math.round(mm)); cab.classList.toggle("ve", p > 0 && p < 1);
      }, { ease: "suave", fin: function () { franjaTxt.classList.add("ve"); } });
    }, function () { franjaEn(fin); franjaTxt.classList.remove("ve"); cab.classList.remove("ve"); });
  }

  /* ===================================================== 4 · las fotos */
  function tira(host) {
    var c = H.caso, h = "";
    var ult = Math.min(36, c.serie.length) - 1;
    c.serie.slice(0, 36).forEach(function (p, i) {
      var alto = Math.min(100, Math.abs(p.v) * 11 + 6);
      h += '<div class="foto" style="--i:' + i + '"><span class="m">' + (i === ult ? "fin" : p.min + "'") + "</span>" +
        '<span class="b ' + (p.v >= 0 ? "azul" : "rojo") + '" style="height:' + alto + '%"></span></div>';
    });
    host.innerHTML = h;
  }

  /* ===================================================== 5 · la medida */
  function medida(host) {
    var e = H.ejemplo, W = 720, Hh = 320, svg = lienzo(host, W, Hh);
    [[5, e.total5, 1, 40], [30, e.total30, 2, 180]].forEach(function (f) {
      txtCuenta({ class: "etq", x: 0, y: f[3], style: "font-size:20px;fill:var(--parchment)", "data-step": f[2] },
        ["Minuto " + f[0] + ": en el mapa hay unos ", { n: Math.round(f[1] / 100) * 100 }, " de oro"], svg);
      // la barra del oro total es una pista (no un dato): clara y con borde, para que la
      // etiqueta en oro que va encima se lea en los dos temas
      el("rect", { class: "barra total crece", x: 0, y: f[3] + 16, width: 700, height: 46, rx: 6, "data-step": f[2] }, svg);
      var w = 700 * e.ventaja / f[1];
      el("rect", { class: "barra oro crece", x: 0, y: f[3] + 16, width: w, height: 46, rx: 6, "data-step": f[2],
        style: "--delay:650ms" }, svg);
      txtCuenta({ class: "etq oro", x: Math.max(w, 8) + 14, y: f[3] + 47, style: "font-size:22px", "data-step": f[2] },
        ["+2,000 = ", { n: Math.round(100 * e.ventaja / f[1]), delay: 650 }, " % del oro"], svg);
      if (f[0] === 30) {   // lo diminuto se señala: si no, no se ve
        el("ellipse", { class: "senal", cx: w / 2 + 1, cy: f[3] + 39, rx: 15, ry: 29, "data-step": f[2] }, svg);
      }
    });
  }

  /* ===================================================== 6 · el tropiezo */
  function tropiezo(host) {
    var W = 1300, Hh = 300, svg = lienzo(host, W, Hh), anchoPanel = 600;
    var max = Math.max.apply(null, H.d1.derrotas.concat(H.d1.victorias));
    [["derrotas", "En mis derrotas", 0, 1, "rojo"], ["victorias", "En mis victorias", 680, 2, "azul"]].forEach(function (f) {
      var datos = H.d1[f[0]], x0 = f[2], bw = anchoPanel / datos.length;
      txt({ class: "etq", x: x0, y: 24, style: "font-size:20px;fill:var(--parchment)", "data-step": f[3] }, f[1], svg);
      txt({ class: "etq", x: x0 + anchoPanel, y: 24, "text-anchor": "end", "data-step": f[3] }, "barra = % de partidas", svg);
      datos.forEach(function (v, m) {
        var h = (v / max) * 200;
        el("rect", { class: "barra " + f[4] + " sube", x: x0 + m * bw + 2, y: 250 - h, width: bw - 4, height: h,
          "data-step": f[3], style: "--delay:" + m * 28 + "ms" }, svg);
      });
      [0, 5, 10, 20, 30].forEach(function (m) {
        txt({ class: "etq", x: x0 + m * bw + bw / 2, y: 278, "text-anchor": "middle", "data-step": f[3] }, "min " + m, svg);
      });
      // paso 3: el circulo a mano alzada sobre los primeros minutos
      // dentro del margen izquierdo y sin tocar las etiquetas de minutos
      var cx = x0 + 6 * bw, rx = 6 * bw;
      el("path", { class: "circulo trazo", "data-step": 3, style: "--dur:900ms",
        d: "M" + (cx - rx) + " 138 a" + rx + " 88 0 1 1 " + (2 * rx) + " 0 a" + rx + " 88 0 1 1 " + (-2 * rx + 16) + " -10" }, svg);
      txt({ class: "etq oro", x: cx + rx + 12, y: 70, "data-step": 3, style: "font-size:19px" }, "casi todo cae aquí", svg);
    });
  }

  /* ===================================================== 7 · pista 1 */
  function pista1(host) {
    // las fases salen de las llaves del resultado («<15», «15-25», «>=25»), no de texto fijo
    var ks = Object.keys(H.h1), lim = ks[1].split("-");
    var s = slideDe(host), W = 1300, Hh = 340, svg = lienzo(host, W, Hh), fases = [
      [ks[0], "Antes del minuto " + lim[0]], [ks[1], "Del minuto " + lim[0] + " al " + lim[1]],
      [ks[2], "Del " + lim[1] + " en adelante"]];
    var X = function (v) { return 360 + v * 640; }, grupos = [];
    fases.forEach(function (f, i) {
      var y0 = 26 + i * 104, d = H.h1[f[0]], paso = i + 1, g = el("g", { class: "fase" }, svg);
      grupos.push(g);
      txt({ class: "etq", x: 0, y: y0 + 42, style: "font-size:21px;fill:var(--parchment)", "data-step": paso }, f[1], g);
      [["vic", "azul", 0, " en victorias"], ["der", "rojo", 40, " en derrotas"]].forEach(function (b, j) {
        el("rect", { class: "barra " + b[1] + " crece", x: 360, y: y0 + b[2], width: X(d[b[0]]) - 360, height: 32, rx: 5,
          "data-step": paso, style: "--delay:" + j * 260 + "ms" }, g);
        txtCuenta({ class: "etq " + b[1], x: X(d[b[0]]) + 12, y: y0 + b[2] + 23, "data-step": paso, style: "font-size:19px" },
          [{ n: Math.round(d[b[0]] * 100) / 10, dec: 1, delay: j * 260 }, b[3]], g);
      });
    });
    // paso 4: la diferencia vive despues del minuto 15
    el("path", { class: "recuadro trazo", "data-step": 4, style: "--dur:1100ms",
      d: "M342 118 L1298 118 L1298 330 L342 330 Z" }, svg);
    efecto(s, 4, function () { grupos[0].classList.add("tenue"); }, function () { grupos[0].classList.remove("tenue"); });
    // donde los intervalos se enciman, la diferencia no se distingue del azar: se dice
    fases.forEach(function (f, i) {
      if (H.h1[f[0]].empate) txt({ class: "etq oro", x: 0, y: 26 + i * 104 + 70, "data-step": 4, style: "font-size:16px" },
        "diferencia dentro del margen de error", svg);
    });
  }

  /* ===================================================== 8 · pista 2 */
  function pista2(host) {
    var W = 1300, Hh = 320, svg = lienzo(host, W, Hh), h2 = H.h2;
    var X = function (v) { return 330 + (v / 50) * 700; };
    [["Cuando pierdo", h2.obsDer, h2.azarDer, 1, 20], ["Cuando gano", h2.obsVic, h2.azarVic, 2, 170]].forEach(function (f) {
      var y = f[4], obs = Math.round(f[1]), azar = Math.round(f[2]);
      txt({ class: "etq", x: 0, y: y + 54, style: "font-size:22px;fill:var(--parchment)", "data-step": f[3] }, f[0], svg);
      el("rect", { class: "barra oro crece", x: 330, y: y + 10, width: X(f[1]) - 330, height: 34, rx: 5, "data-step": f[3] }, svg);
      txtCuenta({ class: "etq oro", x: X(f[1]) + 12, y: y + 34, "data-step": f[3], style: "font-size:19px" },
        [{ n: obs }, " %  cae junto a un monstruo del rival"], svg);
      el("rect", { class: "barra gris crece", x: 330, y: y + 54, width: X(f[2]) - 330, height: 34, rx: 5,
        "data-step": f[3], style: "--delay:300ms" }, svg);
      txtCuenta({ class: "etq", x: X(f[2]) + 12, y: y + 78, "data-step": f[3], style: "font-size:19px" },
        [{ n: azar, delay: 300 }, " %  lo que daría la pura casualidad"], svg);
      // paso 3: cuanto se separa del azar
      el("path", { class: "llave trazo", "data-step": 3, d: "M" + X(f[2]) + " " + (y + 104) + " l0 10 L" + X(f[1]) + " " + (y + 114) + " l0 -10" }, svg);
      txt({ class: "etq oro brecha", x: X(f[1]) + 12, y: y + 122, "data-step": 3, style: "font-size:19px" },
        "+" + (obs - azar) + " sobre el azar", svg);
    });
  }

  /* ===================================================== 9 · pista 3: «de cada 20» */
  function figuras(host, gana) {
    var svg = lienzo(host, 300, 150);
    for (var i = 0; i < 20; i++) {
      var cx = 18 + (i % 10) * 29, cy = 30 + Math.floor(i / 10) * 72;
      var g = el("g", { class: "persona" + (i < gana ? " gana" : ""), style: "--i:" + i }, svg);
      el("circle", { cx: cx, cy: cy - 10, r: 8 }, g);
      el("path", { d: "M" + (cx - 11) + " " + (cy + 26) + " q0 -22 11 -22 q11 0 11 22 z" }, g);
    }
  }
  function curva3(host) {
    var s = slideDe(host), W = 1300, Hh = 214, svg = lienzo(host, W, Hh), c = H.curva;
    var maxM = c[c.length - 1].min;
    var X = function (m) { return 80 + (m / maxM) * 1150; }, Y = function (p) { return 20 + (1 - p / 60) * 170; };
    [0, 20, 40, 60].forEach(function (p) {
      el("line", { class: "eje", x1: 80, x2: 1230, y1: Y(p), y2: Y(p) }, svg);
      txt({ class: "etq", x: 66, y: Y(p) + 5, "text-anchor": "end" }, p + " %", svg);
    });
    [5, 10, 15, 20, 25, 30, 35].forEach(function (m) { if (m <= maxM) txt({ class: "etq", x: X(m), y: 210, "text-anchor": "middle" }, "min " + m, svg); });
    // a la izquierda de la marca del punto sin regreso, para que la linea no lo cruce
    txt({ class: "etq oro", x: X(8), y: Y(48), "text-anchor": "start", style: "font-size:16px" },
      "de las que van perdiendo en ese minuto, % que termina ganando", svg);
    var pts = c.map(function (p) { return [X(p.min), Y(p.p)]; });
    var linea = el("path", { class: "linea azul trazo-js", d: camino(pts) }, svg);
    var punta = el("circle", { class: "punta", r: 7, cx: pts[0][0], cy: pts[0][1] }, svg);
    var etq = txt({ class: "etq punta-txt", x: pts[0][0], y: pts[0][1] - 16, "text-anchor": "middle" }, "", svg);
    // los tres minutos de las figuras, marcados sobre la curva
    var hitos = [5, 15, 30].map(function (m) {
      var p = c.filter(function (q) { return q.min === m; })[0];
      return p ? el("circle", { class: "hito", cx: X(m), cy: Y(p.p), r: 9 }, svg) : null;
    }).filter(Boolean);
    // el punto sin regreso de H3: aparece cuando la curva ya llegó ahí
    var punto = null;
    if (H.punto && H.punto.minuto <= maxM) {
      var xp = X(H.punto.minuto), yu = Y(100 * H.punto.umbral);
      punto = el("g", { class: "aparece" }, svg);
      el("line", { class: "marca", x1: 80, x2: 1230, y1: yu, y2: yu }, punto);
      el("line", { class: "cabezal-linea", x1: xp, x2: xp, y1: Y(60), y2: Y(0) }, punto);
      txt({ class: "etq oro", x: xp + 10, y: Y(30), style: "font-size:17px" },
        "desde el minuto " + H.punto.minuto + ": menos de 1 de cada 20", punto);
    }
    function pinta(f) {
      dibujaJS(linea, f);
      if (punto) punto.classList.toggle("ve", f >= 1);
      var mm = f * (c.length - 1), i = Math.min(c.length - 2, Math.floor(mm)), q = mm - i;
      var x = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * q, y = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * q;
      var val = c[i].p + (c[i + 1].p - c[i].p) * q;
      punta.setAttribute("cx", x.toFixed(1)); punta.setAttribute("cy", y.toFixed(1));
      etq.setAttribute("x", x.toFixed(1)); etq.setAttribute("y", (y - 16).toFixed(1));
      etq.textContent = "min " + c[i].min + ": " + Math.round(val) + " %";
      punta.classList.toggle("ve", f > 0 && f < 1); etq.classList.toggle("ve", f > 0 && f < 1);
      hitos.forEach(function (h) { h.classList.toggle("ve", f >= 1); });
    }
    pinta(0);
    efecto(s, 4, function (rapido) { corre(s, rapido, 3000, pinta, { ease: "lineal", delay: 250 }); }, function () { pinta(0); });
  }

  /* ===================================================== 10 · las formas de perder */
  var TOPE_FORMAS = null;
  function forma(host, clave, paso) {
    if (TOPE_FORMAS === null) {
      TOPE_FORMAS = 2;
      for (var k in H.formas) H.formas[k].forEach(function (p) { TOPE_FORMAS = Math.max(TOPE_FORMAS, Math.abs(p.v)); });
      TOPE_FORMAS = Math.ceil(TOPE_FORMAS + 1);
    }
    var datos = H.formas[clave], W = 300, Hh = 280, svg = lienzo(host, W, Hh);
    var X = function (m) { return 8 + (m / 45) * 284; }, Y = function (v) { return 140 - (v / TOPE_FORMAS) * 132; };
    el("line", { class: "cero", x1: 8, x2: 292, y1: Y(0), y2: Y(0) }, svg);
    var pts = datos.map(function (p) { return [X(p.min), Y(p.v)]; });
    areas(svg, svg, pts, Y(0), W, Hh, { "data-step": paso, class: null }).forEach(function (a, i) {
      a.setAttribute("class", (i ? "area-roja" : "area-azul") + " tarde");
    });
    el("path", { class: "linea clara trazo", d: camino(pts), "data-step": paso, style: "--dur:1500ms" }, svg);
  }

  /* ================================================================ fondo vivo */
  // Motas doradas que suben despacio y un resplandor que cambia de color con el acto.
  function fondo() {
    var cv = document.createElement("canvas");
    cv.id = "fondo"; cv.width = 1600; cv.height = 900; cv.setAttribute("aria-hidden", "true");
    stage.insertBefore(cv, stage.firstChild);
    var b = document.createElement("div"); b.id = "barrido"; stage.appendChild(b);
    var cx = cv.getContext("2d"), semilla = 20261010;
    var azar = function () { semilla = (semilla * 16807) % 2147483647; return (semilla - 1) / 2147483646; };
    // Tramado: un grano fijo de 0 a ~3 niveles de gris encima de todo. Los degradados oscuros
    // (el resplandor, el velo de DERROTA) avanzan un nivel cada ~40 px y, sin esto, se ven
    // como anillos; el grano rompe los escalones y a simple vista no se nota.
    var tg = document.createElement("canvas"); tg.width = tg.height = 256;
    var gx = tg.getContext("2d"), px = gx.createImageData(256, 256);
    for (var q = 0; q < px.data.length; q += 4) {
      px.data[q] = px.data[q + 1] = px.data[q + 2] = 255;
      px.data[q + 3] = Math.round(azar() * 3.6);        // alfa 0-3.6 de 255: hasta ~3 niveles
    }
    gx.putImageData(px, 0, 0);
    var grano = document.createElement("div"); grano.id = "grano"; grano.setAttribute("aria-hidden", "true");
    grano.style.backgroundImage = "url(" + tg.toDataURL("image/png") + ")";
    stage.appendChild(grano);
    var motas = [];
    for (var i = 0; i < 64; i++) motas.push({ x: azar() * 1600, y: azar() * 900, r: 0.7 + azar() * 1.9, v: 5 + azar() * 15, f: azar() * 6.28, a: 0.1 + azar() * 0.38 });
    var color = [188, 139, 44], meta = color.slice(), previo = null;
    stage._tono = function (rgb) { meta = rgb.slice(); if (quieto()) { color = rgb.slice(); cuadro(0, true); } };
    // al cambiar de tema: si no hay animacion corriendo, el fondo se vuelve a pintar una vez
    stage._repinta = function () { if (quieto()) cuadro(0, true); };
    function cuadro(ts, unaVez) {
      var dt = previo === null ? 16 : Math.min(64, ts - previo); previo = ts;
      for (var k = 0; k < 3; k++) color[k] += (meta[k] - color[k]) * Math.min(1, dt / 700);
      cx.clearRect(0, 0, 1600, 900);
      // sobre papel claro el resplandor se baja y las motas pasan a oro oscuro
      var esClaro = claro(), mota = esClaro ? "150,104,14," : "232,200,122,";
      var gx = 800 + Math.sin(ts / 9000) * 420, gy = 360 + Math.cos(ts / 12000) * 180;
      var g = cx.createRadialGradient(gx, gy, 0, gx, gy, 980);
      g.addColorStop(0, "rgba(" + color.map(Math.round).join(",") + (esClaro ? ",0.08)" : ",0.14)"));
      g.addColorStop(1, "rgba(10,26,43,0)");
      cx.fillStyle = g; cx.fillRect(0, 0, 1600, 900);
      motas.forEach(function (m) {
        if (!unaVez) { m.y -= m.v * dt / 1000; if (m.y < -10) { m.y = 910; m.x = azar() * 1600; } }
        var x = m.x + Math.sin(ts / 2600 + m.f) * 16, al = m.a * (0.55 + 0.45 * Math.sin(ts / 900 + m.f * 3));
        cx.beginPath(); cx.arc(x, m.y, m.r, 0, 6.283);
        cx.fillStyle = "rgba(" + mota + (esClaro ? al * 0.7 : al).toFixed(3) + ")"; cx.fill();
      });
      if (!unaVez) requestAnimationFrame(cuadro);
    }
    if (quieto()) cuadro(0, true); else requestAnimationFrame(cuadro);
  }

  /* ================================================================ texto vivo */
  // Cada palabra de los titulares en su propio span (para que entren una por una).
  function partePalabras(raiz) {
    var i = 0;
    (function rec(nodo) {
      Array.prototype.slice.call(nodo.childNodes).forEach(function (n) {
        if (n.nodeType === 3) {
          var frag = document.createDocumentFragment();
          n.textContent.split(/(\s+)/).forEach(function (p) {
            if (!p) return;
            if (/^\s+$/.test(p)) { frag.appendChild(document.createTextNode(p)); return; }
            var sp = document.createElement("span");
            sp.className = "w"; sp.style.setProperty("--wi", i++); sp.textContent = p;
            frag.appendChild(sp);
          });
          nodo.replaceChild(frag, n);
        } else if (n.nodeType === 1 && !n.classList.contains("sub")) rec(n);
      });
    })(raiz);
  }
  function parteLetras(el) {
    var t = el.textContent.trim(); el.textContent = "";
    t.split("").forEach(function (ch, i) {
      var sp = document.createElement("span"); sp.className = "l"; sp.style.setProperty("--li", i); sp.textContent = ch;
      el.appendChild(sp);
    });
    el.setAttribute("aria-label", t);
  }

  /* ================================================================ ARRANQUE */
  function boot() {
    buildRail();
    if (VIDEO) document.body.classList.add("video", "cine");
    slides = Array.prototype.slice.call(document.querySelectorAll(".slide"));
    document.getElementById("pagetot").textContent = String(slides.length);
    document.querySelectorAll(".slide h2, .slide h1, .cierre-grande, .grande").forEach(partePalabras);
    document.querySelectorAll(".defeat-word").forEach(parteLetras);
    fondo();
    var dibujar = {
      eco: eco, mapa: mapa, oro: oro, tira: tira, medida: medida, tropiezo: tropiezo, pista1: pista1, pista2: pista2,
      curva3: curva3,
      caso: function (h) { caso(h, {}); },
      cierre: function (h) { caso(h, { alto: 330, final: true }); }
    };
    document.querySelectorAll("[data-dibujo]").forEach(function (h) {
      var d = h.dataset.dibujo;
      if (dibujar[d]) dibujar[d](h);
      else if (d.indexOf("figuras:") === 0) figuras(h, parseInt(d.split(":")[1], 10));
      else if (d.indexOf("forma:") === 0) forma(h, d.slice(6), parseInt(h.dataset.paso || "1", 10));
    });
    var m = /#d(\d+)$/.exec(location.hash);
    var start = m ? Math.min(slides.length, Math.max(1, parseInt(m[1], 10))) - 1 : 0;
    slides.forEach(function (s) { s.classList.remove("active"); });
    idx = start;
    var s = slides[idx];
    s.classList.add("active", "enter");
    medirTrazos(s);
    pintaPasos(s, TODO ? maxPaso(s) : 0, quieto());
    s._seen = true;
    stage._tono(tonoDe(s));
    fitStage();
    flashHelp();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
