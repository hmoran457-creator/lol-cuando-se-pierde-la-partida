# ¿Cuánto vale esta partida? — probabilidad de ganar

Doble clic en **`probabilidad.html`**: funciona sin internet y es un solo archivo. Escribe el
marcador como lo ves arriba en la pantalla del juego (minuto, asesinatos, torres e inhibidores,
dragones, Atakhan, mejora del barón) y la página dice cuántas de cada 20 partidas así gané, con
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

El modelo elegido sin oro tiene 9 números: el efecto de un asesinato y de una torre baja con el
minuto, y el de un dragón, Atakhan y la mejora del barón es fijo. Con el oro, los asesinatos y las
torres casi dejan de pesar (su valor ya está en el oro), pero los dragones no.

## Cómo se regenera

```
python LoL_Probabilidad/scripts/datos.py        # tabla de entrenamiento (necesita los datos locales)
python LoL_Probabilidad/modelos/base.py         # referencias
python LoL_Probabilidad/modelos/glm.py          # familia logística
python LoL_Probabilidad/modelos/arboles.py      # árboles
python LoL_Probabilidad/modelos/otros.py        # otras familias
python LoL_Probabilidad/modelos/finalistas.py variantes
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
