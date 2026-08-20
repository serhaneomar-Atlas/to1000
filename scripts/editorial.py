"""Comité éditorial autonome — filtre, vérifie et valide les news AVANT publication.

Deux couches :
1. RECHERCHISTE (heuristique, sans API) : écarte d'office les articles non-news
   (how to watch / livestream / paris-cotes / compos probables / pur SEO).
2. CONSEIL DE RÉDACTION (Gemini) : chaîne à 5 étapes qui lit l'article SOURCE
   EN ENTIER, en extrait l'information centrale, la rédige au bon format, la
   transcrée dans les 4 langues du site et la valide avant publication.

Dégradation gracieuse : sans clé Gemini valide, seul le pré-filtre tourne (le
pipeline ne casse jamais). Si l'article complet n'est pas récupérable, on
travaille sur l'extrait RSS — mais le modèle le sait et n'invente rien.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from lib.article_fetch import article_text
    from lib.glossary import prompt_block, protected_terms, repair_pack
except ImportError:  # exécution isolée → dégradation douce
    def article_text(_url, fallback=""): return (fallback or ""), "rss"
    def prompt_block(_terms, _langs=None): return ""
    def protected_terms(*_t, **_k): return []
    def repair_pack(pack): return pack

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

# Formats de restitution. Le rédacteur choisit selon la matière de l'article :
# une info unique ne mérite pas trois paragraphes, un récapitulatif à cinq faits
# ne tient pas en une phrase.
FORMATS = ("brief", "deep", "bullets")

# Tics d'écriture qui font immédiatement « texte généré ». On les proscrit à la
# rédaction ET on les traque à la validation.
ANTI_IA = (
    "HUMANISATION — le texte doit se lire comme celui d'un journaliste, pas "
    "d'une machine. Interdits : « il convient de noter », « il est important de "
    "souligner », « force est de constater », « en effet » en tête de phrase, "
    "« dans un contexte où », « véritable », « incontournable », « ce n'est pas "
    "un hasard si », les énumérations en trois adjectifs, les phrases toutes de "
    "même longueur, les conclusions qui moralisent ou ouvrent sur l'avenir "
    "(« reste à savoir si… », « l'avenir nous dira… »). Écris court quand le "
    "fait est court. Alterne phrases brèves et longues. Nomme les gens et les "
    "chiffres au lieu de tourner autour."
)


def chief_editor_review(translator, title: str, summary: str, src: str,
                        targets: list, url: str = ""):
    """Conseil de rédaction en 5 étapes (refonte 2026-08-19) :

      1. RÉDACTEUR EN CHEF (tri)       — l'article mérite-t-il publication ?
      2. LECTURE DU SOURCE             — récupère l'article COMPLET (pas l'amorce RSS)
      3. EXPERT EN RÉDACTION           — LA nouvelle + développement au bon format
      4. EXPERT EN TRADUCTION          — transcréation, noms propres verrouillés
      5. RÉDACTEUR EN CHEF (validation)— fidélité, ton humain, contrôle final

    Le rejet à l'étape 1 coûte UN seul appel : ni lecture, ni rédaction, ni
    traduction gaspillées. La lecture (étape 2) ne se paie donc que sur les
    articles retenus.

    Retour : {publish, reason, quality, i18n, source_read} ou None si Gemini est
    indisponible (→ l'appelant retombe sur la traduction classique).
    """
    title = (title or "").strip()
    summary = (summary or "").strip()
    if not title:
        return None
    langs = list(dict.fromkeys([src] + [t for t in targets if t != src]))
    # CACHE D'ABORD (gratuit) — marche même si Gemini est coupé (mode cache-only
    # de news-sync). v5 = chaîne 5 étapes avec lecture du source + formats.
    # v8 : surnoms de clubs + hiérarchie des capitaines + féminin renforcé.
    # v7 : lexique sportif arabe ajouté au prompt (قبطان → قائد, féminin du
    # foot féminin). v6 : la consigne arabe a changé (translittération au lieu de « reproduis à
    # l'identique »). Sans nouvelle version de clé, les verdicts déjà en cache
    # rejoueraient les titres mi-arabes mi-latins et le correctif n'aurait aucun
    # effet visible.
    cache_key = "edtv8:" + translator_hash(title, summary, src, langs) if getattr(translator, "cache", None) else None
    if cache_key and translator.cache:
        cached = translator.cache.get(cache_key)
        if cached:
            return cached
    if not getattr(translator, "gemini_enabled", False):
        return None

    def _stage(system, user, max_tokens=900):
        raw = translator._call_gemini(system, user, max_tokens=max_tokens)
        return translator._parse_json_block(raw) if raw else None

    def _memo(out):
        if cache_key and translator.cache:
            translator.cache.set(cache_key, out)
        return out

    triage_payload = json.dumps({"source_lang": src, "title": title,
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
        '"quality": 0-10}', triage_payload, max_tokens=200)
    if not judge or "publish" not in judge:
        return None
    if not judge.get("publish"):
        return _memo({"publish": False, "reason": str(judge.get("reason", ""))[:200],
                      "quality": int(judge.get("quality", 0) or 0), "i18n": None,
                      "source_read": "skipped"})

    # ── Étape 2 : LECTURE — l'article en entier, pas son amorce ────────────
    # C'est ce qui distingue « résumer » de « reformuler le premier paragraphe ».
    body, origin = article_text(url, fallback=summary) if url else (summary, "rss")
    read_note = (
        "Tu disposes de l'ARTICLE COMPLET ci-dessous. Lis-le en entier avant "
        "d'écrire : l'information la plus forte n'est pas toujours dans le "
        "premier paragraphe."
        if origin == "full" else
        "Tu ne disposes que de l'AMORCE de la dépêche (le corps n'a pas pu être "
        "récupéré). Reste strictement dans ce qui est écrit : n'extrapole pas, "
        "n'invente aucun détail absent."
    )

    write_payload = json.dumps({"source_lang": src, "title": title,
                                "article": body[:6000]}, ensure_ascii=False)

    # ── Étape 3 : EXPERT EN RÉDACTION — LA nouvelle, puis le développement ─
    redac = _stage(
        "Tu es un EXPERT EN RÉDACTION de presse sportive. " + read_note + "\n\n"
        "Procède dans cet ordre :\n"
        "1. Identifie L'INFORMATION CENTRALE — le fait le plus fort de "
        "l'article : résultat, décision, chiffre, transfert, conséquence. PAS le "
        "premier paragraphe par défaut, PAS un détail secondaire, PAS une "
        "reformulation du titre.\n"
        "2. Choisis le format de restitution adapté à la matière :\n"
        "   • \"brief\"   — un seul fait clair → 1 paragraphe (40-70 mots)\n"
        "   • \"deep\"    — article riche, plusieurs angles → 2 à 3 paragraphes "
        "(90-200 mots au total)\n"
        "   • \"bullets\" — plusieurs faits distincts, récap, liste → 3 à 5 puces "
        "(12-25 mots chacune)\n"
        "   Dans le doute, prends le format PLUS long : mieux vaut garder une "
        "information que la perdre.\n"
        "3. Écris, dans la LANGUE SOURCE de l'article :\n"
        "   • title   : percutant, fidèle, ≤ 80 caractères\n"
        "   • lead    : UNE phrase, 15-28 mots — LA nouvelle, voix active, le "
        "fait d'abord. C'est ce que le lecteur voit sur la carte du fil.\n"
        "   • body    : le développement au format choisi (liste de paragraphes "
        "ou liste de puces). Il apporte ce que le lead ne dit pas : contexte, "
        "chiffres, conséquences, réactions. JAMAIS une répétition du lead.\n\n"
        "EXACTITUDE : n'ajoute AUCUN fait absent du source. Ne recopie pas de "
        "phrase du source — réécris. « primer capitán / primera capitana » "
        "désigne le RANG dans la hiérarchie des capitaines (capitaine n°1), "
        "jamais une première historique sauf mention explicite. Si le sujet "
        "est une joueuse ou une équipe féminine, accorde tout au féminin. "
        "Coupe du monde 2026 (48 équipes) : "
        "seizièmes (32) → huitièmes (16) → quarts → demies → finale ; gagner en "
        "seizièmes qualifie pour les HUITIÈMES. Si le tour n'est pas nommé, "
        "écris « pour la suite du tournoi ».\n" + ANTI_IA + "\n"
        'JSON : {"title": "...", "lead": "...", "format": "brief|deep|bullets", '
        '"body": ["...", "..."]}',
        write_payload, max_tokens=900)
    if not redac or not redac.get("lead"):
        return None
    fmt = redac.get("format") if redac.get("format") in FORMATS else "brief"
    body_parts = [str(p).strip() for p in (redac.get("body") or []) if str(p).strip()]

    # ── Étape 4 : EXPERT EN TRADUCTION — transcréation ─────────────────────
    names = ", ".join(f'"{l}" ({LANG_NAMES.get(l, l)})' for l in langs)
    terms = protected_terms(title, redac.get("lead", ""), " ".join(body_parts))
    trad = _stage(
        "Tu es un EXPERT EN TRADUCTION-LOCALISATION de presse sportive, natif de "
        "chaque langue cible. TRANSCRÉE ce paquet — surtout PAS de mot-à-mot : "
        "phrasé naturel d'un journaliste sportif natif, idiomes du pays, registre "
        "flash info. Garde les chiffres et scores exacts. Conserve le MÊME nombre "
        "d'éléments dans body, dans le même ordre.\n"
        "Langues cibles : " + names + "\n" + prompt_block(terms, langs) + "\n" + ANTI_IA + "\n"
        'JSON : {"fr": {"title": "...", "lead": "...", "body": ["..."]}, ...} '
        "(une entrée par langue cible)",
        json.dumps({"source_lang": src, "title": redac.get("title") or title,
                    "lead": redac["lead"], "format": fmt, "body": body_parts},
                   ensure_ascii=False),
        max_tokens=2200)
    if not trad:
        return None

    # ── Étape 5 : RÉDACTEUR EN CHEF — validation finale ────────────────────
    # Le validateur reçoit l'article COMPLET (comme le rédacteur), pas un
    # extrait : on ne peut pas juger la complétude d'un résumé contre 1 500
    # caractères. C'est ce qui a laissé passer un lead qui ratait le fait
    # central (« le quatuor de capitaines devient un quintette mené par
    # Patri Guijarro » — absent du résumé publié).
    valid = _stage(
        "Tu es le RÉDACTEUR EN CHEF. Tu as l'ARTICLE SOURCE COMPLET et la "
        "proposition multilingue. Contrôle FINAL avant publication :\n"
        "• COMPLÉTUDE — relis l'article source EN ENTIER puis demande-toi : "
        "un lecteur qui ne lit que notre lead + body connaît-il le fait "
        "central ET les faits majeurs (qui exactement, combien, quel rang, "
        "quelle conséquence) ? Si un fait majeur du source manque, RÉÉCRIS le "
        "lead ou le body pour l'inclure — c'est ta responsabilité, pas celle "
        "d'une étape précédente ;\n"
        "• fidélité aux faits du source, aucune invention, scores/tours exacts "
        "(rappel CdM 2026 : seizièmes AVANT huitièmes) ; « primera capitana » "
        "= rang n°1, pas une première historique ; sujet féminin → féminin "
        "partout ;\n"
        "• le lead porte bien L'INFORMATION CENTRALE, pas une paraphrase du titre ;\n"
        "• body apporte du neuf par rapport au lead, sans redite ;\n"
        "• NOMS PROPRES intacts dans les langues latines : un club ne se traduit "
        "jamais (« Real Madrid » n'est pas « Royal Madrid », « Córdoba » n'est "
        "pas « Cordoue »). En ARABE c'est l'inverse : AUCUN mot en alphabet "
        "latin ne doit subsister — tout nom propre est translittéré "
        "(Arsenal → أرسنال, Mikel Arteta → ميكيل أرتيتا). Un titre arabe "
        "contenant un mot latin est à réécrire ;\n"
        "• chaque version sonne comme un flash info NATIF, écrit par un humain ;\n"
        "• titres ≤ 80 caractères, lead 15-28 mots.\n"
        "Corrige DIRECTEMENT ce qui doit l'être et renvoie le paquet final. "
        "publish=false seulement si le fond est irrécupérable.\n" + ANTI_IA + "\n"
        'JSON : {"publish": true|false, "i18n": {lang: {"title","lead","body":[...]}}}',
        json.dumps({"source": {"title": title, "text": body[:6000],
                                "lu": origin},
                    "proposition": trad}, ensure_ascii=False),
        max_tokens=2400)
    if not valid or "publish" not in valid:
        return None

    i18n = {}
    final = valid.get("i18n") if valid.get("publish") else None
    if final:
        for l in langs:
            e = (final.get(l) or trad.get(l) or {})
            t = str(e.get("title", "")).strip()[:300]
            lead = str(e.get("lead", "")).strip()[:600]
            parts = [str(p).strip()[:800] for p in (e.get("body") or []) if str(p).strip()]
            if t or lead:
                i18n[l] = {
                    "title": t or title,
                    # `summary` reste le champ historique (cartes, RSS, OG) : on y
                    # met le lead pour ne casser aucun consommateur en aval.
                    "summary": lead or summary,
                    "body": parts,
                    "format": fmt,
                    "needs_translation": False,
                    "engine": "gemini-editor",
                }
    # Filet déterministe sur les calques, après le modèle.
    i18n = repair_pack(i18n)

    return _memo({
        "publish": bool(valid.get("publish")),
        "reason": str(judge.get("reason", ""))[:200],
        "quality": int(judge.get("quality", 0) or 0),
        "i18n": i18n if len(i18n) == len(langs) else None,
        "source_read": origin,
    })


def translator_hash(title, summary, src, langs):
    import hashlib
    raw = (title + "|" + (summary or "")[:200] + "|" + src + "|" + ",".join(langs)).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]
