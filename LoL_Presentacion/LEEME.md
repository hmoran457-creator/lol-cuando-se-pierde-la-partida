# ¿En qué minuto se perdió la partida? — presentación

Presentación de **planteamiento de proyecto**, en español.
Todo funciona **sin internet**: no hay una sola referencia a un CDN.

## Hay dos versiones

| Archivo | Láminas | Duración | Para qué |
|---|---|---|---|
| **`presentacion.html`** | 18 | ~10–12 min | La versión completa |
| **`presentacion_5min.html`** | 9 | ~5 min | Versión corta |
| **`presentacion_story.html`** | 12 | ~5–7 min | Versión narrada, avanza por pasos |

Las dos comparten estilos, motor y datos (`assets/` y `data/`), así que un cambio
en la gráfica o en los datos se refleja en ambas. Las dos cubren los **tres puntos
de la rúbrica** y las dos llevan el riel numerado arriba: una versión corta puede
recortar ejemplos, no secciones calificadas.

### Qué se recortó en la de 5 minutos

Nada de las tres secciones obligatorias. Lo que se comprimió:

- Las **cuatro láminas de la partida de ejemplo** (marcador, revelación, rebobinado,
  punto de quiebre) se funden en **una sola**: la gráfica completa con la cortina,
  la banda del pico, los objetivos etiquetados y los hechos en un renglón.
- **Prioridad, mapa de eventos, alcance y límites** salen como láminas propias; lo
  esencial de cada una se conserva dentro de las que quedan.
- Las **seis hipótesis** vuelven a una sola lámina en vez de dos.
- **Arquetipos y plan de trabajo** se funden en la lámina de cierre; en la completa los
  arquetipos ocupan dos láminas (las reglas, y luego sus límites).

### Guion de tiempos para los 5 minutos

| # | Lámina | Segundos | Idea que hay que dejar |
|---|---|---|---|
| 1 | Portada | 10 | La pregunta del título |
| 2 | DERROTA | 20 | Esto es todo lo que el juego te dice |
| 3 | El marcador / el oro | 70 | **Nunca estuvieron detrás y aun así perdieron** |
| 4 | La pregunta | 40 | Qué busca y qué no busca el proyecto |
| 5 | Fuentes de datos | 45 | Dos fuentes, y la muestra me la impone la API |
| 6 | Vista general | 50 | El payload real; el oro lo calculo yo |
| 7 | Hipótesis | 40 | Seis, cada una con su trampa |
| 8 | Arquetipos y cierre | 15 | El entregable y qué lo haría fracasar |
| 9 | Gracias | 10 | Abrir preguntas |

La lámina 3 es la que carga la presentación: la gráfica tarda **1.4 s** en
descubrirse, así que conviene dejarla correr en silencio antes de hablar.

## Cómo abrirla

Doble clic en **`presentacion.html`** (o en **`presentacion_5min.html`**).
Cualquier navegador moderno sirve. Pulsa **F** para pantalla completa antes de empezar.

| Tecla | Acción |
|---|---|
| `→` `↓` `espacio` `Av Pág` | siguiente |
| `←` `↑` `Re Pág` | anterior |
| `Inicio` / `Fin` | primera / última |
| `F` | pantalla completa |
| `B` o `.` | pantalla en negro (cualquier tecla la quita) |
| `R` | repetir la animación de la lámina |
| `1` `2` `3` | saltar a una sección de la rúbrica |

También funciona con clic (izquierda retrocede, resto avanza) y con deslizar en pantalla táctil.
La dirección `#d7` al final de la URL abre directo en la diapositiva 7 — útil para ensayar una sola.

## Para llevarla a otra computadora

Copia **la carpeta completa**, no solo el `.html`. Las rutas son relativas, así que funciona
desde una USB o desde cualquier ruta. Pesa unos 14 MB (casi todo son los payloads crudos
de la partida de ejemplo, en `data/riot_examples/`).

## Estructura

```
presentacion.html          la versión completa, 18 láminas
presentacion_5min.html     la versión corta, 9 láminas
presentacion_story.html    la versión narrada, 12 láminas por pasos
assets/
  deck.css                 estilos, paleta y animaciones
  deck.js                  navegación, gráfica, marcador y mapa
  fonts.css + fonts/       tipografías locales (Archivo, JetBrains Mono)
  champions/               10 retratos, Data Dragon 16.17.1
  misc/                    ilustración de la pantalla de derrota
data/
  story.js                 los datos de la gráfica (define window.LOL_DATA)
  riot_examples/           los payloads crudos de la partida de ejemplo
scripts/
  fetch_and_probe.py       descarga y mide partidas públicas de ejemplo
  build_story.py           convierte el payload crudo en data/story.js
  vendor_fonts.py          descarga las tipografías para uso sin internet
  shoot.py                 captura cualquiera de los dos mazos y revisa maquetación
  probe_alto.py            mide qué ocupa el alto de una lámina
shots/ y shots_5min/       una captura por lámina de cada mazo
VALIDACION.md              la base técnica del proyecto — léelo antes de programar
```

## Las tres secciones que pide la rúbrica

El riel de arriba las muestra siempre, para que el evaluador vea dónde vamos:

| Sección | En la completa | En la de 5 min |
|---|---|---|
| 1 · Problemática | láminas 2–8 | 2–4 |
| 2 · Fuentes de datos y vista general | 9–13 | 5–6 |
| 3 · Hipótesis | 14–17 | 7–8 |  (en la narrada: 9–11)

## Los umbrales de los arquetipos

Las cuatro reglas llevan umbral numérico, y son las mismas en los dos mazos:

- **La medida** es `v` = diferencia de oro del equipo ÷ oro total en el mapa, cuadro por cuadro.
  Es **relativa** a propósito: 2,467 de oro son el 7.7 % del mapa en el minuto 10 y solo el
  2.3 % en el 28 — un umbral fijo en oro diría que son lo mismo.
- **Ventaja real:** `v ≥ 5 %` y al menos 1,500 de oro. El piso absoluto existe para que un
  solo asesinato del minuto 4 no cuente como ventaja.
- **Decisiva:** `|v| ≥ 10 %`.  **Sostenida:** `≥ 3 minutos` seguidos.
- Se evalúan en orden **A4 → A2 → A1 → A3**; lo que no cumple ninguna queda *sin clasificar*.

`python scripts/probe_umbrales.py` comprueba que estas reglas clasifiquen la partida de
ejemplo como **A2**, que es lo que la lámina afirma. Si se cambia un umbral, hay que volver
a correrlo: si deja de dar A2, la lámina se contradice a sí misma.

## La versión narrada y sus pasos

`presentacion_story.html` cuenta lo mismo como historia: una idea por lámina, menos
texto y más aire. Su diferencia mecánica es que **el contenido se descubre por
partes**: cada flecha o clic muestra el siguiente bloque, y al agotarse los pasos
la misma tecla pasa de lámina. El presentador usa un solo botón para todo.

Los **puntos junto al contador** del riel dicen cuántos pasos faltan en la lámina.

| Situación | Qué pasa |
|---|---|
| Se te va un clic de más | `←` retrocede un paso, si la lámina está a medias |
| Ya está revelada del todo | `←` regresa de lámina, para responder una pregunta |
| Vuelves a una lámina ya vista | aparece entera, sin volver a armarse |
| Necesitas verla completa ya | tecla **`A`** |
| Vas a leerla o entregarla | abre con **`?todo`** al final de la dirección: apaga los pasos |

Los otros dos mazos **no tienen pasos**: una flecha, una lámina. El sistema solo
actúa en las láminas marcadas con `data-steps`.

## Qué se mueve, y por qué

Nada se mueve por adorno: cada animación pone en secuencia algo que la lámina
**argumenta**. En los dos mazos:

| Dónde | Qué | Por qué |
|---|---|---|
| Cada cambio de lámina | corte direccional, 260 ms | avanza descubriendo de izquierda a derecha, como se lee |
| La gráfica | **cortina del reloj**, 1 400 ms lineales | el borde avanza en X, y X es el minuto: cada marca aparece cuando le toca |
| Riel y barra de progreso | 260–400 ms | señalan en qué sección de la rúbrica vamos |
| El cierre | subrayado de «esta», 600 ms | hace caer la frase que rima con el título |

La cortina es **lineal** a propósito: representa el paso del tiempo de juego, y el
tiempo no acelera. Volver atrás **no** repite la animación (para eso está `R`).

### Extras sólo del mazo de 5 minutos

Todo lo de abajo se activa con `class="animado"` en su `<body>`. Para tenerlo
también en el mazo largo basta con ponerle la misma clase.

**Cascada de entrada.** Cada lámina se arma sola: primero el rótulo (40 ms), luego
el titular (90 ms), luego los bloques del cuerpo escalonados, y las listas y fichas
de a una. Todo termina antes de **700 ms**, y el titular llega casi de inmediato —
nada que haya que *leer* espera. El recorrido es de 9 px: se lee como que la lámina
se arma, no como que las cosas vuelan.

**Contadores.** Las dos cifras que *son* el argumento de la lámina 3 (+8,052 y
+1,034) cuentan hasta su valor en 820 ms. El `0` se queda quieto: contar hasta cero
no dice nada. El número final ya está escrito en el HTML, así que sin JS la lámina
se lee igual.

**Tres momentos puntuales**, que devuelven lo que se perdió al fundir cuatro
láminas de gráfica en una:

| Lámina | Qué | Por qué |
|---|---|---|
| 2 · DERROTA | el subtítulo llega 900 ms después | primero el veredicto; después, lo que el juego *no* te dice — que es lo que la lámina afirma |
| 3 · La partida | los hechos en prosa llegan al terminar la cortina | la gráfica ya los contó; el texto los confirma, no compite |
| 6 · Vista general | se ilumina `timestamp` a los 1 150 ms | señala el campo del que depende todo el proyecto, sin robarle la lectura al bloque |

Van bajo `.animado` porque los dos mazos comparten ids de lámina. Para activarlas
también en el mazo largo: `<body class="animado">`.

Nada se repite al **retroceder**: al volver a una lámina ya vista se le pone la
clase `visto` y aparece entera. Con `R` se repite a propósito.

`python scripts/probe_animado.py` comprueba las cinco cosas que pueden fallar por
separado: que las puntuales **corran**, que la cascada **se escalone**, que los
contadores **cuenten**, que al retroceder **no se repita nada**, y que ni el mazo
largo ni `prefers-reduced-motion` se vean afectados —dejando siempre el estado
final visible, porque el resaltado del `timestamp` es contenido, no adorno.

> **Cuidado con la especificidad.** Las reglas animadas llevan `:not(.visto)`, que
> cuenta como clase. El bloque de `prefers-reduced-motion` tiene que **repetir ese
> mismo `:not(.visto)`** o pierde la pelea y la animación sigue corriendo con
> movimiento reducido puesto. Ya pasó una vez; lo detectó el sondeo.

## Cuidado al editar: los dos mazos comparten el CSS

`assets/deck.css` sirve a los dos archivos, y **varias láminas usan el mismo `id`**
en ambos (`s-arch`, `s-timeline`, `s-question`, `s-sources`, `s-defeat`). Una regla
como `#s-arch .row.grow { … }` toca **los dos mazos a la vez**, aunque el contenido
de esa lámina sea distinto en cada uno.

Ya mordió una vez: relajar esa regla para el mazo largo —donde los paneles se
habían movido a otra lámina— empujó el cierre sobre el pie en el de 5 minutos.
**Después de tocar el CSS, verifica los dos:**

```
python scripts/shoot.py && python scripts/shoot.py presentacion_5min.html
```

## Sobre los datos

La partida del ejemplo es **`EUW1_6569580003`**: pública, real y **no es mía**. Sirve para
plantear la pregunta, nunca como resultado — la presentación lo dice en cada diapositiva donde
aparece. Cuando tengas tus propias partidas, `scripts/build_story.py` regenera `data/story.js`
y las gráficas se actualizan solas.

Las cifras de las gráficas salen del payload real. Lo único ilustrativo va marcado con una
etiqueta ámbar; lo medido, con una etiqueta azul.

**Trampa al regenerar:** `build_story.py` actualiza las **gráficas**, no el texto de las
diapositivas. Los números que aparecen en prosa (+8,052, +1,034, 28:35, los conteos de eventos)
están escritos a mano en los **dos** `.html` y hay que reescribirlos en ambos, o dejarán de coincidir con
los datos en silencio.

## Si algo se ve mal

`python scripts/shoot.py` vuelve a capturar las láminas en `shots/` y reporta errores de
consola, texto que se sale, contenido que se derrama sobre el pie y gráficas que no
dibujaron. También comprueba que el escenario quepa entero en 1024x768, 1280x720 y
1366x768, que es el caso real de un proyector.

```
python scripts/shoot.py                        # el mazo largo
python scripts/shoot.py presentacion_5min.html # el de 5 minutos -> shots_5min/
python scripts/shoot.py 6                      # una sola lámina
```
