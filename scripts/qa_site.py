#!/usr/bin/env python3
"""qa_site.py — protocole de vérification avant validation.

`qa-check.js` vérifie la cohérence des compteurs de buts. `audit_editorial.py`
juge la qualité du fil News. Il manquait le reste : les coquilles, les données
périmées, les liens morts, les balises SEO absentes — tout ce qui ne casse rien
techniquement mais que le visiteur voit.

Sept familles de contrôles, aucune dépendance réseau :

  1. fraicheur    — données trop vieilles, prochain match déjà passé
  2. coherence    — compteurs qui se contredisent entre fichiers
  3. placeholder  — jeton de configuration jamais remplacé, TODO, lorem ipsum
  4. json         — fichier de données illisible
  5. lien_mort    — lien interne vers une page qui n'existe pas
  6. seo          — title, meta description, canonical ou OG manquants
  7. langue       — mention de langue codée en dur, texte non traduit

  python scripts/qa_site.py                  # rapport console
  python scripts/qa_site.py --json qa.json   # rapport machine
  python scripts/qa_site.py --strict         # les avertissements deviennent bloquants

Code de sortie : 1 s'il reste une erreur (ou un avertissement en --strict).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"

# Pages qui doivent être irréprochables : ce sont les portes d'entrée.
PAGES_CLES = ["index.html", "news.html", "goals.html", "about.html", "contact.html"]

# Fichiers de données dont l'illisibilité casse le site en silence (le JS
# échoue, la page reste sur son contenu statique périmé).
DONNEES = ["stats.json", "news.json", "goals-data.json", "wc.json",
           "dashboard-data.json"]

# Âge maximal toléré avant de considérer la donnée comme périmée.
AGE_MAX = {"stats.json": timedelta(days=3), "news.json": timedelta(hours=12)}

# (motif, libellé, sensible_à_la_casse)
PLACEHOLDERS = [
    (r"REMPLACER_PAR[A-Z_]*", "jeton de configuration jamais remplacé", True),
    # Sensible à la casse : « TODO » est un oubli, « Todo el fútbol » est de
    # l'espagnol tout à fait légitime dans un bundle de traduction.
    (r"\bTODO\b(?![-_])", "TODO laissé dans une page publiée", True),
    (r"\bFIXME\b", "FIXME laissé dans une page publiée", True),
    (r"lorem ipsum", "faux texte de maquette", False),
    (r"XXXX+", "valeur de remplissage", True),
    (r"\[object Object\]", "objet JS rendu en texte", True),
]

# Le fil agrège plusieurs langues sources : annoncer la mauvaise décrédibilise
# autant qu'une faute de fond. On ne cherche pas le mot « anglais » (souvent
# juste), on croise le libellé affiché avec la langue réelle de la source.
LIBELLES_LANGUE = {
    "en": "anglais", "es": "espagnol", "fr": "français", "ar": "arabe",
    "de": "allemand", "it": "italien", "pt": "portugais", "nl": "néerlandais",
}

_TAG = re.compile(r"<[^>]+>")


class Rapport:
    def __init__(self) -> None:
        self.entrees: list[dict] = []

    def add(self, niveau: str, famille: str, ou: str, quoi: str) -> None:
        self.entrees.append({"niveau": niveau, "famille": famille,
                             "ou": ou, "quoi": quoi})

    def erreur(self, famille, ou, quoi):
        self.add("erreur", famille, ou, quoi)

    def alerte(self, famille, ou, quoi):
        self.add("alerte", famille, ou, quoi)

    @property
    def erreurs(self):
        return [e for e in self.entrees if e["niveau"] == "erreur"]

    @property
    def alertes(self):
        return [e for e in self.entrees if e["niveau"] == "alerte"]


def _iso(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        d = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


# ── 1. Fraîcheur ────────────────────────────────────────────────────────────
def controle_fraicheur(r: Rapport, maintenant: datetime) -> None:
    for nom, age_max in AGE_MAX.items():
        chemin = PUBLIC / nom
        if not chemin.exists():
            r.erreur("fraicheur", nom, "fichier de données absent")
            continue
        try:
            data = json.loads(chemin.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue        # signalé par controle_json
        horodatage = _iso(data.get("last_updated") or data.get("generated_at"))
        if not horodatage:
            r.alerte("fraicheur", nom, "aucun horodatage exploitable")
            continue
        age = maintenant - horodatage
        if age > age_max:
            jours = age.days or round(age.total_seconds() / 3600, 1)
            unite = "j" if age.days else "h"
            r.erreur("fraicheur", nom,
                     f"donnée vieille de {jours}{unite} (max {age_max}) — "
                     "la synchro ne tourne probablement plus")

    stats = _charge(PUBLIC / "stats.json")
    if not stats:
        return
    prochain = _iso((stats.get("next_match") or {}).get("kickoff_utc"))
    if prochain and prochain < maintenant:
        r.erreur("fraicheur", "stats.json",
                 f"le « prochain match » est daté du {prochain:%d/%m/%Y}, "
                 "donc déjà joué")
    dernier = _iso((stats.get("last_match") or {}).get("date_iso"))
    if dernier and prochain and dernier > prochain:
        r.erreur("fraicheur", "stats.json",
                 "le dernier match est postérieur au prochain")


# ── 2. Cohérence ────────────────────────────────────────────────────────────
def _charge(chemin: Path):
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def controle_coherence(r: Rapport) -> None:
    stats = _charge(PUBLIC / "stats.json")
    if not stats:
        return
    buts = stats.get("goals")
    cible = stats.get("target", 1000)

    if buts is not None and stats.get("remaining") is not None:
        if stats["remaining"] != cible - buts:
            r.erreur("coherence", "stats.json",
                     f"remaining={stats['remaining']} au lieu de {cible - buts}")

    base = _charge(PUBLIC / "goals-data.json")
    if isinstance(base, list) and buts is not None and base:
        dernier = max((g.get("num") or 0) for g in base)
        if dernier != buts:
            r.erreur("coherence", "goals-data.json",
                     f"{len(base)} buts en base, le plus haut est n°{dernier}, "
                     f"mais le compteur affiche {buts} — "
                     f"{buts - dernier} but(s) sans fiche")

    # Le compteur affiché dans le HTML doit suivre stats.json : deux valeurs
    # différentes sur la même page, c'est le premier truc que le lecteur voit.
    if buts is not None:
        index = _lit(PUBLIC / "index.html")
        if index:
            for motif, libelle in ((r"Live\s*·\s*(\d{3,4})", "pastille Live"),
                                   (r'aria-valuenow="(\d{3,4})"', "barre de progression")):
                for m in re.finditer(motif, index):
                    if int(m.group(1)) != buts:
                        r.erreur("coherence", "index.html",
                                 f"{libelle} affiche {m.group(1)} au lieu de {buts}")


# ── 3. Placeholders ─────────────────────────────────────────────────────────
def _lit(chemin: Path) -> str:
    try:
        return chemin.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


_COMMENTAIRE = re.compile(r"<!--.*?-->", re.S)


def controle_placeholders(r: Rapport, pages: list[Path]) -> None:
    for page in pages:
        # Les commentaires HTML ne sont pas rendus : un « TODO » qui note une
        # décision en attente n'est pas une coquille visible par le lecteur.
        # Un jeton dans un attribut `content`, si.
        texte = _COMMENTAIRE.sub(" ", _lit(page))
        nom = page.relative_to(PUBLIC).as_posix()
        for motif, libelle, casse in PLACEHOLDERS:
            m = re.search(motif, texte, 0 if casse else re.I)
            if m:
                r.erreur("placeholder", nom, f"{libelle} : « {m.group(0)[:40]} »")


# ── 4. JSON ─────────────────────────────────────────────────────────────────
def controle_json(r: Rapport) -> None:
    for nom in DONNEES:
        chemin = PUBLIC / nom
        if not chemin.exists():
            r.alerte("json", nom, "absent")
            continue
        try:
            json.loads(chemin.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            r.erreur("json", nom, f"illisible : {e}")

    # Le JSON-LD nourrit les résultats enrichis Google : cassé, il est ignoré
    # en silence et on perd l'affichage sans jamais le savoir.
    for page in [PUBLIC / p for p in PAGES_CLES if (PUBLIC / p).exists()]:
        texte = _lit(page)
        for i, bloc in enumerate(re.findall(
                r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                texte, re.S)):
            try:
                json.loads(bloc)
            except json.JSONDecodeError as e:
                r.erreur("json", page.name, f"JSON-LD n°{i + 1} invalide : {e}")


# ── 5. Liens internes ───────────────────────────────────────────────────────
def charge_redirections() -> list[tuple[str, str]]:
    """Règles de `public/_redirects` (format Cloudflare Pages / Netlify).

    Un lien couvert par une redirection 301 n'est pas un lien mort : le site
    servait 2 335 pages pointant vers /world-cup/*, toutes redirigées vers
    /coupe-du-monde/. Sans cette lecture, l'audit noyait ses vraies trouvailles
    sous des milliers de faux positifs.
    """
    fichier = PUBLIC / "_redirects"
    regles: list[tuple[str, str]] = []
    if not fichier.exists():
        return regles
    for ligne in _lit(fichier).splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#"):
            continue
        morceaux = ligne.split()
        if len(morceaux) >= 2:
            regles.append((morceaux[0], morceaux[1]))
    return regles


def _redirige(cible: str, regles: list[tuple[str, str]]) -> bool:
    for source, _ in regles:
        if source.endswith("*"):
            if cible.startswith(source[:-1]):
                return True
        elif cible == source or cible == source.rstrip("/"):
            return True
    return False


def controle_liens(r: Rapport, pages: list[Path]) -> None:
    regles = charge_redirections()
    for page in pages:
        texte = _lit(page)
        nom = page.relative_to(PUBLIC).as_posix()
        vus: set[str] = set()
        for m in re.finditer(r'href="(/[^"#?]*)', texte):
            cible = unquote(m.group(1))
            # Un href assemblé en JS (`/news/'+esc(it.id)+'.html`) n'est pas un
            # chemin : le vérifier sur le disque n'a aucun sens.
            if any(c in cible for c in ("'", "+", "${", "`", "{{")):
                continue
            if cible in vus or urlparse(cible).scheme:
                continue
            vus.add(cible)
            chemin = PUBLIC / cible.lstrip("/")
            if cible.endswith("/"):
                existe = (chemin / "index.html").exists() or chemin.is_dir()
            else:
                existe = (chemin.exists()
                          or chemin.with_suffix(".html").exists()
                          or (chemin / "index.html").exists())
            if not existe and not _redirige(cible, regles):
                r.alerte("lien_mort", nom, f"« {cible} » ne correspond à aucun fichier")


# ── 6. SEO ──────────────────────────────────────────────────────────────────
def controle_seo(r: Rapport) -> None:
    attendus = [
        (r"<title>(.{10,})</title>", "title"),
        (r'<meta[^>]+name="description"[^>]+content="(.{40,})"', "meta description"),
        (r'<link[^>]+rel="canonical"', "canonical"),
        (r'<meta[^>]+property="og:title"', "og:title"),
        (r'<meta[^>]+property="og:image"', "og:image"),
    ]
    for nom in PAGES_CLES:
        chemin = PUBLIC / nom
        if not chemin.exists():
            r.alerte("seo", nom, "page clé absente")
            continue
        texte = _lit(chemin)
        for motif, libelle in attendus:
            if not re.search(motif, texte, re.I | re.S):
                r.erreur("seo", nom, f"{libelle} manquant ou trop court")


# ── 7. Mentions de langue ───────────────────────────────────────────────────
def controle_langue(r: Rapport) -> None:
    """La langue annoncée sur la page article correspond-elle à la source ?"""
    news = _charge(PUBLIC / "news.json")
    if not isinstance(news, dict):
        return
    for item in news.get("items", []):
        page = PUBLIC / "news" / f"{item.get('id')}.html"
        if not page.exists():
            continue
        texte = _lit(page)
        m = re.search(r"Voir le texte original(?:\s*\(([^)]+)\))?", texte)
        if not m:
            continue
        affiche = (m.group(1) or "").strip()
        attendu = LIBELLES_LANGUE.get(
            ((item.get("primary_source") or {}).get("lang") or "")[:2].lower(), "")
        if affiche and affiche != attendu:
            r.erreur("langue", f"news/{item.get('id')}.html",
                     f"annonce « {affiche} » alors que la source est "
                     f"{attendu or 'de langue inconnue'}")


def controle_redirections(r: Rapport) -> None:
    """Une 301 vers un 404, c'est pire qu'un lien mort : le visiteur y croit."""
    for source, destination in charge_redirections():
        if destination.startswith(("http://", "https://")) or "*" in destination:
            continue
        chemin = PUBLIC / destination.lstrip("/")
        existe = ((chemin / "index.html").exists() or chemin.exists()
                  or chemin.with_suffix(".html").exists())
        if not existe:
            r.erreur("lien_mort", "_redirects",
                     f"« {source} » redirige vers « {destination} », qui n'existe pas")


def pages_a_verifier(limite: int) -> list[Path]:
    """Pages clés + un échantillon d'articles (les plus récents)."""
    pages = [PUBLIC / p for p in PAGES_CLES if (PUBLIC / p).exists()]
    articles = sorted((PUBLIC / "news").glob("*.html"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
    pages += articles[:limite]
    pages += sorted((PUBLIC / "blog").glob("*.html"))[:limite]
    return pages


def rendu(r: Rapport, verbeux: bool) -> str:
    lignes = ["", "═══ QA SITE — to1000.com ═══", ""]
    if not r.entrees:
        lignes += ["  Aucun problème détecté.", ""]
        return "\n".join(lignes)

    for niveau, symbole in (("erreur", "✗"), ("alerte", "!")):
        entrees = [e for e in r.entrees if e["niveau"] == niveau]
        if not entrees:
            continue
        lignes.append(f"  {niveau.upper()}S ({len(entrees)})")
        familles: dict[str, list[dict]] = {}
        for e in entrees:
            familles.setdefault(e["famille"], []).append(e)
        for famille, items in familles.items():
            lignes.append(f"    {famille} — {len(items)}")
            # Sans --verbeux on montre trois cas : de quoi agir sans noyer.
            for e in (items if verbeux else items[:3]):
                lignes.append(f"      {symbole} {e['ou']} : {e['quoi']}")
            if not verbeux and len(items) > 3:
                lignes.append(f"        … et {len(items) - 3} autre(s)")
        lignes.append("")

    lignes.append(f"  Total : {len(r.erreurs)} erreur(s), {len(r.alertes)} alerte(s)")
    lignes.append("")
    return "\n".join(lignes)


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit de cohérence du site")
    ap.add_argument("--json", dest="json_out", help="écrit le rapport JSON ici")
    ap.add_argument("--strict", action="store_true",
                    help="les alertes deviennent bloquantes")
    ap.add_argument("--verbeux", action="store_true", help="liste tous les cas")
    ap.add_argument("--echantillon", type=int, default=25,
                    help="nombre d'articles échantillonnés (défaut 25)")
    args = ap.parse_args()

    if not PUBLIC.exists():
        print(f"[qa] {PUBLIC} introuvable", file=sys.stderr)
        return 2

    maintenant = datetime.now(timezone.utc)
    pages = pages_a_verifier(args.echantillon)
    r = Rapport()

    controle_fraicheur(r, maintenant)
    controle_coherence(r)
    controle_json(r)
    controle_placeholders(r, pages)
    controle_liens(r, pages)
    controle_seo(r)
    controle_langue(r)
    controle_redirections(r)

    print(rendu(r, args.verbeux))

    if args.json_out:
        sortie = Path(args.json_out)
        sortie.parent.mkdir(parents=True, exist_ok=True)
        sortie.write_text(json.dumps({
            "genere_le": maintenant.isoformat(timespec="seconds"),
            "pages_verifiees": len(pages),
            "erreurs": len(r.erreurs),
            "alertes": len(r.alertes),
            "entrees": r.entrees,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[qa] rapport écrit : {sortie}")

    if r.erreurs or (args.strict and r.alertes):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
