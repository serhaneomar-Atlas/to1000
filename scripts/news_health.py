#!/usr/bin/env python3
"""Vérifie que le fil News du dépôt et le fichier servi sur to1000.com avancent.

Ce contrôle est indépendant du pipeline qui produit news.json : il détecte aussi
les runs planifiés absents, les commits non publiés et les pannes Cloudflare.
Aucun contenu d'article ni secret n'est envoyé dans les alertes.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

DEFAULT_LIVE_URL = "https://to1000.com/news.json"


def parse_utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("horodatage absent")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("horodatage sans fuseau")
    return dt.astimezone(timezone.utc)


def evaluate(repo: dict, live: dict, now: datetime,
             max_age_minutes: int = 150, max_lag_minutes: int = 30) -> list[str]:
    """Retourne les problèmes observables sans interpréter le texte des articles."""
    problems = []
    try:
        repo_at = parse_utc(repo.get("generated_at"))
        live_at = parse_utc(live.get("generated_at"))
    except (ValueError, TypeError) as exc:
        return [f"News : horodatage invalide ({exc})"]
    for label, at in (("dépôt", repo_at), ("site", live_at)):
        age = (now - at).total_seconds() / 60
        if age > max_age_minutes:
            problems.append(f"News {label} obsolète : {int(age)} min depuis le dernier flux")
        elif age < -10:
            problems.append(f"News {label} : horodatage futur incohérent")
    lag = (repo_at - live_at).total_seconds() / 60
    if lag > max_lag_minutes:
        problems.append(f"Déploiement News en retard : {int(lag)} min derrière le dépôt")
    if (repo.get("stats") or {}).get("feeds_fetched") == 0:
        problems.append("Aucun flux RSS n'a été récupéré dans le dernier fil du dépôt")
    if not isinstance(live.get("items"), list):
        problems.append("Le fichier News publié ne contient pas une liste d'articles")
    return problems


def load_live(url: str, now: datetime) -> dict:
    # Le paramètre variable et no-cache évitent une réponse CDN périmée.
    sep = "&" if "?" in url else "?"
    req = Request(f"{url}{sep}health={int(now.timestamp())}", headers={
        "Cache-Control": "no-cache", "User-Agent": "to1000-news-health/1.0",
    })
    with urlopen(req, timeout=20) as response:
        return json.load(response)


def main() -> int:
    ap = argparse.ArgumentParser(description="Contrôle indépendant de la fraîcheur News")
    ap.add_argument("--repo", type=Path, default=Path("public/news.json"))
    ap.add_argument("--live-url", default=DEFAULT_LIVE_URL)
    ap.add_argument("--max-age-minutes", type=int, default=150)
    ap.add_argument("--max-lag-minutes", type=int, default=30)
    args = ap.parse_args()
    now = datetime.now(timezone.utc)
    try:
        repo = json.loads(args.repo.read_text(encoding="utf-8"))
        live = load_live(args.live_url, now)
        problems = evaluate(repo, live, now, args.max_age_minutes,
                            args.max_lag_minutes)
    except (OSError, ValueError, TypeError) as exc:
        problems = [f"Contrôle News impossible : {type(exc).__name__}: {exc}"]
    if problems:
        for problem in problems:
            print(f"::error::{problem}")
        return 1
    print(f"News OK : dépôt et site mis à jour, vérifiés à {now.isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
