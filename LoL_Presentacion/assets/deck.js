/* =========================================================================
   Expediente de una derrota - motor de la presentacion
   Todo el dato del grafico sale de window.LOL_DATA (partida publica real).
   ========================================================================= */

(function () {
  "use strict";

  var D = window.LOL_DATA || {};
  var stage = document.getElementById("stage");
  var slides = [];
  var idx = 0;

  /* ---------------------------------------------------------------- escala */
  function fitStage() {
    var pad = 0;
    var sx = (window.innerWidth - pad) / 1600;
    var sy = (window.innerHeight - pad) / 900;
    var s = Math.min(sx, sy);
    stage.style.transform = "scale(" + s + ")";
  }
  window.addEventListener("resize", fitStage);

  /* ------------------------------------------------------------ navegacion */
  var RAIL = [
    { id: 1, label: "Problemática" },
    { id: 2, label: "Fuentes de datos" },
    { id: 3, label: "Hipótesis" }
  ];

  function buildRail() {
    var rail = document.getElementById("rail");
    if (!rail) return;
    var html = "";
    RAIL.forEach(function (r) {
      html +=
        '<div class="rail-item" data-sec="' + r.id + '">' +
        '<span class="num">' + r.id + "</span>" +
        "<span>" + r.label + "</span></div>";
    });
    html += '<div class="rail-item spacer"></div>';
    html += '<div class="counter"><span id="pageno">1</span> / <span id="pagetot">1</span>'
          + '<span class="pasos" id="pasos"></span></div>';
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
    // puntos de paso: el presentador ve cuantos le faltan en esta lamina
    var ps = document.getElementById("pasos");
    if (ps) {
      var cur = slides[idx], mx = maxPaso(cur), h = "";
      for (var q = 1; q <= mx; q++) {
        h += "<i class='" + (q <= (cur._paso || 0) ? "on" : "") + "'></i>";
      }
      ps.innerHTML = h;
    }
  }

  // Menos movimiento: se consulta una vez y lo respetan tanto el CSS como los
  // contadores, que son JS y no se apagarian solos con la media query.
  var MENOS_MOV = window.matchMedia
    ? window.matchMedia("(prefers-reduced-motion: reduce)")
    : { matches: false };

  /* Contadores. Las cifras que SON el argumento de una lamina cuentan hasta su
     valor. El HTML ya trae el numero final escrito, asi que si el JS no corre la
     lamina se lee igual: la animacion nunca es la unica fuente del dato. */
  function contar(root, visto) {
    Array.prototype.forEach.call(root.querySelectorAll("[data-count]"), function (el) {
      var fin = parseFloat(el.dataset.count);
      var pre = el.dataset.prefix || "";
      var suf = el.dataset.suffix || "";
      var pinta = function (v) { return pre + Math.round(v).toLocaleString("es-MX") + suf; };
      if (visto || MENOS_MOV.matches || isNaN(fin)) { el.textContent = pinta(fin); return; }
      var ini = null, DUR = 820, ESPERA = 360;
      el.textContent = pinta(0);
      requestAnimationFrame(function paso(ts) {
        if (ini === null) ini = ts;
        var p = (ts - ini - ESPERA) / DUR;
        if (p < 0) { requestAnimationFrame(paso); return; }
        if (p >= 1) { el.textContent = pinta(fin); return; }
        el.textContent = pinta(fin * (1 - Math.pow(1 - p, 3)));   // desaceleracion
        requestAnimationFrame(paso);
      });
    });
  }

  function show(n, back) {
    if (n < 0 || n >= slides.length) return;
    slides[idx].classList.remove("active", "enter", "enter-back");
    idx = n;
    var s = slides[idx];
    // No se repite una animacion que la sala ya vio: al retroceder para responder
    // una pregunta, la lamina aparece entera en vez de volver a armarse.
    // `visto` se pone ANTES que `active` para que la cascada ya nazca apagada.
    var visto = s._seen === true;
    s.classList.toggle("visto", visto);
    s.classList.add("active", back ? "enter-back" : "enter");
    // Hacia adelante empieza en cero; al volver, o con ?todo, la lamina se ve entera.
    pintaPasos(s, (TODO || back || visto) ? maxPaso(s) : 0);   // pintaPasos llama a updateRail
    if (typeof s._onEnter === "function") s._onEnter(s, visto);
    contar(s, visto);
    s._seen = true;
    location.replace(location.pathname + "#d" + (idx + 1));
  }

  /* ---------------------------------------------------- revelacion por pasos
     Una lamina marcada con [data-steps] se descubre por partes: cada clic o
     flecha muestra el siguiente [data-step]. Cuando se acaban los pasos, la
     misma tecla pasa de lamina, asi que el presentador usa un solo boton.
     `?todo` en la direccion apaga el sistema: la lamina se lee entera, que es
     lo que hace falta para leer el archivo o entregarlo. */
  var TODO = /[?&]todo\b/.test(location.search);

  function pasosDe(s) {
    return Array.prototype.slice.call(s.querySelectorAll("[data-step]"));
  }
  function maxPaso(s) {
    return pasosDe(s).reduce(function (m, e) {
      return Math.max(m, parseInt(e.dataset.step, 10) || 0);
    }, 0);
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
    var s = slides[idx];
    // Retroceder dentro de la lamina solo si se quedo a medias; ya revelada del
    // todo, la flecha regresa de lamina -- que es lo que se necesita para volver
    // a algo y responder una pregunta.
    var mx = maxPaso(s);
    if (!TODO && mx && s._paso > 0 && s._paso < mx) { pintaPasos(s, s._paso - 1); return; }
    show(idx - 1, true);
  }

  // Pantalla en negro: todo control remoto trae ese boton y toda sala lo espera.
  var blanked = false;
  function setBlank(v) { blanked = v; document.body.classList.toggle("blank", v); }

  document.addEventListener("keydown", function (e) {
    var k = e.key;
    if (k === "b" || k === "B" || k === ".") { e.preventDefault(); setBlank(!blanked); return; }
    if (blanked) { e.preventDefault(); setBlank(false); return; }   // cualquier tecla restaura
    if (e.repeat) return;
    if (k === "ArrowRight" || k === "ArrowDown" || k === "PageDown" || k === " " || k === "Enter") { e.preventDefault(); next(); }
    else if (k === "ArrowLeft" || k === "ArrowUp" || k === "PageUp" || k === "Backspace") { e.preventDefault(); prev(); }
    else if (k === "Home") { e.preventDefault(); show(0, true); }
    else if (k === "End") { e.preventDefault(); show(slides.length - 1, false); }
    else if (k === "f" || k === "F") {
      if (document.fullscreenElement) document.exitFullscreen();
      else document.documentElement.requestFullscreen();
    }
    else if (k === "r" || k === "R") {            // repetir la animacion a proposito
      e.preventDefault();
      var cur = slides[idx];
      if (typeof cur._onEnter === "function") cur._onEnter(cur, false);
    }
    else if (k === "1" || k === "2" || k === "3") {   // saltar a una seccion de la rubrica
      e.preventDefault();
      for (var q = 0; q < slides.length; q++) {
        if (slides[q].dataset.sec === k) { show(q, q < idx); break; }
      }
    }
    else if (k === "a" || k === "A") {          // revelar toda la lamina de golpe
      e.preventDefault(); pintaPasos(slides[idx], maxPaso(slides[idx]));
    }
    else if (k === "?" || k === "h" || k === "H") { e.preventDefault(); flashHelp(); }
    // No se vuelve a mostrar la ayuda: se encimaba con el pie en 11 de 16 laminas.
  });

  // Solo cuenta como clic si el raton no se arrastro: seleccionar texto en una
  // diapositiva no debe pasar a la siguiente.
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
     GRAFICO DE VENTAJA DE ORO
     Medida divergente: por encima de cero = ventaja del equipo que perdio.
     La linea de cero es el argumento: nunca la cruzaron hacia abajo.
     ===================================================================== */

  var NS = "http://www.w3.org/2000/svg";
  function el(name, attrs) {
    var e = document.createElementNS(NS, name);
    for (var k in attrs) if (attrs[k] !== undefined && attrs[k] !== null) e.setAttribute(k, attrs[k]);
    return e;
  }

  // Eventos que importan para la narrativa y caben sin encimarse.
  // El ancla es "^Inhibidor" y no "Inhibidor": /Inhibidor/ tambien casa con
  // "Torre de inhibidor", y como la etiqueta se acorta a "Inhibidor <linea>",
  // los dos eventos terminaban dibujando el MISMO texto encima de si mismo.
  function keyEvents() {
    if (!D.objectives) return [];
    return D.objectives.filter(function (o) {
      return o.type === "DRAGON" || o.type === "BARON_NASHOR" || o.type === "RIFTHERALD" ||
        (o.type === "BUILDING" && /^Inhibidor/.test(o.label));
    });
  }

  function renderChart(host, opt) {
    opt = opt || {};
    host.innerHTML = "";
    var W = 1180, H = opt.height || 380;
    // t deja aire para las anotaciones, que van por encima del area de trazo
    var M = { t: 46, r: 122, b: 42, l: 74 };
    var iw = W - M.l - M.r, ih = H - M.t - M.b;

    var g = D.gold || [];
    if (!g.length) return;

    var maxMin = g[g.length - 1].min;
    var yMax = 9000, yMin = -1800;

    var X = function (m) { return M.l + (m / maxMin) * iw; };
    var Y = function (v) { return M.t + (1 - (v - yMin) / (yMax - yMin)) * ih; };

    var svg = el("svg", { class: "chart", viewBox: "0 0 " + W + " " + H, preserveAspectRatio: "xMidYMid meet" });

    // --- rejilla horizontal
    [-1000, 0, 2000, 4000, 6000, 8000].forEach(function (v) {
      if (v === 0) return;
      svg.appendChild(el("line", { class: "grid-line", x1: M.l, x2: M.l + iw, y1: Y(v), y2: Y(v) }));
      var t = el("text", { class: "axis-label", x: M.l - 12, y: Y(v) + 4, "text-anchor": "end" });
      t.textContent = (v > 0 ? "+" : "") + (v / 1000) + "k";
      svg.appendChild(t);
    });

    // --- area positiva
    var area = "M " + X(0) + " " + Y(0);
    g.forEach(function (p) { area += " L " + X(p.min) + " " + Y(p.adv); });
    area += " L " + X(maxMin) + " " + Y(0) + " Z";
    svg.appendChild(el("path", { class: "area-pos", d: area }));

    // --- linea de cero (el argumento)
    svg.appendChild(el("line", { class: "zero-line", x1: M.l, x2: M.l + iw, y1: Y(0), y2: Y(0) }));
    var z = el("text", { class: "axis-label", x: M.l - 12, y: Y(0) + 4, "text-anchor": "end" });
    z.textContent = "0";
    svg.appendChild(z);
    var zt = el("text", { class: "axis-label", x: M.l + iw + 10, y: Y(0) + 4 });
    zt.textContent = "empate en oro";
    svg.appendChild(zt);

    // --- eje x
    for (var m = 0; m <= maxMin; m += 5) {
      var xt = el("text", { class: "axis-label", x: X(m), y: M.t + ih + 24, "text-anchor": "middle" });
      xt.textContent = m + "'";
      svg.appendChild(xt);
    }

    // --- banda del punto de quiebre
    if (opt.peak && D.peak) {
      var bx1 = X(D.peak.min), bx2 = X(Math.min(maxMin, D.peak.min + 1.5));
      var band = el("rect", { class: "peak-band show", x: bx1, y: M.t, width: Math.max(6, bx2 - bx1), height: ih });
      svg.appendChild(band);
    }

    // --- la linea
    var d = "";
    g.forEach(function (p, i) { d += (i ? " L " : "M ") + X(p.min) + " " + Y(p.adv); });
    var line = el("path", { class: "adv-line", d: d });
    svg.appendChild(line);

    // --- marcadores de eventos
    // Se etiquetan MUY pocos a proposito: con nueve etiquetas se encimaban unas con
    // otras y con la anotacion del pico. El resto de los hechos va en la lista de abajo.
    if (opt.events) {
      var evs = keyEvents();
      var labelled = [];   // x ya ocupadas, para no encimar texto
      var drawn = [];      // x de puntos ya dibujados, para no taparlos
      evs.forEach(function (o, i) {
        var advAt = g[Math.min(g.length - 1, Math.round(o.min))];
        var cy = Y(advAt ? advAt.adv : 0);
        var cx = X(o.min);
        // dos objetivos casi simultaneos tapaban uno al otro (el Baron quedaba
        // ~60% escondido detras del inhibidor); se separa el segundo unos pixeles
        if (drawn.some(function (p) { return Math.abs(p - cx) < 12; })) cx += 5;
        drawn.push(cx);
        var grp = el("g", { class: "evt " + (o.forLoser ? "ours" : "theirs") });
        grp.appendChild(el("circle", { cx: cx, cy: cy, r: 5.5 }));

        var wants = opt.labelTypes && opt.labelTypes.indexOf(o.type) !== -1;
        if (wants) {
          var clash = labelled.some(function (p) { return Math.abs(p - cx) < 92; });
          var t2 = el("text", {
            x: cx, y: cy + (clash ? 24 : -14), "text-anchor": "middle"
          });
          t2.textContent = o.label.replace(/ \(.*\)/, "")
            .replace("Torre de inhibidor", "Inhibidor");
          grp.appendChild(t2);
          labelled.push(cx);
        }
        svg.appendChild(grp);
      });
    }

    // --- anotaciones (van ARRIBA del area de trazo, para no pelearse con la curva)
    (opt.annotations || []).forEach(function (a) {
      var x = X(a.min);
      svg.appendChild(el("line", { class: "marker-line", x1: x, x2: x, y1: M.t - 8, y2: M.t + ih }));
      var anchor = a.anchor || (x > M.l + iw * 0.72 ? "end" : "start");
      var t3 = el("text", {
        class: "marker-text", x: x + (anchor === "end" ? -9 : 9),
        y: M.t - 12, "text-anchor": anchor
      });
      t3.textContent = a.text;
      svg.appendChild(t3);
    });

    host.appendChild(svg);

    // --- CORTINA DEL RELOJ ---------------------------------------------------
    // Un solo rectangulo de recorte en unidades de usuario. El borde avanza en X, y
    // X es el minuto: por eso la animacion es LINEAL y no lleva var(--ease). Revela
    // el area, la linea, los puntos y la banda a la vez, cada marca en su minuto.
    // A prueba de fallos: sin animacion el rect ya cubre toda la zona de trazo.
    var uid = "wipe" + (renderChart._n = (renderChart._n || 0) + 1);
    var cp = el("clipPath", { id: uid, clipPathUnits: "userSpaceOnUse" });
    var wx0 = M.l - 4, wx1 = M.l + iw + 16;
    var cr = el("rect", { x: wx0, y: 0, width: wx1 - wx0, height: H });
    cp.appendChild(cr);
    svg.insertBefore(cp, svg.firstChild);
    Array.prototype.forEach.call(
      svg.querySelectorAll(".area-pos, .peak-band, .adv-line, .evt, .marker-line, .marker-text"),
      function (n) { n.setAttribute("clip-path", "url(#" + uid + ")"); }
    );
    if (opt.animate) {
      cr.style.setProperty("--span", -(wx1 - wx0) + "px");
      if (opt.tail) cr.style.setProperty("--tail", -(wx1 - X(18)) + "px");
      cr.setAttribute("class", "chart-wipe" + (opt.rewind ? " back" : "") + (opt.tail ? " tail" : ""));
    }
    return svg;
  }

  /* =====================================================================
     MARCADOR
     ===================================================================== */

  // Data Dragon trae el nombre para mostrar; el id de la API no es el nombre
  // (KSante -> K'Sante). El id se sigue usando para el archivo del retrato.
  var CHAMP_ES = { KSante: "K'Sante", Belveth: "Bel'Veth" };
  var POS_ES = {
    TOP: "superior", JUNGLE: "jungla", MIDDLE: "central",
    BOTTOM: "inferior", UTILITY: "soporte"
  };

  function renderBoard(host) {
    if (!D.roster) return;
    var loser = D.loser;
    var rows = D.roster.slice().sort(function (a, b) {
      return (a.team === loser ? 0 : 1) - (b.team === loser ? 0 : 1);
    });
    var h =
      "<table class='board'><thead><tr>" +
      "<th>Campeón</th><th class='n'>K / D / A</th><th class='n'>Oro</th>" +
      "<th class='n'>CS</th><th class='n'>Daño</th>" +
      "</tr></thead><tbody>";
    rows.forEach(function (r) {
      h +=
        "<tr class='" + (r.team === loser ? "us" : "them") + "'>" +
        "<td><div class='champ'><img src='assets/champions/" + r.champ + ".png' alt='' loading='eager'>" +
        "<div>" + (CHAMP_ES[r.champ] || r.champ) +
        "<div class='pos'>" + (POS_ES[r.pos] || (r.pos || "").toLowerCase()) + "</div></div></div></td>" +
        "<td class='n'>" + r.k + " / " + r.d + " / " + r.a + "</td>" +
        "<td class='n'>" + r.gold.toLocaleString("es-MX") + "</td>" +
        "<td class='n'>" + r.cs + "</td>" +
        "<td class='n'>" + r.dmg.toLocaleString("es-MX") + "</td>" +
        "</tr>";
    });
    h += "</tbody></table>";
    host.innerHTML = h;
  }

  /* =====================================================================
     MAPA ESQUEMATICO + POSICIONES DE MUERTE
     Coordenadas reales del timeline (0..~15000 en Summoner's Rift).
     ===================================================================== */

  function renderRift(host) {
    var S = 360, P = 16;
    var svg = el("svg", { class: "rift-map", viewBox: "0 0 " + S + " " + S });
    var MAXC = 15000;                              // rango de coordenadas de la grieta
    var X = function (x) { return P + (x / MAXC) * (S - 2 * P); };
    var Y = function (y) { return S - P - (y / MAXC) * (S - 2 * P); };
    var pt = function (x, y) { return X(x) + " " + Y(y); };

    svg.appendChild(el("rect", {
      class: "rift-base", x: P - 4, y: P - 4,
      width: S - 2 * P + 8, height: S - 2 * P + 8, rx: 4
    }));

    // El rio va primero y con tratamiento de BANDA ancha translucida: si se dibuja
    // con el mismo peso que un carril, el conjunto se lee como una X y deja de
    // parecerse al mapa.
    svg.appendChild(el("path", {
      class: "rift-river", d: "M " + pt(2000, 12200) + " L " + pt(12200, 2000)
    }));

    // Los tres carriles, con esquinas redondeadas
    svg.appendChild(el("path", { class: "rift-lane",
      d: "M " + pt(1900, 2500) + " L " + pt(1900, 11900) +
         " Q " + pt(1900, 13100) + " " + pt(3100, 13100) + " L " + pt(12600, 13100) }));
    svg.appendChild(el("path", { class: "rift-lane",
      d: "M " + pt(2500, 2500) + " L " + pt(12500, 12500) }));
    svg.appendChild(el("path", { class: "rift-lane",
      d: "M " + pt(2500, 1900) + " L " + pt(11900, 1900) +
         " Q " + pt(13100, 1900) + " " + pt(13100, 3100) + " L " + pt(13100, 12600) }));

    // Bases
    [[1750, 1750, "rift-nexus-b"], [13250, 13250, "rift-nexus-r"]].forEach(function (b) {
      svg.appendChild(el("circle", { cx: X(b[0]), cy: Y(b[1]), r: 11, fill: "none",
        stroke: b[2] === "rift-nexus-b" ? "var(--blue)" : "var(--red)",
        "stroke-width": 1, opacity: .45 }));
      svg.appendChild(el("circle", { class: b[2], cx: X(b[0]), cy: Y(b[1]), r: 6 }));
    });

    // Las 42 posiciones reales de asesinato
    (D.kills || []).forEach(function (k) {
      if (typeof k.x !== "number") return;
      svg.appendChild(el("circle", {
        class: "rift-kill", cx: X(k.x), cy: Y(k.y), r: 4.5,
        fill: k.forLoser == null ? "var(--neutral)"
            : (k.forLoser ? "var(--blue)" : "var(--red)"), opacity: .9
      }));
    });

    host.innerHTML = "";
    host.appendChild(svg);
  }

  /* =====================================================================
     ARRANQUE
     ===================================================================== */

  function boot() {
    buildRail();
    slides = Array.prototype.slice.call(document.querySelectorAll(".slide"));
    var pt = document.getElementById("pagetot");
    if (pt) pt.textContent = String(slides.length);

    // rellena los valores derivados del dato real
    document.querySelectorAll("[data-fill]").forEach(function (n) {
      var key = n.dataset.fill;
      var v = key.split(".").reduce(function (o, k) { return o && o[k]; }, D);
      if (v === undefined || v === null) return;
      n.textContent = typeof v === "number" ? v.toLocaleString("es-MX") : String(v);
    });

    // enganches por diapositiva
    var hooks = {
      "s-board": function (s) { renderBoard(s.querySelector("[data-board]")); },
      "s-reveal": function (s, seen) {
        renderChart(s.querySelector("[data-chart]"), {
          animate: !seen, height: 340,
          annotations: [{ min: D.gold.length - 1, text: "cae el Nexo", anchor: "end" }]
        });
      },
      "s-rewind": function (s, seen) {
        renderChart(s.querySelector("[data-chart]"), {
          animate: !seen, rewind: true, height: 340, events: true
        });
      },
      "s-break": function (s, seen) {
        renderChart(s.querySelector("[data-chart]"), {
          animate: !seen, height: 340, events: true, peak: true, tail: true,
          labelTypes: ["BARON_NASHOR", "BUILDING"],
          annotations: [{
            min: D.peak.min,
            text: "pico +" + D.peak.adv.toLocaleString("es-MX") + " de oro",
            anchor: "end"
          }]
        });
      },
      "s-map": function (s) { renderRift(s.querySelector("[data-rift]")); },

      // Version narrada: la curva primero limpia, y despues la misma grafica con
      // la banda del pico y los objetivos etiquetados. La cortina de la segunda
      // arranca en el minuto 18 (tail), porque los primeros 20 ya son hecho visto.
      "s-curva": function (s, seen) {
        renderChart(s.querySelector("[data-chart]"), {
          animate: !seen, height: 340, events: true
        });
      },
      "s-quiebre": function (s, seen) {
        renderChart(s.querySelector("[data-chart]"), {
          animate: !seen, height: 340, events: true, peak: true, tail: true,
          labelTypes: ["BARON_NASHOR", "BUILDING"],
          annotations: [{
            min: D.peak.min,
            text: "pico +" + D.peak.adv.toLocaleString("es-MX") + " de oro",
            anchor: "end"
          }]
        });
      },

      // Solo la version de 5 minutos: una sola lamina de grafica que hace el
      // trabajo de las cuatro del mazo largo -- cortina completa, banda del pico
      // y etiquetas de los objetivos que decidieron la partida.
      "s-partida": function (s, seen) {
        renderChart(s.querySelector("[data-chart]"), {
          animate: !seen, height: 340, events: true, peak: true,
          labelTypes: ["BARON_NASHOR", "BUILDING"],
          annotations: [{
            min: D.peak.min,
            text: "pico +" + D.peak.adv.toLocaleString("es-MX") + " de oro",
            anchor: "end"
          }]
        });
      }
    };
    slides.forEach(function (s) { if (hooks[s.id]) s._onEnter = hooks[s.id]; });

    // diapositiva inicial desde el hash
    var m = /^#d(\d+)$/.exec(location.hash);
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
