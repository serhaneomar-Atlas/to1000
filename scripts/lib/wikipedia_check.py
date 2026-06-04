"""
wikipedia_check.py — Cross-check hebdomadaire du total de buts CR7 contre Wikipedia

Source : page "List of career achievements by Cristiano Ronaldo"
URL    : https://en.wikipedia.org/wiki/List_of_career_achievements_by_Cristiano_Ronaldo

Wikipedia est mis à jour très rapidement après chaque but (souvent dans l'heure).
On parse le résumé (REST API summary), qui contient une phrase du type :
    "He has scored a record 971 senior career goals"

But du module : détecter une dérive entre stats.json et la réalité,
sans rien casser même si Wikipedia change le wording.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
import requests

WIKI_PAGE = "List_of_career_achievements_by_Cristiano_Ronaldo"
WIKI_FALLBACK = "Cristiano_Ronaldo"
WIKI_API = f"https://en.wikipedia.org/api/rest_v1/page/summary/{WIKI_PAGE}"
WIKI_API_FALLBACK = f"https://en.wikipedia.org/api/rest_v1/page/summary/{WIKI_FALLBACK}"

USER_AGENT = "to1000-bot/1.0 (+https://to1000.com; cross-check CR7 goals)"
DEFAULT_TIMEOUT = 8

# Patterns par ordre de spécificité décroissante
# On veut un nombre 3-4 chiffres entre 800 et 1200 (tolère un peu de marge)
PATTERNS = [
    r"(?:scored|recorded|reached)\s+(?:a\s+record\s+)?(\d{3,4})\s+senior\s+career\s+goals?",
    r"(\d{3,4})\s+senior\s+career\s+goals?",
    r"career\s+total\s+of\s+(\d{3,4})\s+goals?",
    r"(\d{3,4})\s+(?:career\s+)?goals?\s+for\s+club\s+and\s+country",
]

# Borne de plausibilité — éviter de matcher "143 international goals", "100 SPL goals", etc.
MIN_PLAUSIBLE = 850
MAX_PLAUSIBLE = 1100


@dataclass
class WikiCheckResult:
    parsed_total: int | None
    stats_total: int
    delta: int | None              # parsed - stats (None si pas de match)
    severity: str                  # "ok", "warn", "alert", "unknown"
    message: str
    raw_extract: str               # tronqué à 400 chars pour log


def _fetch_extract(url: str) -> str | None:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return r.json().get("extract", "")
    except Exception:
        return None


def _extract_total(text: str) -> int | None:
    """Cherche la première occurrence plausible (entre 850 et 1100)."""
    for pat in PATTERNS:
        for m in re.finditer(pat, text, flags=re.I):
            try:
                n = int(m.group(1))
            except ValueError:
                continue
            if MIN_PLAUSIBLE <= n <= MAX_PLAUSIBLE:
                return n
    return None


def cross_check(stats_total: int, *, tolerance: int = 1) -> WikiCheckResult:
    """
    Compare stats.json['goals'] avec Wikipedia.

    Sévérité :
      - ok      : delta == 0
      - warn    : |delta| <= tolerance (tolère un décalage minute après un match)
      - alert   : |delta| > tolerance — quelque chose cloche
      - unknown : n'a pas pu parser (ne pas paniquer, juste log)
    """
    extract = _fetch_extract(WIKI_API) or _fetch_extract(WIKI_API_FALLBACK) or ""
    if not extract:
        return WikiCheckResult(
            parsed_total=None,
            stats_total=stats_total,
            delta=None,
            severity="unknown",
            message="Wikipedia inaccessible — cross-check skipped",
            raw_extract="",
        )

    parsed = _extract_total(extract)
    if parsed is None:
        return WikiCheckResult(
            parsed_total=None,
            stats_total=stats_total,
            delta=None,
            severity="unknown",
            message="Could not parse goal total from Wikipedia extract — pattern may have changed",
            raw_extract=extract[:400],
        )

    delta = parsed - stats_total
    if delta == 0:
        sev, msg = "ok", f"Wikipedia confirme {parsed} buts (parfait)"
    elif abs(delta) <= tolerance:
        sev, msg = "warn", f"Léger décalage : Wiki={parsed}, stats={stats_total} (delta={delta:+d})"
    else:
        sev, msg = "alert", f"DÉRIVE : Wiki={parsed}, stats={stats_total} (delta={delta:+d})"

    return WikiCheckResult(
        parsed_total=parsed,
        stats_total=stats_total,
        delta=delta,
        severity=sev,
        message=msg,
        raw_extract=extract[:400],
    )


def _smoke_test() -> int:
    """Vérifie le parsing actuel."""
    res = cross_check(stats_total=971)
    print(f"Severity : {res.severity}")
    print(f"Message  : {res.message}")
    print(f"Wiki     : {res.parsed_total}")
    print(f"Stats    : {res.stats_total}")
    print(f"Delta    : {res.delta}")
    print()
    print("Extract (400c):")
    print(res.raw_extract)
    # Le smoke test passe si on a au moins parsé un nombre plausible
    return 0 if res.parsed_total is not None else 1


if __name__ == "__main__":
    import sys
    sys.exit(_smoke_test())
