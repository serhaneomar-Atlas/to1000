#!/usr/bin/env python3
"""audit_editorial.py — le CONSEIL D'AUDIT du fil News.

Le conseil de rédaction produit ; celui-ci relit ce qui est publié et dit ce qui
ne va pas. Sans lui, une régression de qualité (retour de la traduction
mot-à-mot, résumés qui paraphrasent le titre, ton robotique) reste invisible
jusqu'à ce qu'un lecteur la signale — ou ne la signale pas et ne revienne plus.

Sept contrôles, tous déterministes (aucun appel API, tourne en quelques
secondes) :

  1. calque        — nom propre traduit (« Royal Madrid », « Cordoue CF »)
  2. nom_perdu     — nom propre du source disparu de la traduction
  3. echo_titre    — le résumé ne fait que reformuler le titre
  4. resume_court  — résumé trop court pour porter une information
  5. tic_ia        — tournures qui font « texte généré »
  6. non_enrichi   — article resté en traduction automatique brute
  7. langue_absente — une des 4 langues du site manque
  8. latin_en_arabe — nom propre laissé en alphabet latin dans un texte arabe

Sortie : rapport JSON (machine) + résumé lisible (humain), et un code de sortie
non nul quand le score passe sous le seuil — de quoi faire échouer un run et
alerter au lieu de dégrader en silence.

  python scripts/audit_editorial.py                 # audit + résumé console
  python scripts/audit_editorial.py --json rapport.json
  python scripts/audit_editorial.py --seuil 80      # échoue sous 80/100
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
ROOT = SCRIPT_DIR.parent
NEWS = ROOT / "public" / "news.json"

from lib.glossary import (CALQUES, latin_dans_arabe, missing_terms,  # noqa: E402
                          protected_terms)

SITE_LANGS = ("fr", "en", "es", "ar")

# Moteurs considérés comme « travail éditorial fait ». MyMemory et le repli en
# langue source ne comptent pas : c'est de la traduction brute.
ENGINES_OK = {"gemini-editor", "gemini-edi"}

# Tournures qui trahissent un texte généré. Volontairement resserré : on ne
# chasse que ce qui ne s'écrit quasiment jamais dans une brève de presse.
TICS_IA = [
    r"il convient de (noter|souligner|rappeler)",
    r"il est important de (noter|souligner)",
    r"force est de constater",
    r"^en effet\b",
    r"dans un contexte où",
    r"reste à savoir si",
    r"l'avenir nous dira",
    r"il est à noter que",
    r"en somme\b",
    r"en définitive\b",
    r"cabe (destacar|señalar)",
    r"it is worth noting",
    r"it should be noted",
]
_TICS = [re.compile(p, re.I | re.M) for p in TICS_IA]

# Points retirés à un couple (article, langue) qui part de 100. Le score global
# est la moyenne de ces couples : une panne qui touche tout le fil le fait donc
# vraiment chuter, au lieu d'être diluée par le nombre d'articles.
# Un calque coûte le plus cher — c'est l'erreur qui décrédibilise le plus vite.
POIDS = {
    "calque": 40.0,
    "nom_perdu": 15.0,
    "echo_titre": 25.0,
    "resume_court": 15.0,
    "tic_ia": 20.0,
    "non_enrichi": 30.0,
    "langue_absente": 100.0,
    # Aussi grave qu'un calque, à l'envers : la presse arabe translittère les
    # noms propres. « Arsenal يؤكد أن تجديد عقد Mikel Arteta » est une
    # traduction inachevée, et un lecteur arabophone le voit immédiatement.
    "latin_en_arabe": 40.0,
}

MIN_RESUME_MOTS = 8
_MOT = re.compile(r"[\w’'-]+", re.UNICODE)


def mots(text: str) -> list[str]:
    return _MOT.findall((text or "").lower())


def similarite(a: str, b: str) -> float:
    """Jaccard sur les mots — 1.0 = le résumé ne dit rien de plus que le titre."""
    sa, sb = set(mots(a)), set(mots(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def detecte_calques(text: str, lang: str) -> list[str]:
    """Calques encore présents APRÈS réparation — donc un cas non couvert."""
    trouves = []
    for pattern, correction in CALQUES.get(lang, []):
        if re.search(pattern, text or "", re.I):
            trouves.append(correction)
    return trouves


def audite_item(item: dict) -> list[dict]:
    """Défauts d'un article, tous langues confondues."""
    defauts: list[dict] = []
    item_id = item.get("id", "?")
    i18n = item.get("i18n") or {}
    src_lang = (item.get("primary_source") or {}).get("lang", "")
    src_entry = i18n.get(src_lang) or {}
    src_text = f"{src_entry.get('title', '')} {src_entry.get('summary', '')}".strip() \
        or f"{item.get('title', '')} {item.get('summary', '')}"
    termes = protected_terms(src_text)

    for lang in SITE_LANGS:
        entry = i18n.get(lang)
        if not entry or not (entry.get("title") or entry.get("summary")):
            defauts.append({"id": item_id, "lang": lang, "type": "langue_absente",
                            "detail": "aucune version dans cette langue"})
            continue

        titre = entry.get("title") or ""
        resume = entry.get("summary") or ""
        blob = f"{titre} {resume}"

        for correction in detecte_calques(blob, lang):
            defauts.append({"id": item_id, "lang": lang, "type": "calque",
                            "detail": f"nom propre traduit — attendu « {correction} »"})

        if lang != src_lang:
            perdus = missing_terms(src_text, blob, lang, terms=termes)
            # Un ou deux noms absents d'une brève courte, c'est normal : on ne
            # signale que la disparition massive (le texte a été dénaturé).
            if len(perdus) >= 3:
                defauts.append({"id": item_id, "lang": lang, "type": "nom_perdu",
                                "detail": "noms propres absents : " + ", ".join(perdus[:5])})

        if resume and similarite(titre, resume) >= 0.72:
            defauts.append({"id": item_id, "lang": lang, "type": "echo_titre",
                            "detail": "le résumé reformule le titre sans rien ajouter"})

        if len(mots(resume)) < MIN_RESUME_MOTS:
            defauts.append({"id": item_id, "lang": lang, "type": "resume_court",
                            "detail": f"{len(mots(resume))} mots — trop court pour informer"})

        corps = " ".join(entry.get("body") or [])
        for rx in _TICS:
            m = rx.search(f"{resume} {corps}")
            if m:
                defauts.append({"id": item_id, "lang": lang, "type": "tic_ia",
                                "detail": f"tournure « {m.group(0)} »"})
                break

        if lang == "ar":
            latins = latin_dans_arabe(blob)
            if latins:
                defauts.append({"id": item_id, "lang": lang, "type": "latin_en_arabe",
                                "detail": "mots restés en alphabet latin : "
                                          + ", ".join(dict.fromkeys(latins))[:80]})

        if entry.get("engine") not in ENGINES_OK or entry.get("needs_translation"):
            defauts.append({"id": item_id, "lang": lang, "type": "non_enrichi",
                            "detail": f"moteur « {entry.get('engine') or 'aucun'} » — "
                                      "traduction brute, pas de travail éditorial"})

    return defauts


def audite(news: dict) -> dict:
    items = news.get("items", [])
    defauts: list[dict] = []
    for item in items:
        defauts.extend(audite_item(item))

    par_type = Counter(d["type"] for d in defauts)
    par_langue = Counter(d["lang"] for d in defauts)

    # Chaque couple (article, langue) part de 100 et perd le poids de ses
    # défauts, plancher 0. Le score du fil est la moyenne de ces couples.
    # Un fil vide vaut 0 : c'est une panne, pas une perfection.
    penalites: Counter = Counter()
    for d in defauts:
        penalites[(d["id"], d["lang"])] += POIDS.get(d["type"], 10.0)
    couples = len(items) * len(SITE_LANGS)
    if not couples:
        score = 0.0
    else:
        perdu = sum(min(100.0, p) for p in penalites.values())
        score = max(0.0, 100.0 - perdu / couples)

    enrichis = sum(
        1 for it in items
        if ((it.get("i18n") or {}).get("fr") or {}).get("engine") in ENGINES_OK
    )
    lus_en_entier = sum(
        1 for it in items if (it.get("editorial") or {}).get("source_read") == "full"
    )
    avec_developpement = sum(
        1 for it in items if ((it.get("i18n") or {}).get("fr") or {}).get("body")
    )

    return {
        "genere_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "articles": len(items),
        "score": round(score, 1),
        "defauts_total": len(defauts),
        "par_type": dict(par_type.most_common()),
        "par_langue": dict(par_langue.most_common()),
        "couverture": {
            "enrichis": enrichis,
            "enrichis_pct": round(100 * enrichis / len(items), 1) if items else 0.0,
            "source_lu_en_entier": lus_en_entier,
            "avec_developpement": avec_developpement,
        },
        "defauts": defauts,
    }


def resume_console(rapport: dict) -> str:
    lignes = [
        "",
        "═══ CONSEIL D'AUDIT — fil News ═══",
        f"  {rapport['articles']} articles · score {rapport['score']}/100 "
        f"· {rapport['defauts_total']} défauts",
        "",
    ]
    couv = rapport["couverture"]
    lignes.append(f"  Enrichis par le conseil de rédaction : {couv['enrichis']}"
                  f"/{rapport['articles']} ({couv['enrichis_pct']} %)")
    lignes.append(f"  Source lue en entier                : {couv['source_lu_en_entier']}")
    lignes.append(f"  Avec développement rédigé           : {couv['avec_developpement']}")
    if rapport["par_type"]:
        lignes.append("")
        lignes.append("  Défauts par type :")
        for typ, n in rapport["par_type"].items():
            lignes.append(f"    · {typ:<16} {n:>4}")
    # Trois exemples concrets valent mieux qu'un compteur : on voit quoi corriger.
    if rapport["defauts"]:
        lignes.append("")
        lignes.append("  Exemples :")
        for d in rapport["defauts"][:3]:
            lignes.append(f"    · [{d['lang']}] {d['type']} — {d['detail'][:80]}")
    lignes.append("")
    return "\n".join(lignes)


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit qualité du fil News")
    ap.add_argument("--news", default=str(NEWS), help="chemin de news.json")
    ap.add_argument("--json", dest="json_out", help="écrit le rapport JSON ici")
    ap.add_argument("--seuil", type=float, default=0.0,
                    help="code de sortie 1 si le score passe sous ce seuil")
    ap.add_argument("--quiet", action="store_true", help="pas de résumé console")
    args = ap.parse_args()

    path = Path(args.news)
    if not path.exists():
        print(f"[audit] {path} introuvable", file=sys.stderr)
        return 2

    rapport = audite(json.loads(path.read_text(encoding="utf-8")))

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rapport, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        print(f"[audit] rapport écrit : {out}")

    if not args.quiet:
        print(resume_console(rapport))

    if args.seuil and rapport["score"] < args.seuil:
        print(f"[audit] score {rapport['score']} < seuil {args.seuil}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
