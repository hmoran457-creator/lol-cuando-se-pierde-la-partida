r"""Aplica los arreglos de la revisión multi-lente.

Cada reemplazo lleva su propia aserción: un ancla ausente truena en voz alta en vez
de convertirse en un no-op silencioso, que es como se ve un str.replace que falla.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
applied: list[str] = []
missing: list[str] = []


def sub(path: pathlib.Path, old: str, new: str, tag: str, count: int = 1) -> None:
    s = path.read_text(encoding="utf-8")
    n = s.count(old)
    if n == 0:
        missing.append(f"ANCLA AUSENTE [{tag}] en {path.name}: {old[:70]!r}")
        return
    if n != count:
        missing.append(f"ANCLA AMBIGUA [{tag}] en {path.name}: {n} coincidencias, se esperaban {count}")
        return
    path.write_text(s.replace(old, new), encoding="utf-8")
    applied.append(tag)


H = ROOT / "presentacion.html"
C = ROOT / "assets" / "deck.css"
J = ROOT / "assets" / "deck.js"

# ---------------------------------------------------------------- #3 nombres
sub(J, """    var h =
      "<table class='board'>""",
    """    var h =
      "<table class='board'>""", "3-noop-guard")  # solo confirma que renderBoard sigue ahí

sub(J, """  function renderBoard(host) {""",
    """  // Data Dragon trae el nombre para mostrar; el id de la API no es el nombre
  // (KSante -> K'Sante). El id se sigue usando para el archivo del retrato.
  var CHAMP_ES = { KSante: "K'Sante", Belveth: "Bel'Veth" };
  var POS_ES = {
    TOP: "superior", JUNGLE: "jungla", MIDDLE: "central",
    BOTTOM: "inferior", UTILITY: "soporte"
  };

  function renderBoard(host) {""", "3a-mapas")

sub(J, """        "<td><div class='champ'><img src='assets/champions/" + r.champ + ".png' alt='' loading='eager'>" +
        "<div>" + r.champ + "<div class='pos'>" + (r.pos || "").toLowerCase() + "</div></div></div></td>" +""",
    """        "<td><div class='champ'><img src='assets/champions/" + r.champ + ".png' alt='' loading='eager'>" +
        "<div>" + (CHAMP_ES[r.champ] || r.champ) +
        "<div class='pos'>" + (POS_ES[r.pos] || (r.pos || "").toLowerCase()) + "</div></div></div></td>" +""",
    "3b-render")

# ------------------------------------------------------- #4 encabezado causal
sub(H, "<h3>El evento que dio vuelta la partida</h3>",
    "<h3>El barón del minuto 23:03</h3>", "4-causal")

# ------------------------------------------------- #5 reglas con umbral + orden
sub(H, """        <span class="sub">El entregable no es un número: es una clasificación con reglas escritas
          antes de ver los datos. La regla es lo que se puede discutir; la frecuencia todavía no existe.</span></h2>""",
    """        <span class="sub">El entregable no es un número: es una clasificación cuyas reglas fijo
          por escrito, con su umbral numérico, antes de ver la distribución. La regla es lo que se
          puede discutir; la frecuencia todavía no existe.</span></h2>""", "5a-subtitulo")

sub(H, """        <div class="row" style="gap:var(--s4)">
          <div class="panel" style="flex:1 1 50%; border-left:3px solid var(--red); background:rgba(222,67,97,.06)">""",
    """        <p class="note" style="margin:2px 0 10px">Se aplican en orden: A4 se evalúa antes que A1,
          y lo que no cumple ninguna queda <em>sin clasificar</em>.</p>
        <div class="row" style="gap:var(--s4)">
          <div class="panel" style="flex:1 1 50%; border-left:3px solid var(--red); background:rgba(222,67,97,.06)">""",
    "5b-orden")

# --------------------------------------------------- #7 H5, "la mitad" sin antecedente
sub(H, """              <span class="test">Trampa: la mitad de “error de macro” se corta — no existe ningún campo que lo
              mida. Y yo elijo mis campeones, así que la diferencia confunde habilidad con campeón y emparejamiento.</span>""",
    """              <span class="test">Trampa: la otra mitad de esta hipótesis —la del “error de macro”— la corté:
              no existe ningún campo que lo mida. Y yo elijo mis campeones, así que la diferencia confunde habilidad
              con campeón y emparejamiento.</span>""", "7-H5")

# ------------------------------------------------------ #8b H6, rendiciones aparte
sub(H, """anchos para ubicarlo — y ese sería el resultado.</span>""",
    """anchos para ubicarlo — y ese sería el resultado. Las rendidas van como serie aparte: rendirse
              es un voto humano, no un evento del juego.</span>""", "8b-H6")

# --------------------------------------------------------------- #9 calco "llamada"
sub(H, """              <li class="no">No hay comunicación: ni voz, ni chat, ni pings. Una partida perdida
                por una mala llamada se ve idéntica a una perdida por una mala decisión.</li>""",
    """              <li class="no">No hay comunicación: ni voz, ni chat, ni pings. Una partida perdida
                por un mal <em>call</em> del equipo se ve idéntica a una perdida por una mala
                decisión individual.</li>""", "9-calco")

# ------------------------------------------------------------- #10 duración real
sub(H, "28:25 · partida clasificatoria · Esto es todo lo que el juego te dice al terminar.",
    "28:35 · partida clasificatoria · Esto es todo lo que el juego te dice al terminar.", "10a-derrota")
sub(H, """<li class="no"><em>28:25</em> — cae el Nexo, con la ventaja de oro todavía a su favor.</li>""",
    """<li class="no"><em>28:35</em> — cae el Nexo, con la ventaja de oro todavía a su favor.</li>""",
    "10b-break")

# ------------------------------------------------- #11 tres eventos, tres marcas
sub(H, """        <span class="sub">Minuto 21:54. Tiran el inhibidor y las dos torres del Nexo enemigo.
          Están dentro de la base rival con ocho mil de oro de ventaja. No cierran.</span></h2>""",
    """        <span class="sub">Entre el 21:44 y el 22:02 tiran el inhibidor y las dos torres del Nexo
          enemigo. Están dentro de la base rival y el cuadro del minuto 22 les marca ocho mil de oro
          de ventaja. No cierran.</span></h2>""", "11a-subtitulo")
sub(H, """<li><em>21:54</em> — caen inhibidor y ambas torres del Nexo. Ventaja máxima.</li>""",
    """<li><em>21:44 – 22:02</em> — caen el inhibidor y ambas torres del Nexo. Ventaja máxima en el cuadro del 22.</li>""",
    "11b-lista")

# ------------------------------------------------------- #12 conteos de atributos
sub(H, '<span class="c">… 26 atributos</span>', '<span class="c">… 25 atributos</span>', "12a-champion")
sub(H, '<span class="c">… 13 atributos</span>', '<span class="c">… 12 atributos</span>', "12b-damage")
sub(H, '<span class="c">// events[] — minuto 23:03</span>',
    '<span class="c">// events[] — minuto 23:03, recortado</span>', "12c-recortado")

# -------------------------------------- #13 coordenadas: no en todos los eventos
sub(H, "<li>Los eventos traen tipo, marca de tiempo y coordenadas.</li>",
    "<li>Los asesinatos, las estructuras y los monstruos traen tipo, marca de tiempo y coordenadas.</li>",
    "13a-plan")
sub(H, """        <span class="sub">Un fotograma por minuto con el estado de los diez jugadores, más la
          lista de eventos con su marca de tiempo y su posición en el mapa.</span></h2>""",
    """        <span class="sub">Un cuadro por minuto con el estado de los diez jugadores, más la lista
          de eventos con su marca de tiempo, y la posición en el mapa de los que la traen.</span></h2>""",
    "13b-timeline")

# ------------------------------------------------------- #14 aritmética de celdas
sub(H, """        <p class="note">
          Habrá una categoría <em>“sin clasificar”</em>, y su tamaño se reporta. Un conjunto de
          reglas que acomoda el 100&nbsp;% de las partidas es la señal de que se ajustaron
          después de ver los datos.
        </p>""",
    """        <p class="note">
          Habrá una categoría <em>“sin clasificar”</em>, y su tamaño se reporta. Un conjunto de
          reglas que acomoda el 100&nbsp;% de las partidas es la señal de que se ajustaron
          después de ver los datos.
        </p>
        <p class="note">
          Y el orden de magnitud importa: si la muestra sale en ~200 partidas son ~100 derrotas,
          que entre cuatro arquetipos más el residual dejan ~20 por celda. Con 20, una frecuencia
          del 30&nbsp;% trae un intervalo de Wilson de ~[0.15, 0.52]: puedo describir los
          arquetipos, no puedo ordenarlos por frecuencia. Lo digo ahora, no al final.
        </p>""", "14-aritmetica")

# ------------------------------------------------------------ #15 H2 en equipo
sub(H, """              Con la misma ventaja temprana, en las partidas que pierdo tomo menos objetivos
              por minuto que en las que gano.""",
    """              Con la misma ventaja temprana, en las partidas que pierdo mi equipo toma menos
              objetivos por minuto que en las que gana.""", "15-H2")

# ----------------------------------------------- #16 vocabulario de objetivos A3
sub(H, """<span class="test">Partida pareja hasta que la mayor caída de oro coincide con barón, dragón o heraldo.</span>""",
    """<span class="test">Partida pareja hasta que la mayor caída de oro coincide con un objetivo mayor:
              barón, dragón, heraldo, larvas del vacío o Atakhan.</span>""", "16-A3")

# --------------------------------------------------------------- #17 placas: 16
sub(H, """<div class="srcitem"><div class="n">TURRET_PLATE_DESTROYED<small>placas de torre, presión temprana de línea</small></div><div class="v">presente</div></div>""",
    """<div class="srcitem"><div class="n">TURRET_PLATE_DESTROYED<small>placas de torre, presión temprana de línea</small></div><div class="v">16</div></div>""",
    "17-placas")

# ------------------------------------------------------------- #19 cola 420/440
sub(H, """<div class="srcitem"><div class="n">Cola 420, explícita<small>pedir “ranked” a secas mezcla la cola flexible, que tiene premades</small></div><div class="v">solo individual</div></div>""",
    """<div class="srcitem"><div class="n">Cola 420, explícita<small>pedir “ranked” a secas me mezcla la cola flexible, que permite grupos de hasta cinco</small></div><div class="v">Solo/Dúo</div></div>""",
    "19-cola")

# ----------------------------------------------------- #24 correcciones de español
sub(H, "los ARAM y personalizadas ocupan lugar sin avisar", "los ARAM y las personalizadas ocupan lugar sin avisar", "24a")
sub(H, "así que gana por construcción\n              si no se valida cruzado.", "así que gana por construcción\n              si no se usa validación cruzada.", "24b")
sub(H, "<div>Marcador tal como lo entrega el endpoint de partida</div>", "<div>Marcador tal como lo entrega el registro de partida</div>", "24c")
sub(H, "las partidas se guardan ~2 años, pero la línea temporal solo ~1", "las partidas se guardan ≈ 2 años, pero su línea temporal solo ≈ 1", "24d")
sub(H, "solo mis clasificatorias desde ~septiembre de 2025", "solo mis clasificatorias desde ≈ septiembre de 2025", "24e")
sub(H, "la llave de desarrollo se desactiva cada 24 horas", "la llave de desarrollador se desactiva cada 24 horas", "24f")
sub(H, "la otra da los nombres y las imágenes con que se leen.", "la otra da los nombres y las imágenes con los que se leen esos hechos.", "24g")
sub(H, """                <li>Desde el Mundial 2023 muestra una probabilidad de victoria en vivo durante
                  las transmisiones, construida con AWS.</li>""",
    """                <li>Desde el Mundial 2023 muestra una probabilidad de victoria en vivo durante
                  las transmisiones, calculada por un modelo que Riot construyó con AWS.</li>""", "24h")

# ------------------------------------------- #25 "fotograma" -> "cuadro"
sub(H, "Datos reales del <em>timeline</em>, un fotograma por minuto", "Datos reales del <em>timeline</em>, un cuadro por minuto", "25a")
sub(H, "estado del juego y eventos, fotograma por fotograma", "estado del juego y eventos, cuadro por cuadro", "25b")

# =========================================================== CSS
# --------------------------------- #18 --faint -> --muted donde carga palabras
for tag, old, new in [
    ("18a-rail", "  padding: 0 var(--s3);\n  color: var(--faint);\n  border-right: 1px solid var(--line-soft);",
                 "  padding: 0 var(--s3);\n  color: var(--muted);\n  border-right: 1px solid var(--line-soft);"),
    ("18b-counter", "  display: flex; align-items: center; padding: 0 var(--s3);\n  color: var(--faint); font-weight: 600;",
                    "  display: flex; align-items: center; padding: 0 var(--s3);\n  color: var(--muted); font-weight: 600;"),
    ("18c-note", ".note {\n  font-size: 13px; line-height: 1.5;\n  color: var(--faint); max-width: 78ch;\n}",
                 ".note {\n  font-size: 13px; line-height: 1.5;\n  color: var(--muted); max-width: 78ch;\n}"),
    ("18d-th", "  text-align: left; font-weight: 600; font-size: 12px;\n  color: var(--faint); padding: 0 10px 10px;",
               "  text-align: left; font-weight: 600; font-size: 12px;\n  color: var(--muted); padding: 0 10px 10px;"),
    ("18e-pos", ".board .pos { color: var(--faint); font-size: 12px; }",
                ".board .pos { color: var(--muted); font-size: 12px; }"),
    ("18f-axis", ".axis-label { fill: var(--faint);", ".axis-label { fill: var(--muted);"),
    ("18g-code", ".code .c  { color: var(--faint); }", ".code .c  { color: var(--muted); }"),
    ("18h-small", ".srcitem .n small { display: block; color: var(--faint); font-size: 13px; margin-top: 3px; }",
                  ".srcitem .n small { display: block; color: var(--muted); font-size: 13px; margin-top: 3px; }"),
    ("18i-footer", "  font-size: 12px; color: var(--faint);\n  border-top: 1px solid var(--line-soft); padding-top: 12px;",
                   "  font-size: 12px; color: var(--muted);\n  border-top: 1px solid var(--line-soft); padding-top: 12px;"),
]:
    sub(C, old, new, tag)

# ------------------------------------------------ #20a halo en etiquetas de evento
sub(C, '.evt text { font-size: 11px; fill: var(--muted); font-family: "Archivo", sans-serif; }',
    """.evt text {
  font-size: 11px; fill: var(--muted); font-family: "Archivo", sans-serif;
  /* halo: la curva pasaba por encima del texto de "Barón" */
  paint-order: stroke; stroke: var(--deep); stroke-width: 4; stroke-linejoin: round;
}""", "20a-halo")

# ------------------------------------------------------- #22 ancho de los pies de cifra
sub(C, ".stat .k { font-size: 14px; color: var(--muted); line-height: 1.35; max-width: 22ch; }",
    ".stat .k { font-size: 14px; color: var(--muted); line-height: 1.35; max-width: 26ch; }", "22-statk")

# --------------------------------------------- #23 equipo no solo por tinte de fondo
sub(C, """.board tr.us td { background: rgba(14,158,180,.07); }
.board tr.them td { background: rgba(222,67,97,.06); }""",
    """/* El tinte solo daba 1.06:1 de separacion: el equipo tambien se marca con una
   barra lateral, para que no dependa unicamente del color de fondo. */
.board tr.us td { background: rgba(14,158,180,.07); }
.board tr.them td { background: rgba(222,67,97,.06); }
.board tr.us td:first-child { border-left: 4px solid var(--blue); }
.board tr.them td:first-child { border-left: 4px solid var(--red); }""", "23-barra")

# ------------------------------------------- #26a movimiento reducido en el ::before
sub(C, "  #defeat-screen { transition: none; }", "  #defeat-screen, #defeat-screen::before { transition: none; }", "26a-motion")

# =========================================================== JS
# ------------------------------------- #21 la ayuda no debe reaparecer en la charla
sub(J, """      else document.documentElement.requestFullscreen();
    }
    flashHelp();
  });""",
    """      else document.documentElement.requestFullscreen();
    }
    // No se vuelve a mostrar la ayuda: se encimaba con el pie en 11 de 16 laminas.
  });""", "21-help")

# ------------------------------------------------- #26b sin basura en el historial
sub(J, '    location.hash = "d" + (idx + 1);', '    location.replace(location.pathname + "#d" + (idx + 1));', "26b-hash")

# ------------------------------------------- #26c no avanzar al terminar un arrastre
sub(J, """  document.addEventListener("click", function (e) {
    if (e.target.closest("a")) return;
    if (e.clientX < window.innerWidth * 0.22) prev(); else next();
  });""",
    """  // Solo cuenta como clic si el raton no se arrastro: seleccionar texto en una
  // diapositiva no debe pasar a la siguiente.
  var dnX = 0, dnY = 0;
  document.addEventListener("mousedown", function (e) { dnX = e.clientX; dnY = e.clientY; });
  document.addEventListener("click", function (e) {
    if (e.target.closest("a")) return;
    if (Math.abs(e.clientX - dnX) > 5 || Math.abs(e.clientY - dnY) > 5) return;
    if (e.clientX < window.innerWidth * 0.22) prev(); else next();
  });""", "26c-drag")

# ------------------------------- #20b separar puntos de evento que caen encima
sub(J, """        var grp = el("g", { class: "evt " + (o.forLoser ? "ours" : "theirs") });
        grp.style.animationDelay = (opt.animate ? 2.5 + i * 0.09 : 0) + "s";
        grp.appendChild(el("circle", { cx: cx, cy: cy, r: 5.5 }));""",
    """        // dos objetivos casi simultaneos tapaban uno al otro (el Baron quedaba
        // ~60% escondido detras del inhibidor); se separa el segundo unos pixeles
        if (drawn.some(function (p) { return Math.abs(p - cx) < 12; })) cx += 5;
        drawn.push(cx);
        var grp = el("g", { class: "evt " + (o.forLoser ? "ours" : "theirs") });
        grp.style.animationDelay = (opt.animate ? 2.5 + i * 0.09 : 0) + "s";
        grp.appendChild(el("circle", { cx: cx, cy: cy, r: 5.5 }));""", "20b-nudge")

sub(J, """      var labelled = [];   // x ya ocupadas, para no encimar texto""",
    """      var labelled = [];   // x ya ocupadas, para no encimar texto
      var drawn = [];      // x de puntos ya dibujados, para no taparlos""", "20b-init")

# ================================================================= informe
print("=" * 66)
print(f"aplicados: {len(applied)}")
for a in applied:
    print("  +", a)
if missing:
    print(f"\nFALLARON ({len(missing)}):")
    for m in missing:
        print("  !", m)
    sys.exit(1)
print("\ntodos los reemplazos aplicaron")
