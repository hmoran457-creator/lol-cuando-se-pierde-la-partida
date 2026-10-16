r"""Turn one real public match into the presentation's data file.

Reads the cached match-v5 match + timeline pair and emits `data/story.js`, which
defines `window.LOL_DATA`. It is emitted as a .js file, NOT .json, on purpose:
Chrome blocks fetch() of local files over file://, so the deck must load its data
through a <script> tag to work offline from a USB stick in a classroom.

Everything written here is derived from the real payload. Nothing is invented.
"""
from __future__ import annotations

import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE.parent / "data"
CACHE = DATA / "riot_examples"

MATCH_ID = "EUW1_6569580003"  # ranked solo (queue 420); loser peaked +8052g at min 22

# Riot convention: participantId 1-5 -> teamId 100 (blue), 6-10 -> teamId 200 (red)
BLUE, RED = 100, 200

MONSTER_ES = {
    "DRAGON": "Dragón",
    "RIFTHERALD": "Heraldo",
    "BARON_NASHOR": "Barón",
    "HORDE": "Larvas del Vacío",
    "ELDER_DRAGON": "Dragón Ancestral",
}
DRAGON_ES = {
    "FIRE_DRAGON": "Infernal",
    "WATER_DRAGON": "Océano",
    "EARTH_DRAGON": "Montaña",
    "AIR_DRAGON": "Nube",
    "HEXTECH_DRAGON": "Hextech",
    "CHEMTECH_DRAGON": "Químtech",
    "ELDER_DRAGON": "Ancestral",
}
BUILDING_ES = {
    "OUTER_TURRET": "Torre exterior",
    "INNER_TURRET": "Torre interior",
    "BASE_TURRET": "Torre de inhibidor",
    "NEXUS_TURRET": "Torre del Nexo",
    "INHIBITOR_BUILDING": "Inhibidor",
}
LANE_ES = {"TOP_LANE": "superior", "MID_LANE": "central", "BOT_LANE": "inferior"}


def load(kind: str) -> dict:
    return json.loads((CACHE / f"{kind}_{MATCH_ID}.json").read_text(encoding="utf-8"))


def main() -> None:
    match, tl = load("getMatch"), load("getTimeline")
    minfo, tinfo = match["info"], tl["info"]
    frames = tinfo["frames"]

    winner = next(t["teamId"] for t in minfo["teams"] if t["win"])
    loser = RED if winner == BLUE else BLUE

    # ---- per-minute gold, from the perspective of the team that LOST -------------
    gold = []
    for i, f in enumerate(frames):
        pf = f["participantFrames"]
        b = sum(pf[str(p)]["totalGold"] for p in range(1, 6) if str(p) in pf)
        r = sum(pf[str(p)]["totalGold"] for p in range(6, 11) if str(p) in pf)
        adv = (b - r) if loser == BLUE else (r - b)
        gold.append({"min": i, "adv": adv, "blue": b, "red": r})

    adv_series = [g["adv"] for g in gold]
    peak = max(adv_series)
    peak_min = adv_series.index(peak)

    # biggest single-minute swing AGAINST the losing team, after its peak
    swings = [
        {"min": i, "delta": adv_series[i] - adv_series[i - 1]}
        for i in range(1, len(adv_series))
    ]
    worst = min(swings, key=lambda s: s["delta"])

    # last minute at which the losing team was still ahead
    last_ahead = max((i for i, a in enumerate(adv_series) if a > 0), default=0)

    # ---- events -------------------------------------------------------------------
    pid_team = {p["participantId"]: p["teamId"] for p in minfo["participants"]}
    pid_champ = {p["participantId"]: p["championName"] for p in minfo["participants"]}

    objectives, kills, buildings = [], [], []
    for f in frames:
        for e in f.get("events", []):
            t = e["type"]
            minute = round(e["timestamp"] / 60000, 2)
            if t == "ELITE_MONSTER_KILL":
                mt = e.get("monsterType", "")
                sub = e.get("monsterSubType", "")
                label = MONSTER_ES.get(mt, mt)
                if sub:
                    label += f" ({DRAGON_ES.get(sub, sub)})"
                objectives.append(
                    {
                        "min": minute,
                        "type": mt,
                        "label": label,
                        "team": e.get("killerTeamId"),
                        "forLoser": e.get("killerTeamId") == loser,
                    }
                )
            elif t == "BUILDING_KILL":
                bt = e.get("towerType") or e.get("buildingType", "")
                objectives.append(
                    {
                        "min": minute,
                        "type": "BUILDING",
                        "label": f"{BUILDING_ES.get(bt, bt)} {LANE_ES.get(e.get('laneType',''), '')}".strip(),
                        # teamId on BUILDING_KILL is the team that OWNED the building
                        "team": BLUE if e.get("teamId") == RED else RED,
                        "forLoser": e.get("teamId") != loser,
                    }
                )
                buildings.append({"min": minute, "lostBy": e.get("teamId")})
            elif t == "CHAMPION_KILL":
                # killerId 0 = ejecutado por torre o subditos: no hay equipo al que
                # atribuirlo. Se emite forLoser=None para que el mapa lo pinte
                # neutro en vez de contarlo silenciosamente como del rival.
                k = e.get("killerId", 0)
                team = pid_team.get(k)
                kills.append(
                    {
                        "min": minute,
                        "killerTeam": team,
                        "forLoser": None if team is None else team == loser,
                        "champ": pid_champ.get(k, ""),
                        "x": e.get("position", {}).get("x"),
                        "y": e.get("position", {}).get("y"),
                        "bounty": e.get("bounty", 0),
                    }
                )

    # ---- scoreboard: "la explicación fácil" ---------------------------------------
    roster = []
    for p in sorted(minfo["participants"], key=lambda p: p["participantId"]):
        roster.append(
            {
                "champ": p["championName"],
                "team": p["teamId"],
                "pos": p.get("teamPosition") or "",
                "k": p["kills"],
                "d": p["deaths"],
                "a": p["assists"],
                "cs": p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0),
                "gold": p.get("goldEarned", 0),
                "dmg": p.get("totalDamageDealtToChampions", 0),
                "vision": p.get("visionScore", 0),
                "win": p.get("win", False),
            }
        )

    def team_kda(team: int) -> str:
        rs = [r for r in roster if r["team"] == team]
        return f"{sum(r['k'] for r in rs)}/{sum(r['d'] for r in rs)}/{sum(r['a'] for r in rs)}"

    payload = {
        "matchId": MATCH_ID,
        "patch": minfo.get("gameVersion"),
        "queueId": minfo.get("queueId"),
        "durationMin": round(minfo.get("gameDuration", 0) / 60, 1),
        "frameIntervalMs": tinfo.get("frameInterval"),
        "frameCount": len(frames),
        "winner": winner,
        "loser": loser,
        "gold": gold,
        "peak": {"min": peak_min, "adv": peak},
        "worstSwing": worst,
        "lastMinuteAhead": last_ahead,
        "objectives": objectives,
        "kills": kills,
        "roster": roster,
        "kdaLoser": team_kda(loser),
        "kdaWinner": team_kda(winner),
        "eventTypes": sorted(
            {e["type"] for f in frames for e in f.get("events", [])}
        ),
        "champions": sorted({r["champ"] for r in roster}),
    }

    DATA.mkdir(parents=True, exist_ok=True)
    out = DATA / "story.js"
    out.write_text(
        "/* Generado por scripts/build_story.py a partir de una partida publica real\n"
        "   (match-v5 examples, MingweiSamuel/riotapi-schema). Ningun valor es inventado. */\n"
        "window.LOL_DATA = " + json.dumps(payload, ensure_ascii=False, indent=1) + ";\n",
        encoding="utf-8",
    )

    print(f"match {MATCH_ID}  patch {payload['patch']}  queue {payload['queueId']}  "
          f"{payload['durationMin']} min  {payload['frameCount']} frames")
    print(f"perdedor = equipo {loser}; pico +{peak}g en el minuto {peak_min}")
    print(f"ultimo minuto por delante: {last_ahead}")
    print(f"peor caida en un minuto: {worst['delta']}g en el minuto {worst['min']}")
    print(f"KDA perdedor {payload['kdaLoser']}  |  KDA ganador {payload['kdaWinner']}")
    print(f"objetivos: {len(objectives)}  asesinatos: {len(kills)}")
    print("campeones:", ", ".join(payload["champions"]))
    print(f"\nwrote {out}  ({out.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
