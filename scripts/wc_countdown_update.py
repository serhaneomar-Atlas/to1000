#!/usr/bin/env python3
"""
wc_countdown_update.py — Maintient public/wc.json à jour.

Aujourd'hui le countdown est statique côté front (JS calcule depuis la date target).
Ce script sert à :
  1. Mettre à jour le `last_updated`
  2. À terme : fetcher standings live depuis FIFA/ESPN une fois la WC commencée
  3. Mettre à jour les next_match Maroc/Portugal au fur et à mesure (1/16, 1/8, etc.)

Pour l'instant, version minimaliste — refresh du timestamp + cohérence basique.
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
WC_JSON = PROJECT_DIR / "public" / "wc.json"


def main():
    if not WC_JSON.exists():
        print(f"⚠ {WC_JSON} introuvable")
        return 1
    with open(WC_JSON, encoding="utf-8") as f:
        data = json.load(f)

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    old = data.get("last_updated")
    data["last_updated"] = now_iso

    # Calcul du prochain match Maroc/Portugal pour faciliter le front
    now = datetime.now(timezone.utc)

    def next_upcoming(fixtures: list) -> dict | None:
        upcoming = []
        for f in fixtures or []:
            try:
                dt = datetime.fromisoformat(f.get("date_utc", "").replace("Z", "+00:00"))
                if dt > now:
                    upcoming.append((dt, f))
            except Exception:
                pass
        upcoming.sort(key=lambda x: x[0])
        return upcoming[0][1] if upcoming else None

    data["morocco_next"] = next_upcoming(data.get("morocco_fixtures", []))
    data["portugal_next"] = next_upcoming(data.get("portugal_fixtures", []))

    # Days until kickoff (informatif)
    try:
        opening = datetime.fromisoformat(data["opening_match"]["kickoff_utc"].replace("Z", "+00:00"))
        days = (opening - now).days
        data["days_to_opening"] = max(0, days)
    except Exception:
        data["days_to_opening"] = None

    with open(WC_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ wc.json updated. Days to opening: {data.get('days_to_opening')}, last_updated: {now_iso}")
    print(f"   morocco_next: {(data.get('morocco_next') or {}).get('opponent', 'n/a')}")
    print(f"   portugal_next: {(data.get('portugal_next') or {}).get('opponent', 'n/a')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
