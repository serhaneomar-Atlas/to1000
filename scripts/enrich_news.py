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

Résilience : chaque item est traité dans son propre périmètre d'erreur. Le
20/08, un NameError dans translator.py a tué 24 runs d'affilée parce qu'UN
item cassé annulait tout le lot — plus jamais : un item qui explose est
signalé et sauté, le reste du lot continue, et le travail déjà fait est sauvé.
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

BATCH = int(os.environ.get("ENRICH_BATCH", "50"))        # palier payant : on enrichit TOUS les articles d'un run
MAX_S = int(os.environ.get("ENRICH_MAX_SECONDS", "600"))  # plafond temps (sous timeout 15min)


def _engine(item):
    return ((item.get("i18n", {}) or {}).get("fr", {}) or {}).get("engine")


def _traiter(it: dict, tr: Translator) -> tuple[bool, bool, bool]:
    """Un item de bout en bout : (appel_fait, item_modifié, écarté).

    Toute exception est confinée par l'appelant — jamais fatale au lot.
    """
    src = (it.get("primary_source") or {}).get("lang", "en")
    src_i18n = (it.get("i18n", {}) or {}).get(src, {}) or {}
    title = src_i18n.get("title") or it.get("title") or ""
    summary = src_i18n.get("summary") or it.get("summary") or ""
    if not title:
        return False, False, False
    targets = [l for l in SITE_LANGS if l != src]

    before = tr._calls_gemini
    modified = False
    ecarte = False
    review = chief_editor_review(tr, title, summary, src, targets,
                                 url=it.get("url", ""))

    if review and review.get("i18n"):
        merged = {**(it.get("i18n") or {}), **review["i18n"]}
        if merged != it.get("i18n"):
            it["i18n"] = merged
            modified = True
    elif review is not None and not review.get("publish"):
        # Le rédacteur en chef écarte l'article de la Une — mais il reste
        # dans le fil. Le laisser en traduction MyMemory mot-à-mot, c'est
        # publier « Royal Madrid » : on lui donne au moins une traduction
        # Gemini propre (un appel, pas la chaîne complète).
        ecarte = True
        if _engine(it) not in ("gemini-edi", "gemini-editor"):
            pack = tr.editorialize_pair(title, summary, src, targets)
            if pack:
                merged = {**(it.get("i18n") or {}), **pack}
                if merged != it.get("i18n"):
                    it["i18n"] = merged
                    modified = True

    if review is not None:
        ed_prev = it.get("editorial") or {}
        ed = {**ed_prev,
              "publish": bool(review.get("publish")),
              "quality": review.get("quality", 0),
              "source_read": review.get("source_read", "rss")}
        if it.get("editorial") != ed:
            it["editorial"] = ed
            modified = True

    return tr._calls_gemini > before, modified, ecarte


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

    # On parcourt TOUS les articles : le cache dédoublonne — un hit est
    # gratuit (idempotent), un miss = 1 appel Gemini. Le budget porte sur les
    # VRAIS appels → ré-enrichit aussi les anciens résumés vers le style
    # courant, sur plusieurs runs, sans jamais dépasser le quota ni le timeout.
    print(f"[enrich] {len(items)} articles · budget {BATCH} appels Gemini · plafond {MAX_S}s")
    t0 = time.monotonic()
    new_calls = 0
    touched = 0
    rejected = 0
    plantes = 0
    for it in items:
        if new_calls >= BATCH or (time.monotonic() - t0) >= MAX_S:
            break
        try:
            made_call, modified, ecarte = _traiter(it, tr)
        except Exception as e:
            plantes += 1
            print(f"::warning::[enrich] item {it.get('id')} en échec ({e!r}) — sauté")
            continue
        if made_call:
            new_calls += 1
        if modified:
            touched += 1
        if ecarte:
            rejected += 1

    # Le cache se sauve DÈS QU'UN APPEL A ÉTÉ FAIT, pas seulement quand un
    # article change. Sinon un run où tout est rejeté jette ses décisions et le
    # run suivant repaie les mêmes appels — boucle stérile observée en prod
    # (48 appels, 0 cache_hit, à chaque run pendant des semaines).
    if new_calls or touched:
        tr.cache.save()
    if touched:
        data["items"] = items
        NEWS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    if plantes:
        print(f"::warning::[enrich] {plantes} item(s) sautés sur exception")
    print(f"[enrich] {touched} maj / {rejected} écartés / {new_calls} appels Gemini "
          f"en {int(time.monotonic() - t0)}s · {tr.stats()}")
    # Échec seulement si RIEN n'a pu être traité alors qu'il y avait des
    # candidats : là c'est une vraie panne de chaîne, pas un item isolé.
    if plantes and not (touched or new_calls):
        print("::error::[enrich] aucun item traité — panne de chaîne probable")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
