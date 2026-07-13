import json
from collections import defaultdict

with open('data/data-gtd.json') as f:
    data = json.load(f)

# Build map: athlete name -> list of divisions they appear in
name_to_divs = defaultdict(list)

for div in data['divisions']:
    div_name = div['name']
    seen_in_div = set()
    for entry in div.get('overall', []):
        # Individual athlete or team name
        n = entry['name'].strip().lower()
        if n not in seen_in_div:
            name_to_divs[n].append(div_name)
            seen_in_div.add(n)
        # Team members
        for m in entry.get('members', []):
            mn = m['name'].strip().lower()
            if mn not in seen_in_div:
                name_to_divs[mn].append(div_name)
                seen_in_div.add(mn)

# Find anyone in more than one division
multi = {name: divs for name, divs in name_to_divs.items() if len(divs) > 1}

if not multi:
    print("No athletes found in multiple divisions.")
else:
    print(f"Found {len(multi)} athlete(s)/team(s) registered in multiple divisions:\n")
    for name, divs in sorted(multi.items()):
        print(f"  {name.title()}")
        for d in divs:
            print(f"    → {d}")

