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
    """Chaîne éditoriale en 4 étapes (refonte 2026-07-06, demande Omar) :

      1. RÉDACTEUR EN CHEF (tri)      — l'article mérite-t-il publication ?
      2. EXPERT EN RÉDACTION (résumé) — extraire L'INFORMATION CENTRALE
      3. EXPERT EN TRADUCTION         — transcréation naturelle (pas de mot-à-mot)
      4. RÉDACTEUR EN CHEF (validation finale) — contrôle avant publication

    Le rejet à l'étape 1 coûte UN seul appel (pas de résumé/traduction gaspillés).
    Retour identique à l'ancienne version : {publish, reason, quality, i18n} ou
    None si Gemini indisponible/échec (→ fallback traduction classique).
    """
    title = (title or "").strip()
    summary = (summary or "").strip()
    if not title:
        return None
    langs = list(dict.fromkeys([src] + [t for t in targets if t != src]))
    # CACHE D'ABORD (gratuit) — marche même si Gemini est coupé (mode cache-only
    # de news-sync). v4 = chaîne 4 étapes (purge des sorties mono-appel edtv3).
    cache_key = "edtv4:" + translator_hash(title, summary, src, langs) if getattr(translator, "cache", None) else None
    if cache_key and translator.cache:
        cached = translator.cache.get(cache_key)
        if cached:
            return cached
    if not getattr(translator, "gemini_enabled", False):
        return None

    def _stage(system, user, max_tokens=900):
        raw = translator._call_gemini(system, user, max_tokens=max_tokens)
        return translator._parse_json_block(raw) if raw else None

    payload = json.dumps({"source_lang": src, "title": title,
                          "text": (summary or title)[:1200]}, ensure_ascii=False)

    # ── Étape 1 : RÉDACTEUR EN CHEF — tri ──────────────────────────────────
    judge = _stage(
        "Tu es le RÉDACTEUR EN CHEF d'un site d'actu football grand public "
        "(hub football + compte à rebours des 1000 buts de Ronaldo ; lectorat : "
        "Europe francophone, Maghreb, fans de grands clubs). Décide si cette "
        "dépêche mérite d'être publiée. publish=false si : article utilitaire "
        "(comment regarder, streaming, cotes/pronostics, compo probable), hors "
        "football, périmé, intérêt trop local ou anecdotique, contenu creux ou "
        "purement promotionnel. En cas de doute sérieux sur les faits : false.\n"
        'Réponds UNIQUEMENT en JSON : {"publish": true|false, "reason": "1 phrase", '
        '"quality": 0-10}', payload, max_tokens=200)
    if not judge or "publish" not in judge:
        return None
    if not judge.get("publish"):
        out = {"publish": False, "reason": str(judge.get("reason", ""))[:200],
               "quality": int(judge.get("quality", 0) or 0), "i18n": None}
        if cache_key and translator.cache:
            translator.cache.set(cache_key, out)
        return out

    # ── Étape 2 : EXPERT EN RÉDACTION — résumé de l'essentiel ──────────────
    redac = _stage(
        "Tu es un EXPERT EN RÉDACTION de brèves sportives (flash info TV/radio). "
        "Identifie d'abord L'INFORMATION CENTRALE de la dépêche — le fait le plus "
        "fort : résultat, décision, chiffre, transfert, conséquence. PAS le premier "
        "paragraphe par défaut, PAS un détail secondaire. Puis écris, dans la "
        "LANGUE SOURCE de la dépêche :\n"
        "• title : percutant, fidèle, ≤ 80 caractères\n"
        "• summary : UNE phrase (deux max), 15-28 mots, voix active, le fait "
        "d'abord — INTERDIT de recopier une phrase du source, RÉÉCRIS.\n"
        "EXACTITUDE : n'ajoute AUCUN fait absent du source. Coupe du monde 2026 "
        "(48 équipes) : seizièmes (32) → huitièmes (16) → quarts → demies → "
        "finale ; gagner en seizièmes qualifie pour les HUITIÈMES. Si le tour "
        "n'est pas nommé, écris « pour la suite du tournoi ».\n"
        'JSON : {"title": "...", "summary": "..."}', payload, max_tokens=300)
    if not redac or not redac.get("summary"):
        return None

    # ── Étape 3 : EXPERT EN TRADUCTION — transcréation ─────────────────────
    names = ", ".join(f'"{l}" ({LANG_NAMES.get(l, l)})' for l in langs)
    trad = _stage(
        "Tu es un EXPERT EN TRADUCTION-LOCALISATION de presse sportive, natif de "
        "chaque langue cible. TRANSCRÉE ce titre et ce résumé — surtout PAS de "
        "mot-à-mot : phrasé naturel d'un journaliste sportif natif, idiomes du "
        "pays, registre flash info. Noms propres : orthographe usuelle de chaque "
        "langue (arabe : translittérations standards des joueurs/clubs, ex. "
        "مبابي، ريال مدريد). Ne traduis JAMAIS les noms de clubs en calque. "
        "Garde les chiffres et scores exacts.\n"
        "Langues cibles : " + names + "\n"
        'JSON : {"fr": {"title","summary"}, ...} (une entrée par langue cible)',
        json.dumps({"source_lang": src, "title": redac.get("title") or title,
                    "summary": redac["summary"]}, ensure_ascii=False),
        max_tokens=1200)
    if not trad:
        return None

    # ── Étape 4 : RÉDACTEUR EN CHEF — validation finale ────────────────────
    valid = _stage(
        "Tu es le RÉDACTEUR EN CHEF. Contrôle FINAL avant publication du paquet "
        "multilingue ci-dessous (source + 4 versions) :\n"
        "• fidélité aux faits du source, aucune invention, scores/tours exacts "
        "(rappel CdM 2026 : seizièmes AVANT huitièmes) ;\n"
        "• chaque version sonne comme un flash info NATIF (pas de calque) ;\n"
        "• titres ≤ 80c, résumés 15-28 mots.\n"
        "Corrige DIRECTEMENT ce qui doit l'être et renvoie le paquet final. "
        "publish=false seulement si le fond est irrécupérable.\n"
        'JSON : {"publish": true|false, "i18n": {lang: {"title","summary"}}}',
        json.dumps({"source": {"title": title, "text": (summary or title)[:800]},
                    "proposition": trad}, ensure_ascii=False),
        max_tokens=1300)
    if not valid or "publish" not in valid:
        return None

    i18n = {}
    final = valid.get("i18n") if valid.get("publish") else None
    if final:
        for l in langs:
            e = (final.get(l) or trad.get(l) or {})
            t = str(e.get("title", "")).strip()[:300]
            s = str(e.get("summary", "")).strip()[:600]
            if t or s:
                i18n[l] = {"title": t or title, "summary": s or summary,
                           "needs_translation": False, "engine": "gemini-editor"}
    out = {
        "publish": bool(valid.get("publish")),
        "reason": str(judge.get("reason", ""))[:200],
        "quality": int(judge.get("quality", 0) or 0),
        "i18n": i18n if len(i18n) == len(langs) else None,
    }
    if cache_key and translator.cache:
        translator.cache.set(cache_key, out)
    return out


def translator_hash(title, summary, src, langs):
    import hashlib
    raw = (title + "|" + (summary or "")[:200] + "|" + src + "|" + ",".join(langs)).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]
