import json
import os

R = 0.354
CAP_MS = 900_000
WORKOUT_TOTAL = 190

def fmt_ms(ms):
    if not ms: return "?"
    s = round(ms / 1000)
    m, s = divmod(s, 60)
    return f"{m}:{s:02d}"

def wod1_effective(members):
    total = 0.0
    for m in members:
        t = m.get('time')
        r = m.get('reps')
        if t and r:
            total += r
        elif t and not r:
            time_saved_s = (CAP_MS - t) / 1000
            total += WORKOUT_TOTAL + time_saved_s * R
    return total

def fmt_score(row):
    t, r, tb, cap = row.get('time'), row.get('reps'), row.get('tiebreak'), row.get('cap', False)
    is_cap = cap or (t and r)
    if is_cap and r:
        return f"{r} reps @ {fmt_ms(tb)}" if tb else f"{r} reps"
    if t: return fmt_ms(t)
    if r: return f"{r} reps"
    return "?"

with open(os.path.join(os.path.dirname(__file__), 'data', 'data-gtd.json')) as f:
    gtd = json.load(f)
with open(os.path.join(os.path.dirname(__file__), 'data', 'data-atd.json')) as f:
    atd = json.load(f)

gtd_div = next(d for d in gtd['divisions'] if d['name'] == 'Intermediate Teams of 2 Male/Female')
atd_div = next(d for d in atd['divisions'] if d['name'] == 'Intermediate Teams of 2 Male/Female')

TEAMS = ['Forschung & keine Technik', 'Cinghiali Bavaresi']

def estimate_pos(score, rows, wname):
    """Estimate position of a score in the given leaderboard rows."""
    v_time = score.get('time')
    v_reps = score.get('reps')
    v_tb   = score.get('tiebreak')
    v_cap  = score.get('cap', False) or (v_time and v_reps)
    v_members = score.get('members', [])

    is_reps_wod = rows and all(r.get('time') is None for r in rows)
    is_wod1 = 'QWOD26.1' in wname

    v_eff = wod1_effective(v_members) if (is_wod1 and v_members) else None

    beaten_by = 0
    for row in rows:
        r_time = row.get('time')
        r_reps = row.get('reps')
        r_tb   = row.get('tiebreak')
        r_cap  = row.get('cap', False) or (r_time and r_reps)
        r_members = row.get('members', [])

        if is_wod1 and v_eff is not None and r_members:
            r_eff = wod1_effective(r_members)
            if r_eff > v_eff:
                beaten_by += 1
        elif is_reps_wod:
            if r_reps and v_reps and r_reps > v_reps:
                beaten_by += 1
        elif v_cap:
            if not r_cap:
                beaten_by += 1
            elif r_reps and v_reps and r_reps > v_reps:
                beaten_by += 1
            elif (r_reps or 0) == (v_reps or 0) and r_tb and v_tb and r_tb < v_tb:
                beaten_by += 1
        else:
            if not r_cap and r_time and v_time and r_time < v_time:
                beaten_by += 1
    return beaten_by + 1

wod_names = gtd_div['wods']

print(f"Simulating GTD Int. Teams M/F → ATD Int. Teams M/F")
print(f"ATD division: {atd_div['result_count']} teams with results / {atd_div['athlete_count']} registered\n")

for team_name in TEAMS:
    # Get team's scores from GTD per_wod data
    team_scores = {}
    for wname in wod_names:
        row = next((r for r in gtd_div['per_wod'].get(wname, []) if r['name'] == team_name), None)
        if row:
            team_scores[wname] = row

    if not team_scores:
        print(f"{team_name}: not found in GTD data\n")
        continue

    # Get current GTD rank
    gtd_entry = next((e for e in gtd_div['overall'] if e['name'] == team_name), None)
    gtd_rank = gtd_entry['rank'] if gtd_entry else '?'

    print(f"{'='*60}")
    print(f"Team: {team_name}  (GTD rank: #{gtd_rank} of {gtd_div['result_count']})")
    print(f"{'='*60}")

    total_pts = 0
    for wname in wod_names:
        score = team_scores.get(wname)
        if not score:
            total_pts += len(atd_div['per_wod'].get(wname, [])) + 1
            print(f"  {wname}: no score")
            continue
        # ATD uses "ATD QWOD..." prefix instead of "GTD QWOD..."
        atd_wname = wname.replace('GTD ', 'ATD ')
        atd_rows = atd_div['per_wod'].get(atd_wname, atd_div['per_wod'].get(wname, []))
        pos = estimate_pos(score, atd_rows, wname)
        total_pts += pos
        print(f"  {wname}: {fmt_score(score)}  → ATD pos {pos}/{len(atd_rows)}")

    est_rank = sum(1 for e in atd_div['overall'] if e['points'] < total_pts) + 1
    n_results = atd_div['result_count']

    # Find rank-20 team's points for gap calculation
    rank20_entry = next((e for e in atd_div['overall'] if e['rank'] == 20), None)
    if not rank20_entry and len(atd_div['overall']) >= 20:
        rank20_entry = atd_div['overall'][19]

    print(f"\n  Estimated ATD total: {total_pts} pts → rank #{est_rank} of {n_results}")
    if est_rank <= 20:
        print(f"  ✅ Would qualify (top 20)")
    else:
        gap = total_pts - (rank20_entry['points'] if rank20_entry else 0)
        r20_name = rank20_entry['name'] if rank20_entry else '?'
        r20_pts  = rank20_entry['points'] if rank20_entry else '?'
        print(f"  ❌ Outside top 20 (by {est_rank - 20} spots)")
        print(f"     Rank 20: {r20_name} ({r20_pts} pts) — need to save {gap+1} more pts")
    print()
