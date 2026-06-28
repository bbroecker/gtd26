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
# Helpers
# ---------------------------------------------------------------------------
def apply_member_combined_score(entry, members):
    """
    If team members hit the timecap (time > 0 AND reps > 0), the platform's
    combined team `time` field is unreliable. Derive the correct score:
    - any member capped → sum reps, sum tiebreaks, clear misleading time
    - all members finished → keep existing combined time (platform is reliable here)
    """
    any_capped = any(m.get("time") and m.get("reps") for m in members)
    if any_capped:
        total_reps = sum(m.get("reps") or 0 for m in members)
        combined_tb = sum(m.get("tiebreak") or 0 for m in members)
        if total_reps > 0:
            entry["reps"] = total_reps
            entry["cap"] = True
            entry["time"] = None
            if combined_tb > 0:
                entry["tiebreak"] = combined_tb


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
        wod_exercise_ids = {}  # wname -> exercise UUID (needed for per-athlete fetch)
        per_wod = {}

        for wod_entry in lb.get("wods", []):
            for workout_entry in wod_entry.get("workouts", []):
                wname = workout_entry.get("workout", {}).get("name", "?")
                wod_names.append(wname)
                wod_units[wname] = workout_entry.get("workout", {}).get("units_of_measure") or ""
                wod_exercise_ids[wname] = workout_entry.get("workout", {}).get("id", "")

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
                # Scores: participant_id -> {time, reps, tiebreak, cap}
                scores_map = {
                    participant_id(r): {
                        "time": r.get("time"),
                        "reps": r.get("how_many"),
                        "tiebreak": r.get("tie_break"),
                        "cap": bool(r.get("cap")),
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
                    entry = {
                        "rank": pos,
                        "name": athlete.get("name", "?"),
                        "country": athlete.get("country") or "",
                        "club": athlete.get("club_name") or "",
                        "time": score["time"],
                        "reps": score["reps"],
                        "tiebreak": score["tiebreak"],
                        "cap": score["cap"],
                    }
                    wod_ranked.append(entry)
                per_wod[wname] = wod_ranked[:TOP_N]

        # ---- Overall top-20 ----
        # Build per-WOD position + score lookup (only for athletes with results)
        wod_pos_maps = {}    # wname -> {athlete_id: position}
        wod_score_maps = {}  # wname -> {athlete_id: {time, reps, tiebreak, cap}}
        for wod_entry in lb.get("wods", []):
            for workout_entry in wod_entry.get("workouts", []):
                wname = workout_entry.get("workout", {}).get("name", "?")
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
                        "time": r.get("time"),
                        "reps": r.get("how_many"),
                        "tiebreak": r.get("tie_break"),
                        "cap": bool(r.get("cap")),
                    }
                    for r in workout_entry.get("results", []) if participant_id(r)
                }

        # Sort athletes/teams by their overall points (lower = better)
        ranked_athletes = sorted(
            [a for a in participants if a["id"] in athletes_with_results],
            key=lambda a: (a.get("points") or 0, a.get("name", "")),
        )

        # ---- For team divisions: fetch per-member scores per exercise ----
        # team_id -> [{ name, gender, athlete_id }]
        team_members_map = {}  # team_id -> list of member dicts
        # team_id -> { wname -> [{ name, gender, time, reps, tiebreak, cap }] }
        team_member_scores = {}  # team_id -> wname -> member score list

        if not is_individual:
            teams_with_results = [a for a in participants if a["id"] in athletes_with_results]
            print(f"   Fetching member details for {len(teams_with_results)} teams...")
            for team in teams_with_results:
                team_id = team["id"]
                try:
                    member_resp = get(f"{API_BASE}/teams/{team_id}/member")
                    members = []
                    for m in (member_resp if isinstance(member_resp, list) else []):
                        ath = m.get("athlete", {})
                        user = ath.get("user", {})
                        members.append({
                            "athlete_id": m.get("athlete_id"),
                            "name": user.get("name") or ath.get("name") or "?",
                            "gender": user.get("gender") or "",
                        })
                    team_members_map[team_id] = members
                    time.sleep(0.3)

                    # Fetch per-member score for each exercise
                    wname_scores = {}
                    for wname, ex_id in wod_exercise_ids.items():
                        if not ex_id:
                            continue
                        member_wod_scores = []
                        for member in members:
                            ath_id = member["athlete_id"]
                            if not ath_id:
                                continue
                            try:
                                res = get(f"{API_BASE}/workouts/{ex_id}/results?athlete_id={ath_id}")
                                data = res.get("data", [])
                                if data:
                                    r = data[0]
                                    member_wod_scores.append({
                                        "name": member["name"],
                                        "gender": member["gender"],
                                        "time": r.get("time"),
                                        "reps": r.get("how_many"),
                                        "tiebreak": r.get("tie_break"),
                                        "cap": bool(r.get("cap")),
                                    })
                                time.sleep(0.2)
                            except Exception:
                                pass
                        if member_wod_scores:
                            wname_scores[wname] = member_wod_scores
                    team_member_scores[team_id] = wname_scores
                except Exception as e:
                    print(f"     ⚠️  Members for {team.get('name')}: {e}")

        overall_top20 = []
        for rank, athlete in enumerate(ranked_athletes[:TOP_N], 1):
            wod_data = {}
            for wname in wod_names:
                pos = wod_pos_maps.get(wname, {}).get(athlete["id"])
                score = wod_score_maps.get(wname, {}).get(athlete["id"])
                if pos is not None:
                    wod_entry_data = {
                        "position": pos,
                        "time": score["time"] if score else None,
                        "reps": score["reps"] if score else None,
                        "tiebreak": score["tiebreak"] if score else None,
                        "cap": score["cap"] if score else False,
                    }
                    members_for_wod = team_member_scores.get(athlete["id"], {}).get(wname)
                    if members_for_wod:
                        apply_member_combined_score(wod_entry_data, members_for_wod)
                        wod_entry_data["members"] = members_for_wod
                    wod_data[wname] = wod_entry_data
            entry = {
                "rank": rank,
                "name": athlete.get("name", "?"),
                "country": athlete.get("country") or "",
                "club": athlete.get("club_name") or "",
                "points": athlete.get("points") or 0,
                "wods": wod_data,
            }
            if athlete["id"] in team_members_map:
                entry["members"] = team_members_map[athlete["id"]]
            overall_top20.append(entry)

        # Attach member scores to per_wod entries too
        if not is_individual:
            for wname, rows in per_wod.items():
                for row in rows:
                    team = next((a for a in participants if a.get("name") == row["name"]), None)
                    if team:
                        members_for_wod = team_member_scores.get(team["id"], {}).get(wname)
                        if members_for_wod:
                            apply_member_combined_score(row, members_for_wod)
                            row["members"] = members_for_wod

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
