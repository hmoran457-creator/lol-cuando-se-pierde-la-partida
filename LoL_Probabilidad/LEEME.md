# ¿Cuánto vale esta partida? — probabilidad de ganar

Doble clic en **`probabilidad.html`**: funciona sin internet y es un solo archivo. Escribe el
marcador como lo ves en el juego (minuto, asesinatos, torres e inhibidores, dragones y la suma de
niveles de cada equipo, que se ve con Tab) y la página dice cuántas de cada 20 partidas así gané, con
el rango del modelo, qué la movería y cómo cambiaría si el marcador se quedara igual. Si conoces
el oro de cada equipo (en una repetición o como espectador), agrégalo y la estimación mejora.

El modelo aprendió de **mis** 1,195 partidas: describe mis partidas, no las de cualquier jugador.

## Cómo se eligió el modelo

Una tabla con una fila por partida y minuto (35,886 filas), y un banco de pruebas común
(`scripts/evaluar.py`) con reglas fijas antes de probar nada:

- validación cruzada de 5 pliegues **por partida**: los minutos de una partida nunca quedan
  repartidos entre entrenamiento y prueba;
- la medida es la pérdida logarítmica (también Brier, AUC y calibración);
- las partidas de mayo de 2026 en adelante (232) se apartaron como **prueba temporal** y se
  usaron una sola vez, al final;
- regla de elección: el modelo más simple dentro del margen de error del mejor.

Tres familias se exploraron en paralelo, cada una en su script de `modelos/`:

| Familia | Script | Mejor pérdida, sin oro | Con oro |
|---|---|---:|---:|
| Referencias (proporción de victorias; logística simple) | `base.py` | 0.689; 0.554 | 0.545 (solo oro) |
| Logística con efectos que cambian con el minuto | `glm.py` | 0.549 | 0.531 |
| Árboles combinados (*gradient boosting*, bosques) | `arboles.py` | 0.554 | 0.537 |
| Otras: redes neuronales, un modelo por minuto, vecinos, combinaciones | `otros.py` | 0.549 | 0.531 |

Ganó la logística: los árboles perdieron por 0.005 con intervalos que excluyen el cero, y la red
neuronal empata con unos 400 parámetros contra 9. `finalistas.py` quitó tres términos que
confundían en la página sin costar precisión (el número de barones cuya mejora ya terminó tenía
coeficiente negativo, y el heraldo y las larvas no aportaban) y midió a los finalistas en la
prueba temporal. Ahí la pérdida subió para todos (≈ 0.58 sin oro, ≈ 0.56 con oro) y las
diferencias entre finalistas, de menos de 0.003, no son significativas con 232 partidas; la
calibración también empeoró (error de 4 puntos contra 1 en la validación).

**Una corrección después de la prueba.** Una revisión independiente encontró que la tabla
contaba las ejecuciones (muertes ante una torre o los súbditos) como asesinatos del rival, y el
marcador del juego no las cuenta. Se corrigió `datos.py` y se volvió a correr todo, incluida la
prueba temporal, que así se usó dos veces. La elección no cambió y las cifras se movieron en el
cuarto decimal.

## Segunda ronda: el nivel

Una curva de aprendizaje mostró que más partidas casi no ayudan (de 385 a 770 partidas de
entrenamiento la pérdida baja 0.002): el límite era la información de las entradas, no el
algoritmo ni la cantidad de datos. Se probó entonces la suma de niveles de cada equipo, que se ve
en la partida con Tab, con la regla fijada antes: entra solo si mejora al elegido con un intervalo
que excluye el cero (`finalistas.py nivel`).

| Modo | Sin niveles | Con niveles | Diferencia [IC 95 %] |
|---|---:|---:|---|
| Marcador | 0.548 | **0.536** | −0.013 [−0.019, −0.007] |
| Marcador + oro | 0.531 | **0.527** | −0.004 [−0.007, −0.0004] |

Fue la mejora más grande de todo el proceso, mayor que cualquier cambio de algoritmo: el marcador
con niveles ya predice mejor que el oro solo (0.545). La experiencia, que no se ve en la partida,
no agrega nada sobre los niveles. Con los niveles, Atakhan y la mejora del barón quedaron con
coeficientes negativos y sin significancia (su valor ya está en niveles y torres), así que se
quitaron con la misma regla de legibilidad: la versión sin ellos empata con la completa. En la
prueba temporal (que ya se había usado antes, así que es una medición más, no una prueba ciega)
el modelo sin oro mejoró de 0.581 a 0.574 y el de oro quedó igual (0.562 contra 0.561).

El modelo sin oro tiene ahora 8 números: el efecto de un asesinato y de una torre baja con el
minuto, y el de un dragón y un nivel es fijo. Los asesinatos pesan poco porque su valor ya se nota
en los niveles; con el oro, los asesinatos y las torres casi dejan de pesar, pero los dragones no:
sus mejoras no se ven ni en el oro ni en los niveles.

## Tercera ronda: el detalle de los objetivos (no entró)

La tabla anonimizada no distingue torres de inhibidores ni el dragón ancestral; el JSON crudo, que
solo existe en local, sí. Como la llave de los seudónimos fue efímera, `datos.py` enlaza cada línea
de tiempo cruda con su partida por la huella de sus asesinatos (los milisegundos exactos); el
enlace vive solo en memoria y la salida no guarda ningún matchId. Las 1,195 partidas se enlazaron,
y torres + inhibidores del crudo coinciden con las estructuras de la tabla en el 100 % de las filas.

Con la misma regla (`finalistas.py objetivos`), ninguna variante mejoró al modelo con niveles:
torres e inhibidores por separado, inhibidores caídos ahora, torres del nexo, dragones elementales
con alma y ancestral, la mejora del ancestral, o todo junto. Todas quedaron a ±0.0005 con
intervalos que incluyen el cero, y tampoco hubo ganancia al mirar aparte el final de las partidas
ni las situaciones con alma, ancestral o un inhibidor caído (revisión hecha después, fuera de la
regla). Algunos coeficientes son grandes (el alma, la mejora del ancestral), pero esas situaciones
son raras (el ancestral aparece en el 8 % de las partidas) y, cuando ocurren, los niveles, las
torres y los asesinatos ya dicen quién va ganando. La herramienta no cambió.

## Cómo se regenera

```
python LoL_Probabilidad/scripts/datos.py        # tabla de entrenamiento (necesita los datos locales y el JSON crudo)
python LoL_Probabilidad/modelos/base.py         # referencias
python LoL_Probabilidad/modelos/glm.py          # familia logística
python LoL_Probabilidad/modelos/arboles.py      # árboles
python LoL_Probabilidad/modelos/otros.py        # otras familias
python LoL_Probabilidad/modelos/finalistas.py variantes
python LoL_Probabilidad/modelos/finalistas.py nivel
python LoL_Probabilidad/modelos/finalistas.py objetivos
python LoL_Probabilidad/modelos/finalistas.py prueba
python LoL_Probabilidad/scripts/exportar.py     # herramienta/modelo.json
python LoL_Probabilidad/scripts/construir.py    # probabilidad.html
python LoL_Probabilidad/scripts/verificar.py    # revisión en Chromium
```

Solo los dos últimos corren desde el repositorio público: los anteriores leen las tablas por
participante, que no se publican. `verificar.py` comprueba que la página calcula lo mismo que
Python (diferencia máxima 2e-16 en 1,000 cálculos), que nada a favor baja la probabilidad, que no
hay errores de consola y que la página cabe en un teléfono.

**Se edita `herramienta/`, nunca `probabilidad.html`**, que se sobrescribe.

## Archivos

- `probabilidad.html` — la herramienta.
- `herramienta/` — plantilla, motor del modelo (`motor.js`), interfaz (`interfaz.js`) y el modelo
  exportado (`modelo.json`: coeficientes, 200 remuestreos y agregados; ninguna fila de partida).
- `scripts/` — tabla de entrenamiento, banco de pruebas, exportación, construcción y revisión.
- `modelos/` — los experimentos de cada familia y la elección final.
- `resultados/` — métricas de cada modelo probado (`prueba_temporal.json`: la prueba final).
- `datos/` — tabla de entrenamiento y predicciones fuera de muestra; **no se publica**
  (`.gitignore`).
