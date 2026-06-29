"""
espn_client.py — Client ESPN public pour le watcher CR7

Version : 2026-05-16-multi-league
Modifié le 2026-05-16 pour ajouter le support multi-ligue (SPL + AFC Cup) suite
à la finale Al Nassr vs Gamba Osaka. Force-bump du mtime pour invalider pycache.

Utilise l'API publique site.api.espn.com (pas de clé requise, pas de quota visible).

Endpoints couverts :
  - GET /scoreboard         → matchs du jour (Saudi Pro League)
  - GET /teams/{id}/schedule → calendrier complet de l'équipe
  - GET /summary?event={id}  → détail d'un match (buteurs, minutes, cartons)

IDs ESPN connus :
  - League "ksa.1" = Saudi Pro League
  - Team 817      = Al Nassr
  - Team 793      = Al Shabab
  - Team 22022    = Al Qadsiah
  - Athlete 22774 = Cristiano Ronaldo
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import requests

# ─── CONSTANTES ────────────────────────────────────────────────────────────
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
ESPN_BASE_ALT = "https://site.web.api.espn.com/apis/site/v2/sports/soccer"
SAUDI_PL = "ksa.1"
AFC_CUP = "afc.cup"   # AFC Champions League Two (ex AFC Cup)
# Ordre = priorité de tie-break. SPL d'abord car saison régulière, AFC ensuite.
# Fix 2026-05-16 : ajout AFC_CUP suite à la finale Al Nassr vs Gamba Osaka qui
# n'était pas captée. Si CR7 joue un jour CWC ou amicaux il faudra étendre.
AL_NASSR_LEAGUES = [SAUDI_PL, AFC_CUP]
AL_NASSR_ID = 817
CR7_ATHLETE_ID = 22774
TARGET_GOALS = 1000

# Fix 2026-06-05 : suivi de la sélection du Portugal (amicaux + Coupe du Monde 2026).
# Le but 974+ peut tomber avec le Portugal (Chili 6/6, Nigéria 10/6, puis WC dès le 11/6).
# ATTENTION : l'endpoint /teams/{id}/schedule d'ESPN est INCOMPLET pour les sélections
# (les amicaux de juin n'y figurent pas) → on passe par /scoreboard?dates=YYYYMMDD-YYYYMMDD.
PORTUGAL_ID = 482
PORTUGAL_LEAGUES = ["fifa.friendly", "fifa.world", "uefa.nations", "fifa.worldq.uefa"]
# IDs (str) des équipes de CR7 — pour les checks is_home côté consommateurs.
CR7_TEAM_IDS = {str(AL_NASSR_ID), str(PORTUGAL_ID)}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 8     # secondes
DEFAULT_RETRIES = 2     # tentatives en plus en cas d'erreur réseau


# ─── DATACLASSES ───────────────────────────────────────────────────────────
@dataclass
class GoalEvent:
    """Représente un but extrait des keyEvents ESPN."""
    event_id: str             # ex "47647104" — unique, sert d'anti-doublon
    match_id: str             # ex "756196"
    minute: str               # ex "75'" ou "90'+8'"
    minute_int: int           # ex 75 ou 98 (utilisé pour tri/log)
    period: int               # 1 ou 2
    scorer_id: str            # ex "22774"
    scorer_name: str          # ex "Cristiano Ronaldo"
    team_name: str            # ex "Al Nassr"
    is_cr7: bool
    raw_text: str             # ex "Cristiano Ronaldo (Al Nassr) Goal at 75'"


@dataclass
class MatchSummary:
    """Résumé d'un match utile pour stats.json."""
    event_id: str
    date_iso: str             # ex "2026-05-07T18:00:00Z"
    competition: str          # ex "Saudi Pro League"
    home_team: str
    away_team: str
    home_team_id: str
    away_team_id: str
    score_home: int | None    # None si match pas commencé
    score_away: int | None
    venue: str
    status: str               # ex "STATUS_FULL_TIME", "STATUS_SCHEDULED"
    is_finished: bool
    is_in_progress: bool
    goals: list[GoalEvent]
    league_slug: str = ""     # Fix 2026-05-17 : ex "ksa.1" ou "afc.cup" — pour re-fetch via get_match_summary


# ─── HTTP HELPER ───────────────────────────────────────────────────────────
def _get(url: str, *, timeout: int = DEFAULT_TIMEOUT, retries: int = DEFAULT_RETRIES) -> dict[str, Any]:
    """GET JSON avec User-Agent et retry simple."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"ESPN GET failed after {retries + 1} attempts: {url} | {last_err}")


# ─── PARSING ───────────────────────────────────────────────────────────────
def _parse_minute(display_value: str) -> int:
    """Convertit '75'' en 75, '90'+8'' en 98."""
    if not display_value:
        return 0
    s = display_value.strip().rstrip("'")
    if "+" in s:
        base, extra = s.split("+", 1)
        try:
            return int(base.rstrip("'")) + int(extra.rstrip("'"))
        except ValueError:
            return 0
    try:
        return int(s)
    except ValueError:
        return 0


def _key_event_to_goal(ev: dict[str, Any], match_id: str) -> GoalEvent | None:
    """Convertit un keyEvent ESPN en GoalEvent si c'est bien un but."""
    type_text = ev.get("type", {}).get("text", "")
    if "Goal" not in type_text:
        return None
    parts = ev.get("participants", [])
    if not parts:
        return None
    ath = parts[0].get("athlete", {}) or {}
    scorer_id = str(ath.get("id", ""))
    scorer_name = ath.get("displayName", "")
    minute_str = ev.get("clock", {}).get("displayValue", "")
    return GoalEvent(
        event_id=str(ev.get("id", "")),
        match_id=match_id,
        minute=minute_str,
        minute_int=_parse_minute(minute_str),
        period=int(ev.get("period", {}).get("number", 0) or 0),
        scorer_id=scorer_id,
        scorer_name=scorer_name,
        team_name=ev.get("team", {}).get("displayName", ""),
        is_cr7=(scorer_id == str(CR7_ATHLETE_ID)),
        raw_text=ev.get("text", ""),
    )


def _competition_to_summary(comp: dict[str, Any], status_obj: dict[str, Any], date_iso: str, comp_name: str) -> MatchSummary:
    """Construit un MatchSummary depuis l'objet competition d'un event scoreboard/schedule."""
    competitors = comp.get("competitors", [])
    home = next((c for c in competitors if c.get("homeAway") == "home"), {})
    away = next((c for c in competitors if c.get("homeAway") == "away"), {})

    def _score(c: dict[str, Any]) -> int | None:
        s = c.get("score")
        if isinstance(s, dict):
            v = s.get("value")
            try:
                return int(v) if v is not None else None
            except (TypeError, ValueError):
                return None
        try:
            return int(s) if s not in (None, "", "-") else None
        except (TypeError, ValueError):
            return None

    state = (status_obj.get("type") or {}).get("name", "")
    return MatchSummary(
        event_id=str(comp.get("id", "")),
        date_iso=date_iso,
        competition=comp_name,
        home_team=home.get("team", {}).get("displayName", ""),
        away_team=away.get("team", {}).get("displayName", ""),
        home_team_id=str(home.get("team", {}).get("id", "") or home.get("id", "")),
        away_team_id=str(away.get("team", {}).get("id", "") or away.get("id", "")),
        score_home=_score(home),
        score_away=_score(away),
        venue=(comp.get("venue") or {}).get("fullName", ""),
        status=state,
        is_finished=(state in ("STATUS_FULL_TIME", "STATUS_FINAL")),
        is_in_progress=state in ("STATUS_IN_PROGRESS", "STATUS_HALFTIME", "STATUS_FIRST_HALF", "STATUS_SECOND_HALF"),
        goals=[],
    )


# ─── ENDPOINTS PUBLICS ─────────────────────────────────────────────────────
def get_today_scoreboard(league: str = SAUDI_PL) -> list[MatchSummary]:
    """Tous les matchs du jour pour la ligue donnée."""
    data = _get(f"{ESPN_BASE}/{league}/scoreboard")
    league_name = (data.get("leagues") or [{}])[0].get("name", league)
    out: list[MatchSummary] = []
    for ev in data.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        out.append(_competition_to_summary(
            comp, ev.get("status", {}), ev.get("date", ""), league_name
        ))
    return out


def get_team_schedule(team_id: int = AL_NASSR_ID, league: str = SAUDI_PL) -> list[MatchSummary]:
    """Calendrier complet de l'équipe (passé + futur)."""
    # /site.web.api.espn.com expose le schedule détaillé ; l'autre host renvoie une variante moins riche
    data = _get(f"{ESPN_BASE_ALT}/{league}/teams/{team_id}/schedule")
    league_name = league
    out: list[MatchSummary] = []
    for ev in data.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        # La ligue propre à l'event est plus précise (Coupe, AFC, etc.)
        ev_league = ev.get("league", {}).get("name") or league_name
        out.append(_competition_to_summary(
            comp, ev.get("status", {}), ev.get("date", ""), ev_league
        ))
    return out


def get_match_summary(event_id: str | int, league: str = SAUDI_PL) -> MatchSummary | None:
    """Détail d'un match, avec liste des buteurs et minutes."""
    data = _get(f"{ESPN_BASE}/{league}/summary?event={event_id}")
    hdr = data.get("header") or {}
    if not hdr:
        return None
    comp = (hdr.get("competitions") or [{}])[0]
    status_obj = comp.get("status") or hdr.get("status") or {}
    summary = _competition_to_summary(
        comp,
        status_obj,
        hdr.get("competitions", [{}])[0].get("date", "") or hdr.get("competitions", [{}])[0].get("startDate", ""),
        (data.get("league") or {}).get("name") or hdr.get("league", {}).get("name", "")
    )
    summary.event_id = str(event_id)
    # Extraire les buts depuis keyEvents
    goals: list[GoalEvent] = []
    for ev in data.get("keyEvents", []):
        g = _key_event_to_goal(ev, str(event_id))
        if g is not None:
            goals.append(g)
    summary.goals = goals
    return summary


def _aggregate_schedule(team_id: int, leagues: list[str]) -> list[MatchSummary]:
    """Aggrège le schedule de l'équipe sur plusieurs ligues, en dédupliquant par event_id.
    Fix 2026-05-16 : ESPN sépare SPL et compétitions continentales (AFC Cup) sur
    des endpoints distincts ; sans aggrégation, find_next_match ratait les finales
    de coupe d'Asie (ex. Al Nassr vs Gamba Osaka le 16 mai 2026)."""
    seen: set[str] = set()
    out: list[MatchSummary] = []
    for lg in leagues:
        try:
            for m in get_team_schedule(team_id, lg):
                key = str(m.event_id or "")
                if key and key in seen:
                    continue
                seen.add(key)
                # Tag la ligue d'origine pour les appels summary plus tard
                m.competition = m.competition or lg
                m.league_slug = lg   # Fix 2026-05-17 : permet à refresh_last_match de re-fetcher dans la bonne ligue
                out.append(m)
        except Exception:
            # Ligue inexistante / hors-saison pour cette équipe : on continue.
            continue
    return out


def find_last_match(team_id: int = AL_NASSR_ID, league: str | None = None) -> MatchSummary | None:
    """Dernier match terminé de l'équipe, toutes compétitions confondues."""
    leagues = [league] if league else AL_NASSR_LEAGUES
    schedule = _aggregate_schedule(team_id, leagues)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    past = [m for m in schedule if m.date_iso and m.date_iso < now]
    if not past:
        return None
    past.sort(key=lambda m: m.date_iso)
    return past[-1]


def find_next_match(team_id: int = AL_NASSR_ID, league: str | None = None) -> MatchSummary | None:
    """Prochain match planifié de l'équipe, toutes compétitions confondues."""
    leagues = [league] if league else AL_NASSR_LEAGUES
    schedule = _aggregate_schedule(team_id, leagues)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    future = [m for m in schedule if m.date_iso and m.date_iso >= now]
    if not future:
        return None
    future.sort(key=lambda m: m.date_iso)
    return future[0]


def find_team_match_today(team_id: int = AL_NASSR_ID, league: str | None = None) -> MatchSummary | None:
    """S'il y a un match de l'équipe aujourd'hui, retourne son MatchSummary détaillé.
    Fix 2026-05-16 : itère sur AL_NASSR_LEAGUES si aucun league explicite, pour
    capter aussi les matchs continentaux (ex. finale ACL Two)."""
    leagues = [league] if league else AL_NASSR_LEAGUES
    today_local_date = datetime.now(timezone.utc).date()
    for lg in leagues:
        try:
            sb = get_today_scoreboard(lg)
        except Exception:
            continue
        for m in sb:
            if not m.date_iso:
                continue
            try:
                d = datetime.fromisoformat(m.date_iso.replace("Z", "+00:00")).date()
            except ValueError:
                continue
            if d != today_local_date:
                continue
            if m.home_team_id == str(team_id) or m.away_team_id == str(team_id):
                # Charger le détail complet (avec buteurs) sur la bonne ligue
                detail = get_match_summary(m.event_id, lg)
                if detail:
                    return detail
    return None


# ─── PORTUGAL / MULTI-ÉQUIPE CR7 ───────────────────────────────────────────
# Fix 2026-06-05 : le site ne suivait qu'Al Nassr. Avec les amicaux du Portugal
# (Chili 6/6, Nigéria 10/6) et la Coupe du Monde 2026 (dès le 11/6), les buts
# 974+ peuvent tomber en sélection. Les fonctions *_cr7() combinent les deux.

def get_scoreboard_range(league: str, start_yyyymmdd: str, end_yyyymmdd: str) -> list[MatchSummary]:
    """Matchs d'une ligue sur une plage de dates via /scoreboard?dates=A-B.
    Nécessaire pour les sélections : /teams/{id}/schedule est incomplet
    (les amicaux de juin 2026 du Portugal n'y apparaissent pas)."""
    data = _get(f"{ESPN_BASE}/{league}/scoreboard?dates={start_yyyymmdd}-{end_yyyymmdd}&limit=300")
    league_name = (data.get("leagues") or [{}])[0].get("name", league)
    out: list[MatchSummary] = []
    for ev in data.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        m = _competition_to_summary(comp, ev.get("status", {}), ev.get("date", ""), league_name)
        if not m.event_id:
            m.event_id = str(ev.get("id", ""))
        m.league_slug = league
        out.append(m)
    return out


def _portugal_matches(days_back: int = 14, days_fwd: int = 60) -> list[MatchSummary]:
    """Matchs du Portugal (passés récents + futurs) toutes compétitions, dédupliqués."""
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days_back)).strftime("%Y%m%d")
    end = (now + timedelta(days=days_fwd)).strftime("%Y%m%d")
    seen: set[str] = set()
    out: list[MatchSummary] = []
    for lg in PORTUGAL_LEAGUES:
        try:
            for m in get_scoreboard_range(lg, start, end):
                if str(PORTUGAL_ID) not in (m.home_team_id, m.away_team_id):
                    continue
                key = str(m.event_id or "")
                if key and key in seen:
                    continue
                seen.add(key)
                out.append(m)
        except Exception:
            # Ligue hors-saison / indisponible : on continue.
            continue
    return out


def find_next_match_cr7() -> MatchSummary | None:
    """Prochain match de CR7, club (Al Nassr) OU sélection (Portugal) — le plus proche."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    candidates: list[MatchSummary] = []
    nm = find_next_match(AL_NASSR_ID)
    if nm:
        candidates.append(nm)
    candidates.extend(m for m in _portugal_matches() if m.date_iso and m.date_iso >= now)
    if not candidates:
        return None
    candidates.sort(key=lambda m: m.date_iso)
    return candidates[0]


def find_last_match_cr7() -> MatchSummary | None:
    """Dernier match joué par CR7, club OU sélection — le plus récent."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    candidates: list[MatchSummary] = []
    lm = find_last_match(AL_NASSR_ID)
    if lm:
        candidates.append(lm)
    candidates.extend(m for m in _portugal_matches() if m.date_iso and m.date_iso < now)
    if not candidates:
        return None
    candidates.sort(key=lambda m: m.date_iso)
    return candidates[-1]


def find_team_match_today_cr7() -> MatchSummary | None:
    """Match du jour de CR7 : Al Nassr d'abord, sinon Portugal."""
    m = find_team_match_today(AL_NASSR_ID)
    if m is not None:
        return m
    return _portugal_match_today()


def _portugal_match_today() -> MatchSummary | None:
    """Match du Portugal aujourd'hui (détaillé, avec buteurs), sinon None."""
    today = datetime.now(timezone.utc).date()
    for lg in PORTUGAL_LEAGUES:
        try:
            sb = get_today_scoreboard(lg)
        except Exception:
            continue
        for m in sb:
            if not m.date_iso:
                continue
            try:
                d = datetime.fromisoformat(m.date_iso.replace("Z", "+00:00")).date()
            except ValueError:
                continue
            if d != today:
                continue
            if str(PORTUGAL_ID) in (m.home_team_id, m.away_team_id):
                detail = get_match_summary(m.event_id, lg)
                if detail:
                    detail.league_slug = lg
                    return detail
    return None


# ─── SMOKE TEST ────────────────────────────────────────────────────────────
def _smoke_test() -> int:
    """Vérifie que les 3 endpoints répondent. Retourne 0 si OK, 1 sinon."""
    try:
        sb = get_today_scoreboard()
        print(f"[OK] scoreboard: {len(sb)} match(s) aujourd'hui")
        for m in sb:
            print(f"     {m.away_team} @ {m.home_team} | {m.score_away}-{m.score_home} | {m.status}")

        sched = get_team_schedule()
        print(f"[OK] schedule Al Nassr: {len(sched)} match(s) au total")

        # Match-test connu : 7 mai 2026 vs Al Shabab
        ms = get_match_summary(756196)
        if ms is None:
            print("[KO] summary 756196 retourne None")
            return 1
        cr7_goals = [g for g in ms.goals if g.is_cr7]
        print(f"[OK] summary 756196: {len(ms.goals)} but(s), dont {len(cr7_goals)} CR7")
        for g in cr7_goals:
            print(f"     CR7: min {g.minute} | event_id={g.event_id} | match_id={g.match_id}")
        if not cr7_goals:
            print("[WARN] aucun but CR7 détecté dans 756196 — anomalie")
            return 1
        if cr7_goals[0].minute_int != 75:
            print(f"[WARN] CR7 attendu 75' mais détecté {cr7_goals[0].minute_int}'")
        return 0
    except Exception as e:
        print(f"[KO] smoke test failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(_smoke_test())
