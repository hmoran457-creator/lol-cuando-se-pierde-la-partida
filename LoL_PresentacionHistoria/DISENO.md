# Presentación narrada — diseño aprobado

## Para quién y para qué

- **Audiencia:** gente que no juega League of Legends.
- **Objetivo:** contar la historia del proyecto con datos, con movimiento, ejemplos e
  imágenes, en 10 minutos, cubriendo los puntos de la rúbrica sin que se note la
  estructura de reporte.
- **Éxito:** alguien que nunca jugó puede explicar al salir qué es el oro, qué se
  investigó y cuál fue la respuesta.

## La historia, en 6 actos

| Acto (riel) | Rúbrica que cubre | Láminas |
|---|---|---|
| 1 · El misterio | Descripción del problema | DERROTA; el juego en 60 s (mapa); el oro; quién soy; el caso (V1) |
| 2 · Las pistas | Hipótesis iniciales | la pregunta y tres pistas (H1–H3) en lenguaje cotidiano |
| 3 · Las pruebas | Bases de datos, filtrado, preprocesamiento, método | 1,241 partidas como «fotos por minuto»; cómo se mide la ventaja (ejemplo); el tropiezo de la primera regla |
| 4 · Lo que encontré | Experimentos y visualizaciones | pista 1, 2 y 3; las formas de perder |
| 5 · La respuesta | Hipótesis finales y conclusiones | veredicto de cada pista; vuelta al caso del inicio |

## Reglas de diseño

- **Cero jerga sin explicar.** «Objetivo», «Nexo», «tirador», «clasificatoria» se definen
  la primera vez. Nada de D1/D2 ni v(t) en los titulares.
- **Cada cifra con traducción cotidiana** («de cada 20 partidas…»).
- **Azul = mi equipo, rojo = rival, dorado = lo que hay que mirar** (siempre con texto).
- **El movimiento cuenta algo:** las líneas se trazan en el orden del tiempo, los objetivos
  aparecen uno por uno, las figuras se llenan. Todo por pasos, al ritmo del presentador.
- **Ninguna cifra a mano:** salen de `LoL_Analisis/resultados/` vía `scripts/construir.py`.
- **Privacidad:** la partida del caso, solo a nivel equipo. Imágenes: el mapa y los íconos
  se dibujan; el arte oficial de Caitlyn y Smolder (Data Dragon, autorizado) es del
  propio jugador.

## Auditoría

1. `scripts/shoot.py`: consola, desbordes, encuadre en proyectores, capturas.
2. Revisión visual lámina por lámina y de cifras contra los resultados.
3. Lectura independiente por un agente con el papel de alguien que nunca jugó.

## Desviaciones tras la auditoría

El diseño aprobado se respetó en estructura (seis actos, 17 láminas), pero la auditoría de
redacción cambió tres cosas del contenido:

1. **El caso ya no se cuenta «desde el minuto 15».** La franja dorada empieza en la ventaja
   máxima (minuto 16, +5.9 % del oro del mapa). «5 objetivos nuestros contra 12 del rival
   desde el 15» mezclaba el desgaste con el remate final: 6 de esos 12 fueron en los últimos
   2 minutos. Ahora la lámina dice que la ventaja se encogió de +5.9 % a +2.1 % (minuto 32)
   y luego vino el remate, marcado aparte.
2. **El cierre rebobina hasta el minuto 16**, no hasta el 15: «perdimos el 64 % de la
   ventaja antes del remate».
3. **El titular del cierre se suavizó**: «No encontré un minuto que decida mis partidas.
   Se van perdiendo.» La curva de remontadas es un promedio y no basta para afirmar que
   cada partida se pierde poco a poco.

## Desviaciones tras la auditoría del proyecto completo

Una segunda auditoría, del proyecto entero y no solo de esta presentación, encontró que dos
veredictos se apartaban de las reglas registradas en el plan. Con autorización del autor, se
aplicaron las reglas tal como se escribieron, y eso cambió el mensaje de dos láminas:

4. **Pista 3 ya no dice «no hay un punto sin regreso».** El plan decía que H3 se mantiene si
   la muestra alcanza y que se refuta solo si la curva no baja. La curva sí baja: desde el
   minuto 27, menos de 1 de cada 20 partidas que van abajo remonta. El título queda «la puerta
   se va cerrando poco a poco… y hacia el minuto 27 ya casi no se abre», con el marcador en la
   curva. El umbral de 5 % se fijó después de ver los datos y la lámina lo dice.
5. **Pista 2 queda «no se puede afirmar».** Con la definición del quiebre que se registró
   (la mayor caída) la coincidencia no supera al azar; con la principal, apenas.
6. **El cierre** pasa a «Mis partidas casi nunca se pierden en el último momento. Se van
   perdiendo.», coherente con un punto casi sin regreso al que se llega poco a poco.
7. **Los campeones se cuentan en la muestra final** (1,195 partidas): Smolder 108 y Caitlyn
   106, en ese orden. Cada tarjeta toma el arte de su campeón por nombre.

El 15 de la pista 1 ya no está escrito a mano: sale de `umbral` en `construir.py`.

## Versión corta (noviembre de 2026)

Para la exposición, la presentación pasó de 17 a 14 láminas y de unos 9 a unos 6 minutos:
entre los datos y los hallazgos se daba demasiada información de golpe.

8. **Se quitaron tres láminas.** *El oro*: su idea es ahora el paso 4 de «el juego en 30
   segundos» (los monstruos se unieron al paso de las torres). *El tropiezo*: la regla del
   quiebre y que la primera falló se dicen en el pie de la pista 2; el detalle está en el
   reporte. *Formas de perder*: está en el reporte y en las preguntas del guion. Los dibujos
   `oro`, `tropiezo` y `forma` siguen en `historia.js` sin usarse.
9. **Una cifra por paso.** Se quitaron casi todos los subtítulos de dos líneas y los pies
   largos; el texto en pantalla bajó de unas 1,470 a unas 790 palabras. El veredicto pone, en
   cada tarjeta, la hipótesis inicial (pregunta) y la final (respuesta). Se dejaron en
   pantalla dos aclaraciones para quien no juega: el caso dice que la ventaja va «en % del oro
   del mapa» (la medida se explica tres láminas después) y la pista 2 dice qué es la «pura
   casualidad» (los mismos monstruos en minutos al azar).
10. **La etiqueta del eje de la curva de remontadas** se movió a la izquierda: la marca del
    minuto 27 la cruzaba.

## Tema claro (noviembre de 2026)

11. **Abre en claro; `T` (o el botón del riel) cambia a oscuro** y la elección se recuerda.
    Papel cálido `#FAF7F0`, tinta azul marino `#14253B`, los mismos tonos de equipo más
    oscuros (azul `#0A7A8C`, rojo `#C22E5E`) y el oro partido en dos: `#B07D10` para marcas y
    `#87590A` para letras. Contraste: texto ≥ 4.7:1, marcas ≥ 3:1. Daltonismo (Machado 2009,
    OKLab): azul, rojo y oro separados ≥ 9.9 en protan, deutan y tritan; el rojo se movió hacia
    el magenta porque el primer intento quedaba en 5.1 contra el oro en deutan.
12. **Los colores fijos pasaron a fichas** (`assets/tema.css`): el mapa, las figuras grises,
    los sellos, las tarjetas del veredicto, el rojo y el azul para letras y el texto sobre
    barras. El nombre de los campeones va sobre la franja oscura de su imagen en los dos temas,
    así que lleva colores claros fijos.
13. **DERROTA se queda oscura** en los dos temas: es la pantalla del juego al perder, y en
    claro se le devuelven sus fichas oscuras.
14. **Con `?todo` (PDF y capturas) ya no aparece la ayuda de teclas** al abrir: en claro se
    alcanzaba a ver en la esquina de las capturas.
15. **La lámina de la medida**: la barra del oro total pasó a ser una pista con borde
    (`--barra-total`), clara en claro y azul marino en oscuro. La etiqueta en oro encima
    quedaba en 1.7:1 sobre el gris en claro (y 2.9:1 en oscuro); ahora 5.0:1 y 6.6:1.
16. **La lámina que sale se desvanece en claro** en vez de oscurecerse: el `brightness(.45)`
    del corte volvía gris lodoso las tarjetas blancas del veredicto a mitad de la transición.
