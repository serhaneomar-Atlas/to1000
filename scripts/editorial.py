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
    # v2 = nouveau prompt « flash info » (brèves TV/radio). Bump la clé pour
    # ré-enrichir tous les articles au lieu de servir les anciens résumés cachés.
    cache_key = "edtv2:" + translator_hash(title, summary, src, langs) if getattr(translator, "cache", None) else None
    if cache_key and translator.cache:
        cached = translator.cache.get(cache_key)
        if cached:
            return cached
    # Pas de hit → appel Gemini SEULEMENT s'il est actif (news-sync le coupe).
    if not getattr(translator, "gemini_enabled", False):
        return None
    names = ", ".join(f'"{l}" ({LANG_NAMES.get(l, l)})' for l in langs)
    system = (
        "Tu es la RÉDACTION d'un FLASH INFO football (soccer), façon présentateur "
        "TV/radio. Trois expertises en une : un RÉDACTEUR EN CHEF qui tranche, un "
        "PROMPT ENGINEER qui structure la sortie, un TRADUCTEUR POLYGLOTTE qui écrit "
        "dans chaque langue comme un présentateur NATIF. Tu transformes une dépêche en "
        "BRÈVE DE FLASH INFO. Réponds UNIQUEMENT en JSON :\n"
        '{ "publish": true|false, "reason": "1 phrase", "quality": 0-10, '
        '"i18n": { ' + names + ': {"title":"...","summary":"..."} } }\n\n'
        "publish=false si : pas une vraie news (guide « comment regarder », streaming, "
        "paris/cotes, compo probable, preview creux, listicle SEO, pub) ; hors "
        "football ; périmé (match déjà joué annoncé à venir) ; ou doute sur le contenu.\n\n"
        "Le « summary » est une BRÈVE DE FLASH INFO, PAS un résumé d'article :\n"
        "• UNE phrase (deux max), 15-28 mots, le FAIT LE PLUS FORT EN PREMIER "
        "(résultat, décision, chiffre, transfert).\n"
        "• Voix active, ton direct d'un présentateur qui lit l'info en 10 secondes.\n"
        "• INTERDIT de recopier ou traduire la 1re phrase du source : RÉÉCRIS de zéro. "
        "Pas d'ouverture molle (« X a annoncé que », « selon »). Droit au fait.\n"
        "• Coupe le contexte, les détails secondaires, les formules de remplissage — "
        "garde uniquement ce qu'un téléspectateur doit retenir.\n"
        "• Chaque langue = phrasé NATUREL d'un présentateur de ce pays, pas une "
        "traduction mot-à-mot. « title » : court, percutant, fidèle.\n\n"
        "EXEMPLES (source → brève attendue) :\n"
        "Source : « Le FC Barcelone a annoncé ce mardi le départ de son attaquante "
        "Salma Paralluelo, qui a remporté trois Ligue des champions sous le maillot. »\n"
        "→ « Salma Paralluelo quitte le Barça après quatre saisons et trois Ligues des "
        "champions. »\n"
        "Source : « Le Brésil s'est qualifié pour les huitièmes de la Coupe du monde "
        "2026 en battant péniblement le Japon (2-1) à Houston, porté par Vinicius Jr. »\n"
        "→ « Le Brésil file en huitièmes : 2-1 sur le Japon à Houston, Vinicius Jr "
        "décisif. »"
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
