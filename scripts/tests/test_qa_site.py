"""Protocole QA — chaque contrôle attrape son défaut, et rien d'autre.

Les faux positifs sont testés explicitement : un audit qui signale « Todo el
fútbol » comme un TODO oublié, ou 2 335 liens redirigés comme morts, finit par
ne plus être lu — et c'est alors qu'on rate la vraie coquille.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import qa_site  # noqa: E402
from qa_site import Rapport, _redirige  # noqa: E402

MAINTENANT = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def site(tmp_path, monkeypatch):
    """Un mini-site sur disque, que chaque test déforme à sa guise."""
    public = tmp_path / "public"
    (public / "news").mkdir(parents=True)
    (public / "blog").mkdir()

    (public / "stats.json").write_text(json.dumps({
        "goals": 976, "remaining": 24, "target": 1000,
        "last_updated": (MAINTENANT - timedelta(hours=2)).isoformat(),
        "last_match": {"date_iso": "2026-07-06T19:00Z"},
        "next_match": {"kickoff_utc": "2026-09-24T18:45Z"},
    }), encoding="utf-8")
    (public / "news.json").write_text(json.dumps({
        "generated_at": (MAINTENANT - timedelta(hours=1)).isoformat(),
        "items": [],
    }), encoding="utf-8")
    (public / "goals-data.json").write_text(
        json.dumps([{"num": n} for n in range(1, 977)]), encoding="utf-8")
    (public / "index.html").write_text(
        '<meta name="theme-color" content="#000">'
        '<span class="livepill">Live · 976</span>'
        '<div aria-valuenow="976"></div>', encoding="utf-8")

    monkeypatch.setattr(qa_site, "PUBLIC", public)
    monkeypatch.setattr(qa_site, "PAGES_CLES", ["index.html"])
    monkeypatch.setattr(qa_site, "DONNEES", ["stats.json", "news.json"])
    return public


def _familles(r):
    return {e["famille"] for e in r.entrees}


# ── Fraîcheur ───────────────────────────────────────────────────────────────
def test_donnee_fraiche_ne_declenche_rien(site):
    r = Rapport()
    qa_site.controle_fraicheur(r, MAINTENANT)
    assert r.entrees == []


def test_stats_perimees_sont_une_erreur(site):
    data = json.loads((site / "stats.json").read_text())
    data["last_updated"] = (MAINTENANT - timedelta(days=24)).isoformat()
    (site / "stats.json").write_text(json.dumps(data), encoding="utf-8")
    r = Rapport()
    qa_site.controle_fraicheur(r, MAINTENANT)
    assert any("24" in e["quoi"] for e in r.erreurs)


def test_un_prochain_match_deja_joue_est_une_erreur(site):
    """Le symptôme visible d'une synchro morte, côté visiteur."""
    data = json.loads((site / "stats.json").read_text())
    data["next_match"]["kickoff_utc"] = "2026-07-01T18:45Z"
    (site / "stats.json").write_text(json.dumps(data), encoding="utf-8")
    r = Rapport()
    qa_site.controle_fraicheur(r, MAINTENANT)
    assert any("déjà joué" in e["quoi"] for e in r.erreurs)


# ── Cohérence ───────────────────────────────────────────────────────────────
def test_compteurs_coherents_ne_declenchent_rien(site):
    r = Rapport()
    qa_site.controle_coherence(r)
    assert r.entrees == []


def test_base_de_buts_en_retard_sur_le_compteur(site):
    (site / "goals-data.json").write_text(
        json.dumps([{"num": n} for n in range(1, 968)]), encoding="utf-8")
    r = Rapport()
    qa_site.controle_coherence(r)
    assert any("9 but(s) sans fiche" in e["quoi"] for e in r.erreurs)


def test_pastille_live_desynchronisee(site):
    (site / "index.html").write_text(
        '<span class="livepill">Live · 975</span>', encoding="utf-8")
    r = Rapport()
    qa_site.controle_coherence(r)
    assert any("975" in e["quoi"] for e in r.erreurs)


def test_remaining_incoherent(site):
    data = json.loads((site / "stats.json").read_text())
    data["remaining"] = 30
    (site / "stats.json").write_text(json.dumps(data), encoding="utf-8")
    r = Rapport()
    qa_site.controle_coherence(r)
    assert any("remaining" in e["quoi"] for e in r.erreurs)


# ── Placeholders ────────────────────────────────────────────────────────────
def test_jeton_de_config_jamais_remplace(site):
    page = site / "index.html"
    page.write_text('<meta content="REMPLACER_PAR_TON_TOKEN_GSC">', encoding="utf-8")
    r = Rapport()
    qa_site.controle_placeholders(r, [page])
    assert any("jeton" in e["quoi"] for e in r.erreurs)


def test_todo_espagnol_n_est_pas_un_todo_oublie(site):
    """« Todo el fútbol » est du contenu, pas une note de développeur."""
    page = site / "index.html"
    page.write_text("<p>Todo el fútbol · Todos los goles</p>", encoding="utf-8")
    r = Rapport()
    qa_site.controle_placeholders(r, [page])
    assert r.entrees == []


def test_todo_en_majuscules_est_signale(site):
    page = site / "index.html"
    page.write_text("<p>TODO: écrire ce paragraphe</p>", encoding="utf-8")
    r = Rapport()
    qa_site.controle_placeholders(r, [page])
    assert any("TODO" in e["quoi"] for e in r.erreurs)


def test_un_todo_en_commentaire_html_n_est_pas_une_coquille(site):
    """Invisible pour le lecteur : c'est une note interne, pas un défaut."""
    page = site / "index.html"
    page.write_text("<!-- TODO: créer l'alias email -->\n<p>Contact</p>",
                    encoding="utf-8")
    r = Rapport()
    qa_site.controle_placeholders(r, [page])
    assert r.entrees == []


# ── JSON ────────────────────────────────────────────────────────────────────
def test_json_illisible_est_une_erreur(site):
    (site / "stats.json").write_text("{cassé", encoding="utf-8")
    r = Rapport()
    qa_site.controle_json(r)
    assert any(e["famille"] == "json" for e in r.erreurs)


def test_json_ld_invalide_est_une_erreur(site):
    (site / "index.html").write_text(
        '<script type="application/ld+json">{"a":}</script>', encoding="utf-8")
    r = Rapport()
    qa_site.controle_json(r)
    assert any("JSON-LD" in e["quoi"] for e in r.erreurs)


# ── Liens ───────────────────────────────────────────────────────────────────
def test_lien_vers_une_page_absente(site):
    page = site / "index.html"
    page.write_text('<a href="/nulle-part.html">x</a>', encoding="utf-8")
    r = Rapport()
    qa_site.controle_liens(r, [page])
    assert any("nulle-part" in e["quoi"] for e in r.alertes)


def test_lien_couvert_par_une_redirection_n_est_pas_mort(site):
    """2 335 pages pointent vers /world-cup/* — toutes redirigées en 301."""
    (site / "coupe-du-monde").mkdir()
    (site / "coupe-du-monde" / "index.html").write_text("ok", encoding="utf-8")
    (site / "_redirects").write_text(
        "/world-cup/*  /coupe-du-monde/  301\n", encoding="utf-8")
    page = site / "index.html"
    page.write_text('<a href="/world-cup/maroc/">x</a>', encoding="utf-8")
    r = Rapport()
    qa_site.controle_liens(r, [page])
    assert r.entrees == []


def test_href_construit_en_js_n_est_pas_un_chemin(site):
    page = site / "index.html"
    page.write_text("""<a href="/news/'+esc(it.id)+'.html">x</a>""", encoding="utf-8")
    r = Rapport()
    qa_site.controle_liens(r, [page])
    assert r.entrees == []


def test_redirection_vers_une_cible_absente(site):
    """Une 301 vers un 404 : le visiteur y croit deux fois."""
    (site / "_redirects").write_text("/vieux  /neuf/  301\n", encoding="utf-8")
    r = Rapport()
    qa_site.controle_redirections(r)
    assert any("n'existe pas" in e["quoi"] for e in r.erreurs)


def test_regle_de_redirection_avec_joker():
    regles = [("/world-cup/*", "/coupe-du-monde/")]
    assert _redirige("/world-cup/maroc/", regles)
    assert not _redirige("/autre/", regles)


# ── SEO ─────────────────────────────────────────────────────────────────────
def test_page_sans_balises_de_partage(site):
    (site / "index.html").write_text("<title>Trop court</title>", encoding="utf-8")
    r = Rapport()
    qa_site.controle_seo(r)
    assert {"og:title manquant ou trop court"} <= {e["quoi"] for e in r.erreurs}


# ── Langue ──────────────────────────────────────────────────────────────────
def test_langue_annoncee_differente_de_la_source(site):
    (site / "news.json").write_text(json.dumps({"items": [
        {"id": "abc", "primary_source": {"lang": "es"}}]}), encoding="utf-8")
    (site / "news" / "abc.html").write_text(
        "<summary>Voir le texte original (anglais)</summary>", encoding="utf-8")
    r = Rapport()
    qa_site.controle_langue(r)
    assert any("espagnol" in e["quoi"] for e in r.erreurs)


def test_langue_annoncee_conforme(site):
    (site / "news.json").write_text(json.dumps({"items": [
        {"id": "abc", "primary_source": {"lang": "es"}}]}), encoding="utf-8")
    (site / "news" / "abc.html").write_text(
        "<summary>Voir le texte original (espagnol)</summary>", encoding="utf-8")
    r = Rapport()
    qa_site.controle_langue(r)
    assert r.entrees == []


def test_libelle_neutre_est_accepte(site):
    """Les archives portent « Voir le texte original » sans langue : c'est exact."""
    (site / "news.json").write_text(json.dumps({"items": [
        {"id": "abc", "primary_source": {"lang": "de"}}]}), encoding="utf-8")
    (site / "news" / "abc.html").write_text(
        "<summary>Voir le texte original</summary>", encoding="utf-8")
    r = Rapport()
    qa_site.controle_langue(r)
    assert r.entrees == []
