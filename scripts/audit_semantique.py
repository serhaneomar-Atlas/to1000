#!/usr/bin/env python3
"""audit_semantique.py — le juge de FOND du conseil d'audit.

L'audit déterministe attrape la forme (calques, registre, longueurs). Il ne
peut pas juger le SENS : un résumé fluide qui rate le fait central de
l'article passe tous ses contrôles. Cas vécu : « le quatuor de capitaines du
Barça devient un quintette mené par Patri Guijarro » — le fait central du
source, absent du résumé publié, et aucun contrôle de forme ne pouvait le voir.

Ce juge relit, pour un échantillon borné d'articles enrichis :
  1. l'article SOURCE complet (re-récupéré) ;
  2. ce que NOUS avons publié (lead + développement) ;
et rend un verdict : le fait central y est-il ? les faits majeurs y sont-ils ?
note 0-10.

Un article jugé infidèle ou incomplet est SANCTIONNÉ, pas seulement noté :
  - ses traductions sont retirées de l'affichage (engine → retire-par-audit,
    le garde-fou de publication les remplace par le texte source original) ;
  - son entrée de cache est purgée → le prochain run du conseil de rédaction
    refait l'article de zéro, avec les prompts à jour.

Tourne dans news-editorial.yml (même groupe de concurrence que la
publication : pas de course sur news.json), budget SEM_BATCH articles par run.
Verdicts journalisés dans EDITORIAL/state/semantic_audit.jsonl ; l'audit
déterministe les relit et compte tout article « retiré » comme défaut.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
ROOT = SCRIPT_DIR.parent
NEWS = ROOT / "public" / "news.json"
CACHE = ROOT / "public" / "translations_cache.json"
JOURNAL = ROOT / "EDITORIAL" / "state" / "semantic_audit.jsonl"

from editorial import translator_hash  # noqa: E402
from lib.article_fetch import article_text  # noqa: E402
from translator import Translator  # noqa: E402

SITE_LANGS = ["fr", "en", "es", "ar"]
BATCH = int(os.environ.get("SEM_BATCH", "6"))
MAX_S = int(os.environ.get("SEM_MAX_SECONDS", "240"))
NOTE_MIN = float(os.environ.get("SEM_NOTE_MIN", "7"))

# On ne juge que ce que le conseil de rédaction a produit : juger un brouillon
# MyMemory n'apprend rien (on sait qu'il est mauvais, et il n'est plus affiché).
ENGINE_JUGEABLE = "gemini-editor"


def _cache_key(item: dict) -> str:
    """Reproduit la clé utilisée par chief_editor_review pour cet item."""
    src = (item.get("primary_source") or {}).get("lang", "en")
    src_i18n = (item.get("i18n", {}) or {}).get(src, {}) or {}
    title = src_i18n.get("title") or item.get("title") or ""
    summary = src_i18n.get("summary") or item.get("summary") or ""
    langs = list(dict.fromkeys([src] + [l for l in SITE_LANGS if l != src]))
    return "edtv8:" + translator_hash(title, summary, src, langs)


def juger(tr: Translator, item: dict) -> dict | None:
    """Verdict du juge sur un article enrichi. None si Gemini indisponible."""
    src = (item.get("primary_source") or {}).get("lang", "en")
    fr = (item.get("i18n") or {}).get("fr") or {}
    corps, origine = article_text(item.get("url", ""),
                                  fallback=item.get("summary", ""))
    publie = {
        "titre": fr.get("title", ""),
        "lead": fr.get("summary", ""),
        "developpement": fr.get("body") or [],
    }
    raw = tr._call_gemini(
        "Tu es un RELECTEUR DE FOND indépendant pour un site d'actu football. "
        "On te donne un article SOURCE (complet quand lu=full, sinon son "
        "amorce) et ce que la rédaction a publié (titre + lead + "
        "développement). Juge le FOND, pas le style :\n"
        "1. fait_central : le fait le plus fort du source — nommé précisément "
        "(qui, quoi, combien, quel rang).\n"
        "2. central_restitue : ce fait est-il dans le publié ?\n"
        "3. faits_manquants : faits MAJEURS du source absents du publié "
        "(liste courte, vide si rien de majeur ne manque). Un détail "
        "secondaire n'est pas un fait majeur.\n"
        "4. erreurs : contresens ou faits déformés dans le publié (genre d'une "
        "personne, rang hiérarchique, score, nom).\n"
        "5. note : 0-10. 10 = un lecteur du publié sait tout ce qui compte. "
        "≤6 = le publié rate le central, déforme un fait, ou omet plusieurs "
        "faits majeurs.\n"
        'JSON strict : {"fait_central": "...", "central_restitue": true|false, '
        '"faits_manquants": ["..."], "erreurs": ["..."], "note": 0-10}',
        json.dumps({"source_lang": src, "lu": origine,
                    "source": {"titre": item.get("title", ""),
                               "texte": corps[:6000]},
                    "publie": publie}, ensure_ascii=False),
        max_tokens=600)
    verdict = tr._parse_json_block(raw) if raw else None
    if not verdict or "note" not in verdict:
        return None
    verdict["lu"] = origine
    return verdict


def sanctionner(item: dict, cache: dict) -> None:
    """Retire l'article de l'affichage et force sa re-rédaction."""
    for lang, entry in (item.get("i18n") or {}).items():
        if isinstance(entry, dict) and entry.get("engine") == ENGINE_JUGEABLE:
            entry["engine"] = "retire-par-audit"
    cache.pop(_cache_key(item), None)


def main() -> int:
    if not NEWS.exists():
        print("[sem] news.json absent")
        return 0
    data = json.loads(NEWS.read_text(encoding="utf-8"))
    items = data.get("items", [])

    tr = Translator(cache_path=CACHE)
    if not tr.gemini_enabled:
        print("[sem] GEMINI_API_KEY absente — audit sémantique sauté")
        return 0

    cache_raw = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    candidats = [
        it for it in items
        if ((it.get("i18n") or {}).get("fr") or {}).get("engine") == ENGINE_JUGEABLE
        and "semantique" not in (it.get("editorial") or {})
    ]
    print(f"[sem] {len(candidats)} candidats · budget {BATCH} · plafond {MAX_S}s")

    t0 = time.monotonic()
    juges = retires = 0
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with JOURNAL.open("a", encoding="utf-8") as journal:
        for it in candidats:
            if juges >= BATCH or (time.monotonic() - t0) >= MAX_S:
                break
            verdict = juger(tr, it)
            if verdict is None:
                continue
            juges += 1
            note = float(verdict.get("note", 0) or 0)
            mauvais = (note < NOTE_MIN
                       or not verdict.get("central_restitue")
                       or bool(verdict.get("erreurs")))
            ed = it.setdefault("editorial", {})
            ed["semantique"] = {
                "note": note,
                "central_restitue": bool(verdict.get("central_restitue")),
                "manque": (verdict.get("faits_manquants") or [])[:3],
                "erreurs": (verdict.get("erreurs") or [])[:3],
                "retire": mauvais,
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            if mauvais:
                sanctionner(it, cache_raw)
                retires += 1
                print(f"[sem] ✗ {it.get('id')} note={note} — retiré, sera refait "
                      f"(manque: {'; '.join(ed['semantique']['manque'])[:90]})")
            else:
                print(f"[sem] ✓ {it.get('id')} note={note}")
            journal.write(json.dumps({
                "ts": ed["semantique"]["ts"], "id": it.get("id"),
                "note": note, "retire": mauvais, "lu": verdict.get("lu"),
                "fait_central": str(verdict.get("fait_central", ""))[:160],
            }, ensure_ascii=False) + "\n")

    if juges:
        NEWS.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        CACHE.write_text(json.dumps(cache_raw, ensure_ascii=False),
                         encoding="utf-8")
    print(f"[sem] {juges} jugés · {retires} retirés pour re-rédaction")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
