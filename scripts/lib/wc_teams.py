"""wc_teams.py — les 48 équipes de la Coupe du Monde 2026.

Clé = id d'équipe ESPN (stable, déjà utilisé par espn_client pour le Portugal).
`fr` = nom d'affichage français, `slug` = segment d'URL (/coupe-du-monde/equipe/{slug}/),
`iso2` = code drapeau flagcdn.com (motif déjà utilisé sur la home pour le prochain match).
"""
from __future__ import annotations

import re

TEAMS: dict[str, dict] = {
    "624":   {"en": "Algeria",            "fr": "Algérie",          "slug": "algerie",          "iso2": "dz"},
    "202":   {"en": "Argentina",          "fr": "Argentine",        "slug": "argentine",        "iso2": "ar"},
    "628":   {"en": "Australia",          "fr": "Australie",        "slug": "australie",        "iso2": "au"},
    "474":   {"en": "Austria",            "fr": "Autriche",         "slug": "autriche",         "iso2": "at"},
    "459":   {"en": "Belgium",            "fr": "Belgique",         "slug": "belgique",         "iso2": "be"},
    "452":   {"en": "Bosnia-Herzegovina", "fr": "Bosnie-Herzégovine","slug": "bosnie-herzegovine","iso2": "ba"},
    "205":   {"en": "Brazil",             "fr": "Brésil",           "slug": "bresil",           "iso2": "br"},
    "206":   {"en": "Canada",             "fr": "Canada",           "slug": "canada",           "iso2": "ca"},
    "2597":  {"en": "Cape Verde",         "fr": "Cap-Vert",         "slug": "cap-vert",         "iso2": "cv"},
    "208":   {"en": "Colombia",           "fr": "Colombie",         "slug": "colombie",         "iso2": "co"},
    "2850":  {"en": "Congo DR",           "fr": "RD Congo",         "slug": "rd-congo",         "iso2": "cd"},
    "477":   {"en": "Croatia",            "fr": "Croatie",          "slug": "croatie",          "iso2": "hr"},
    "11678": {"en": "Curaçao",            "fr": "Curaçao",          "slug": "curacao",          "iso2": "cw"},
    "450":   {"en": "Czechia",            "fr": "Tchéquie",         "slug": "tchequie",         "iso2": "cz"},
    "209":   {"en": "Ecuador",            "fr": "Équateur",         "slug": "equateur",         "iso2": "ec"},
    "2620":  {"en": "Egypt",              "fr": "Égypte",           "slug": "egypte",           "iso2": "eg"},
    "448":   {"en": "England",            "fr": "Angleterre",       "slug": "angleterre",       "iso2": "gb-eng"},
    "478":   {"en": "France",             "fr": "France",           "slug": "france",           "iso2": "fr"},
    "481":   {"en": "Germany",            "fr": "Allemagne",        "slug": "allemagne",        "iso2": "de"},
    "4469":  {"en": "Ghana",              "fr": "Ghana",            "slug": "ghana",            "iso2": "gh"},
    "2654":  {"en": "Haiti",              "fr": "Haïti",            "slug": "haiti",            "iso2": "ht"},
    "469":   {"en": "Iran",               "fr": "Iran",             "slug": "iran",             "iso2": "ir"},
    "4375":  {"en": "Iraq",               "fr": "Irak",             "slug": "irak",             "iso2": "iq"},
    "4789":  {"en": "Ivory Coast",        "fr": "Côte d'Ivoire",    "slug": "cote-divoire",     "iso2": "ci"},
    "627":   {"en": "Japan",              "fr": "Japon",            "slug": "japon",            "iso2": "jp"},
    "2917":  {"en": "Jordan",             "fr": "Jordanie",         "slug": "jordanie",         "iso2": "jo"},
    "203":   {"en": "Mexico",             "fr": "Mexique",          "slug": "mexique",          "iso2": "mx"},
    "2869":  {"en": "Morocco",            "fr": "Maroc",            "slug": "maroc",            "iso2": "ma"},
    "449":   {"en": "Netherlands",        "fr": "Pays-Bas",         "slug": "pays-bas",         "iso2": "nl"},
    "2666":  {"en": "New Zealand",        "fr": "Nouvelle-Zélande", "slug": "nouvelle-zelande", "iso2": "nz"},
    "464":   {"en": "Norway",             "fr": "Norvège",          "slug": "norvege",          "iso2": "no"},
    "2659":  {"en": "Panama",             "fr": "Panama",           "slug": "panama",           "iso2": "pa"},
    "210":   {"en": "Paraguay",           "fr": "Paraguay",         "slug": "paraguay",         "iso2": "py"},
    "482":   {"en": "Portugal",           "fr": "Portugal",         "slug": "portugal",         "iso2": "pt"},
    "4398":  {"en": "Qatar",              "fr": "Qatar",            "slug": "qatar",            "iso2": "qa"},
    "655":   {"en": "Saudi Arabia",       "fr": "Arabie saoudite",  "slug": "arabie-saoudite",  "iso2": "sa"},
    "580":   {"en": "Scotland",           "fr": "Écosse",           "slug": "ecosse",           "iso2": "gb-sct"},
    "654":   {"en": "Senegal",            "fr": "Sénégal",          "slug": "senegal",          "iso2": "sn"},
    "467":   {"en": "South Africa",       "fr": "Afrique du Sud",   "slug": "afrique-du-sud",   "iso2": "za"},
    "451":   {"en": "South Korea",        "fr": "Corée du Sud",     "slug": "coree-du-sud",     "iso2": "kr"},
    "164":   {"en": "Spain",              "fr": "Espagne",          "slug": "espagne",          "iso2": "es"},
    "466":   {"en": "Sweden",             "fr": "Suède",            "slug": "suede",            "iso2": "se"},
    "475":   {"en": "Switzerland",        "fr": "Suisse",           "slug": "suisse",           "iso2": "ch"},
    "659":   {"en": "Tunisia",            "fr": "Tunisie",          "slug": "tunisie",          "iso2": "tn"},
    "465":   {"en": "Türkiye",            "fr": "Turquie",          "slug": "turquie",          "iso2": "tr"},
    "660":   {"en": "United States",      "fr": "États-Unis",       "slug": "etats-unis",       "iso2": "us"},
    "212":   {"en": "Uruguay",            "fr": "Uruguay",          "slug": "uruguay",          "iso2": "uy"},
    "2570":  {"en": "Uzbekistan",         "fr": "Ouzbékistan",      "slug": "ouzbekistan",      "iso2": "uz"},
}

# Slots pas encore décidés ("Quarterfinal 1 Winner", "Round of 32 11 Winner",
# "Semifinal 2 Loser", "TBD"…). Mots entiers pour ne pas matcher un vrai nom.
_PLACEHOLDER_RE = re.compile(r"\b(Winner|Loser|TBD)\b|\bRound of \d+\b|^To Be", re.I)


def is_placeholder(team_name: str) -> bool:
    return bool(_PLACEHOLDER_RE.search(team_name or ""))


def team_by_espn_id(espn_id: str) -> dict | None:
    return TEAMS.get(str(espn_id))
