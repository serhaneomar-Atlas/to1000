"""wc_data.py — couche données de la section /coupe-du-monde/.

Adaptateur source-agnostique :
  - ESPN (défaut) : API publique déjà utilisée par le compteur de buts, sans clé.
    /scoreboard?dates=A-B donne les 104 matchs, le tour via event.season.slug.
  - football-data.org (prioritaire dès que FOOTBALL_DATA_TOKEN est défini —
    clé gratuite à créer par Omar, compétition WC = 2000). Interdit par la spec :
    scraper des sites tiers.

Cache « côté serveur » pour cette stack statique = public/coupe-du-monde/data.json
commité et servi par Cloudflare (même motif que stats.json). Si l'API est
indisponible, on regénère depuis ce cache : jamais de page vide.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .espn_client import _get
from .wc_teams import TEAMS, is_placeholder, team_by_espn_id

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_JSON = PROJECT_DIR / "public" / "coupe-du-monde" / "data.json"

ET = ZoneInfo("America/New_York")   # fuseau de repli demandé (heure de l'Est)
WC_START, WC_END = "20260611", "20260719"

MONTHS_FR = ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
             "août", "septembre", "octobre", "novembre", "décembre"]

ROUNDS_FR = {
    "group-stage": "Phase de groupes",
    "round-of-32": "32es de finale",
    "round-of-16": "Huitièmes de finale",
    "quarterfinals": "Quarts de finale",
    "semifinals": "Demi-finales",
    "third-place-playoff": "Match pour la 3e place",
    "third-place": "Match pour la 3e place",
    "final": "Finale",
}
# Ordre chronologique des tours pour trier le hub.
ROUND_ORDER = ["group-stage", "round-of-32", "round-of-16", "quarterfinals",
               "semifinals", "third-place-playoff", "third-place", "final"]


def _dt_et(date_iso: str) -> datetime:
    return datetime.fromisoformat(date_iso.replace("Z", "+00:00")).astimezone(ET)


def date_fr_et(date_iso: str) -> str:
    d = _dt_et(date_iso)
    return f"{d.day} {MONTHS_FR[d.month]} {d.year}"


def time_fr_et(date_iso: str) -> str:
    d = _dt_et(date_iso)
    return f"{d.hour} h {d.minute:02d}"


def match_slug(home_slug: str, away_slug: str, date_iso: str) -> str:
    d = _dt_et(date_iso)
    return f"{home_slug}-vs-{away_slug}-{d.day}-{MONTHS_FR[d.month]}-{d.year}"


def round_label(round_slug: str) -> str:
    return ROUNDS_FR.get(round_slug, round_slug)


def _state(status_name: str) -> str:
    if "FULL_TIME" in status_name or "FINAL" in status_name:
        return "finished"
    if status_name in ("STATUS_SCHEDULED", "STATUS_POSTPONED", "STATUS_DELAYED", ""):
        return "scheduled"
    return "live"


def _fetch_espn() -> list[dict]:
    data = _get("https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/"
                f"scoreboard?dates={WC_START}-{WC_END}&limit=300")
    out = []
    for ev in data.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        comps = comp.get("competitors", [])
        home = next((c for c in comps if c.get("homeAway") == "home"), {})
        away = next((c for c in comps if c.get("homeAway") == "away"), {})

        def _team(c):
            t = c.get("team", {}) or {}
            return {"espn_id": str(t.get("id", "")), "name_en": t.get("displayName", "")}

        def _score(c):
            s = c.get("score")
            try:
                return int(s) if s not in (None, "", "-") else None
            except (TypeError, ValueError):
                return None

        status = ((ev.get("status") or {}).get("type") or {}).get("name", "")
        venue = comp.get("venue") or {}
        note = (comp.get("notes") or [{}])
        out.append({
            "id": str(ev.get("id", "")),
            "date_iso": ev.get("date", ""),
            "round": (ev.get("season") or {}).get("slug", ""),
            "home": _team(home), "away": _team(away),
            "score_home": _score(home), "score_away": _score(away),
            "state": _state(status),
            "status_note": note[0].get("headline", "") if note else "",
            "venue": venue.get("fullName", ""),
            "city": (venue.get("address") or {}).get("city", ""),
            "country": (venue.get("address") or {}).get("country", ""),
        })
    return out


def _fetch_football_data(token: str) -> list[dict]:
    """football-data.org v4 — compétition 2000 (FIFA World Cup)."""
    import requests
    r = requests.get("https://api.football-data.org/v4/competitions/2000/matches",
                     headers={"X-Auth-Token": token}, timeout=15)
    r.raise_for_status()
    stage_map = {"GROUP_STAGE": "group-stage", "LAST_32": "round-of-32",
                 "LAST_16": "round-of-16", "QUARTER_FINALS": "quarterfinals",
                 "SEMI_FINALS": "semifinals", "THIRD_PLACE": "third-place",
                 "FINAL": "final"}
    state_map = {"FINISHED": "finished", "IN_PLAY": "live", "PAUSED": "live"}
    out = []
    for m in r.json().get("matches", []):
        ft = (m.get("score") or {}).get("fullTime") or {}
        out.append({
            "id": f"fd-{m.get('id')}",
            "date_iso": m.get("utcDate", ""),
            "round": stage_map.get(m.get("stage", ""), m.get("stage", "").lower()),
            # tla ≠ id ESPN : le matching se fait par nom EN dans enrich().
            "home": {"espn_id": "", "name_en": (m.get("homeTeam") or {}).get("name", "")},
            "away": {"espn_id": "", "name_en": (m.get("awayTeam") or {}).get("name", "")},
            "score_home": ft.get("home"), "score_away": ft.get("away"),
            "state": state_map.get(m.get("status", ""), "scheduled"),
            "status_note": "",
            "venue": m.get("venue", "") or "",
            "city": "", "country": "",
        })
    return out


def _enrich(matches: list[dict]) -> list[dict]:
    """Ajoute nom FR / slug / drapeau à chaque équipe + slug d'URL du match."""
    by_en = {t["en"]: t for t in TEAMS.values()}
    for m in matches:
        for side in ("home", "away"):
            t = m[side]
            info = team_by_espn_id(t.get("espn_id", "")) or by_en.get(t.get("name_en", ""))
            t["placeholder"] = is_placeholder(t.get("name_en", "")) or not info
            if info:
                t.update({"fr": info["fr"], "slug": info["slug"], "iso2": info["iso2"]})
            else:
                t.update({"fr": t.get("name_en", "À déterminer"), "slug": "", "iso2": ""})
        if not m["home"]["placeholder"] and not m["away"]["placeholder"]:
            m["slug"] = match_slug(m["home"]["slug"], m["away"]["slug"], m["date_iso"])
        else:
            m["slug"] = ""
    return matches


def is_live_window(matches: list[dict], now: datetime) -> bool:
    """Vrai si un match non terminé est entre kickoff-20 min et kickoff+3 h 30
    (90' + prolongations + tirs au but). Le cron */5 n'agit que dans ce cas
    pour économiser les minutes GitHub Actions hors matchs."""
    from datetime import timedelta
    for m in matches:
        if m.get("state") == "finished" or not m.get("date_iso"):
            continue
        try:
            ko = datetime.fromisoformat(m["date_iso"].replace("Z", "+00:00"))
        except ValueError:
            continue
        if ko - timedelta(minutes=20) <= now <= ko + timedelta(hours=3, minutes=30):
            return True
    return False


def load_cache() -> list[dict] | None:
    try:
        return json.loads(DATA_JSON.read_text(encoding="utf-8"))["matches"]
    except Exception:
        return None


def save_cache(matches: list[dict]) -> None:
    DATA_JSON.parent.mkdir(parents=True, exist_ok=True)
    DATA_JSON.write_text(json.dumps(
        {"generated_at": datetime.utcnow().isoformat() + "Z", "matches": matches},
        ensure_ascii=False, indent=1), encoding="utf-8")


def fetch_matches() -> list[dict]:
    """Source prioritaire → fallback → cache. Ne retourne jamais None si un cache existe."""
    token = os.environ.get("FOOTBALL_DATA_TOKEN", "").strip()
    sources = ([lambda: _fetch_football_data(token)] if token else []) + [_fetch_espn]
    for src in sources:
        try:
            matches = _enrich(src())
            if matches:
                matches.sort(key=lambda m: m["date_iso"])
                save_cache(matches)
                return matches
        except Exception as e:
            print(f"  ⚠ source matchs échouée ({src.__name__}): {e}")
    cached = load_cache()
    if cached is not None:
        print("  ⚠ API indisponible → dernier cache servi")
        return cached
    raise RuntimeError("aucune source de matchs disponible et pas de cache")
