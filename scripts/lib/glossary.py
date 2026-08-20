"""glossary.py — protection des noms propres à la traduction.

Le problème qu'on répare : le pipeline traduisait « Real Madrid » en « Royal
Madrid », « Córdoba CF » en « Cordoue CF », « Girona » en « Gérone ». Un nom de
club n'est pas un mot : c'est une marque. Un site qui écrit « Royal Madrid »
perd sa crédibilité de source d'info en une ligne.

Trois couches, du moins cher au plus cher :

1. `protected_terms(text)` — repère les noms propres présents dans le texte
   source (clubs connus + entités capitalisées). On les injecte dans le prompt
   de traduction : « reproduis ces chaînes CARACTÈRE POUR CARACTÈRE ».
2. `repair_calques(text, lang)` — corrige après coup les calques connus
   (« Royal Madrid » → « Real Madrid »). Filet de sécurité déterministe, zéro
   appel API.
3. `missing_terms(src_text, out_text, lang)` — signale les noms propres du
   source qui ont disparu de la traduction. Sert au council d'audit.

L'arabe est exempté des couches 1 et 3 : les noms propres y sont
translittérés (ريال مدريد), donc « présent à l'identique » n'a pas de sens.
"""
from __future__ import annotations

import re

# Langues où un nom propre latin doit rester tel quel. L'arabe translittère.
LATIN_LANGS = {"fr", "en", "es", "pt", "it", "de", "nl"}

# ── Clubs, sélections et compétitions dont le nom ne se traduit jamais ──
# Liste volontairement courte : elle sert d'amorce au repérage. La détection
# générique (mots capitalisés) attrape le reste.
PROTECTED_NAMES = [
    # Espagne — les plus massacrés par la traduction automatique
    "Real Madrid", "Real Sociedad", "Real Betis", "Real Valladolid", "Real Oviedo",
    "Atlético de Madrid", "Atlético Madrid", "Athletic Club", "Athletic Bilbao",
    "Córdoba CF", "Girona FC", "Girona", "Sevilla FC", "Real Zaragoza",
    "Deportivo La Coruña", "Villarreal CF", "Villarreal", "Rayo Vallecano",
    "Celta de Vigo", "Espanyol", "Getafe CF", "Valencia CF", "Osasuna",
    "LaLiga", "LaLiga Hypermotion", "LaLiga EA Sports",
    # Portugal
    "Sporting CP", "Sporting Clube de Portugal", "SL Benfica", "Benfica",
    "FC Porto", "Vitória de Guimarães", "Braga", "Primeira Liga",
    # Angleterre
    "Manchester United", "Manchester City", "Newcastle United", "Tottenham Hotspur",
    "Aston Villa", "West Ham United", "Nottingham Forest", "Crystal Palace",
    "Wolverhampton Wanderers", "Premier League", "Championship",
    # Italie / Allemagne / France
    "Inter", "Inter Milan", "AC Milan", "Juventus", "AS Roma", "SSC Napoli",
    "Bayern Munich", "Bayern München", "Borussia Dortmund", "Bayer Leverkusen",
    "RB Leipzig", "Eintracht Frankfurt", "Bundesliga", "Serie A",
    "Paris Saint-Germain", "Olympique de Marseille", "Olympique Lyonnais",
    "AS Monaco", "LOSC Lille", "Ligue 1",
    # Moyen-Orient / Afrique / Amériques
    "Al Nassr", "Al-Nassr", "Al Hilal", "Al-Hilal", "Al Ittihad", "Al-Ittihad",
    "Al Ahli", "Al-Ahly", "Wydad AC", "Raja Club Athletic", "Saudi Pro League",
    "Botafogo", "Flamengo", "Palmeiras", "River Plate", "Boca Juniors",
    # Compétitions
    "Champions League", "UEFA Champions League", "Europa League",
    "Conference League", "Nations League", "Copa del Rey", "Copa Libertadores",
    "FIFA Club World Cup", "Ballon d'Or", "Coupe du Monde", "World Cup",
    "CAN", "AFCON", "Euro",
    # Stades / lieux-marques
    "Santiago Bernabéu", "Camp Nou", "Anfield", "Old Trafford",
    "Estádio José Alvalade", "Estádio da Luz", "Signal Iduna Park",
]

# ── Calques connus → forme correcte, par langue ──
# Uniquement des erreurs certaines : on ne touche pas aux exonymes légitimes
# (la ville de Séville, Munich, Turin restent traduisibles hors nom de club).
CALQUES = {
    "fr": [
        (r"\bRoyal(?:e)? Madrid\b", "Real Madrid"),
        (r"\bRéel(?:le)? Madrid\b", "Real Madrid"),
        (r"\bRoyal(?:e)? Sociedad\b", "Real Sociedad"),
        (r"\bRéel(?:le)? Sociedad\b", "Real Sociedad"),
        (r"\bRoyal(?:e)? Betis\b", "Real Betis"),
        (r"\bCordoue CF\b", "Córdoba CF"),
        (r"\bGérone FC\b", "Girona FC"),
        (r"\bGérone\b", "Girona"),
        (r"\bSaragosse\b", "Zaragoza"),
        (r"\bLa Corogne\b", "La Coruña"),
        (r"\bSéville FC\b", "Sevilla FC"),
        (r"\bLe Betis\b", "Le Real Betis"),
        (r"\bAthlétique Club\b", "Athletic Club"),
        (r"\bAthlétique Bilbao\b", "Athletic Bilbao"),
        (r"\bVillaréal\b", "Villarreal"),
        (r"\bSportif(?:ve)? CP\b", "Sporting CP"),
        (r"\bLigue des Nations\b", "Nations League"),
        (r"\bBallon d'or\b", "Ballon d'Or"),
    ],
    "en": [
        (r"\bRoyal Madrid\b", "Real Madrid"),
        (r"\bRoyal Sociedad\b", "Real Sociedad"),
        (r"\bRoyal Betis\b", "Real Betis"),
        (r"\bCordoba CF\b", "Córdoba CF"),
        (r"\bGerona FC\b", "Girona FC"),
    ],
    "es": [
        (r"\bReal Madrid CF de Madrid\b", "Real Madrid"),
        (r"\bManchester Unido\b", "Manchester United"),
        (r"\bNiños de la Ciudad\b", "Manchester City"),
    ],
    # Faux sens certains en arabe — erreurs de REGISTRE, pas d'orthographe.
    # « قبطان » est un capitaine de NAVIRE : la presse sportive arabe écrit
    # قائد الفريق (fém. قائدة). Vu en prod : « أول قبطان لبرجة » pour la
    # première capitaine du Barça féminin. Même logique que « Royal Madrid » :
    # un seul mot suffit à trahir la traduction automatique.
    "ar": [
        (r"قبطانة", "قائدة"),
        (r"القبطانة", "القائدة"),
        (r"قبطان", "قائد"),
        (r"القبطان", "القائد"),
        (r"حارس البوابة", "حارس المرمى"),
        (r"حارسة البوابة", "حارسة المرمى"),
    ],
}

_CALQUES_C = {
    lang: [(re.compile(p, re.I), r) for p, r in rules]
    for lang, rules in CALQUES.items()
}

# Un nom propre = suite de mots capitalisés, éventuellement liés par de/du/of…
# Bornée à 4 mots : sans limite, la regex enchaînait les groupes capitalisés
# séparés par de la ponctuation et produisait des chimères du genre
# « LaLiga Hypermotion El Córdoba CF », inutilisables comme terme protégé.
_PROPER_RE = re.compile(
    r"\b[A-ZÀ-ÝÄÖÜ][\w'’\-]+(?:\s+(?:de|del|da|do|of|van|von|el|al|le|la)\s+"
    r"[A-ZÀ-ÝÄÖÜ][\w'’\-]+)?"
    r"(?:\s+[A-ZÀ-ÝÄÖÜ][\w'’\-]+){0,2}"
)

# Mots capitalisés en début de phrase qui ne sont pas des noms propres.
_NOT_PROPER = {
    "le", "la", "les", "un", "une", "des", "ce", "cette", "ces", "il", "elle",
    "the", "a", "an", "this", "that", "these", "his", "her", "after", "before",
    "el", "los", "las", "una", "este", "esta", "der", "die", "das", "ein",
    "selon", "après", "avant", "mais", "pour", "avec", "dans", "sur", "quand",
    "and", "but", "for", "with", "from", "when", "what", "why", "how",
    "y", "e", "o", "u", "en", "por", "para", "con", "sin", "sobre",
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def protected_terms(*texts: str, limit: int = 25) -> list[str]:
    """Noms propres à reproduire à l'identique dans la traduction.

    Union de deux sources : les clubs de PROTECTED_NAMES effectivement présents
    dans le texte, et les groupes capitalisés détectés génériquement (noms de
    joueurs, stades, villes-clubs que la liste ne connaît pas).
    """
    blob = _norm(" ".join(t for t in texts if t))
    if not blob:
        return []
    found: list[str] = []
    seen: set[str] = set()

    for name in PROTECTED_NAMES:
        if name.lower() in blob.lower() and name.lower() not in seen:
            seen.add(name.lower())
            found.append(name)

    for m in _PROPER_RE.finditer(blob):
        term = _norm(m.group(0)).strip(".,;:!?")
        # Un article en tête de phrase est capitalisé sans être un nom propre :
        # « El Córdoba CF » doit se réduire à « Córdoba CF ».
        head = term.split(" ", 1)
        while len(head) == 2 and head[0].lower() in _NOT_PROPER:
            term = head[1]
            head = term.split(" ", 1)
        if len(term) < 4 or term.lower() in _NOT_PROPER:
            continue
        # Un mot unique tout en majuscules est probablement un sigle bruyant.
        if term.isupper() and len(term.split()) == 1 and len(term) <= 3:
            continue
        low = term.lower()
        if low in seen or any(low in s for s in seen):
            continue
        seen.add(low)
        found.append(term)

    return found[:limit]


def repair_calques(text: str, lang: str) -> str:
    """Corrige les calques connus. Déterministe, sans appel API."""
    if not text:
        return text
    for rx, repl in _CALQUES_C.get(lang, []):
        text = rx.sub(repl, text)
    return text


def repair_pack(i18n: dict) -> dict:
    """Applique repair_calques sur title+summary de chaque langue d'un paquet."""
    for lang, entry in (i18n or {}).items():
        if not isinstance(entry, dict):
            continue
        for field in ("title", "summary"):
            if entry.get(field):
                entry[field] = repair_calques(entry[field], lang)
    return i18n


def missing_terms(src_text: str, out_text: str, lang: str,
                  terms: list[str] | None = None) -> list[str]:
    """Noms propres du source absents de la traduction — signal d'audit.

    Renvoie une liste vide pour l'arabe (translittération légitime) et pour un
    texte de sortie vide.
    """
    if lang not in LATIN_LANGS or not out_text:
        return []
    terms = terms if terms is not None else protected_terms(src_text)
    low = out_text.lower()
    return [t for t in terms if t.lower() not in low]


# Translittérations de référence pour l'arabe. La consigne « reproduis à
# l'identique » y est TOXIQUE : elle produit des titres mi-arabes mi-latins
# (« Arsenal يؤكد أن تجديد عقد Mikel Arteta ») — observé sur 25 articles sur 44.
# Pour un lecteur arabophone, c'est aussi décrédibilisant que « Royal Madrid »
# pour un francophone.
TRANSLITTERATIONS_AR = {
    "Real Madrid": "ريال مدريد", "Barcelona": "برشلونة", "Barça": "برشلونة",
    "Arsenal": "أرسنال", "Manchester United": "مانشستر يونايتد",
    "Manchester City": "مانشستر سيتي", "Liverpool": "ليفربول",
    "Chelsea": "تشيلسي", "Bayern Munich": "بايرن ميونخ",
    "Juventus": "يوفنتوس", "AC Milan": "ميلان", "Inter": "إنتر",
    "Paris Saint-Germain": "باريس سان جيرمان", "PSG": "باريس سان جيرمان",
    "Al Nassr": "النصر", "Al Hilal": "الهلال", "Al Ittihad": "الاتحاد",
    "Al-Ahly": "الأهلي", "Benfica": "بنفيكا", "FC Porto": "بورتو",
    "Sporting CP": "سبورتينغ لشبونة", "Atlético Madrid": "أتلتيكو مدريد",
    "Ligue 1": "الدوري الفرنسي", "Premier League": "الدوري الإنجليزي",
    "LaLiga": "الدوري الإسباني", "Serie A": "الدوري الإيطالي",
    "Bundesliga": "الدوري الألماني", "Champions League": "دوري أبطال أوروبا",
}


# Registre de la presse sportive arabe. Le problème n'est pas l'orthographe
# mais le SENS : un traducteur générique prend « capitaine » au sens maritime
# (قبطان) là où tout journaliste sportif écrit قائد الفريق. Ces équivalences
# vont dans le prompt arabe ; les cas certains ont en plus une réparation
# déterministe dans CALQUES["ar"].
LEXIQUE_SPORT_AR = (
    "\nREGISTRE SPORTIF ARABE — écris comme la presse sportive arabe "
    "(بي إن سبورتس، الجزيرة الرياضية، كووورة), jamais en calque de l'anglais ou "
    "de l'espagnol. Équivalences obligatoires :\n"
    "capitaine → قائد الفريق (JAMAIS قبطان — c'est un capitaine de navire) ; "
    "gardien → حارس المرمى ; entraîneur → مدرب / المدير الفني ; "
    "transfert → انتقال / صفقة ; mercato → الميركاتو / سوق الانتقالات ; "
    "doublé → ثنائية ; triplé → هاتريك ; clean sheet → شباك نظيفة ; "
    "prolongation de contrat → تجديد العقد ; prolongations (match) → "
    "الوقت الإضافي ; derby → ديربي ; montée → الصعود ; relégation → الهبوط ; "
    "match nul → تعادل ; blessure → إصابة ; suspension → إيقاف.\n"
    "FOOTBALL FÉMININ : accorde au féminin — قائدة، لاعبة، حارسة، مدرِّبة. "
    "« Première capitaine » se dit أول قائدة, jamais أول قائد ni أول قبطان."
)


def prompt_block(terms: list[str], langs: list[str] | None = None) -> str:
    """Bloc d'instruction à coller dans un prompt de traduction.

    `langs` sert à savoir s'il faut ajouter la consigne arabe : « reproduis à
    l'identique » ne doit JAMAIS s'appliquer à une langue qui translittère.
    """
    if not terms:
        return ""
    listed = " · ".join(terms)
    bloc = (
        "\nNOMS PROPRES — dans les langues à alphabet latin (français, anglais, "
        "espagnol, portugais…), reproduis ces chaînes CARACTÈRE POUR CARACTÈRE, "
        "sans les traduire, sans les franciser/hispaniser, accents compris :\n"
        + listed + "\n"
        "Un nom de club est une marque : « Real Madrid » ne devient jamais "
        "« Royal Madrid », « Córdoba » jamais « Cordoue », « Girona » jamais "
        "« Gérone »."
    )
    if langs is None or "ar" in langs:
        exemples = " · ".join(
            f"{lat} → {ar}" for lat, ar in list(TRANSLITTERATIONS_AR.items())[:6])
        bloc += (
            "\nEN ARABE, la règle est INVERSE : ne laisse AUCUN mot en alphabet "
            "latin. Translittère chaque nom propre selon l'usage de la presse "
            "arabe — noms de clubs, de joueurs, de compétitions, de villes. "
            "Exemples : " + exemples + ". Un titre arabe où subsiste un mot "
            "latin est à réécrire."
            + LEXIQUE_SPORT_AR
        )
    return bloc


_LATIN = re.compile(r"[A-Za-zÀ-ÿ]{3,}")


def latin_dans_arabe(text: str) -> list[str]:
    """Mots en alphabet latin restés dans un texte arabe.

    La presse arabe translittère les noms propres : un mot latin dans un titre
    arabe est une traduction inachevée, pas un choix éditorial.
    """
    return _LATIN.findall(text or "")
