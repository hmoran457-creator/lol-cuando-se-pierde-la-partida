r"""Download real public match-v5 example payloads and probe them.

Source: MingweiSamuel/riotapi-schema `examples/` - real Riot API responses committed
as documentation fixtures. Keyless, public. Used ONLY to (a) confirm the real field
names for the "vista general de las fuentes" slides and (b) drive the gold-difference
chart with a genuine game rather than an invented one.

Nothing here touches Hector's own API key.
"""
from __future__ import annotations

import json
import pathlib
import urllib.request

RAW = "https://raw.githubusercontent.com/MingweiSamuel/riotapi-schema/master/examples"
HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE.parent / "data"
CACHE = DATA / "riot_examples"
CACHE.mkdir(parents=True, exist_ok=True)

MATCH_IDS = [
    "EUW1_7261321891",
    "EUW1_6869252626",
    "EUW1_6852390800",
    "EUW1_6511808246",
    "EUW1_6349186754",
    "EUW1_6569580003",
    "EUW1_5765650307",
]


def grab(kind: str, match_id: str) -> dict | None:
    """kind is 'getMatch' or 'getTimeline'. Cached on disk."""
    dest = CACHE / f"{kind}_{match_id}.json"
    if not dest.exists():
        url = f"{RAW}/match-v5.{kind}/{match_id}.json"
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                dest.write_bytes(resp.read())
        except Exception as exc:  # noqa: BLE001 - probe script, report and continue
            print(f"  !! {kind} {match_id}: {exc}")
            return None
    try:
        return json.loads(dest.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"  !! parse {kind} {match_id}: {exc}")
        return None


def team_gold_series(timeline: dict) -> tuple[list[int], list[int]]:
    """Per-frame total gold for team 100 and team 200.

    participantId 1-5 are team 100, 6-10 are team 200 (Riot's convention).
    """
    blue, red = [], []
    for frame in timeline["info"]["frames"]:
        pf = frame["participantFrames"]
        b = sum(pf[str(i)]["totalGold"] for i in range(1, 6) if str(i) in pf)
        r = sum(pf[str(i)]["totalGold"] for i in range(6, 11) if str(i) in pf)
        blue.append(b)
        red.append(r)
    return blue, red


def probe(match_id: str) -> dict | None:
    m = grab("getMatch", match_id)
    t = grab("getTimeline", match_id)
    if not m or not t:
        return None
    info = m["info"]
    tinfo = t["info"]
    frames = tinfo["frames"]
    blue, red = team_gold_series(t)
    diff = [b - r for b, r in zip(blue, red)]

    winner = next((tm["teamId"] for tm in info["teams"] if tm["win"]), None)
    # Peak lead held by the team that eventually LOST
    loser = 200 if winner == 100 else 100
    loser_lead = [d if loser == 100 else -d for d in diff]
    peak_lead = max(loser_lead) if loser_lead else 0
    peak_minute = loser_lead.index(peak_lead) if loser_lead else 0

    ev_types: dict[str, int] = {}
    for f in frames:
        for e in f.get("events", []):
            ev_types[e["type"]] = ev_types.get(e["type"], 0) + 1

    return {
        "matchId": match_id,
        "gameVersion": info.get("gameVersion"),
        "queueId": info.get("queueId"),
        "durationMin": round(info.get("gameDuration", 0) / 60, 1),
        "frames": len(frames),
        "frameIntervalMs": tinfo.get("frameInterval"),
        "winner": winner,
        "loserPeakLead": peak_lead,
        "loserPeakLeadMinute": peak_minute,
        "finalDiff": diff[-1] if diff else 0,
        "eventTypes": ev_types,
        "timelineBytes": (CACHE / f"getTimeline_{match_id}.json").stat().st_size,
        "matchBytes": (CACHE / f"getMatch_{match_id}.json").stat().st_size,
    }


def main() -> None:
    rows = []
    for mid in MATCH_IDS:
        print(f"probing {mid} ...")
        r = probe(mid)
        if r:
            rows.append(r)

    print("\n" + "=" * 96)
    print(f"{'matchId':<20}{'patch':<12}{'q':<7}{'min':<7}{'frames':<8}{'win':<6}{'loserPeakLead':<15}{'@min':<6}")
    print("-" * 96)
    for r in rows:
        print(
            f"{r['matchId']:<20}{str(r['gameVersion'])[:10]:<12}{str(r['queueId']):<7}"
            f"{r['durationMin']:<7}{r['frames']:<8}{str(r['winner']):<6}"
            f"{r['loserPeakLead']:<15}{r['loserPeakLeadMinute']:<6}"
        )

    print("\nframe intervals:", {r["matchId"]: r["frameIntervalMs"] for r in rows})
    print("\ntimeline sizes (KB):", {r["matchId"]: round(r["timelineBytes"] / 1024) for r in rows})
    print("match sizes (KB):   ", {r["matchId"]: round(r["matchBytes"] / 1024) for r in rows})

    all_ev: dict[str, int] = {}
    for r in rows:
        for k, v in r["eventTypes"].items():
            all_ev[k] = all_ev.get(k, 0) + v
    print("\nevent type vocabulary observed across all games:")
    for k, v in sorted(all_ev.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<32} {v}")

    (DATA / "probe_summary.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )
    print(f"\nwrote {DATA / 'probe_summary.json'}")


if __name__ == "__main__":
    main()
