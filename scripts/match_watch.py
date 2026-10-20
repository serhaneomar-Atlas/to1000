"""Guetteur de match CR7 — suivi fiable des buts en direct (ajouté 2026-10-20).

Pourquoi : GitHub saute la plupart des passages programmés de
`update-cr7-goals.yml` (« toutes les 5 min » → ~6 passages par jour observés).
Un but pouvait rester invisible sur le site pendant des heures.

Principe : ce script est lancé souvent (crons + fin d'autres workflows). S'il
trouve un match de Ronaldo en cours ou qui commence dans les WINDOW_H prochaines
heures, il reste actif : il attend le coup d'envoi, interroge ESPN toutes les
POLL_S secondes et déclenche `update-cr7-goals.yml` (workflow_dispatch, qui,
lui, n'est jamais sauté) :
  - à chaque nouveau but de Ronaldo, puis 4 et 10 min après (confirmation ESPN) ;
  - à la fin du match, puis 10 min après.
Sinon il s'arrête en quelques secondes. Le workflow `match-watch.yml` a un
groupe de concurrence : un seul guetteur actif à la fois.

Usage local : python scripts/match_watch.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import espn_client as e  # noqa: E402

WINDOW_H = 5.0            # attendre un coup d'envoi jusqu'à 5 h à l'avance
PRE_KICKOFF_S = 10 * 60   # commencer à interroger 10 min avant
POLL_S = 90
MAX_RUN_S = 5 * 3600 + 40 * 60   # GitHub coupe un job à 6 h
FOLLOW_UPS_GOAL = (240, 600)
FOLLOW_UP_END = 600
REPO = os.environ.get("GITHUB_REPOSITORY", "serhaneomar-Atlas/to1000")
TARGET_WORKFLOW = "update-cr7-goals.yml"


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc):%H:%M:%S}Z] {msg}", flush=True)


def parse_iso(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def dispatch(reason: str, dry_run: bool) -> None:
    if dry_run:
        log(f"(simulation) déclenchement {TARGET_WORKFLOW} — {reason}")
        return
    token = os.environ.get("GITHUB_TOKEN", "")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/actions/workflows/{TARGET_WORKFLOW}/dispatches",
        data=json.dumps({"ref": "main"}).encode(),
        method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            log(f"déclenchement {TARGET_WORKFLOW} ({reason}) → HTTP {r.status}")
    except Exception as x:  # on n'arrête jamais le guet pour un échec ponctuel
        log(f"ÉCHEC déclenchement ({reason}) : {x}")


def cr7_goal_count(m) -> int:
    try:
        d = e.get_match_summary(m.event_id, m.league_slug) if m.league_slug else e.get_match_summary(m.event_id)
    except Exception:
        d = None
    goals = (d.goals if d else None) or m.goals or []
    return sum(1 for g in goals if getattr(g, "is_cr7", False))


def find_target():
    """Match en cours aujourd'hui, sinon prochain match dans la fenêtre."""
    try:
        today = e.find_team_match_today_cr7()
    except Exception as x:
        log(f"ESPN (match du jour) indisponible : {x}")
        today = None
    if today and not today.is_finished:
        return today
    try:
        nxt = e.find_next_match_cr7()
    except Exception as x:
        log(f"ESPN (prochain match) indisponible : {x}")
        return None
    ko = parse_iso(nxt.date_iso) if nxt else None
    if ko and (ko - datetime.now(timezone.utc)).total_seconds() <= WINDOW_H * 3600:
        return nxt
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="n'appelle pas GitHub")
    ap.add_argument("--once", action="store_true", help="un seul passage (test)")
    args = ap.parse_args()
    started = time.time()

    target = find_target()
    if not target:
        log("Aucun match de Ronaldo en cours ni dans les 5 h : fin.")
        return 0
    log(f"Match visé : {target.home_team} – {target.away_team}, coup d'envoi {target.date_iso}")

    ko = parse_iso(target.date_iso)
    if ko and not args.once:
        wait = (ko - datetime.now(timezone.utc)).total_seconds() - PRE_KICKOFF_S
        if wait > 0:
            log(f"Attente du coup d'envoi : {int(wait // 60)} min")
            time.sleep(wait)

    last = None
    pending: list[float] = []
    finished_at = None
    while time.time() - started < MAX_RUN_S:
        try:
            m = e.find_team_match_today_cr7()
        except Exception as x:
            log(f"ESPN indisponible : {x}")
            m = None
        now = time.time()
        if m and str(m.event_id) == str(target.event_id):
            state = (m.score_home, m.score_away, cr7_goal_count(m), bool(m.is_finished))
            if last is None:
                log(f"État initial : {state[0]}-{state[1]}, buts Ronaldo {state[2]}, statut {m.status}")
                if state[2] > 0:   # but marqué avant le démarrage du guet
                    dispatch(f"but(s) de Ronaldo déjà marqué(s), {state[0]}-{state[1]}", args.dry_run)
                    pending += [now + d for d in FOLLOW_UPS_GOAL]
            elif state != last:
                if state[2] > last[2]:
                    dispatch(f"but de Ronaldo, {state[0]}-{state[1]}", args.dry_run)
                    pending += [now + d for d in FOLLOW_UPS_GOAL]
                elif state[3] and not last[3]:
                    dispatch(f"fin du match {state[0]}-{state[1]}", args.dry_run)
                else:
                    log(f"Score {state[0]}-{state[1]} ({m.status})")
            last = state
            if state[3] and finished_at is None:
                finished_at = now
                pending.append(now + FOLLOW_UP_END)
        for t in sorted(t for t in pending if t <= now):
            dispatch("vérification différée", args.dry_run)
            pending.remove(t)
        if args.once:
            break
        if finished_at and not pending:
            log("Match terminé et vérifications faites : fin du guet.")
            break
        time.sleep(POLL_S)
    else:
        log("Durée maximale atteinte : fin du guet (un autre passage prendra le relais).")
        dispatch("relais en fin de durée maximale", args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
