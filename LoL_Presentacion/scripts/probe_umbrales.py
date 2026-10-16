r"""Comprueba que las reglas con umbral que van impresas en la lámina de arquetipos
clasifiquen la partida de ejemplo como A2.

La lámina afirma que la partida del inicio es "ventaja temprana desperdiciada".
Si las reglas publicadas no producen A2, la lámina se contradice a sí misma.
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
s = (ROOT / "data" / "story.js").read_text(encoding="utf-8")
D = json.loads(s[s.index("{"):s.rindex(";")])

g = D["gold"]
adv = [x["adv"] for x in g]
v = [100 * x["adv"] / (x["blue"] + x["red"]) if (x["blue"] + x["red"]) else 0.0 for x in g]

VENT, DECIS, PISO, RACHA, TARDE = 5.0, 10.0, 1500, 3, 15


def ventaja_real(i: int) -> bool:
    return v[i] >= VENT and adv[i] >= PISO


def desventaja_real(i: int) -> bool:
    return v[i] <= -VENT and adv[i] <= -PISO


# A4 · v <= -10 % antes del minuto 15 y nunca se recupera por encima de -5 %
a4 = (any(v[i] <= -DECIS for i in range(min(TARDE + 1, len(v))))
      and all(v[i] <= -VENT for i in range(TARDE, len(v))))

# A2 · ventaja real >= 3 minutos seguidos, alguno en el 15 o despues, y derrota
racha = mejor = 0
tarde = False
for i in range(len(v)):
    if ventaja_real(i):
        racha += 1
        mejor = max(mejor, racha)
        if i >= TARDE:
            tarde = True
    else:
        racha = 0
a2 = mejor >= RACHA and tarde

# A1 · v <= -5 % en el minuto 15 y la ventaja nunca vuelve a ser positiva
a1 = desventaja_real(TARDE) and all(a <= 0 for a in adv[TARDE:])

# A3 · |v| < 5 % hasta la mayor caida de v, y esa caida junto a un objetivo rival
caidas = [(v[i] - v[i - 1], i) for i in range(1, len(v))]
peor_delta, peor_min = min(caidas)
tranquila = all(abs(x) < VENT for x in v[:peor_min])
obj_rival = any((not o["forLoser"]) and abs(o["min"] - peor_min) <= 1
                and o["type"] in ("DRAGON", "BARON_NASHOR", "RIFTHERALD")
                for o in D["objectives"])
a3 = tranquila and obj_rival

orden = [("A4", a4), ("A2", a2), ("A1", a1), ("A3", a3)]
asignado = next((k for k, ok in orden if ok), "sin clasificar")

print("Umbrales publicados en la lamina")
print(f"  ventaja real  : v >= {VENT} %  Y  >= {PISO} de oro")
print(f"  decisiva      : |v| >= {DECIS} %")
print(f"  sostenida     : >= {RACHA} minutos seguidos, alguno en el {TARDE} o despues")
print()
print("Evaluacion de la partida de ejemplo, en orden")
for k, ok in orden:
    print(f"  {k}: {'SI' if ok else 'no'}")
print(f"\n  racha mas larga con ventaja real : {mejor} minutos")
print(f"  mayor caida de v                 : {peor_delta:.2f} puntos, en el minuto {peor_min}")
print(f"\n  -> arquetipo asignado: {asignado}")
print("\nCOINCIDE con lo que dice la lamina" if asignado == "A2"
      else "\nNO COINCIDE -- la lamina afirma A2; hay que corregir umbrales o texto")
