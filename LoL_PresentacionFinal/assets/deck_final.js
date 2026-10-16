/* =========================================================================
   Presentacion final - motor
   Derivado de LoL_Presentacion/assets/deck.js (misma navegacion, pasos,
   pantalla en negro y contadores). Cambia:
     * el riel: las secciones de la rubrica final;
     * la grafica: v(t) en % del oro del mapa, con la escala tomada del dato
       (la original tenia ejes fijos en oro para otra partida).
   Todo el dato sale de window.LOL_DATA, que construir.py escribe en el HTML.
   ========================================================================= */

(function () {
  "use strict";

  var D = window.LOL_DATA || {};
  var stage = document.getElementById("stage");
  var slides = [];
  var idx = 0;

  /* ---------------------------------------------------------------- escala */
  function fitStage() {
    var s = Math.min(window.innerWidth / 1600, window.innerHeight / 900);
    stage.style.transform = "scale(" + s + ")";
  }
  window.addEventListener("resize", fitStage);

  /* ------------------------------------------------------------ navegacion */
  var RAIL = [
    { id: 1, label: "Problema" },
    { id: 2, label: "Hipótesis" },
    { id: 3, label: "Datos y método" },
    { id: 4, label: "Resultados" },
    { id: 5, label: "Conclusiones" }
  ];

  function buildRail() {
    var rail = document.getElementById("rail");
    if (!rail) return;
    var html = "";
    RAIL.forEach(function (r) {
      html += '<div class="rail-item" data-sec="' + r.id + '"><span class="num">' + r.id +
        "</span><span>" + r.label + "</span></div>";
    });
    html += '<div class="rail-item spacer"></div>';
    html += '<div class="counter"><span id="pageno">1</span> / <span id="pagetot">1</span>' +
      '<span class="pasos" id="pasos"></span></div>';
    rail.innerHTML = html;
  }

  function updateRail() {
    var sec = parseInt(slides[idx].dataset.sec || "0", 10);
    document.querySelectorAll(".rail-item[data-sec]").forEach(function (el) {
      var n = parseInt(el.dataset.sec, 10);
      el.classList.toggle("on", n === sec);
      el.classList.toggle("done", n < sec);
    });
    var pn = document.getElementById("pageno");
    if (pn) pn.textContent = String(idx + 1);
    var pb = document.getElementById("progress");
    if (pb) pb.style.width = ((idx + 1) / slides.length) * 100 + "%";
    var ps = document.getElementById("pasos");
    if (ps) {
      var cur = slides[idx], mx = maxPaso(cur), h = "";
      for (var q = 1; q <= mx; q++) h += "<i class='" + (q <= (cur._paso || 0) ? "on" : "") + "'></i>";
      ps.innerHTML = h;
    }
  }

  var MENOS_MOV = window.matchMedia
    ? window.matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };

  // Las cifras que SON el argumento cuentan hasta su valor; el HTML ya trae el
  // numero final, asi que sin JS la lamina se lee igual.
  function contar(root, visto) {
    Array.prototype.forEach.call(root.querySelectorAll("[data-count]"), function (el) {
      var fin = parseFloat(el.dataset.count);
      var dec = parseInt(el.dataset.dec || "0", 10);
      var pre = el.dataset.prefix || "", suf = el.dataset.suffix || "";
      var pinta = function (v) {
        return pre + v.toLocaleString("es-MX", { minimumFractionDigits: dec, maximumFractionDigits: dec }) + suf;
      };
      if (visto || MENOS_MOV.matches || isNaN(fin)) { el.textContent = pinta(fin); return; }
      var ini = null, DUR = 820, ESPERA = 360;
      el.textContent = pinta(0);
      requestAnimationFrame(function paso(ts) {
        if (ini === null) ini = ts;
        var p = (ts - ini - ESPERA) / DUR;
        if (p < 0) { requestAnimationFrame(paso); return; }
        if (p >= 1) { el.textContent = pinta(fin); return; }
        el.textContent = pinta(fin * (1 - Math.pow(1 - p, 3)));
        requestAnimationFrame(paso);
      });
    });
  }

  function show(n, back) {
    if (n < 0 || n >= slides.length) return;
    slides[idx].classList.remove("active", "enter", "enter-back");
    idx = n;
    var s = slides[idx];
    var visto = s._seen === true;
    s.classList.toggle("visto", visto);
    s.classList.add("active", back ? "enter-back" : "enter");
    pintaPasos(s, (TODO || back || visto) ? maxPaso(s) : 0);
    if (typeof s._onEnter === "function") s._onEnter(s, visto);
    contar(s, visto);
    s._seen = true;
    location.replace(location.pathname + location.search + "#d" + (idx + 1));
  }

  /* Pasos: [data-step] se descubre por partes; ?todo apaga el sistema. */
  var TODO = /[?&]todo\b/.test(location.search);
  function pasosDe(s) { return Array.prototype.slice.call(s.querySelectorAll("[data-step]")); }
  function maxPaso(s) {
    return pasosDe(s).reduce(function (m, e) { return Math.max(m, parseInt(e.dataset.step, 10) || 0); }, 0);
  }
  function pintaPasos(s, n) {
    s._paso = n;
    pasosDe(s).forEach(function (e) {
      e.classList.toggle("mostrado", (parseInt(e.dataset.step, 10) || 0) <= n);
    });
    updateRail();
  }
  function next() {
    var s = slides[idx];
    if (!TODO && s._paso < maxPaso(s)) { pintaPasos(s, s._paso + 1); return; }
    show(idx + 1, false);
  }
  function prev() {
    var s = slides[idx], mx = maxPaso(s);
    if (!TODO && mx && s._paso > 0 && s._paso < mx) { pintaPasos(s, s._paso - 1); return; }
    show(idx - 1, true);
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
      if (document.fullscreenElement) document.exitFullscreen();
      else document.documentElement.requestFullscreen();
    }
    else if (k === "r" || k === "R") {
      e.preventDefault();
      var cur = slides[idx];
      if (typeof cur._onEnter === "function") cur._onEnter(cur, false);
    }
    else if (/^[1-5]$/.test(k)) {                 // saltar a una seccion de la rubrica
      e.preventDefault();
      for (var q = 0; q < slides.length; q++) {
        if (slides[q].dataset.sec === k) { show(q, q < idx); break; }
      }
    }
    else if (k === "a" || k === "A") { e.preventDefault(); pintaPasos(slides[idx], maxPaso(slides[idx])); }
    else if (k === "?" || k === "h" || k === "H") { e.preventDefault(); flashHelp(); }
  });

  var dnX = 0, dnY = 0;
  document.addEventListener("mousedown", function (e) { dnX = e.clientX; dnY = e.clientY; });
  document.addEventListener("click", function (e) {
    if (e.target.closest("a")) return;
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
    if (!h) return;
    h.classList.add("show");
    clearTimeout(helpT);
    helpT = setTimeout(function () { h.classList.remove("show"); }, 2200);
  }

  /* =====================================================================
     V1 · v(t) DE UNA DERROTA PROPIA
     Divergente: arriba de cero, ventaja de mi equipo (azul); abajo, del
     rival (rojo). Los objetivos van en dos filas fuera de la curva: arriba
     los mios, abajo los del rival. Rombo = monstruo epico, cuadro = estructura.
     ===================================================================== */
  var NS = "http://www.w3.org/2000/svg";
  function el(name, attrs) {
    var e = document.createElementNS(NS, name);
    for (var k in attrs) if (attrs[k] !== undefined && attrs[k] !== null) e.setAttribute(k, attrs[k]);
    return e;
  }
  function txt(attrs, s) { var t = el("text", attrs); t.textContent = s; return t; }

  function renderV(host, opt) {
    opt = opt || {};
    host.innerHTML = "";
    var g = D.v1 && D.v1.serie;
    if (!g || !g.length) return;
    var W = 1180, H = opt.height || 400;
    var M = { t: 64, r: 120, b: 66, l: 74 };
    var iw = W - M.l - M.r, ih = H - M.t - M.b;
    var maxMin = D.v1.duracion;
    var vals = g.map(function (p) { return p.v; });
    var tope = Math.max(4, Math.ceil(Math.max.apply(null, vals.map(Math.abs)) / 2) * 2 + 2);
    var yMin = -tope, yMax = tope;
    var X = function (m) { return M.l + (m / maxMin) * iw; };
    var Y = function (v) { return M.t + (1 - (v - yMin) / (yMax - yMin)) * ih; };
    var svg = el("svg", { class: "chart", viewBox: "0 0 " + W + " " + H, preserveAspectRatio: "xMidYMid meet" });

    for (var v = -tope; v <= tope; v += 2) {
      if (v === 0) continue;
      svg.appendChild(el("line", { class: "grid-line", x1: M.l, x2: M.l + iw, y1: Y(v), y2: Y(v) }));
      svg.appendChild(txt({ class: "axis-label", x: M.l - 12, y: Y(v) + 4, "text-anchor": "end" },
        (v > 0 ? "+" : "−") + Math.abs(v) + " %"));
    }
    for (var m = 0; m <= maxMin; m += 5) {
      svg.appendChild(txt({ class: "axis-label", x: X(m), y: M.t + ih + 22, "text-anchor": "middle" }, m + "'"));
    }

    // area: un solo poligono hasta cero, recortado arriba (azul) y abajo (rojo)
    var area = "M " + X(0) + " " + Y(0);
    g.forEach(function (p) { area += " L " + X(p.min) + " " + Y(p.v); });
    area += " L " + X(g[g.length - 1].min) + " " + Y(0) + " Z";
    var uidA = "arriba" + (renderV._n = (renderV._n || 0) + 1), uidB = "abajo" + renderV._n;
    var cA = el("clipPath", { id: uidA }); cA.appendChild(el("rect", { x: 0, y: 0, width: W, height: Y(0) }));
    var cB = el("clipPath", { id: uidB }); cB.appendChild(el("rect", { x: 0, y: Y(0), width: W, height: H }));
    svg.appendChild(cA); svg.appendChild(cB);
    var gPos = el("g", { "clip-path": "url(#" + uidA + ")" });
    gPos.appendChild(el("path", { class: "area-pos", d: area }));
    var gNeg = el("g", { "clip-path": "url(#" + uidB + ")" });
    gNeg.appendChild(el("path", { class: "area-neg", d: area }));
    svg.appendChild(gPos); svg.appendChild(gNeg);

    svg.appendChild(el("line", { class: "zero-line", x1: M.l, x2: M.l + iw, y1: Y(0), y2: Y(0) }));
    svg.appendChild(txt({ class: "axis-label", x: M.l + iw + 10, y: Y(0) + 4 }, "empate"));
    svg.appendChild(txt({ class: "axis-label", x: M.l + iw + 10, y: Y(tope * .6) }, "arriba"));
    svg.appendChild(txt({ class: "axis-label", x: M.l + iw + 10, y: Y(-tope * .6) }, "abajo"));

    var d = "";
    g.forEach(function (p, i) { d += (i ? " L " : "M ") + X(p.min) + " " + Y(p.v); });
    svg.appendChild(el("path", { class: "adv-line", d: d }));

    // objetivos, en filas fuera de la curva
    var filas = { ours: M.t - 26, theirs: M.t + ih + 44 };
    (D.v1.objetivos || []).forEach(function (o) {
      var lado = o.propio ? "ours" : "theirs";
      var cx = X(o.min), cy = filas[lado];
      var grp = el("g", { class: "evt " + lado });
      if (o.monstruo) {
        grp.appendChild(el("path", { d: "M " + cx + " " + (cy - 8) + " L " + (cx + 8) + " " + cy +
          " L " + cx + " " + (cy + 8) + " L " + (cx - 8) + " " + cy + " Z" }));
      } else {
        grp.appendChild(el("rect", { x: cx - 5.5, y: cy - 5.5, width: 11, height: 11 }));
      }
      svg.appendChild(grp);
    });
    svg.appendChild(txt({ class: "row-label", x: M.l - 12, y: filas.ours + 5, "text-anchor": "end" }, "mi equipo"));
    svg.appendChild(txt({ class: "row-label", x: M.l - 12, y: filas.theirs + 5, "text-anchor": "end" }, "rival"));

    (opt.marcas || []).forEach(function (a) {
      var x = X(a.min);
      svg.appendChild(el("line", { class: "marker-line", x1: x, x2: x, y1: M.t - 8, y2: M.t + ih }));
      var anchor = a.anchor || (x > M.l + iw * 0.7 ? "end" : "start");
      svg.appendChild(txt({ class: "marker-text", x: x + (anchor === "end" ? -9 : 9),
        y: Y(a.y !== undefined ? a.y : tope * .85), "text-anchor": anchor }, a.text));
    });
    host.appendChild(svg);

    // CORTINA DEL RELOJ: lineal, porque X es el minuto y el tiempo no acelera.
    var uid = "wipe" + renderV._n;
    var cp = el("clipPath", { id: uid, clipPathUnits: "userSpaceOnUse" });
    var wx0 = M.l - 4, wx1 = M.l + iw + 16;
    var cr = el("rect", { x: wx0, y: 0, width: wx1 - wx0, height: H });
    cp.appendChild(cr);
    svg.insertBefore(cp, svg.firstChild);
    Array.prototype.forEach.call(svg.querySelectorAll(".adv-line, .evt, .marker-line, .marker-text"),
      function (n) { n.setAttribute("clip-path", "url(#" + uid + ")"); });
    [gPos, gNeg].forEach(function (gr) {
      var w = el("g", { "clip-path": "url(#" + uid + ")" });
      gr.parentNode.insertBefore(w, gr); w.appendChild(gr);
    });
    if (opt.animate) {
      cr.style.setProperty("--span", -(wx1 - wx0) + "px");
      cr.setAttribute("class", "chart-wipe");
    }
  }

  /* ================================================================ ARRANQUE */
  function boot() {
    buildRail();
    slides = Array.prototype.slice.call(document.querySelectorAll(".slide"));
    var pt = document.getElementById("pagetot");
    if (pt) pt.textContent = String(slides.length);

    var hooks = {
      "f-partida": function (s, seen) {
        renderV(s.querySelector("[data-chart]"), {
          animate: !seen, height: 410,
          marcas: [
            { min: D.v1.min_max, y: D.v1.v_max + 1.2, text: "máximo " + D.v1.v_max_txt, anchor: "start" },
            { min: D.v1.d2, text: "cae el Nexo · minuto " + D.v1.d2, anchor: "end" }
          ]
        });
      }
    };
    slides.forEach(function (s) { if (hooks[s.id]) s._onEnter = hooks[s.id]; });

    var m = /#d(\d+)$/.exec(location.hash);
    var start = m ? Math.min(slides.length, Math.max(1, parseInt(m[1], 10))) - 1 : 0;
    slides.forEach(function (s) { s.classList.remove("active"); });
    idx = start;
    slides[idx].classList.add("active");
    updateRail();
    pintaPasos(slides[idx], TODO ? maxPaso(slides[idx]) : 0);
    if (typeof slides[idx]._onEnter === "function") slides[idx]._onEnter(slides[idx], false);
    contar(slides[idx], false);
    slides[idx]._seen = true;
    fitStage();
    flashHelp();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
