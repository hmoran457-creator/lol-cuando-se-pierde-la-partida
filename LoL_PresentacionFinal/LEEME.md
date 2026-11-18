# ¿En qué minuto se perdió la partida? — presentación final (10 minutos)

Doble clic en **`presentacion_final.html`**. Funciona sin internet: las figuras y el dato
van incrustados en el archivo. Para llevarla a otra computadora, copia **la carpeta
completa** (el HTML necesita `assets/`).

| Tecla | Acción |
|---|---|
| `→` `↓` `espacio` | siguiente |
| `←` `↑` | anterior |
| `F` | pantalla completa |
| `B` o `.` | pantalla en negro |
| `R` | repetir la animación de la lámina (la cortina de la gráfica) |
| `1`–`5` | saltar a una sección de la rúbrica |

## Guion de tiempos

| # | Lámina | Seg. | Idea que hay que dejar |
|---|---|---:|---|
| 1 | Portada | 10 | La pregunta del título |
| 2 | DERROTA | 15 | Esto es todo lo que el juego te dice |
| 3 | La partida (V1) | 75 | Arriba en oro casi toda la partida, y perdida. Dejar correr la cortina en silencio (1.4 s) antes de hablar |
| 4 | Hipótesis | 60 | Cómo empezaron y cómo terminaron, con la razón de cada cambio |
| 5 | Datos y filtrado | 50 | Seis cuentas; el embudo; las victorias son el control |
| 6 | Preprocesamiento | 50 | La diferencia de oro se construye; anonimizar primero |
| 7 | E1 | 55 | La primera definición falló, y se dice |
| 8 | H1 | 60 | Antes del 15 no se distingue; después, sí |
| 9 | H2 | 60 | No concluyente: depende de la nula y de la definición, y pasa más al ganar |
| 10 | H3 | 50 | Se confirma: desde el minuto 27 casi nadie remonta (umbral declarado) |
| 11 | Arquetipos | 55 | Explican el 48 %; el resto son partidas parejas |
| 12 | Conclusiones | 40 | Se van perdiendo; y lo que no se puede afirmar |
| 13 | Gracias | 10 | Abrir preguntas |
| | **Total** | **590** | 9 min 50 s |

## Cómo se regenera

Ninguna cifra está escrita a mano: salen de los resultados del análisis
(`LoL_Analisis/resultados/`). Si el análisis cambia, desde la carpeta del proyecto:

```
python LoL_PresentacionFinal/scripts/figuras_deck.py   # figuras SVG con el tema del mazo
python LoL_PresentacionFinal/scripts/construir.py      # plantilla.html -> presentacion_final.html
python LoL_PresentacionFinal/scripts/shoot.py          # capturas + revisión de maquetación
python LoL_PresentacionFinal/scripts/exportar_pdf.py   # presentacion_final.pdf, el respaldo
```

`presentacion_final.pdf` es la misma presentación, una lámina por página y completa (sin
animaciones), para cuando el HTML no se pueda abrir. Son capturas a doble resolución: el
texto no se puede seleccionar.

**Se edita `plantilla.html`, nunca `presentacion_final.html`**: este último se sobrescribe.
`construir.py` falla si queda alguna `{{cifra}}` sin valor.

`shoot.py` revisa errores de consola, contenido que se sale del escenario o se encima con
el pie, que la gráfica animada dibuje su línea, que cada figura esté incrustada, y que el
escenario quepa en 1024×768, 1280×720 y 1366×768 (proyectores).

## Qué se reutilizó y qué es nuevo

- `assets/deck.css` y las fuentes son **copias sin cambios** del mazo de la primera
  entrega (`LoL_Presentacion/`). Lo nuevo vive en `assets/final.css` con ids `f-*`, así que
  editar este mazo no rompe los anteriores.
- `assets/deck_final.js` conserva la navegación del motor original; cambia el riel (las
  secciones de la rúbrica final) y la gráfica, que ahora usa `v(t)` en % del oro del mapa
  con la escala tomada del dato.
- Las figuras se exportan como SVG con el texto como texto, al tamaño exacto en píxeles
  de la lámina: así no se estiran y heredan la tipografía Archivo de la página.

## Privacidad

La partida de V1 se muestra **a nivel equipo**: curva de oro y objetivos. Sin nombres, sin
campeones de otros jugadores y sin el identificador de la partida.
