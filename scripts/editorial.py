"""Comité éditorial autonome — filtre, vérifie et valide les news AVANT publication.

Deux couches :
1. RECHERCHISTE (heuristique, sans API) : écarte d'office les articles non-news
   (how to watch / livestream / paris-cotes / compos probables / pur SEO).
2. RÉDACTEUR EN CHEF (Gemini) : pour chaque candidat, vérifie la FIDÉLITÉ au
   source, la VALEUR éditoriale et le POSITIONNEMENT, décide PUBLIER / REJETER,
   et fournit le titre + résumé essentiel poli en FR/EN/ES/AR.

Dégradation gracieuse : sans clé Gemini valide, seul le pré-filtre tourne (le
pipeline ne casse jamais).
"""
import json
import re

# ── Recherchiste : motifs « utilitaire / non-news » à écarter d'office ──
NON_EDITORIAL = [
    r"how to watch", r"where to watch", r"live ?stream", r"livestream", r"free stream",
    r"watch .{0,30} free", r"for free\b", r"tv channel", r"what time\b", r"kick.?off time",
    r"comment (re)?garder", r"o[uù] (re)?garder", r"[àa] quelle heure", r"\bstreaming\b",
    r"\bodds\b", r"betting", r"\btips\b", r"\bprediction\b", r"pronostic", r"\bcotes?\b",
    r"predicted (line|xi)", r"team news\b", r"line-?ups?\b", r"diffusion en direct",
]
_NE = re.compile("|".join(NON_EDITORIAL), re.I)

def is_non_editorial(title: str) -> bool:
    """True si le titre est un article utilitaire (pas de la vraie news)."""
    return bool(_NE.search(title or ""))

LANG_NAMES = {"fr": "français", "en": "English", "es": "español", "ar": "العربية"}


def chief_editor_review(translator, title: str, summary: str, src: str, targets: list):
    """UN appel Gemini = le comité éditorial complet.

    Retourne dict {publish, reason, quality, i18n:{lang:{title,summary,engine}}}
    ou None si Gemini indisponible/échec (→ le caller retombe sur le pipeline normal).
    """
    title = (title or "").strip()
    summary = (summary or "").strip()
    if not title:
        return None
    langs = list(dict.fromkeys([src] + [t for t in targets if t != src]))
    # CACHE D'ABORD (gratuit) — marche même si Gemini est coupé (mode cache-only de
    # news-sync). Le cache est alimenté par news-editorial (le « cerveau » éditorial).
    cache_key = "edt:" + translator_hash(title, summary, src, langs) if getattr(translator, "cache", None) else None
    if cache_key and translator.cache:
        cached = translator.cache.get(cache_key)
        if cached:
            return cached
    # Pas de hit → appel Gemini SEULEMENT s'il est actif (news-sync le coupe).
    if not getattr(translator, "gemini_enabled", False):
        return None
    names = ", ".join(f'"{l}" ({LANG_NAMES.get(l, l)})' for l in langs)
    system = (
        "Tu es le COMITÉ ÉDITORIAL d'un média de football (soccer) haut de gamme, "
        "branché actu, dont l'image est : l'essentiel, sourcé, sans clickbait. "
        "Trois rôles réunis : un RECHERCHISTE vérifie la fidélité au source, un "
        "JOURNALISTE rédige, un RÉDACTEUR EN CHEF tranche. À partir du titre et du "
        "texte source, renvoie UNIQUEMENT ce JSON :\n"
        '{ "publish": true|false, "reason": "1 phrase", "quality": 0-10, '
        '"i18n": { ' + names + ': {"title":"...","summary":"..."} } }\n\n'
        "publish=false si UNE règle échoue :\n"
        "- VRAIE NEWS : un fait/événement/déclaration/transfert/résultat. PAS de "
        "guide « comment regarder », streaming, paris/cotes, compo probable, preview "
        "creux, listicle SEO, ni pub.\n"
        "- FIDÉLITÉ : le résumé doit refléter fidèlement le source, sans inventer ni "
        "diverger. Doute sur le contenu réel → publish=false.\n"
        "- FOOT PERTINENT : football/soccer uniquement, sujet d'intérêt (grands "
        "clubs/joueurs/compétitions, ou Cristiano Ronaldo).\n"
        "- PAS PÉRIMÉ : un match déjà joué annoncé comme à venir → publish=false.\n\n"
        "Si publish=true : pour CHAQUE langue, « title » = traduction fidèle du titre ; "
        "« summary » = l'essentiel à retenir, 1-2 phrases, ~35 mots, neutre, faits clés "
        "(qui/quoi/chiffres/enjeu), zéro clickbait."
    )
    user = json.dumps({"source_lang": src, "title": title, "text": (summary or title)[:1000]},
                      ensure_ascii=False)
    raw = translator._call_gemini(system, user, max_tokens=1300)
    obj = translator._parse_json_block(raw) if raw else None
    if not obj or "publish" not in obj:
        return None
    i18n = {}
    for l in langs:
        e = (obj.get("i18n") or {}).get(l) or {}
        t = str(e.get("title", "")).strip()[:300]
        s = str(e.get("summary", "")).strip()[:600]
        if t or s:
            i18n[l] = {"title": t or title, "summary": s or summary,
                       "needs_translation": False, "engine": "gemini-editor"}
    out = {
        "publish": bool(obj.get("publish")),
        "reason": str(obj.get("reason", ""))[:200],
        "quality": int(obj.get("quality", 0) or 0),
        "i18n": i18n if len(i18n) == len(langs) else None,
    }
    if cache_key and translator.cache:
        translator.cache.set(cache_key, out)
    return out


def translator_hash(title, summary, src, langs):
    import hashlib
    raw = (title + "|" + (summary or "")[:200] + "|" + src + "|" + ",".join(langs)).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]
