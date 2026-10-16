r"""Aplica el plan de movimiento de la revisión UI/UX.

Cada reemplazo lleva aserción: un ancla ausente truena en vez de convertirse en un
no-op silencioso. Los rangos vienen de la revisión de seis lentes.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
H, C, J = ROOT / "presentacion.html", ROOT / "assets/deck.css", ROOT / "assets/deck.js"
ok: list[str] = []
bad: list[str] = []


def sub(p: pathlib.Path, old: str, new: str, tag: str) -> None:
    s = p.read_text(encoding="utf-8")
    n = s.count(old)
    if n != 1:
        bad.append(f"[{tag}] {p.name}: {n} coincidencias (se esperaba 1) :: {old[:60]!r}")
        return
    p.write_text(s.replace(old, new), encoding="utf-8")
    ok.append(tag)


# ══════════════════════════════════════════════════ #1 soldar la gráfica
sub(J, "animate: true, rewind: true, height: 370, events: true",
       "animate: !seen, rewind: true, height: 340, events: true", "1a+3-rewind")
sub(J, "animate: true, height: 370, events: true, peak: true,",
       "animate: !seen, height: 340, events: true, peak: true, tail: true,", "1b+2+3-break")
sub(J, """          animate: true, height: 340,
          annotations: [{ min: D.gold.length - 1, text: "cae el Nexo", anchor: "end" }]""",
       """          animate: !seen, height: 340,
          annotations: [{ min: D.gold.length - 1, text: "cae el Nexo", anchor: "end" }]""", "1c+3-reveal")

# ══════════════════════════════════════════════════ #2 la cortina del reloj
sub(J, """    // --- animacion de trazo
    if (opt.animate) {
      var len = line.getTotalLength();
      line.style.setProperty("--len", len);
      line.classList.add(opt.rewind ? "rewind" : "draw");
    }
    return svg;""",
    """    // --- CORTINA DEL RELOJ ---------------------------------------------------
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
    return svg;""", "2-cortina")

sub(J, """        grp.style.animationDelay = (opt.animate ? 2.5 + i * 0.09 : 0) + "s";
""", "", "2b-sin-stagger")

# ══════════════════════════════════════════════════ #3 no repetir lo ya visto
sub(J, "    if (typeof s._onEnter === \"function\") s._onEnter(s);",
       "    // No se repite una animacion que la sala ya vio: al retroceder para responder\n"
       "    // una pregunta, la grafica aparece entera en vez de volver a dibujarse.\n"
       "    if (typeof s._onEnter === \"function\") { s._onEnter(s, s._seen === true); s._seen = true; }",
       "3a-show")
sub(J, "    if (typeof slides[idx]._onEnter === \"function\") slides[idx]._onEnter(slides[idx]);",
       "    if (typeof slides[idx]._onEnter === \"function\") {\n"
       "      slides[idx]._onEnter(slides[idx], false); slides[idx]._seen = true;\n"
       "    }", "3b-boot")
sub(J, '      "s-rewind": function (s) {', '      "s-rewind": function (s, seen) {', "3c-sig-rewind")
sub(J, '      "s-break": function (s) {', '      "s-break": function (s, seen) {', "3d-sig-break")
sub(J, '      "s-reveal": function (s) {', '      "s-reveal": function (s, seen) {', "3e-sig-reveal")

# ══════════════════════════════════════════════════ #7 quitar el filtro invisible
sub(J, """      "s-defeat": function (s) {
        var d = s.querySelector("#defeat-screen") || s;
        d.classList.remove("recover");
        setTimeout(function () { d.classList.add("recover"); }, 900);
      },
""", "", "7-sin-filtro-js")

# ══════════════════════════════════════════════════ #11 controles del presentador
sub(J, """  document.addEventListener("keydown", function (e) {
    var k = e.key;
    if (k === "ArrowRight" || k === "PageDown" || k === " " || k === "Enter") { e.preventDefault(); next(); }
    else if (k === "ArrowLeft" || k === "PageUp" || k === "Backspace") { e.preventDefault(); prev(); }""",
    """  // Pantalla en negro: todo control remoto trae ese boton y toda sala lo espera.
  var blanked = false;
  function setBlank(v) { blanked = v; document.body.classList.toggle("blank", v); }

  document.addEventListener("keydown", function (e) {
    var k = e.key;
    if (k === "b" || k === "B" || k === ".") { e.preventDefault(); setBlank(!blanked); return; }
    if (blanked) { e.preventDefault(); setBlank(false); return; }   // cualquier tecla restaura
    if (e.repeat) return;
    if (k === "ArrowRight" || k === "ArrowDown" || k === "PageDown" || k === " " || k === "Enter") { e.preventDefault(); next(); }
    else if (k === "ArrowLeft" || k === "ArrowUp" || k === "PageUp" || k === "Backspace") { e.preventDefault(); prev(); }""",
    "11a-teclas")

sub(J, """    else if (k === "f" || k === "F") {
      if (document.fullscreenElement) document.exitFullscreen();
      else document.documentElement.requestFullscreen();
    }""",
    """    else if (k === "f" || k === "F") {
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
    else if (k === "?" || k === "h" || k === "H") { e.preventDefault(); flashHelp(); }""",
    "11b-teclas2")

# ══════════════════════════════════════════════════════════════════ CSS
# #1 soldar
sub(C, ".chart-wrap { position: relative; flex: 1; min-height: 0; }",
    """/* La misma grafica ocupa los MISMOS pixeles en 04, 05 y 06: el eje X es una regla
   fija a la que el presentador apunta tres veces. Sin esto la curva salta 32px
   entre laminas y el borde de la cortina deja de ser "el reloj". */
.chart-wrap { position: relative; flex: 1; min-height: 0; }
#s-break h2, #s-break h2 .sub { max-width: 96ch; }
#s-reveal .chart-wrap, #s-rewind .chart-wrap, #s-break .chart-wrap { flex: 0 0 428px; height: 428px; }""",
    "1d-css-soldar")

# #2 + #9 cortina y banda
sub(C, """/* trazo animado */
.adv-line.draw {
  stroke-dasharray: var(--len); stroke-dashoffset: var(--len);
  animation: draw 2.4s var(--ease) forwards;
}
@keyframes draw { to { stroke-dashoffset: 0; } }

/* rebobinado: se dibuja desde el final hacia el principio */
.adv-line.rewind {
  stroke-dasharray: var(--len); stroke-dashoffset: calc(var(--len) * -1);
  animation: draw 2.2s var(--ease) forwards;
}

.evt { opacity: 0; animation: pop .32s var(--ease) forwards; }
@keyframes pop { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
""",
    """/* La cortina: 1400ms LINEALES sobre el ancho del area de trazo, o sea ~48ms por
   minuto de partida, igual en las tres laminas. Lineal a proposito: el borde
   representa el paso del tiempo de juego, que no acelera. */
.chart-wipe      { animation: wipe-fwd 1400ms linear 260ms backwards; }
.chart-wipe.back { animation-name: wipe-back; }
.chart-wipe.tail { animation: wipe-tail 560ms linear 260ms backwards; }
@keyframes wipe-fwd  { from { transform: translateX(var(--span)); } to { transform: none; } }
@keyframes wipe-back { from { transform: translateX(calc(var(--span) * -1)); } to { transform: none; } }
@keyframes wipe-tail { from { transform: translateX(var(--tail)); } to { transform: none; } }

.evt { opacity: 1; }
""", "2c-css-cortina")

sub(C, """.peak-band { fill: var(--gold); opacity: 0; }
.peak-band.show { animation: band .6s var(--ease) forwards; }
@keyframes band { to { opacity: .10; } }""",
    """/* La banda deja de ser una animacion propia y pasa a ser un ESTADO que la cortina
   descubre al llegar al minuto 22. El borde le da peso sin subir el tinte. */
.peak-band { fill: var(--gold); opacity: 0; }
.peak-band.show {
  opacity: 1; fill-opacity: .12;
  stroke: var(--gold); stroke-width: 1.5; stroke-opacity: .85;
}""", "2d+9-banda")

# #8 linea de cero visible
sub(C, ".zero-line { stroke: var(--neutral); stroke-width: 1.5; stroke-dasharray: 4 4; }",
    "/* 3.46:1 sobre el fondo: visible, pero mas callada que la curva (5.49:1) */\n"
    ".zero-line { stroke: var(--faint); stroke-width: 1.5; stroke-dasharray: 4 4; }", "8-cero")

# #4 direccion y duracion del corte
sub(C, """.slide.enter {
  animation: cut .42s var(--ease-sharp) both;
}
@keyframes cut {
  from { clip-path: inset(0 0 0 100%); }
  to   { clip-path: inset(0 0 0 0%); }
}
.slide.enter-back { animation: cut-back .42s var(--ease-sharp) both; }
@keyframes cut-back {
  from { clip-path: inset(0 100% 0 0); }
  to   { clip-path: inset(0 0 0 0); }
}""",
    """/* Avanzar descubre de IZQUIERDA a derecha, que es como se lee; retroceder al reves.
   260ms: a 420ms el corte se notaba como espera entre laminas. */
.slide.enter { animation: cut .26s cubic-bezier(0,0,.2,1) both; }
@keyframes cut {
  from { clip-path: inset(0 100% 0 0); }
  to   { clip-path: inset(0 0 0 0); }
}
.slide.enter-back { animation: cut-back .26s cubic-bezier(0,0,.2,1) both; }
@keyframes cut-back {
  from { clip-path: inset(0 0 0 100%); }
  to   { clip-path: inset(0 0 0 0); }
}""", "4-corte")

# #5 barra de progreso viva + riel con forma
sub(C, """#progress {
  position: absolute; top: 63px; left: 0; height: 2px;
  background: var(--gold); z-index: 41;
  transition: width .45s var(--ease);
}""",
    """#progress {
  position: absolute; top: 63px; left: 0; height: 2px;
  background: var(--gold); z-index: 41;
}""", "5a-progress")

sub(C, "#rail, #progress { transition: opacity .35s var(--ease); }",
    "#rail     { transition: opacity .35s var(--ease); }\n"
    "#progress { transition: width .26s var(--ease), opacity .35s var(--ease); }", "5b-progress")

sub(C, ".rail-item.done { color: var(--muted); }",
    "/* Tres formas, no tres tonos: a escala de proyector el color no se lee, el\n"
    "   contraste lleno-contra-contorno si. */\n"
    ".rail-item.done { color: var(--muted); }\n"
    ".rail-item.done .num { background: var(--muted); color: var(--deep); border-color: var(--muted); }",
    "5c-riel")

# #6 desenterrar los arquetipos
sub(C, "/* =========================================================================\n   Etiqueta de dato ilustrativo",
    """/* La lamina 16 se tapaba a si misma: .row.grow media 36px con 196px de contenido,
   asi que los dos paneles se encimaban sobre las reglas A2 y A4 -- justo el
   entregable de la lamina. Los paneles pasan a ser notas con filete. */
#s-arch .body { gap: 16px; }
#s-arch .row.grow { flex: 0 0 auto; }
#s-arch .panel {
  padding: 0 0 0 16px; background: none; border: 0;
  border-left-width: 3px; border-left-style: solid;
}
#s-arch .panel p { font-size: 15px; line-height: 1.45; }
#s-arch h2 .sub { font-size: 19px; max-width: 78ch; }

/* =========================================================================
   Etiqueta de dato ilustrativo""", "6-arquetipos")

# #7 pantalla de derrota sin filtro muerto
sub(C, """#defeat-screen::before {
  content: ""; position: absolute; inset: 0;
  background: url("./misc/splash_Yone.jpg") center 20% / cover no-repeat;
  filter: saturate(0) brightness(.40) contrast(.95);
  transition: filter 1.8s var(--ease);
}
#defeat-screen.recover::before { filter: saturate(1) brightness(.66) contrast(1); }""",
    """/* Se retiro la transicion gris->color: medida contra el velo, la sala no la veia,
   y costaba 2.7s de la apertura. Se conserva el estado final. */
#defeat-screen::before {
  content: ""; position: absolute; inset: 0;
  background: url("./misc/splash_Yone.jpg") center 20% / cover no-repeat;
  filter: saturate(1) brightness(.66) contrast(1);
}""", "7-sin-filtro-css")

# #10 el cierre aterriza
sub(C, "/* =========================================================================\n   Ayuda de navegacion",
    """/* El cierre rima con el titulo: merece tamano propio, y el subrayado se dibuja
   una vez para que la frase caiga en vez de diluirse en el descargo legal. */
.closer {
  font-size: 23px; line-height: 1.45; color: var(--parchment);
  max-width: 62ch; margin-top: var(--s3);
}
.closer .hinge {
  color: var(--gold-lit); font-weight: 700;
  background-image: linear-gradient(var(--gold), var(--gold));
  background-repeat: no-repeat; background-position: 0 100%; background-size: 0% 3px;
}
.slide.active .closer .hinge { animation: underline 600ms var(--ease) 500ms forwards; }
@keyframes underline { to { background-size: 100% 3px; } }
#s-plan .footer div:first-child { max-width: 92ch; }

/* =========================================================================
   Ayuda de navegacion""", "10-cierre")

# #11 pantalla negra + pastilla con fondo
sub(C, """#help {
  position: fixed; bottom: 14px; right: 16px; z-index: 60;""",
    """#blank {
  position: fixed; inset: 0; background: #000; z-index: 100;
  opacity: 0; pointer-events: none; transition: opacity .18s var(--ease);
}
body.blank #blank { opacity: 1; pointer-events: auto; }

#help {
  position: fixed; bottom: 12px; right: 12px; z-index: 60;
  background: rgba(6,16,28,.94); border: 1px solid #22384E;
  border-radius: 3px; padding: 6px 10px;""", "11c-negro")

# reduccion de movimiento, reescrita para lo que ahora existe
sub(C, """@media (prefers-reduced-motion: reduce) {
  .slide.enter, .slide.enter-back { animation: none; }
  .adv-line.draw, .adv-line.rewind { animation: none; stroke-dashoffset: 0; }
  .evt { animation: none; opacity: 1; }
  .peak-band.show { animation: none; opacity: .10; }
  #defeat-screen, #defeat-screen::before { transition: none; }
}""",
    """@media (prefers-reduced-motion: reduce) {
  .slide.enter, .slide.enter-back { animation: none; }
  /* La cortina se apaga y el rect de recorte se queda cubriendo todo: la grafica
     aparece completa. NO se toca .peak-band.show: su opacidad ahora es estado, y
     una regla posterior aqui la volveria invisible (opacity .10 x fill-opacity .12). */
  .chart-wipe, .chart-wipe.back, .chart-wipe.tail { animation: none; }
  #rail, #progress, #help, .rail-item, #blank { transition: none; }
  /* el subrayado del cierre es contenido: se queda puesto, solo no se dibuja */
  .closer .hinge { animation: none; background-size: 100% 3px; }
}""", "12-reduccion")

# ══════════════════════════════════════════════════════════════════ HTML
sub(H, """        <p class="note" style="font-size:17px; color:var(--ink)">
          Sé en qué minuto se perdió <em>esta</em> partida. La pregunta es si se puede decir lo
          mismo de las mías, y con qué intervalo.
        </p>""",
    """        <p class="closer">
          Sé en qué minuto se perdió <em class="hinge">esta</em> partida. La pregunta es si se
          puede decir lo mismo de las mías, y con qué intervalo.
        </p>""", "10b-cierre-html")

sub(H, """<div id="help">
  <span><kbd>←</kbd><kbd>→</kbd> navegar</span>
  <span><kbd>F</kbd> pantalla completa</span>
</div>""",
    """<div id="blank"></div>

<div id="help">
  <span><kbd>←</kbd><kbd>→</kbd> navegar</span>
  <span><kbd>F</kbd> pantalla completa</span>
  <span><kbd>B</kbd> negro</span>
  <span><kbd>R</kbd> repetir</span>
  <span><kbd>1</kbd><kbd>2</kbd><kbd>3</kbd> sección</span>
</div>""", "11d-help-html")

# los paneles de s-arch pierden su fondo en linea (el filete queda)
for tag, old, new in [
    ("6b-panel-rojo",
     'style="flex:1 1 50%; border-left:3px solid var(--red); background:rgba(222,67,97,.06)"',
     'style="flex:1 1 50%; border-left:3px solid var(--red)"'),
    ("6c-panel-oro",
     'style="flex:1 1 50%; border-left:3px solid var(--gold); background:rgba(188,139,44,.06)"',
     'style="flex:1 1 50%; border-left:3px solid var(--gold)"'),
]:
    sub(H, old, new, tag)

# ══════════════════════════════════════════════════════════════════ informe
print("=" * 66)
print(f"aplicados: {len(ok)}")
for a in ok:
    print("  +", a)
if bad:
    print(f"\nFALLARON ({len(bad)}):")
    for m in bad:
        print("  !", m)
    sys.exit(1)
print("\ntodos los reemplazos aplicaron")
