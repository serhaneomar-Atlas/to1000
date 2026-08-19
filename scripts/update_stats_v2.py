"""
update_stats_v2.py — Sync ponctuelle de stats.json depuis ESPN

Remplace l'ancien update_stats.py qui dépendait d'API-Football.

UTILISATION
===========
  python update_stats_v2.py                    # refresh last_match + next_match depuis ESPN
  FORCE_GOALS=972 python update_stats_v2.py    # override manuel du compteur
  python update_stats_v2.py --dry-run          # n'écrit pas

Depuis 2026-07-01, ce script gère AUSSI l'incrément automatique du compteur
'goals' (sync_goals) : goal_watcher_v2.py, censé le faire, n'a jamais été
commité — le compteur ne bougeait que par FORCE_GOALS manuel. Le workflow
update-cr7-goals.yml (*/5 min en fenêtre de match) fournit le quasi temps réel,
stats-sync.yml (quotidien) sert de filet. Le ledger anti-double-comptage
(processed_goal_event_ids + goal_sync_baseline) vit dans stats.json.
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
    find_last_match_cr7, find_next_match_cr7, find_team_match_today_cr7,
    get_match_summary,
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


def select_new_cr7_goals(goals, processed_ids: set, match_date_iso: str, baseline_iso: str) -> list:
    """Filtre les buts d'un match à créditer au compteur.

    Garde-fous (fix 2026-07-01, remplace le goal_watcher_v2 jamais commité) :
      - anti-doublon par event_id ESPN (ledger processed_goal_event_ids)
      - baseline : un match antérieur à goal_sync_baseline est ignoré en bloc
        (ses buts ont été comptés à la main avant l'activation de la sync)
      - séance de tirs au but (period >= 5) : ne compte pas comme but officiel
      - but contre son camp : exclu
    """
    if not match_date_iso or not baseline_iso or match_date_iso < baseline_iso:
        return []
    out = []
    for g in goals:
        if not g.is_cr7 or not g.event_id:
            continue
        if g.event_id in processed_ids:
            continue
        if g.period >= 5:
            continue
        if "own goal" in (g.raw_text or "").lower():
            continue
        out.append(g)
    return out


def sync_goals(stats: dict) -> bool:
    """Crédite au compteur les nouveaux buts de CR7 détectés sur ESPN.

    Regarde d'abord le match du jour (live ou fini) pour l'incrément quasi
    temps réel via le workflow */10 min, sinon le dernier match terminé
    (filet de sécurité du run quotidien). Le ledger vit DANS stats.json pour
    être commité/déployé atomiquement avec le compteur.
    """
    baseline = stats.get("goal_sync_baseline")
    if not baseline:
        print("  ⚠ sync_goals désactivé : goal_sync_baseline absent de stats.json")
        return False
    detail = None
    try:
        detail = find_team_match_today_cr7()
    except Exception as e:
        print(f"  ⚠ sync_goals: fetch match du jour échoué: {e}")
    if detail is None:
        try:
            last = find_last_match_cr7()
            if last and last.event_id:
                detail = get_match_summary(last.event_id, getattr(last, "league_slug", None) or "ksa.1")
        except Exception as e:
            print(f"  ⚠ sync_goals: fetch dernier match échoué: {e}")
    if not detail or not (detail.is_finished or detail.is_in_progress):
        return False

    processed = list(stats.get("processed_goal_event_ids") or [])
    new_goals = select_new_cr7_goals(detail.goals, set(processed), detail.date_iso, baseline)
    if not new_goals:
        return False

    for g in new_goals:
        stats["goals"] = stats.get("goals", 0) + 1
        processed.append(g.event_id)
        print(f"  ⚽ BUT CR7 #{stats['goals']} crédité ! {g.minute} vs "
              f"{detail.away_team if str(detail.home_team_id) in CR7_TEAM_IDS else detail.home_team} "
              f"(event {g.event_id})")
    stats["remaining"] = TARGET_GOALS - stats["goals"]
    stats["processed_goal_event_ids"] = processed[-100:]
    is_home = str(detail.home_team_id) in CR7_TEAM_IDS
    stats["last_goal_date"] = (detail.date_iso or "")[:10]
    stats["last_goal_opponent"] = detail.away_team if is_home else detail.home_team
    stats["last_goal_competition"] = detail.competition
    return True


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
        else:
            # Un override manuel intègre déjà les buts du match en cours/du jour :
            # on marque leurs event_ids comme traités pour que sync_goals ne les
            # recompte pas au passage suivant (double-comptage).
            try:
                today = find_team_match_today_cr7()
                if today:
                    processed = list(stats.get("processed_goal_event_ids") or [])
                    for g in today.goals:
                        if g.is_cr7 and g.event_id and g.event_id not in processed:
                            processed.append(g.event_id)
                    stats["processed_goal_event_ids"] = processed[-100:]
            except Exception as e:
                print(f"  ⚠ FORCE_GOALS: marquage des buts du jour échoué: {e}")

    # Chaque source est isolée. Avant, une erreur ESPN sur le DERNIER match
    # (403 quotidien depuis le 12/08) remontait et tuait tout le script : ni
    # next_match rafraîchi, ni stats.json écrit — donc les buts déjà
    # synchronisés avec succès étaient perdus eux aussi, et stats.json est resté
    # figé au 26/07 pendant trois semaines. Une panne partielle ne doit jamais
    # annuler le travail qui a réussi.
    etapes = (
        ("goals synced from ESPN", sync_goals),
        ("last_match refreshed from ESPN", refresh_last_match),
        ("next_match refreshed from ESPN", refresh_next_match),
    )
    echecs = []
    for libelle, etape in etapes:
        try:
            if etape(stats):
                print(f"  {libelle}")
                changed = True
        except Exception as e:
            echecs.append(etape.__name__)
            print(f"  ⚠ {etape.__name__} a échoué (source conservée) : {e}")

    if echecs:
        # Visible dans l'onglet Actions sans faire échouer le run : une panne
        # côté ESPN n'est pas une régression de notre code, et un workflow
        # rouge en permanence finit par ne plus être lu.
        print(f"::warning::stats partiellement rafraîchies — échecs : {', '.join(echecs)}")

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
    # Échec seulement si TOUTES les sources sont tombées : là, c'est une vraie
    # panne qui mérite une alerte.
    if len(echecs) == len(etapes):
        print("::error::toutes les sources ESPN ont échoué")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
