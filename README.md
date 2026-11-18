# ¿En qué minuto se perdió la partida?

Proyecto final de *Visualización de datos y narración de historias* (Especialidad en Ciencia
de Datos). A partir de 1,195 partidas clasificatorias propias de League of Legends (537
derrotas y 658 victorias, de 6 cuentas en el servidor de Latinoamérica Norte), el proyecto
busca en qué momento se pierde una partida.

**La respuesta corta:** mis partidas casi nunca se pierden en el último momento: se van
perdiendo, y hacia el minuto 27 ya casi no tienen regreso. Remontar estando abajo pasa del
37 % en el minuto 5 al 20 % en el 15, y desde el 27 lo logra menos de una de cada veinte
partidas. Con ventaja, en las derrotas se toman menos objetivos, pero solo después del minuto
15. Y que el quiebre coincida con un monstruo del rival no se puede afirmar: depende de cómo
se mida y pasa más cuando gano.

## Por dónde empezar

| Qué | Dónde |
|---|---|
| **Presentación de la exposición** (10 min, 13 láminas) | [`LoL_PresentacionFinal/`](LoL_PresentacionFinal/): abrir `presentacion_final.html`; en PDF, [`presentacion_final.pdf`](LoL_PresentacionFinal/presentacion_final.pdf) |
| **Reporte final** (método, pruebas, código) | [`LoL_Reporte/reporte_final.pdf`](LoL_Reporte/reporte_final.pdf) |
| Presentación narrada, para quien nunca ha jugado (complementaria) | [`LoL_PresentacionHistoria/`](LoL_PresentacionHistoria/): abrir `presentacion_historia.html` |
| Video de la presentación narrada | [`LoL_PresentacionHistoria/video/historia.mp4`](LoL_PresentacionHistoria/video/historia.mp4) |
| Planteamiento del proyecto (el plan, registrado antes de ver los datos) | [`LoL_Planteamiento/planteamiento_proyecto_final.pdf`](LoL_Planteamiento/planteamiento_proyecto_final.pdf) |
| Actividad de anonimización (sobre el piloto de 7 partidas públicas) | [`LoL_Anonimizacion/reporte_anonimizacion.pdf`](LoL_Anonimizacion/reporte_anonimizacion.pdf) |
| Actividad de reducción de dimensionalidad (PCA, LDA, t-SNE, UMAP) | [`LoL_Dimensionalidad/reduccion_dimensionalidad.pdf`](LoL_Dimensionalidad/reduccion_dimensionalidad.pdf) (y su `.ipynb`) |
| Análisis exploratorio posterior al proyecto | [`LoL_Exploratorio/analisis_exploratorio.pdf`](LoL_Exploratorio/analisis_exploratorio.pdf) (y su `.ipynb`) |
| **Herramienta: probabilidad de ganar** según el marcador (y el oro, si se conoce) | [`LoL_Probabilidad/probabilidad.html`](LoL_Probabilidad/probabilidad.html); cómo se eligió el modelo en su [LEEME](LoL_Probabilidad/LEEME.md) |

Las presentaciones son HTML que funcionan sin internet. Para verlas, descarga el repositorio
completo, porque cada una necesita su carpeta `assets/`. La política de privacidad aplicada al
corpus real (y su riesgo residual) está en el reporte final, sección «Preprocesamiento».

## Los dos notebooks

Cada uno se entrega como `.ipynb` ya ejecutado (con todas sus salidas) y como PDF. Ninguno
cambia las conclusiones del proyecto.

### Reducción de dimensionalidad

[`LoL_Dimensionalidad/`](LoL_Dimensionalidad/) es una actividad del curso: cada partida que
llegó al minuto 20 (1,132) es un punto en 20 dimensiones, la ventaja de oro minuto a minuto. Se
proyecta a 2D con PCA, LDA, t-SNE y UMAP, cada uno con su barrido de parámetros, y los mapas se
comparan con confiabilidad y silueta.

- **No hay grupos separados:** las victorias y las derrotas forman un continuo ordenado por la
  ventaja de oro en los cuatro métodos.
- **Con PCA basta:** dos componentes guardan el 83 % de la varianza, y la primera es la ventaja
  promedio.
- **El minuto 20 dice tanto como los 20 minutos:** decir «victoria» si se va arriba al minuto 20
  acierta tanto como LDA con la curva completa (77 % contra 76 %).
- **Las derrotas de «ventaja tirada» (A2) caen entre las victorias:** se perdieron después de la
  ventana que ven los mapas.

Usa solo las tablas públicas, así que se puede volver a ejecutar desde el repositorio.

### Análisis exploratorio

[`LoL_Exploratorio/`](LoL_Exploratorio/) hace cuatro preguntas que surgieron al cerrar el
proyecto. **No estaban registradas antes de ver los datos**, así que sus resultados son pistas
para una siguiente ronda, no confirmaciones.

1. **¿Perdí yo?** Casi nunca en mi línea: en mis derrotas jugando BOTTOM, mi duelo aporta el 13 %
   del déficit del equipo al minuto 15 y MIDDLE el 31 %.
2. **¿Qué pasa en el quiebre?** Peleas perdidas, no objetivos: sobran las muertes de mi equipo,
   los dragones y las torres aparecen lo normal, y solo el barón del rival destaca.
3. **¿Importa el camino?** No: con la ventaja del minuto actual basta. Incluye una tabla de
   probabilidad de ganar por minuto y ventaja («de cada 20 partidas…»).
4. **¿Dónde muero?** En las derrotas muero más y, después del minuto 15, en mi propia mitad,
   defendiendo.

Este notebook lee las tablas por participante, que no se publican (ver «Privacidad»), así que
**no se puede volver a ejecutar desde el repositorio**.

## Estructura

```
LoL_Datos/                 descarga desde la API de Riot (match-v5) y revisión de la muestra
  anonimizado/publico/     las tablas públicas: partidas, oro por equipo y objetivos por equipo
  anonimizado/resumen_descarga.json   conteos agregados de lo que se queda en local
LoL_Anonimizacion/         actividad de anonimización (piloto): política, barrido de fugas, riesgo
LoL_EDA/                   análisis exploratorio (piloto)
LoL_Analisis/              experimentos E1–E8 y V1: scripts, resultados, figuras y pruebas
LoL_Dimensionalidad/       notebook de reducción de dimensionalidad (actividad del curso)
LoL_Exploratorio/          notebook de análisis exploratorio posterior al proyecto
LoL_Probabilidad/          herramienta de probabilidad de ganar: modelos comparados, elegido y página
LoL_Reporte/               reporte final (LaTeX)
LoL_Planteamiento/         planteamiento del proyecto (LaTeX)
LoL_PresentacionFinal/     presentación final, la de la exposición
LoL_PresentacionHistoria/  presentación narrada con movimiento y su video
LoL_Presentacion/          primera presentación (avance; histórica, no se mantiene)
```

`LoL_Presentacion/` es la entrega de avance y se conserva como estaba. Sus scripts
`apply_*`, `probe_*` y `fix_*` fueron parches de un solo uso sobre aquel HTML: no se deben
volver a correr.

## Reproducir

Requiere Python 3.13 y las versiones fijadas en `requirements.txt`. Desde la carpeta del
proyecto:

```
python -m pip install -r requirements.txt
python -m pytest LoL_Analisis/tests LoL_Anonimizacion/tests LoL_Datos/tests    # ~1.5 min

python LoL_Analisis/scripts/e1_quiebre.py     # ~15 s
python LoL_Analisis/scripts/e2_e4.py          # ~30 s
python LoL_Analisis/scripts/e5_e8.py          # ~4-5 min
python LoL_Analisis/scripts/v1_partida.py     # ~10 s
```

Los experimentos leen **solo** las tablas públicas de `LoL_Datos/anonimizado/publico/` y
regeneran `LoL_Analisis/resultados/` idéntico, con las semillas fijas.

**El reporte en PDF** (necesita LuaLaTeX, de TeX Live o MiKTeX, y la fuente DejaVu Sans Mono):

```
python LoL_Reporte/scripts/cifras.py
latexmk -cd -lualatex LoL_Reporte/reporte_final.tex
```

**Las presentaciones** (necesitan `python -m playwright install chromium` para las revisiones):

```
python LoL_PresentacionFinal/scripts/figuras_deck.py
python LoL_PresentacionFinal/scripts/construir.py
python LoL_PresentacionFinal/scripts/shoot.py
python LoL_PresentacionHistoria/scripts/construir.py
python LoL_PresentacionHistoria/scripts/shoot.py
python LoL_PresentacionHistoria/scripts/teclado.py
```

El video se graba con `LoL_PresentacionHistoria/scripts/video.py` (ver su
[LEEME](LoL_PresentacionHistoria/LEEME.md); necesita un ffmpeg con H.264).

**Los notebooks** (también necesitan playwright con Chromium, para el PDF). Cada script arma el
`.ipynb`, lo ejecuta completo y lo exporta a PDF:

```
python LoL_Dimensionalidad/scripts/construir_notebook.py
python LoL_Exploratorio/scripts/construir_notebook.py      # ~1.5 min; solo con los datos locales
```

El texto de las celdas vive en `scripts/celdas.py` de cada carpeta: se edita ahí, no en el
`.ipynb`, que se sobrescribe.

Ninguna cifra de los reportes ni de las presentaciones está escrita a mano: `cifras.py` y los
`construir.py` las toman de `LoL_Analisis/resultados/` y de
`LoL_Datos/anonimizado/resumen_descarga.json`. Este último guarda, ya contados, los pocos
datos que solo existen en local (partidas por cuenta, dúos entre cuentas propias, eventos de
la muestra y los campeones del autor). Lo que **no** corre sin los datos originales es la
descarga, la anonimización, `resumen_publico.py`, el EDA piloto, el notebook exploratorio y el
entrenamiento del modelo de probabilidad; sus salidas sí están incluidas (la página de la
herramienta se reconstruye con `python LoL_Probabilidad/scripts/construir.py`).

## Privacidad

Las partidas incluyen a otras nueve personas en cada juego, que no dieron permiso para
publicar sus datos. Por eso este repositorio **no contiene**:

- el JSON crudo de Riot, que trae el Riot ID y el PUUID de los diez jugadores;
- tablas por participante, porque el campeón y el rol de cada desconocido podrían identificarlo;
- los Riot ID de las cuentas del autor;
- la llave de la API de Riot.

Solo se publican tablas **por equipo**, con la partida bajo un seudónimo, la fecha
generalizada a mes y la cuenta propia como `C1`–`C6`. De los eventos solo van torres y
monstruos épicos, sin posición en el mapa.

El notebook exploratorio sí usa las tablas por participante, pero solo en local. Publica
únicamente **agregados**: tasas, curvas, tablas por rol y un mapa de densidad de las muertes del
propio autor en celdas. Ninguna salida trae filas por partida. El modelo de probabilidad también
se entrena en local; lo publicado son sus coeficientes, 200 juegos de coeficientes remuestreados
y agregados por minuto. Su tabla de entrenamiento (`LoL_Probabilidad/datos/`) no se publica.
El `construir_notebook.py` del notebook exploratorio se
detiene sin guardar si alguna salida contiene el seudónimo de una partida o de un jugador, o el
campeón de otro jugador. Las partidas siguen siendo enlazables con el
historial público del autor (mes, cuenta y duración casi siempre señalan una sola), pero eso no
expone a los otros jugadores más allá de lo que ese historial ya muestra. Volver a descargar los
datos requiere una llave propia de Riot (`LoL_Datos/scripts/descargar_partidas.py`). Los
ejemplos con partidas `EUW1_…` vienen de los ejemplos públicos de `MingweiSamuel/riotapi-schema`
y no son partidas del autor.

## Licencias

Código bajo MIT ([`LICENSE`](LICENSE)); textos, figuras, presentaciones y video bajo CC BY 4.0;
fuentes tipográficas bajo SIL OFL 1.1; el arte de los campeones y los datos del juego son de
Riot Games. El detalle está en [`LICENCIAS.md`](LICENCIAS.md).

---

Héctor Manuel Morán Maldonado. Elaborado con la asistencia de Claude (Anthropic).

*Proyecto no avalado por Riot Games. League of Legends y Riot Games son marcas registradas de
Riot Games, Inc. El arte de los campeones es de Riot Games (Data Dragon).*
