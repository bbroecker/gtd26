"""
German Throwdown 2026 — Leaderboard Data Fetcher
Writes data/data.json consumed by index.html.

Usage:
    python3 fetch.py

Token:
    Set CIRCLE21_TOKEN env var, or replace the placeholder below.
    Token expires: ~2027-05-04 (exp field in JWT).
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TOKEN = os.environ.get(
    "CIRCLE21_TOKEN",
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5ODlmMDRjZC1iNWRhLTQ2ZTUtOTg0Yy1kYjU3YmIxOWNlZjIiLCJqdGkiOiJmZDE1NzM3MDM2YTczYWIyZTY4MjAyNmQ4YmJiMzdlNDVhNjY0YjlkZmM5YzI5YmFjZWFlMGIzNzZhYTdjZjM0ODZhZGM2ODhlYThmZmMyNiIsImlhdCI6MTc3Mjk4NjU5MC44NzI1MiwibmJmIjoxNzcyOTg2NTkwLjg3MjUyMywiZXhwIjoxODA0NTIyNTkwLjg2NjUzNywic3ViIjoiMzA1Y2M1ZGItMGNmMS00MzFiLThjYzktYjg5MWFiOWQwMzNmIiwic2NvcGVzIjpbXX0.qTGPTD2SmVhihQgeX_yYEjNXU8wuyXJOrm9OliEbWNUf48LoY1xRONGjtIQPbdVdk-7Ye2kpvyNOfdrT7N8dKCWPIht9wLXafasFGF4qRrdD-EPxPuR6Ygxvu-tmlrDEbTj9mF94bucWuil83cXfAVAYrTyGITa-mK26bPIBHGC-Wbk0VJzDGL9a4oiQEo_RDHyh3MOrkA_iralEStNYfdZ-jF8nJVsPkeWVcPYnyZK1Ar0NuIFD0yIEhGbaJKbZu8RoJDgFwAk2aRyrAhVSc1cRg6tF49VAISJAk-KGJr4Bs7Yw7rop89dOVdzh-ZeyqLvdMR4tpQzpt8t7Y6KSXl9Rmq9OYuOThfavvqir5CqCQmYWixy2yrXHwcqhBcVk0SvajUmRuKrDyqPrcv5xWFQjcDD_rYFPj355FQoZDmbqyhsp2P7NRMlXdCjWtwInnOQ2q1zGKnaXATkD1yHMD_C3bTqlxLLQy2odTQmX9U6Ggp8B6ZEvyL2GICEL7ZFT427M3O0WJhDSPRpR2w9K1bIyoRGzPy2t_aOfLwqoD3x-PxljIfB1O6hxbf1kSz3oeWjVvBkTm48V48v2fwgfubSiclm8hLn3wHErSj_u6LY8gQR42DSKGDHpSZVw8W0TNQ8RGTcwOs5WDnlh0FG5WAWc1CWXBvTVlSkXF3IIb6M",
)
COMPETITION_ID = "cd3809c9-4aae-43bd-9d78-53c3b19b97c9"
API_BASE = "https://api.circle21.events/api"
TOP_N = 20
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "data", "data.json")

HDR = {
    "accept": "application/json",
    "authorization": f"Bearer {TOKEN}",
}


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------
def get(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HDR)
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code} for {url}")
            if e.code == 401:
                print("  ❌ Unauthorized — token may be expired. Update CIRCLE21_TOKEN.")
                sys.exit(1)
            if attempt == retries - 1:
                raise
            time.sleep(2)
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(f"  Retry {attempt + 1}: {e}")
            time.sleep(2)


# ---------------------------------------------------------------------------
# Main fetch logic
# ---------------------------------------------------------------------------
def fetch_all():
    print("🏆 German Throwdown 2026 — Fetching leaderboard data\n")

    # Step 1: Fetch competition metadata + all divisions
    print("📋 Fetching competition divisions...")
    comp = get(f"{API_BASE}/competition/{COMPETITION_ID}")
    comp_name = comp.get("name", "German Throwdown 2026")

    all_divisions = sorted(
        comp.get("competition_division", []),
        key=lambda d: d.get("order", 99),
    )
    # Only visible divisions
    divisions = [d for d in all_divisions if d.get("visibility")]
    print(f"   Found {len(divisions)} visible divisions (of {len(all_divisions)} total)\n")

    output = {
        "meta": {
            "competition_name": comp_name,
            "competition_id": COMPETITION_ID,
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updated_at_readable": datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
        },
        "divisions": [],
    }

    # Step 2: Fetch leaderboard per division
    for div in divisions:
        div_id = div["id"]
        div_name = div["name"]
        is_individual = bool(div.get("individual"))
        print(f"⏳ {div_name}...")

        try:
            lb = get(
                f"{API_BASE}/leaderboard?competition_id={COMPETITION_ID}&division_id={div_id}"
            )
        except Exception as e:
            print(f"   ⚠️  Skipped ({e})")
            continue

        # For team divisions the API returns "teams" instead of "athletes"
        participants = lb.get("teams", lb.get("athletes", []))
        # top-level teams may be a dict (id→obj) or a list; normalise to list
        if isinstance(participants, dict):
            participants = list(participants.values())
        athletes_map = {a["id"]: a for a in participants}

        # Collect athletes/teams who have submitted at least one result
        def participant_id(r):
            return r.get("team_id") or r.get("athlete_id")

        athletes_with_results = set()
        for wod_entry in lb.get("wods", []):
            for workout_entry in wod_entry.get("workouts", []):
                for r in workout_entry.get("results", []):
                    pid = participant_id(r)
                    if pid:
                        athletes_with_results.add(pid)

        # ---- Per-WOD data ----
        wod_names = []
        wod_units = {}  # wname -> display unit string (e.g. "Reps", "Kilograms")
        per_wod = {}

        for wod_entry in lb.get("wods", []):
            for workout_entry in wod_entry.get("workouts", []):
                wname = workout_entry.get("workout", {}).get("name", "?")
                wod_names.append(wname)
                wod_units[wname] = workout_entry.get("workout", {}).get("units_of_measure") or ""

                results = workout_entry.get("results", [])
                first_field = workout_entry.get("workout", {}).get("first_field", "time")
                is_reps_based = first_field == "how_many"

                # For team divisions positions live in workout["teams"], not ["athletes"]
                wk_participants = workout_entry.get("teams", workout_entry.get("athletes", []))
                if isinstance(wk_participants, dict):
                    wk_participants = list(wk_participants.values())
                # Position map: athlete_id -> position (Circle21 pre-computed)
                pos_map = {
                    a["id"]: a.get("position")
                    for a in wk_participants
                    if a.get("position") is not None
                }
                # Scores: participant_id -> {time, reps, tiebreak}
                # For reps-based WODs, `time` in results is the cap (same for everyone)
                # so we null it out to avoid misleading display.
                scores_map = {
                    participant_id(r): {
                        "time": None if is_reps_based else r.get("time"),
                        "reps": r.get("how_many"),
                        "tiebreak": r.get("athlete_tie_break"),
                    }
                    for r in results if participant_id(r)
                }
                result_ids = set(scores_map.keys())

                # Top-N for this WOD: only athletes with actual submissions, sorted by position
                wod_ranked = []
                for a_id, pos in sorted(pos_map.items(), key=lambda x: (x[1] or 99999)):
                    if a_id not in result_ids:
                        continue
                    athlete = athletes_map.get(a_id, {})
                    score = scores_map[a_id]
                    wod_ranked.append(
                        {
                            "rank": pos,
                            "name": athlete.get("name", "?"),
                            "country": athlete.get("country") or "",
                            "club": athlete.get("club_name") or "",
                            "time": score["time"],
                            "reps": score["reps"],
                            "tiebreak": score["tiebreak"],
                        }
                    )
                per_wod[wname] = wod_ranked[:TOP_N]

        # ---- Overall top-20 ----
        # Build per-WOD position + score lookup (only for athletes with results)
        wod_pos_maps = {}    # wname -> {athlete_id: position}
        wod_score_maps = {}  # wname -> {athlete_id: {time, reps, tiebreak}}
        for wod_entry in lb.get("wods", []):
            for workout_entry in wod_entry.get("workouts", []):
                wname = workout_entry.get("workout", {}).get("name", "?")
                first_field = workout_entry.get("workout", {}).get("first_field", "time")
                is_reps_based = first_field == "how_many"
                result_ids_wod = {participant_id(r) for r in workout_entry.get("results", []) if participant_id(r)}
                wk_p = workout_entry.get("teams", workout_entry.get("athletes", []))
                if isinstance(wk_p, dict):
                    wk_p = list(wk_p.values())
                wod_pos_maps[wname] = {
                    a["id"]: a.get("position")
                    for a in wk_p
                    if a.get("position") is not None and a["id"] in result_ids_wod
                }
                wod_score_maps[wname] = {
                    participant_id(r): {
                        "time": None if is_reps_based else r.get("time"),
                        "reps": r.get("how_many"),
                        "tiebreak": r.get("athlete_tie_break"),
                    }
                    for r in workout_entry.get("results", []) if participant_id(r)
                }

        # Sort athletes/teams by their overall points (lower = better)
        ranked_athletes = sorted(
            [a for a in participants if a["id"] in athletes_with_results],
            key=lambda a: (a.get("points") or 0, a.get("name", "")),
        )

        overall_top20 = []
        for rank, athlete in enumerate(ranked_athletes[:TOP_N], 1):
            wod_data = {}
            for wname in wod_names:
                pos = wod_pos_maps.get(wname, {}).get(athlete["id"])
                score = wod_score_maps.get(wname, {}).get(athlete["id"])
                if pos is not None:
                    wod_data[wname] = {
                        "position": pos,
                        "time": score["time"] if score else None,
                        "reps": score["reps"] if score else None,
                        "tiebreak": score["tiebreak"] if score else None,
                    }
            overall_top20.append(
                {
                    "rank": rank,
                    "name": athlete.get("name", "?"),
                    "country": athlete.get("country") or "",
                    "club": athlete.get("club_name") or "",
                    "points": athlete.get("points") or 0,
                    "wods": wod_data,
                }
            )

        result_count = len(athletes_with_results)
        total_count = len(participants)
        print(
            f"   ✅ {total_count} athletes, {result_count} with results, "
            f"{len(wod_names)} WODs"
        )

        output["divisions"].append(
            {
                "id": div_id,
                "name": div_name,
                "order": div.get("order", 99),
                "individual": is_individual,
                "athlete_count": total_count,
                "result_count": result_count,
                "wods": wod_names,
                "wod_units": wod_units,
                "overall": overall_top20,
                "per_wod": per_wod,
            }
        )

    # Step 3: Write output
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    div_count = len(output["divisions"])
    print(f"\n✅ Done — wrote {OUTPUT_PATH}")
    print(f"   {div_count} divisions, updated at {output['meta']['updated_at_readable']}")


if __name__ == "__main__":
    fetch_all()
