"""
update_stats.py — Fetches CR7's current goal totals and upcoming fixture,
                   then updates public/stats.json

Sources used (in priority order):
  1. API-Football (api-sports.io) — free tier: 100 req/day
     Sign up at: https://dashboard.api-football.com/register
     Add your key as GitHub Secret: APIFOOTBALL_KEY

  2. Manual override via FORCE_GOALS env variable (for GitHub Actions workflow_dispatch)

CR7 IDs on API-Football:
  Player ID : 874
  Al Nassr  : 2911  (Saudi Pro League: 307)
  Portugal  : 27    (FIFA WC Qual / Nations League / Euro Qual)
"""

import json, os, sys, requests
from datetime import datetime, timezone
from pathlib import Path

# ─── CONFIG ────────────────────────────────────────────────────────────────
STATS_FILE   = Path(__file__).parent.parent / "public" / "stats.json"
API_KEY      = os.environ.get("APIFOOTBALL_KEY", "")
FORCE_GOALS  = os.environ.get("FORCE_GOALS", "").strip()
CR7_ID       = 874
ALNASSR_ID   = 2911
PORTUGAL_ID  = 27
SPL_ID       = 307   # Saudi Pro League
TARGET       = 1000

# Career total as of the last known date (baseline)
# Increase this each time the season rolls over
HISTORICAL_BASELINE = 832   # goals before current Al Nassr + Portugal 2025-26 season

# Team logo URLs (static, updated manually if clubs change)
TEAM_LOGOS = {
    2911: "https://upload.wikimedia.org/wikipedia/en/thumb/e/e2/Al_Nassr_FC_Logo.svg/200px-Al_Nassr_FC_Logo.svg.png",
    27:   "https://upload.wikimedia.org/wikipedia/en/thumb/5/5b/Flag_of_Portugal.svg/200px-Flag_of_Portugal.svg.png",
    # Saudi clubs
    2912: "https://upload.wikimedia.org/wikipedia/en/thumb/2/22/Al-Ittihad-Badge.svg/200px-Al-Ittihad-Badge.svg.png",
    2922: "https://upload.wikimedia.org/wikipedia/en/thumb/b/b2/Al_Hilal_FC_logo.svg/200px-Al_Hilal_FC_logo.svg.png",
}

API_BASE = "https://v3.football.api-sports.io"
HEADERS  = {
    "x-rapidapi-host": "v3.football.api-sports.io",
    "x-rapidapi-key": API_KEY,
}

# ─── LOAD CURRENT STATS ────────────────────────────────────────────────────
def load_current():
    if STATS_FILE.exists():
        with open(STATS_FILE) as f:
            return json.load(f)
    return {"goals": 967, "target": TARGET, "remaining": 33}

# ─── API-FOOTBALL FETCH ────────────────────────────────────────────────────
def fetch_player_stats(team_id, league_id, season):
    """Fetch CR7's goals and minutes for a specific team/league/season from API-Football.
    Returns (goals, minutes) tuple or (None, None) on failure."""
    try:
        r = requests.get(f"{API_BASE}/players", headers=HEADERS, params={
            "id": CR7_ID, "team": team_id, "league": league_id, "season": season,
        }, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("response"):
            stats = data["response"][0].get("statistics", [])
            if stats:
                goals   = stats[0].get("goals",  {}).get("total",   0) or 0
                minutes = stats[0].get("games",  {}).get("minutes", 0) or 0
                return goals, minutes
    except Exception as e:
        print(f"  API error ({team_id}/{league_id}): {e}")
    return None, None

def fetch_all_goals():
    """
    Combine club + international goals for the current season,
    add to historical baseline.
    Returns (total_goals, season_goals_club, port_goals, alnassr_minutes) or None on failure.
    """
    if not API_KEY:
        print("  No APIFOOTBALL_KEY set — skipping API fetch")
        return None

    season = datetime.now().year if datetime.now().month >= 7 else datetime.now().year - 1
    print(f"  Fetching season {season}…")

    # Al Nassr — Saudi Pro League
    alnassr_goals, alnassr_minutes = fetch_player_stats(ALNASSR_ID, SPL_ID, season)
    print(f"  Al Nassr SPL goals this season: {alnassr_goals} ({alnassr_minutes} min)")

    # Portugal — UEFA Nations League (5) + Euro Qual (29) + WC Qual (32)
    port_goals_nl,  _ = fetch_player_stats(PORTUGAL_ID, 5,  season)  # Nations League
    port_goals_wcq, _ = fetch_player_stats(PORTUGAL_ID, 29, season)  # Euro/WC Qual
    port_goals = (port_goals_nl or 0) + (port_goals_wcq or 0)
    print(f"  Portugal goals this season: {port_goals}")

    if alnassr_goals is None and port_goals == 0:
        return None

    season_total = (alnassr_goals or 0) + port_goals
    career_total = HISTORICAL_BASELINE + season_total
    print(f"  Career total estimate: {HISTORICAL_BASELINE} + {season_total} = {career_total}")

    return career_total, (alnassr_goals or 0), port_goals, (alnassr_minutes or 0)

# ─── NEXT FIXTURE FETCH ────────────────────────────────────────────────────
def fetch_next_fixture():
    """
    Fetch the next upcoming fixture for Al Nassr or Portugal that includes CR7.
    Returns a next_match dict or None.
    """
    if not API_KEY:
        return None

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    best = None

    for team_id in [ALNASSR_ID, PORTUGAL_ID]:
        try:
            r = requests.get(f"{API_BASE}/fixtures", headers=HEADERS, params={
                "team": team_id, "next": 5,
            }, timeout=10)
            r.raise_for_status()
            fixtures = r.json().get("response", [])
            for fx in fixtures:
                kickoff = fx.get("fixture", {}).get("date", "")
                if not kickoff:
                    continue
                # Pick the soonest upcoming fixture
                if best is None or kickoff < best["kickoff_utc"]:
                    home = fx["teams"]["home"]
                    away = fx["teams"]["away"]
                    league = fx.get("league", {})
                    best = {
                        "home_team": home["name"],
                        "away_team": away["name"],
                        "home_logo": home.get("logo", TEAM_LOGOS.get(home.get("id"), "")),
                        "away_logo": away.get("logo", TEAM_LOGOS.get(away.get("id"), "")),
                        "competition": league.get("name", ""),
                        "kickoff_utc": kickoff,
                        "venue": fx.get("fixture", {}).get("venue", {}).get("name", ""),
                        "is_cr7_team_home": home.get("id") == team_id,
                    }
        except Exception as e:
            print(f"  Fixture fetch error (team {team_id}): {e}")

    if best:
        print(f"  Next fixture: {best['home_team']} vs {best['away_team']} on {best['kickoff_utc']}")
    return best

# ─── MAIN ──────────────────────────────────────────────────────────────────
def main():
    current = load_current()
    old_goals = current.get("goals", 967)
    print(f"Current stats.json: {old_goals} goals")

    new_goals_per_90 = current.get("goals_per_90", None)

    # ── Manual override (from workflow_dispatch) ──
    if FORCE_GOALS:
        try:
            new_goals = int(FORCE_GOALS)
            print(f"  Manual override: setting goals to {new_goals}")
        except ValueError:
            print(f"  Invalid FORCE_GOALS value: {FORCE_GOALS}")
            sys.exit(1)
    else:
        result = fetch_all_goals()
        if result is None:
            print("  Could not fetch goal count from API — keeping existing value")
            # Still try to update the fixture
            new_goals = old_goals
        else:
            new_goals = result[0]
            alnassr_minutes = result[3] if len(result) > 3 else 0
            alnassr_goals   = result[1]
            if alnassr_minutes and alnassr_minutes > 0:
                new_goals_per_90 = round(alnassr_goals / alnassr_minutes * 90, 2)
                print(f"  Goals per 90 min (SPL): {new_goals_per_90}")

    # ── Fetch next fixture ──
    next_match = fetch_next_fixture()
    if next_match:
        current["next_match"] = next_match
    elif "next_match" not in current:
        current["next_match"] = None

    goals_changed = (new_goals != old_goals and new_goals > old_goals)

    if not goals_changed and next_match is None:
        print(f"  No change in goals ({old_goals}) and no fixture update — nothing to do")
        sys.exit(0)

    if new_goals < old_goals:
        print(f"  New value ({new_goals}) < current ({old_goals}) — ignoring goal change (data anomaly)")
        new_goals = old_goals

    # ── Build updated stats ──
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    updated = {
        **current,
        "goals": new_goals,
        "remaining": TARGET - new_goals,
        "last_updated": now,
        "version": current.get("version", 1) + 1,
    }
    if new_goals_per_90 is not None:
        updated["goals_per_90"] = new_goals_per_90

    with open(STATS_FILE, "w") as f:
        json.dump(updated, f, indent=2)

    if goals_changed:
        print(f"  ✅ Goals updated: {old_goals} → {new_goals} (+{new_goals - old_goals})")
    if next_match:
        print(f"  ✅ Fixture updated: {next_match['home_team']} vs {next_match['away_team']}")
    print(f"  File: {STATS_FILE}")

if __name__ == "__main__":
    main()
