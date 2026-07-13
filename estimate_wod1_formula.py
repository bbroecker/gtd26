"""
Estimate the time→reps conversion rate R for WOD1.

Model:
  effective_reps = actual_reps_done + (cap_time - finish_time) × R
  (cappers: finish_time = cap_time, so no bonus)
  (finishers: get bonus = time_saved × R)
  Team effective = sum of members' effective_reps
  Ranking: higher effective_reps = better

We find R by finding adjacent pairs in WOD1 rankings where we know
member-level data, and deriving: ranked_higher.effective > ranked_lower.effective
"""
import json, os

def load(slug):
    with open(os.path.join(os.path.dirname(__file__), 'data', f'data-{slug}.json')) as f:
        return json.load(f)

CAP_MS = 900_000  # 15:00 in ms
WORKOUT_TOTAL = 190  # assumed total reps to finish the workout

def member_effective(m, R):
    t = m.get('time')
    r = m.get('reps')
    if t and r:
        # capped: time = cap time, reps = actual reps
        return r  # no bonus (already at cap)
    if t and not r:
        # finished: bonus = (cap - finish) * R + total
        time_saved_s = (CAP_MS - t) / 1000
        return WORKOUT_TOTAL + time_saved_s * R
    return None

lower_bounds = []
upper_bounds = []
evidence = []

for slug, data in [('gtd', load('gtd')), ('atd', load('atd'))]:
    for div in data['divisions']:
        if div['individual']:
            continue
        wod1 = next((w for w in div['wods'] if 'QWOD26.1' in w), None)
        if not wod1:
            continue
        rows = sorted(div['per_wod'].get(wod1, []), key=lambda x: x['rank'])

        # Build scored list (with member data)
        scored = []
        for row in rows:
            members = row.get('members', [])
            if not members:
                continue
            # Check if any member finished
            has_finisher = any(m.get('time') and not m.get('reps') for m in members)
            has_capper   = any(m.get('time') and m.get('reps') for m in members)
            scored.append({
                'rank': row['rank'],
                'name': row['name'],
                'members': members,
                'has_finisher': has_finisher,
                'has_capper': has_capper,
                'comp': slug,
                'div': div['name'],
            })

        # For adjacent pairs, derive R constraints
        for i in range(len(scored) - 1):
            a = scored[i]    # higher rank (better)
            b = scored[i+1]  # lower rank (worse)

            # Only useful if the two teams differ in type
            if a['has_finisher'] == b['has_finisher']:
                continue  # same type, skip

            # Effective reps as function of R:
            # eff(team, R) = sum(member_effective(m, R)) 
            # = constant + coefficient * R
            def eff_parts(team):
                const, coeff = 0, 0
                for m in team['members']:
                    t = m.get('time')
                    r = m.get('reps')
                    if t and r:      # capper
                        const += r
                    elif t and not r:  # finisher
                        time_saved_s = (CAP_MS - t) / 1000
                        const += WORKOUT_TOTAL
                        coeff += time_saved_s
                return const, coeff

            ac, ak = eff_parts(a)
            bc, bk = eff_parts(b)

            # Constraint: a.eff > b.eff → (ac + ak*R) > (bc + bk*R)
            # → (ak - bk)*R > bc - ac
            # → if (ak - bk) > 0: R > (bc - ac) / (ak - bk)
            # → if (ak - bk) < 0: R < (bc - ac) / (ak - bk)
            diff_k = ak - bk
            diff_c = bc - ac
            if diff_k == 0:
                continue
            bound = diff_c / diff_k
            label = f"[{slug}/{div['name']}] #{a['rank']}({a['name'][:20]},fin={a['has_finisher']}) > #{b['rank']}({b['name'][:20]},fin={b['has_finisher']})"
            if diff_k > 0:
                lower_bounds.append(bound)
                evidence.append(f"R > {bound:.3f}   {label}")
            else:
                upper_bounds.append(bound)
                evidence.append(f"R < {bound:.3f}   {label}")

print("Evidence:")
for e in sorted(evidence):
    print(" ", e)

print()
if lower_bounds:
    print(f"Tightest lower bound: R > {max(lower_bounds):.3f} reps/sec")
if upper_bounds:
    print(f"Tightest upper bound: R < {min(upper_bounds):.3f} reps/sec")
if lower_bounds and upper_bounds:
    lo, hi = max(lower_bounds), min(upper_bounds)
    if lo < hi:
        print(f"\nEstimated R range: {lo:.3f} – {hi:.3f} reps/sec")
        best = (lo + hi) / 2
        print(f"Best estimate:      R ≈ {best:.3f} reps/sec")
        print(f"  (= 1 rep per {1/best:.1f} seconds)")
    else:
        print(f"\n⚠️  No consistent R found (lo={lo:.3f} >= hi={hi:.3f}) — model may not be purely linear")
