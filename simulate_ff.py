import json
import os

def fmt_ms(ms):
    if not ms:
        return None
    s = round(ms / 1000)
    m, s = divmod(s, 60)
    return f"{m}:{s:02d}"

with open(os.path.join(os.path.dirname(__file__), 'data', 'data-gtd.json')) as f:
    data = json.load(f)

athletes = {}
mf_div = next(d for d in data['divisions'] if d['name'] == 'Intermediate Teams of 2 Male/Female')
for team_entry in mf_div['overall']:
    for wname, wod in team_entry.get('wods', {}).items():
        for member in wod.get('members', []):
            name = member.get('name', '')
            if 'Anna' in name or 'Corinna' in name:
                if name not in athletes:
                    athletes[name] = {}
                athletes[name][wname] = {
                    'time': member.get('time'),
                    'reps': member.get('reps'),
                    'tiebreak': member.get('tiebreak'),
                    'cap': member.get('cap', False),
                }

anna = next(v for k, v in athletes.items() if 'Anna' in k)
corinna = next(v for k, v in athletes.items() if 'Corinna' in k)

def combine(a, b):
    members = [a, b]
    any_capped = any(m.get('time') and m.get('reps') for m in members)
    if any_capped:
        total_reps = sum(m.get('reps') or 0 for m in members)
        combined_tb = sum(m.get('tiebreak') or 0 for m in members)
        return {'time': None, 'reps': total_reps, 'tiebreak': combined_tb if combined_tb else None, 'cap': True}
    else:
        t1 = a.get('time') or 0
        t2 = b.get('time') or 0
        return {'time': t1 + t2, 'reps': None, 'tiebreak': None, 'cap': False}

wod_names = mf_div['wods']
virtual_scores = {wname: combine(anna.get(wname, {}), corinna.get(wname, {})) for wname in wod_names}

# Show combined scores
print("Virtual team combined scores:")
for wname, s in virtual_scores.items():
    t, r, tb, cap = s['time'], s['reps'], s['tiebreak'], s['cap']
    if cap and r:
        score_str = f"{r} reps @ {fmt_ms(tb)}" if tb else f"{r} reps"
    elif t:
        score_str = fmt_ms(t)
    else:
        score_str = "?"
    print(f"  {wname}: {score_str}  [tiebreak raw: {tb}]")

ff_div = next(d for d in data['divisions'] if 'Female/Female' in d['name'] and 'Intermediate' in d['name'])

print(f"\n--- Ranking in '{ff_div['name']}' (corrected WOD1 formula) ---\n")

total_points = 0
for wname in wod_names:
    rows = ff_div['per_wod'].get(wname, [])
    vs = virtual_scores[wname]
    v_time, v_reps, v_tb, v_cap = vs['time'], vs['reps'], vs['tiebreak'], vs['cap']

    beaten_by = 0
    for row in rows:
        r_time = row.get('time')
        r_reps = row.get('reps')
        r_tb = row.get('tiebreak')
        r_cap = row.get('cap', False) or (r_time and r_reps)

        if v_cap:
            # Team WOD1: tiebreak-first (finisher's time converts to tiebreak equiv)
            if not r_cap:
                beaten_by += 1
            elif r_tb and v_tb and r_tb < v_tb:
                beaten_by += 1
            elif (r_tb or 0) == (v_tb or 0) and r_reps and v_reps and r_reps > v_reps:
                beaten_by += 1
        else:
            # both finished: sort by time asc
            if not r_cap and r_time and v_time and r_time < v_time:
                beaten_by += 1

    est_pos = beaten_by + 1
    total = len(rows)
    total_points += est_pos

    if v_cap:
        score_str = f"{v_reps} reps @ {fmt_ms(v_tb)}" if v_tb else f"{v_reps} reps"
    elif v_time:
        score_str = fmt_ms(v_time)
    else:
        score_str = "?"
    print(f"  {wname}: {score_str}  → est pos {est_pos}/{total}")

print(f"\nEstimated total points: {total_points}")
print(f"F/F division: {ff_div['result_count']} teams with results")

# Show where that puts them overall
overall = ff_div['overall']
for i, e in enumerate(overall):
    if e['points'] > total_points:
        print(f"→ Would rank approximately #{i+1} overall (between #{i} and #{i+1})")
        break
