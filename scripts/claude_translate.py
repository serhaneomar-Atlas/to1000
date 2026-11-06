"""
claude_translate.py — traduction des actus par Claude (abonnement Max), en
remplacement de Gemini quand son crédit est épuisé (panne du 23/10/2026).

Trois commandes, aucune n'appelle d'API elle-même (c'est le workflow
news-translate.yml qui fait travailler Claude entre `prepare` et `ingest`) :

  prepare  → .translate/todo.json : les articles du fil auxquels il manque une
             version publiable en fr / en / es / ar, avec le texte source, la
             liste des langues manquantes et le glossaire des noms propres.
  ingest   → lit .translate/done.json (écrit par Claude), valide chaque
             traduction, la range dans EDITORIAL/state/claude_translations.json
             (le « magasin »), puis applique le magasin au fil.
  merge    → applique le magasin au fil sans rien demander à Claude. news-sync
             l'appelle après chaque rafraîchissement : sinon le fil reconstruit
             toutes les heures effacerait les traductions.

Les traductions entrent avec engine="redaction" : moteur déjà accepté par le
contrat de langue (news_locale.py et locale-news.js).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from news_locale import publishable  # noqa: E402

try:
    from lib.glossary import prompt_block, protected_terms, repair_pack
except ImportError:  # dégradation douce
    def prompt_block(_t, _l=None): return ""
    def protected_terms(*_t, **_k): return []
    def repair_pack(p): return p

NEWS = ROOT / "public" / "news.json"
STORE = ROOT / "EDITORIAL" / "state" / "claude_translations.json"
WORK = ROOT / ".translate"
LANGS = ("fr", "en", "es", "ar")
ENGINE = "redaction"
STORE_MAX = 800
_AR = re.compile(r"[؀-ۿ]")


def gh(level: str, msg: str) -> None:
    print(f"::{level}::{msg}", flush=True)


def load(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def save(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)  # écriture atomique : un run tué ne laisse pas un JSON coupé


def src_lang(it: dict) -> str:
    return str((it.get("primary_source") or {}).get("lang") or it.get("source_lang") or "").lower()[:2]


def source_text(it: dict) -> tuple[str, str]:
    """(titre, résumé) dans la langue d'origine."""
    e = (it.get("i18n") or {}).get(src_lang(it)) or {}
    return (e.get("title") or it.get("title") or "").strip(), (e.get("summary") or it.get("summary") or "").strip()


def fingerprint(it: dict) -> str:
    t, s = source_text(it)
    return hashlib.sha1(f"{src_lang(it)}|{t}|{s}".encode("utf-8")).hexdigest()[:12]


def missing_langs(it: dict) -> list[str]:
    if (it.get("editorial") or {}).get("publish") is False:
        return []
    return [l for l in LANGS if not publishable(it, l)]


# ── prepare ────────────────────────────────────────────────────────────────
def cmd_prepare(limit: int) -> int:
    feed = load(NEWS, {})
    store = load(STORE, {})
    todo = []
    for it in feed.get("items", []):
        rec = store.get(it.get("id") or "") or {}
        if rec.get("skip") and rec.get("fp") == fingerprint(it):
            continue  # déjà écarté par Claude (direct, paris…) : on ne redemande pas
        miss = missing_langs(it)
        title, summary = source_text(it)
        if not miss or not title or not summary:
            continue
        terms = protected_terms(title, summary)
        todo.append({
            "id": it.get("id"),
            "src_lang": src_lang(it) or "inconnue",
            "title": title,
            "summary": summary[:1500],
            "source": (it.get("primary_source") or {}).get("name") or "",
            "missing": miss,
            "noms_propres": terms,
            "consignes_noms": prompt_block(terms, miss),
        })
        if len(todo) >= limit:
            break
    WORK.mkdir(exist_ok=True)
    save(WORK / "todo.json", {"generated_at": datetime.now(timezone.utc).isoformat(), "items": todo})
    total = sum(len(t["missing"]) for t in todo)
    print(f"[translate] {len(todo)} articles à traiter, {total} traductions manquantes")
    import os
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"count={len(todo)}\n")
    return 0


# ── validation ─────────────────────────────────────────────────────────────
def valid_entry(lang: str, e: dict, src_title: str, src_summary: str) -> str | None:
    """None si correct, sinon la raison du rejet."""
    if not isinstance(e, dict):
        return "format"
    t, s = (e.get("title") or "").strip(), (e.get("summary") or "").strip()
    if not (5 <= len(t) <= 220):
        return "titre-longueur"
    if not (15 <= len(s) <= 1500):
        return "résumé-longueur"
    if t == src_title or s == src_summary:
        return "identique-au-source"
    if lang == "ar":
        if not (_AR.search(t) and _AR.search(s)):
            return "arabe-absent"
    elif _AR.search(t + s):
        return "arabe-dans-latin"
    return None


def apply_store(feed: dict, store: dict) -> int:
    """Pose les traductions du magasin sur le fil. Renvoie le nombre posé."""
    n = 0
    for it in feed.get("items", []):
        rec = store.get(it.get("id") or "")
        if not rec or rec.get("fp") != fingerprint(it):
            continue  # article modifié depuis : la traduction ne correspond plus
        if rec.get("skip"):
            # Même effet que le rejet du rédacteur en chef Gemini : l'article
            # utilitaire (direct, paris, « comment regarder ») n'est pas publié.
            if (it.get("editorial") or {}).get("publish") is not False:
                it["editorial"] = {"publish": False, "reason": rec["skip"], "by": "claude"}
                n += 1  # compte comme modification : le fil doit être réécrit
            continue
        i18n = it.setdefault("i18n", {})
        for lang, e in (rec.get("i18n") or {}).items():
            if publishable(it, lang):
                continue  # une version publiable existe déjà (source ou Gemini)
            i18n[lang] = dict(e)
            if publishable(it, lang):
                n += 1
            else:  # ne jamais laisser une entrée non affichable remplacer l'ancienne
                i18n.pop(lang, None)
    return n


def cmd_merge() -> int:
    feed, store = load(NEWS, {}), load(STORE, {})
    if not store or not feed:
        print("[translate] magasin vide ou fil absent — rien à appliquer")
        return 0
    n = apply_store(feed, store)
    if n:
        save(NEWS, feed)
    print(f"[translate] {n} traductions du magasin appliquées au fil")
    return 0


# ── ingest ─────────────────────────────────────────────────────────────────
def cmd_ingest() -> int:
    done = load(WORK / "done.json", None)
    todo = {t["id"]: t for t in load(WORK / "todo.json", {}).get("items", [])}
    feed, store = load(NEWS, {}), load(STORE, {})
    by_id = {it.get("id"): it for it in feed.get("items", [])}
    if not isinstance(done, dict) or not isinstance(done.get("items"), list):
        gh("warning", "Claude n'a pas produit .translate/done.json exploitable — rien d'appliqué")
        return 0
    ok, rejected = 0, {}
    now = datetime.now(timezone.utc).isoformat()
    for row in done["items"]:
        iid = row.get("id") if isinstance(row, dict) else None
        t, it = todo.get(iid), by_id.get(iid)
        if not t or not it:
            continue
        reason = str(row.get("skip") or "").strip()
        if reason:
            store[iid] = {"fp": fingerprint(it), "skip": reason[:120], "at": now}
            rejected["écarté-non-article"] = rejected.get("écarté-non-article", 0) + 1
            continue
        pack = {}
        for lang in t["missing"]:
            e = (row.get("i18n") or {}).get(lang)
            why = valid_entry(lang, e, t["title"], t["summary"])
            if why:
                rejected[why] = rejected.get(why, 0) + 1
                continue
            pack[lang] = {"title": e["title"].strip(), "summary": e["summary"].strip(),
                          "body": [], "format": "brief", "engine": ENGINE, "by": "claude"}
        if not pack:
            continue
        pack = repair_pack(pack)
        for e in pack.values():  # repair_pack ne touche que title/summary
            e.setdefault("engine", ENGINE)
        rec = store.get(iid) or {}
        if rec.get("fp") != fingerprint(it):
            rec = {"fp": fingerprint(it), "i18n": {}}
        rec["i18n"].update(pack)
        rec["at"] = now
        store[iid] = rec
        ok += len(pack)
    # magasin borné : on garde les plus récents
    if len(store) > STORE_MAX:
        for k in sorted(store, key=lambda k: store[k].get("at", ""))[:-STORE_MAX]:
            store.pop(k, None)
    save(STORE, store)
    applied = apply_store(feed, store)
    if applied:
        save(NEWS, feed)
    msg = f"{ok} traductions validées, {applied} appliquées au fil"
    if rejected:
        msg += " · rejets : " + ", ".join(f"{k}={v}" for k, v in sorted(rejected.items()))
    gh("notice", "[translate] " + msg)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare"); p.add_argument("--limit", type=int, default=20)
    sub.add_parser("ingest")
    sub.add_parser("merge")
    a = ap.parse_args()
    if a.cmd == "prepare":
        return cmd_prepare(a.limit)
    if a.cmd == "ingest":
        return cmd_ingest()
    return cmd_merge()


if __name__ == "__main__":
    sys.exit(main())
