import json
import os

def fmt_ms(ms):
    if not ms: return "?"
    s = round(ms / 1000)
    m, s = divmod(s, 60)
    return f"{m}:{s:02d}"

with open(os.path.join(os.path.dirname(__file__), 'data', 'data-gtd.json')) as f:
    data = json.load(f)

# --- Find Bastian's individual scores from team member data ---
bastian = {}
mf_div = next(d for d in data['divisions'] if d['name'] == 'Intermediate Teams of 2 Male/Female')
for team_entry in mf_div['overall']:
    for wname, wod in team_entry.get('wods', {}).items():
        for member in wod.get('members', []):
            if 'Bastian' in member.get('name', ''):
                bastian[wname] = {
                    'time': member.get('time'),
                    'reps': member.get('reps'),
                    'tiebreak': member.get('tiebreak'),
                    'cap': member.get('cap', False),
                }

if not bastian:
    print("Bastian Broecker not found in data.")
    exit()

print("Bastian Broecker individual scores (from Int. M/F team data):")
for wname, s in bastian.items():
    t, r, tb, cap = s['time'], s['reps'], s['tiebreak'], s['cap']
    is_cap = cap or (t and r)
    if is_cap and r:
        score_str = f"{r} reps @ {fmt_ms(tb)}" if tb else f"{r} reps"
    elif t:
        score_str = fmt_ms(t)
    elif r:
        score_str = f"{r} reps"
    else:
        score_str = "no score"
    print(f"  {wname}: {score_str}")

# --- Compare against Masters 40+ Male ---
m40_div = next((d for d in data['divisions'] if 'Masters 40' in d['name'] and 'Male' in d['name'] and 'Female' not in d['name']), None)
if not m40_div:
    print("\nMasters 40+ Male division not found")
    exit()

print(f"\n--- Estimated ranking in '{m40_div['name']}' ---")
print(f"(Division has {m40_div['result_count']} athletes with results / {m40_div['athlete_count']} registered)\n")

wod_names = m40_div['wods']
total_points = 0
for wname in wod_names:
    rows = m40_div['per_wod'].get(wname, [])
    s = bastian.get(wname, {})
    if not s:
        print(f"  {wname}: no score")
        total_points += len(rows) + 1
        continue

    v_time = s['time']
    v_reps = s['reps']
    v_tb = s['tiebreak']
    v_cap = s['cap'] or (v_time and v_reps)

    # Detect WOD type from the leaderboard rows:
    # if all rows have time=None → reps/weight WOD, sort by reps desc
    is_reps_wod = rows and all(r.get('time') is None for r in rows)

    beaten_by = 0
    for row in rows:
        r_time = row.get('time')
        r_reps = row.get('reps')
        r_tb = row.get('tiebreak')
        r_cap = row.get('cap', False) or (r_time and r_reps)

        if is_reps_wod:
            # Reps/weight WOD: more reps = better
            if r_reps and v_reps and r_reps > v_reps:
                beaten_by += 1
        elif v_cap:
            if not r_cap:
                beaten_by += 1
            elif r_tb and v_tb and r_tb < v_tb:
                beaten_by += 1
            elif r_tb == v_tb and r_reps and v_reps and r_reps > v_reps:
                beaten_by += 1
        else:
            if not r_cap and r_time and v_time and r_time < v_time:
                beaten_by += 1

    est_pos = beaten_by + 1
    total_points += est_pos

    if v_cap:
        score_str = f"{v_reps} reps @ {fmt_ms(v_tb)}" if v_tb else f"{v_reps} reps"
    elif v_time:
        score_str = fmt_ms(v_time)
    elif v_reps:
        score_str = f"{v_reps} reps"
    else:
        score_str = "?"

    # Show context: who's around that position
    nearby = [r for r in rows if est_pos - 1 <= r['rank'] <= est_pos + 1]
    context = ', '.join(f"#{r['rank']} {r['name'].split()[0]}" for r in nearby)
    print(f"  {wname}: {score_str}  → est pos {est_pos}/{len(rows)}  [{context}]")

print(f"\nEstimated total points: {total_points}")
overall = m40_div['overall']
if overall:
    est_rank = sum(1 for e in overall if e['points'] < total_points) + 1
    print(f"Estimated overall rank: #{est_rank} of {len(overall)} athletes with results")
    print(f"Top 20 cutoff: {'✅ QUALIFIES' if est_rank <= 20 else f'❌ Need to improve ({est_rank - 20} spots away)'}")

    # Show surrounding ranks
    print()
    for e in overall:
        if abs(e['rank'] - est_rank) <= 2:
            marker = " ← you'd be here" if e['rank'] == est_rank else ""
            print(f"  #{e['rank']:>2} {e['name']:<35} {e['points']} pts{marker}")
