# ¿En qué minuto se perdió la partida? — versión narrada (storytelling con datos)

Doble clic en **`presentacion_historia.html`**. Funciona sin internet: las gráficas se
dibujan en el navegador a partir de los datos incrustados en el archivo. Para llevarla a
otra computadora copia **la carpeta completa** (el HTML necesita `assets/`).

Está pensada para un público que **nunca ha jugado** League of Legends: explica el juego en
una lámina, traduce cada gráfica a una idea cotidiana (el oro como la posesión del balón,
«de cada 20 partidas…») y cuenta el análisis como un misterio en cinco actos, en 14 láminas
y unos 6 minutos.

| Tecla | Acción |
|---|---|
| `→` `↓` `espacio` / clic | siguiente paso (cada lámina se arma por pasos) |
| `←` `↑` | paso anterior |
| `F` | pantalla completa |
| `B` o `.` | pantalla en negro |
| `R` | repetir la animación de la lámina desde su primer paso |
| `P` | **modo cine**: la presentación avanza sola; `P` otra vez lo detiene |
| `A` | revelar todos los pasos de la lámina |
| `1`–`5` | saltar a un acto |

Al regresar a una lámina ya vista, aparece completa (no se repite la animación).
Con «reducir movimiento» activado en el sistema, todo aparece sin animación.

## Guion de tiempos (exposición en vivo, ~6 min 10 s)

Es la presentación de la exposición oral. Cada lámina se arma por pasos (50 clics en total);
se dice una idea por paso y se deja ver cada gráfica un segundo antes de explicarla.

| # | Lámina | Seg. | Idea que hay que dejar |
|---|---|---:|---|
| 1 | Portada | 10 | La pregunta |
| 2 | DERROTA | 15 | Es todo lo que el juego te dice. ¿Último minuto o mucho antes? |
| 3 | El juego en 30 s | 35 | Dos equipos, una base, torres y monstruos = objetivos; todo da oro |
| 4 | Las partidas son mías | 15 | 1,195 partidas mías, de seis cuentas |
| 5 | El caso | 50 | Callar mientras corre la línea. Arriba 31 de 34 minutos; desde el 16 la ventaja se encoge; el remate |
| 6 | Tres hipótesis | 30 | Escritas antes de ver los datos; aquí nace «el quiebre» |
| 7 | Los datos | 30 | La base de datos (API de Riot); el filtrado: de 1,241 a 1,195; las victorias como control |
| 8 | La medida | 25 | Preprocesamiento: 2,000 de oro no pesan igual, por eso % del oro del mapa |
| 9 | Pista 1 | 35 | Antes del 15 no se distingue; después, 9.5 contra 6.1 |
| 10 | Pista 2 | 25 | No se puede afirmar: apenas supera al azar, y al ganar lo supera más. El pie dice que la primera regla del quiebre falló |
| 11 | Pista 3 | 35 | 7 → 4 → 1 de cada 20: la puerta se cierra poco a poco, y desde el 27 casi no se abre |
| 12 | Veredicto | 25 | Se confirma, no concluyente, se confirma |
| 13 | La respuesta | 30 | Se van perdiendo: el 64 % de la ventaja se fue antes del remate. Y lo que no puedo afirmar |
| 14 | Gracias | 10 | «Pregúntate cuándo empezó» |
| | **Total** | **370** | ≈ 6 min 10 s |

**Versión corta (noviembre de 2026).** La versión anterior tenía 17 láminas y unos 9 minutos.
Para no dar demasiada información de golpe se quitaron tres láminas: *El oro* (su idea quedó
como el paso 4 del juego), *El tropiezo* (la regla que falló se dice en el pie de la pista 2 y
completa en el reporte) y *Formas de perder* (está en el reporte). El texto en pantalla bajó de
unas 1,470 palabras a unas 790.

`presentacion_historia.pdf` es la misma presentación, una lámina por página y completa (sin
animaciones), por si el HTML no se puede abrir. Se regenera con
`python LoL_PresentacionHistoria/scripts/exportar_pdf.py`.

## Auditoría hecha

1. **Automática** (`shoot.py`): 0 problemas en las 14 láminas de la versión corta (y antes, en
   las 17 de la anterior).
2. **Visual**: cada captura revisada a mano, y cuadros sueltos del video a mitad de animación.
   En la versión corta se volvieron a revisar a mano las 14 capturas.

Las rondas 3 y 4 se hicieron sobre la versión anterior, de 17 láminas, y **no se repitieron
en la versión corta**. Lo que cambió al recortar está al final de `DISENO.md`; en particular,
el quiebre ahora se nombra en la lámina 6 y su regla (y que la primera falló) va en el pie de
la pista 2.

3. **Redacción para quien no juega**: un revisor independiente leyó la presentación como
   alguien que nunca ha jugado y cotejó cada cifra con `LoL_Analisis/resultados/`. Lo que
   cambió por eso: el caso ahora cuenta lo que de verdad pasó (la ventaja se encogió del
   minuto 16 al 32 y el rival remató en los últimos 2 minutos, en vez de «5 contra 12 desde
   el 15», que mezclaba el remate con el desgaste); «el quiebre» se define una sola vez y se
   usa igual en todas las láminas; la pista 2 ya no dice «pasa más cuando gano» sin aclarar
   que es la ventaja *sobre el azar*; los umbrales («con claridad» = 5 % del oro del mapa)
   están en pantalla; la diferencia antes del minuto 15 se marca como dentro del margen de
   error; el cierre dice «no encontré un minuto que decida mis partidas» en vez de una
   afirmación causal; el último cuadro de la partida se dibuja en su minuto real (34:08).
4. **Video y movimiento** (segunda ronda, revisor independiente, cuadro por cuadro): se
   corrigió la lámina vieja que quedaba encimada al cambiar (falla del grabador), los anillos
   del fondo (tramado), las líneas animadas que aparecían completas y se «borraban» al
   abrir la lámina (también pasaba en vivo), el salto de las imágenes al salir, y el reparto
   del tiempo en modo cine (menos pantalla vacía tras cada título, más tiempo para cada
   conclusión, fundido al final). Además: 1,195 en el título de los datos, el quiebre
   definido de forma general en la lámina 7, la «pura casualidad» explicada en pantalla, los
   objetivos del caso en dos filas cerca de su minuto real y el título del eje de la curva de
   remontadas. Se revisaron todas las transiciones a 30 cuadros por segundo.

## El video

**`video/historia.mp4`**: la presentación en modo cine, grabada cuadro por cuadro
(1600×900, 30 cuadros por segundo, 6 min 38 s, H.264, 69 MB, sin audio, termina con un fundido a negro). Lo abre
cualquier reproductor, PowerPoint, Teams o el celular. **Se grabó de la versión anterior, de
17 láminas** (incluye *El oro*, *El tropiezo* y *Formas de perder*); no se ha vuelto a grabar
con la versión corta.

Para regenerarlo, desde la carpeta del proyecto:

```
python LoL_PresentacionHistoria/scripts/video.py --ffmpeg RUTA\ffmpeg.exe --salida LoL_PresentacionHistoria/video/historia.mp4
```

Hace falta un ffmpeg con H.264 (sin `--ffmpeg`, el script usa el que trae Playwright, que
solo produce WebM/VP8). El que se usó viene del paquete `imageio-ffmpeg` de PyPI (compilación
«essentials» de gyan.dev, versión 7.1), instalado aparte con
`python -m pip install --target CARPETA imageio-ffmpeg`; el ejecutable queda en
`CARPETA\imageio_ffmpeg\binaries\`. Conviene una carpeta que Windows no limpie sola, como
`%LOCALAPPDATA%\lol-ffmpeg` (la carpeta temporal se vació una vez y hubo que reinstalarlo). También se puede indicar con la variable `FFMPEG`.

No es una grabación de pantalla: `video.py` reemplaza el reloj de la página por uno que
solo avanza cuando se le pide, pausa cada animación CSS y la coloca en su instante exacto
antes de cada captura. Por eso ninguna animación se acelera ni se atrasa aunque la captura
sea lenta, y cada animación cae en el mismo cuadro en todas las corridas. Los píxeles no
son idénticos al bit: el rasterizado de la imagen difuminada de DERROTA varía hasta 5
niveles de 255 en unos pocos píxeles, invisible a simple vista (`--prueba` imprime una
huella de los cuadros para comparar corridas).

Dos detalles que costaron encontrar:

- **Animaciones «desligadas».** Una animación pausada desde JavaScript ya no se cancela
  sola cuando el elemento cambia de clase. Sin corregirlo, la entrada de cada lámina seguía
  activa cuando la lámina salía y la dejaba encimada bajo la siguiente durante 0.8 s. El
  reloj de `video.py` ahora cancela, en cada cuadro, las animaciones que ya no corresponden
  y las transiciones que ya terminaron. En vivo no ocurre: ahí el navegador las cancela.
- **Anillos en los fondos oscuros.** El resplandor del fondo avanza un nivel de gris cada
  ~40 px y, en 8 bits, se ve como anillos. Una capa de grano fijo (`#grano`, hasta ~3 niveles)
  los rompe, y el H.264 se codifica con `-tune film` y `aq-mode=3` para no alisar ese grano.

`python LoL_PresentacionHistoria/scripts/video.py --ventana K` guarda todos los cuadros de
la transición hacia la lámina K (en `video/muestras/`) para revisarla cuadro por cuadro.

## Cómo se regenera

Ninguna cifra está escrita a mano: salen de los resultados del análisis
(`LoL_Analisis/resultados/`) y de las tablas públicas anonimizadas. Desde la carpeta del
proyecto:

```
python LoL_PresentacionHistoria/scripts/construir.py   # plantilla.html -> presentacion_historia.html
python LoL_PresentacionHistoria/scripts/shoot.py       # capturas + revisión automática
python LoL_PresentacionHistoria/scripts/teclado.py     # recorrido con teclado (en vivo)
python LoL_PresentacionHistoria/scripts/video.py --ffmpeg RUTA\ffmpeg.exe --salida LoL_PresentacionHistoria/video/historia.mp4
```

`teclado.py` recorre todas las láminas paso a paso como en clase, con movimiento normal y con
«reducir movimiento», y revisa que cada lámina termine completa, que al regresar aparezca
hecha, que `R` la repita y que `P` avance solo.

**Se edita `plantilla.html`, nunca `presentacion_historia.html`**: este último se
sobrescribe. `construir.py` falla si queda alguna `{{cifra}}` sin valor.

`shoot.py` revisa: errores de consola, contenido que se sale del escenario o se encima con
el pie, que cada gráfica se haya dibujado, que cada línea animada quede completa, que cada
contador llegue a su cifra, que las imágenes carguen, y que el escenario quepa en
1024×768, 1280×720 y 1366×768 (proyectores).

## Archivos

- `assets/historia.js` — motor: navegación, pasos, «efectos» por paso, gráficas, fondo
  vivo y modo cine.
- `assets/historia.css` — todo el movimiento (sus reglas están al inicio del archivo).
- `assets/deck.css` y las fuentes — copias sin cambios del primer mazo.
- `assets/img/` — arte oficial de Caitlyn y Smolder (Riot Games, Data Dragon).
- `DISENO.md` — el diseño aprobado: actos, reglas y auditoría.
