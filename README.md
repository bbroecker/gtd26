# German Throwdown 2026 — Leaderboard

Static leaderboard page for the German Throwdown 2026 Online Qualifier.  
Shows **Top 20** per division — overall standings + per-WOD scores.

Live at: *(set up GitHub Pages after creating the repo)*

---

## How it works

1. `fetch.py` calls the Circle21 API and writes `data/data.json`
2. `index.html` + `app.js` read `data/data.json` at page load — no backend needed
3. GitHub Actions runs `fetch.py` every 30 minutes and commits the updated JSON

---

## Competition

| Field | Value |
|---|---|
| Name | German Throwdown 2026 Online Qualifier |
| Competition ID | `cd3809c9-4aae-43bd-9d78-53c3b19b97c9` |
| Qualifier period | 11 June – 13 July 2026 |
| Finals | 7–8 November 2026, Berlin |

### Divisions (23 total)

| # | Name | Type |
|---|---|---|
| 1 | Elite Male | Individual |
| 2 | Elite Female | Individual |
| 3 | Intermediate Male | Individual |
| 4 | Intermediate Female | Individual |
| 5 | Scaled Male | Individual |
| 6 | Scaled Female | Individual |
| 7 | Masters 35+ Male | Individual |
| 8 | Masters 35+ Female | Individual |
| 9 | Masters 40+ Male | Individual |
| 10 | Masters 40+ Female | Individual |
| 11–23 | Various Team divisions | Team |

---

## Setup

### 1. Run locally

```bash
# Install nothing — pure stdlib Python 3
python3 fetch.py
# Opens index.html in browser (needs a local server for fetch() to work)
python3 -m http.server 8080
# → http://localhost:8080
```

### 2. Deploy to GitHub Pages

1. Create a new GitHub repo (e.g. `gtd-leaderboard`)
2. Push this folder to the repo root
3. Go to **Settings → Pages → Branch: main / root**
4. Add the Bearer token as a repository secret: **Settings → Secrets → `CIRCLE21_TOKEN`**
5. The workflow will sync every 30 minutes automatically

---

## Bearer Token

The Circle21 API requires a JWT Bearer token.

- Current token expires: **~May 2027** (embedded in `fetch.py` as fallback)
- To update: log into circle21.events, open DevTools → Network, copy any `/api/leaderboard` request's `Authorization: Bearer …` header value
- Set as GitHub Actions secret `CIRCLE21_TOKEN`, or update the fallback in `fetch.py`

---

## Data format (`data/data.json`)

```json
{
  "meta": {
    "competition_name": "German Throwdown 2026 Online Qualifier",
    "updated_at": "2026-06-14T10:00:00Z",
    "updated_at_readable": "2026-06-14 10:00 UTC"
  },
  "divisions": [
    {
      "id": "...",
      "name": "Elite Male",
      "individual": true,
      "athlete_count": 500,
      "result_count": 420,
      "wods": ["GTD QWOD26.1", "GTD QWOD26.2", "GTD QWOD26.3 A, GTD QWOD26.3 B"],
      "overall": [
        {
          "rank": 1,
          "name": "John Doe",
          "country": "DE",
          "club": "CrossFit Berlin",
          "points": 3,
          "wods": {
            "GTD QWOD26.1": { "position": 1, "time": 532000, "reps": null, "tiebreak": null },
            "GTD QWOD26.2": { "position": 2, "time": null, "reps": 135, "tiebreak": null }
          }
        }
      ],
      "per_wod": {
        "GTD QWOD26.1": [
          { "rank": 1, "name": "John Doe", "country": "DE", "club": "...", "time": 532000, "reps": null, "tiebreak": null }
        ]
      }
    }
  ]
}
```

---

## Files

| File | Purpose |
|---|---|
| `index.html` | Page structure, tabs, selectors |
| `app.js` | Rendering logic, score formatting |
| `styles.css` | Dark theme |
| `fetch.py` | Data fetcher → `data/data.json` |
| `data/data.json` | Generated — committed by CI |
| `.github/workflows/sync.yml` | Scheduled sync every 30 min |
