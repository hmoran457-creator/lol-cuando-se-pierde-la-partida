# Validación del proyecto — "¿En qué minuto se perdió la partida?"

Fecha: 2026-09-04. Este documento no es para la presentación: es la base técnica para
construir el proyecto después. Todo lo de aquí se verificó contra la API, la documentación
de Riot o payloads reales — no contra recuerdos.

**Veredicto: adelante, con condiciones.** El dato existe y alcanza. Lo que no está resuelto
es el tamaño de la muestra, la definición del "minuto de quiebre" y el diseño estadístico.

---

## 1. Lo que hay que medir ANTES de diseñar el análisis

Estas tres son bloqueantes en el sentido literal: si salen mal, cambia el alcance del proyecto.

**1.1 Contar la muestra real.** Pedir
`/lol/match/v5/matches/by-puuid/{puuid}/ids` con `queue=420` paginando hasta que regrese vacío.
Anotar el total y el `gameCreation` más viejo. Después pedir el *timeline* de la partida **más
vieja** y anotar el código de estado.

Hay dos techos y ninguno avisa:

| Techo | Valor | Cómo se manifiesta |
|---|---|---|
| Retención del *timeline* | ~1 año | La lista y el registro de partida responden 200; el *timeline* da 404 |
| Retención de la partida | ~2 años | — |
| Tope de la lista de IDs | ~1,000 entradas | Los ARAM, personalizadas y eventos ocupan lugar sin avisar |

Un caso real reportado en 2026 llegó solo a ~500 partidas alcanzables. Si resultan menos de
~150 clasificatorias con *timeline*, hay que bajar el número de arquetipos antes de escribir nada.

**1.2 Fijar por escrito UNA definición de "el minuto que voltea la partida"**, con su umbral
numérico, antes de ver la distribución. Esto no es formalismo: sobre **una sola partida real**,
tres reglas defendibles dieron **tres minutos distintos** (cambio de signo, ventaja máxima, y
mayor caída en un minuto). Calcular una segunda definición en paralelo y reportar el **porcentaje
de desacuerdo entre ambas** — ese número es, por sí mismo, uno de los resultados más honestos
que puede dar el proyecto.

**1.3 Guardar todo el JSON crudo en disco al primer jalón**, con reanudación y punto de control
por partida. Tres razones convergen: la llave de desarrollo se desactiva cada 24 horas, la
retención va borrando los *timelines* viejos mientras trabajas, y tú sigues jugando — así que
volver a descargar **no da la misma muestra**. Sin el corpus guardado el estudio no es repetible.

---

## 2. Trampas medidas en los datos

Cada una de éstas invierte o distorsiona un resultado **sin fallar**, que es lo que las hace caras.

**El `teamId` de una estructura nombra al equipo que la PERDIÓ.** En `BUILDING_KILL` y
`TURRET_PLATE_DESTROYED`, `teamId` no es quien la destruyó. Medido: en 16 de 16 eventos
atribuibles, `teamId` **nunca** coincidió con el equipo del asesino. Atribuir torres y placas por
ese campo invierte cada gráfica de "perdí desde línea" dejándola con aspecto correcto.
Atribuir siempre por el equipo de `killerId`, y cuadrar los conteos contra
`info.teams[].objectives[].tower.kills` como verificación gratuita.

**Indexar los cuadros por posición en la lista, nunca por `timestamp // 60000`.** Las marcas de
tiempo se desvían hasta +582 ms y el último cuadro es el fin de la partida, no un minuto exacto.
La división mete los cuadros 28 y 29 en la misma casilla: 29 casillas para 30 cuadros, y la que
se pierde es justo el minuto donde se decidió.

**`gameDuration` cambia de unidad.** Es en milisegundos si `gameEndTimestamp` **no** viene en la
respuesta, y en segundos si **sí** viene (cambió en el parche 11.20). Equivocarse escala cada
normalización por minuto por 1000, y el error es invisible.

**No filtrar por `endOfGameResult == "GameComplete"`.** Hay un bug abierto de Riot desde
2024-06-12: devuelve `Abort_Unexpected` en partidas normales, y dice que afecta especialmente a
la cola 420 — justo la de este proyecto. Ese filtro borra partidas buenas. El orden correcto es:
(1) descartar partidas con `participants` vacío, (2) usar `gameEndedInEarlySurrender` por
participante, (3) descartar lo que dure menos de ~5 minutos.

**Pedir `queue=420` explícitamente.** `type=ranked` incluye también la cola flexible (440), que
permite grupos de hasta cinco y tiene otra dispersión de nivel. La 420 es Solo/Dúo: admite
grupos de dos.

**La diferencia de oro no existe como campo.** Se calcula sumando `totalGold` de los
participantes 1–5 menos 6–10, cuadro por cuadro. Y el *timeline* **no trae el equipo** de cada
jugador — `ParticipantTimeLineDto` es solo `{participantId, puuid}` — así que el mapeo hay que
cruzarlo con el registro de partida.

**Enumerar el vocabulario de eventos desde tus propias partidas.** Riot declara `type` como texto
libre, sin catálogo, y tiene un bug de documentación abierto reconociendo ~30 campos sin
documentar. Los eventos de Atakhan y larvas del vacío existen en toda tu ventana (parche 15.1,
enero 2025) y no aparecen en la documentación de objetivos.

**Leer los campos opcionales con `.get()`.** `assistingParticipantIds` falta en 11 de 49
asesinatos de una partida — y esos 11 son justamente los *solo kills*, los más informativos para
la fase de línea. `monsterSubType` solo viene en dragones.

**No construir "participación en objetivos" con `assistingParticipantIds` de
`ELITE_MONSTER_KILL`.** Esa lista contiene participantes **enemigos** y puede repetir ids
(medido: un Heraldo con `killerTeamId` 200 y asistencias `[2,4,9,10,9]`). Usar solo `killerTeamId`.

---

## 3. Diseño estadístico

**No son seis pruebas de hipótesis.** Seis pruebas al 5 % dan 26.5 % de probabilidad de al menos
un falso positivo, y los grados de libertad reales son muchos más que seis (cada umbral libre
cuenta). El encuadre que sí aguanta: **una taxonomía descriptiva pre-registrada**, con intervalos,
que dice qué patrones se resuelven con esta n y cuáles no.

**La aritmética que conviene decir antes de que te la pregunten:** con ~50–100 derrotas repartidas
en cinco arquetipos quedan 10–20 partidas por celda. Una celda de 20/100 trae un intervalo del
95 % de [0.12, 0.28]; dos arquetipos al 30 % y 20 % difieren 0.10 ± 0.137 — el intervalo incluye
el cero, así que **no se pueden ni ordenar por frecuencia**. Resolver 0.30 de 0.20 al 80 % de
potencia pide ~385 derrotas, o sea ~770 partidas, que ya roza el tope de la lista de IDs.

Usar intervalos de **Wilson**, no Wald: a n=25 y p=0.20, Wald da [0.043, 0.357] y Wilson
[0.089, 0.391] — el límite inferior se equivoca por un factor de dos.

**Las victorias entran como grupo de control.** Toda partida tiene su mayor cambio de oro,
también las ganadas. Sin la comparación, un histograma de "minuto del mayor cambio" describe
cómo son las partidas de League, no cómo pierdes tú. No cuesta ni una llamada extra: ya vienen
en la misma descarga.

**Para H6, partir la muestra por fecha:** ajustar el punto de quiebre en la primera mitad y
reportarlo en la segunda. Si se mueve más de un par de minutos, es ruido y hay que decirlo.

---

## 4. Preguntas difíciles y la respuesta honesta

| Pregunta | Respuesta |
|---|---|
| Toda partida tiene su mayor cambio de oro, incluidas las ganadas. ¿Cómo sabes que esto describe cómo pierdes tú? | No lo sé, salvo que las victorias estén en el conjunto. Por eso van como grupo de control. |
| Eres uno de diez jugadores. ¿Cuál es *tu* aporte? | No es recuperable, y hay que decirlo de frente. El resultado es de equipo; `win` existe por participante pero es idéntico para los cinco. |
| ¿Cómo elegiste la partida de la primera diapositiva? | Solo sobrevive una respuesta: se eligió **al final**, es la mediana de su arquetipo, y aquí está el punto que muestra dónde cae en la distribución. |
| ¿Los arquetipos los ajustaste a los datos o los encontraste? | Reglas y umbrales escritos antes, mutuamente excluyentes, con orden de desempate. Un conjunto que clasifica el 100 % sin residuo es la señal de que se ajustaron después. |
| ¿El barón *causó* el desplome? | No se puede saber. La pelea ocurre antes que el objetivo: el objetivo marca el momento, no lo causa. |
| ¿De dónde sacaste que existe `monsterType`? | De medirlo. Riot documenta tres campos del evento y declara `type` sin catálogo. Decirlo primero es una fortaleza. |
| Riot ya hace esto en Worlds. ¿Qué aportas? | Sí lo hace, desde 2023 y por segundo. Corre sobre un canal profesional al que nadie del público accede. La API pública da un cuadro por minuto y solo al terminar. |
| ¿Cuántos parches abarcan tus partidas? | ~25 (15.17 a 16.17), ~8 partidas por parche, más el reinicio de rango del 8 de enero de 2026. El efecto de parche se reconoce, no se controla. |
| ¿Y Oracle's Elixir? | Sería otro proyecto: solo toma fotos a los minutos 10, 15, 20 y 25, así que no puede encontrar un punto de quiebre. Y es juego profesional. |

---

## 5. Privacidad y política

- Cada partida trae `riotIdGameName`, `riotIdTagline` y `summonerName` de los **diez**
  participantes. La política de Riot prohíbe desanonimizar jugadores. Hay que borrarlos o
  aplicarles hash **antes** de que lleguen a un repositorio, un CSV o una diapositiva.
- La llave de API nunca se sube al repositorio.
- Sin logos ni marcas de Riot en las diapositivas. El aviso de la sección 6 del *Legal Jibber
  Jabber* sí va (ya está en la última diapositiva).
- Los recursos de imagen se descargan localmente con la versión fijada (Data Dragon 16.17.1) y se
  referencian con rutas relativas — nunca desde el CDN en vivo durante la exposición.
- Sin llamadas a la API durante la presentación: la llave de desarrollo se desactiva cada 24 horas.

---

## 6. Lo que quedó sin verificar

No se pudo confirmar y conviene medirlo:

- Si realmente tienes 100–200 partidas de cola 420 con *timeline* recuperable. **Es la medición
  go / no-go** y necesita tu llave.
- Tu tasa de victorias real. Se asumió ~50 %; si es 45 % o 55 %, cambia cada conteo de derrotas.
- Tu profundidad alcanzable en la lista de IDs.
- Si la retención de 1 año del *timeline* sigue vigente en 2026 — descansa en una nota de Riot de
  2019 más repetición de la comunidad. Trata el piso de ~septiembre 2025 como ±1 mes.
- El valor exacto de `monsterType` para Atakhan. No hardcodearlo sin verlo en tu propio JSON.
- Si `OBJECTIVE_BOUNTY_FINISH` existe siquiera; solo se verificó `OBJECTIVE_BOUNTY_PRESTART`.
- El límite de peticiones exacto de una llave de **desarrollo**. Riot publica el de la personal
  (20 por segundo, 100 cada 2 minutos) y dice que no revela los detalles de su *rate limiting*.

---

## Anexo: la partida de ejemplo

`EUW1_6569580003` — pública, sin llave, del repositorio de ejemplos `MingweiSamuel/riotapi-schema`.
Parche 13.16, cola 420, 28.6 min, 30 cuadros. **No es una partida mía** y la presentación lo dice.

El equipo que perdió **nunca estuvo abajo en oro**: pico de +8,052 en el minuto 22 y todavía
+1,034 cuando cayó su Nexo. Minuto 21:54 tiran inhibidor y ambas torres del Nexo; 23:03 el rival
mata al Barón; después del minuto 22 no consiguen un solo asesinato contra nueve recibidos.

Se usa para **plantear la pregunta**, nunca como resultado. Al terminar el análisis hay que
sustituirla por una partida propia elegida como la mediana de su arquetipo.
