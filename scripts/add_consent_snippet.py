#!/usr/bin/env python3
"""add_consent_snippet.py — injecte /consent.js avant le loader GA4 sur toutes les pages.

Consent Mode v2 : les défauts de consentement (denied) doivent être poussés dans
dataLayer AVANT que gtag.js ne s'initialise, sinon GA4 dépose ses cookies sans
consentement (non conforme RGPD, et bloquant pour AdSense en UE). consent.js est
donc chargé en SYNCHRONE juste avant le <script async ...gtag/js...>.

Idempotent : relançable sans doublon. Utilisé en one-shot pour les ~2400 pages
existantes ; les templates (news_to_html.py) génèrent le tag nativement ensuite.

Usage :  python add_consent_snippet.py [--dry-run]
"""
from __future__ import annotations

import sys
from pathlib import Path

PUB = Path(__file__).resolve().parent.parent / "public"
CONSENT_TAG = '<script src="/consent.js"></script>'
GTAG_LOADER_PREFIX = '<script async src="https://www.googletagmanager.com/gtag/js'


def inject_consent(html: str) -> tuple[str, bool]:
    """Insère CONSENT_TAG juste avant le loader gtag. Retourne (html, changé)."""
    if CONSENT_TAG in html:
        return html, False
    pos = html.find(GTAG_LOADER_PREFIX)
    if pos == -1:
        return html, False
    return html[:pos] + CONSENT_TAG + "\n" + html[pos:], True


def main() -> int:
    dry = "--dry-run" in sys.argv
    changed = skipped = already = 0
    for f in sorted(PUB.rglob("*.html")):
        html = f.read_text(encoding="utf-8")
        out, did = inject_consent(html)
        if did:
            changed += 1
            if not dry:
                f.write_text(out, encoding="utf-8")
        elif CONSENT_TAG in html:
            already += 1
        else:
            skipped += 1
    print(f"[consent] {changed} pages injectées · {already} déjà faites · {skipped} sans gtag"
          + (" (dry-run)" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
