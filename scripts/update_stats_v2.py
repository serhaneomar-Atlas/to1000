"""
update_stats_v2.py — Sync ponctuelle de stats.json depuis ESPN

Remplace l'ancien update_stats.py qui dépendait d'API-Football.

UTILISATION
===========
  python update_stats_v2.py                    # refresh last_match + next_match depuis ESPN
  FORCE_GOALS=972 python update_stats_v2.py    # override manuel du compteur
  python update_stats_v2.py --dry-run          # n'écrit pas

Note : la mise à jour incrémentale du compteur 'goals' à chaque but est gérée
par goal_watcher_v2.py (smart polling). Ce script-ci sert pour :
  1. les sync manuelles (override FORCE_GOALS)
  2. les workflows GitHub Actions périodiques pour rafraîchir last_match/next_match
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from lib.espn_client import (
    AL_NASSR_ID, CR7_TEAM_IDS, TARGET_GOALS,
    find_last_match_cr7, find_next_match_cr7, get_match_summary,
)

PROJECT_DIR = SCRIPT_DIR.parent
STATS_FILE  = PROJECT_DIR / "public" / "stats.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def load_stats() -> dict:
    with open(STATS_FILE, encoding="utf-8") as f:
        return json.load(f)

def save_stats(stats: dict) -> None:
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)


def refresh_last_match(stats: dict) -> bool:
    """Si le dernier match terminé de CR7 (Al Nassr OU Portugal) a un cr7_minute, on rafraîchit last_match.
    Fix 2026-05-17 : passer le league_slug à get_match_summary pour les matchs continentaux
    (sans ça, la finale ACL Two du 16/05 n'était pas re-fetchée et last_match restait stale).
    Fix 2026-06-05 : suit aussi le Portugal (amicaux + Coupe du Monde 2026) via find_last_match_cr7."""
    last = find_last_match_cr7()
    if not last or not last.event_id:
        return False
    league = getattr(last, "league_slug", None) or "ksa.1"
    detail = get_match_summary(last.event_id, league)
    if not detail or not detail.is_finished:
        return False
    is_home = str(detail.home_team_id) in CR7_TEAM_IDS
    opp = detail.away_team if is_home else detail.home_team
    cr7_goals = [g for g in detail.goals if g.is_cr7]
    cr7_scored = bool(cr7_goals)
    cr7_minute = cr7_goals[-1].minute_int if cr7_goals else None

    result = "?"
    if detail.score_home is not None and detail.score_away is not None:
        our = detail.score_home if is_home else detail.score_away
        their = detail.score_away if is_home else detail.score_home
        result = "W" if our > their else ("L" if our < their else "D")

    try:
        d = datetime.fromisoformat(detail.date_iso.replace("Z", "+00:00"))
        short = d.strftime("%b %#d") if os.name == "nt" else d.strftime("%b %-d")
    except Exception:
        short = detail.date_iso[:10]

    new_block = {
        "home_team": detail.home_team,
        "away_team": detail.away_team,
        "score_home": detail.score_home,
        "score_away": detail.score_away,
        "date": short,
        "competition": detail.competition,
        "venue": detail.venue,
        "is_cr7_team_home": is_home,
        "result": result,
        "cr7_scored": cr7_scored,
        "cr7_goal_num": stats.get("goals", 0) if cr7_scored else None,
        "cr7_minute": cr7_minute,
        "fotmob_url": stats.get("last_match", {}).get("fotmob_url", ""),
        "date_iso": detail.date_iso,
    }
    if stats.get("last_match") == new_block:
        return False
    # Fix 2026-06-29 : garde-fou anti-régression. Ne jamais reculer dans le temps.
    # Si find_last_match_cr7() échoue à fetch le Portugal (runner GH Actions),
    # il retombe sur le dernier Al Nassr (intersaison, déjà ancien). On refuse
    # alors d'écraser un last_match plus récent (ex. Colombie–Portugal du Mondial).
    prev_iso = (stats.get("last_match") or {}).get("date_iso")
    if prev_iso and detail.date_iso and detail.date_iso < prev_iso:
        print(f"  last_match: conservé ({prev_iso} plus récent que {detail.date_iso}) — fetch probablement échoué")
        return False
    stats["last_match"] = new_block
    if cr7_scored:
        stats["last_goal_date"] = detail.date_iso[:10]
        stats["last_goal_opponent"] = opp
        stats["last_goal_competition"] = detail.competition
    return True


def refresh_next_match(stats: dict) -> bool:
    # Fix 2026-06-05 : cherche le prochain match club OU sélection (Portugal).
    nm = find_next_match_cr7()
    if not nm:
        # Fix 2026-05-16 : avant d'écrire off_season, vérifier si l'ancien
        # next_match correspond à un match probablement EN COURS. Un match qui
        # vient de kicker off (kickoff_utc dans les 3h passées) ne doit pas être
        # écrasé par sentinel, sinon on perd la finale ACL Two en plein direct.
        from datetime import datetime, timezone, timedelta
        cur_nm = stats.get("next_match") or {}
        cur_kickoff = cur_nm.get("kickoff_utc")
        if cur_kickoff and cur_nm.get("home_team"):
            try:
                ko = datetime.fromisoformat(cur_kickoff.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                # Match en cours : kickoff dans les 3h passées (couvre 90' + prolongations + tirs au but)
                if timedelta(0) <= (now - ko) <= timedelta(hours=3):
                    print("  next_match: match probablement en cours, préservation")
                    return False
                # Fix 2026-06-29 : garde-fou anti-régression. Si le next_match
                # actuel est encore DANS LE FUTUR, c'est qu'on connaît déjà un vrai
                # match à venir et que find_next_match_cr7() vient probablement
                # d'échouer (fetch ESPN Portugal KO sur le runner GH Actions →
                # fallback Al Nassr intersaison). On NE doit PAS écraser un match
                # futur connu (ex. Portugal–Croatie, Coupe du Monde) par off_season.
                if ko > now:
                    print(f"  next_match: futur connu préservé ({cur_nm.get('home_team')} vs {cur_nm.get('away_team')}, {cur_kickoff}) — fetch probablement échoué")
                    return False
            except (ValueError, AttributeError):
                pass

        # Pas de match futur trouvé sur ESPN (typiquement : fin de saison SPL,
        # entre mai et août). On écrit un sentinel pour que le front-end puisse
        # afficher "Saison terminée — calendrier 2026-27 à venir" plutôt que
        # rester figé sur l'ancien match déjà joué.
        # Fix 2026-05-15 : avant ce patch, refresh_next_match retournait False
        # silencieusement → next_match restait sur la dernière valeur (déjà passée).
        sentinel = {
            "status": "off_season",
            "home_team": None,
            "away_team": None,
            "competition": None,
            "kickoff_utc": None,
            "venue": None,
            "is_cr7_team_home": None,
            "fotmob_url": "",
            "note": "Saison SPL terminée — prochain match TBD",
        }
        if stats.get("next_match", {}).get("status") == "off_season":
            return False
        stats["next_match"] = sentinel
        return True
    is_home = str(nm.home_team_id) in CR7_TEAM_IDS
    new_block = {
        "home_team": nm.home_team,
        "away_team": nm.away_team,
        "competition": nm.competition,
        "kickoff_utc": nm.date_iso,
        "venue": nm.venue,
        "is_cr7_team_home": is_home,
        "fotmob_url": "",
    }
    if stats.get("next_match") == new_block:
        return False
    stats["next_match"] = new_block
    return True


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    stats = load_stats()
    changed = False

    # Override manuel ?
    fg = os.environ.get("FORCE_GOALS", "").strip()
    if fg:
        try:
            new_goals = int(fg)
            if new_goals != stats.get("goals"):
                print(f"  FORCE_GOALS: {stats.get('goals')} → {new_goals}")
                stats["goals"] = new_goals
                stats["remaining"] = TARGET_GOALS - new_goals
                changed = True
        except ValueError:
            print(f"  ⚠ FORCE_GOALS invalide: {fg}")

    # Refresh last_match (peut surfacer un but loupé pour info)
    if refresh_last_match(stats):
        print("  last_match refreshed from ESPN")
        changed = True
    # Refresh next_match
    if refresh_next_match(stats):
        print("  next_match refreshed from ESPN")
        changed = True

    if changed:
        stats["version"] = stats.get("version", 1) + 1
        stats["last_updated"] = _now_iso()
        if args.dry_run:
            print("  [dry-run] would write:")
            print(json.dumps({k: stats.get(k) for k in ("goals", "remaining", "version", "last_updated", "last_match", "next_match")},
                             indent=2, ensure_ascii=False))
        else:
            save_stats(stats)
            print(f"  ✅ stats.json updated → version {stats['version']}")
            # Sync les nombres hardcodés dans les fichiers HTML statiques
            # (meta tags, OG, Twitter Cards, JSON-LD, i18n bundles, JS state).
            # Sans ça Google et les partages sociaux voient une valeur figée.
            try:
                from update_html_counts import main as sync_html
                print("  → syncing HTML counts...")
                sys.argv = ["update_html_counts.py"]  # reset args pour le sous-call
                sync_html()
            except Exception as e:
                print(f"  ⚠ update_html_counts a échoué: {e}")
    else:
        print("  no change")
    return 0


if __name__ == "__main__":
    sys.exit(main())
