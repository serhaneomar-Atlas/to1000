#!/usr/bin/env python3
"""enrich_news.py — le « cerveau » éditorial, DÉCOUPLÉ de la publication.

news-sync publie vite (cache-only, zéro Gemini live → jamais de timeout). Ce
script, lui, prend la news.json publiée et enrichit un PETIT lot d'articles pas
encore passés au rédacteur en chef (engine != "gemini-editor") via Gemini, en
RYTHMANT les appels (sous le free tier) et BORNÉ en temps. Il met à jour
news.json EN PLACE + alimente le cache. news-sync préserve ensuite cet
enrichissement par id (cf. news_aggregator).

→ Publication jamais bloquée, ET la qualité éditoriale monte run après run.
Tourne dans le workflow news-editorial (toutes les ~30 min).
"""
import json
import os
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
ROOT = SCRIPT_DIR.parent
NEWS = ROOT / "public" / "news.json"
CACHE = ROOT / "public" / "translations_cache.json"
SITE_LANGS = ["fr", "en", "es", "ar"]

from translator import Translator  # noqa: E402
from editorial import chief_editor_review  # noqa: E402

BATCH = int(os.environ.get("ENRICH_BATCH", "12"))        # nb d'articles enrichis / run
MAX_S = int(os.environ.get("ENRICH_MAX_SECONDS", "600"))  # plafond temps (sous timeout 15min)


def _engine(item):
    return ((item.get("i18n", {}) or {}).get("fr", {}) or {}).get("engine")


def main():
    if not NEWS.exists():
        print("[enrich] news.json absent — rien à faire")
        return 0
    data = json.loads(NEWS.read_text(encoding="utf-8"))
    items = data.get("items", [])

    tr = Translator(cache_path=CACHE)
    if not tr.gemini_enabled:
        print("[enrich] GEMINI_API_KEY absente — pas d'enrichissement (news-sync publie quand même)")
        return 0

    todo = [it for it in items if _engine(it) != "gemini-editor"]
    print(f"[enrich] {len(todo)}/{len(items)} articles à enrichir · lot={BATCH} · plafond={MAX_S}s")

    t0 = time.monotonic()
    done = 0
    for it in todo:
        if done >= BATCH or (time.monotonic() - t0) >= MAX_S:
            break
        src = (it.get("primary_source") or {}).get("lang", "en")
        src_i18n = (it.get("i18n", {}) or {}).get(src, {}) or {}
        title = src_i18n.get("title") or it.get("title") or ""
        summary = src_i18n.get("summary") or it.get("summary") or ""
        if not title:
            continue
        targets = [l for l in SITE_LANGS if l != src]
        review = chief_editor_review(tr, title, summary, src, targets)
        if review and review.get("i18n"):
            it["i18n"] = {**(it.get("i18n") or {}), **review["i18n"]}
            done += 1

    if done:
        tr.cache.save()
        data["items"] = items
        NEWS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[enrich] {done} enrichis en {int(time.monotonic() - t0)}s · {tr.stats()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
