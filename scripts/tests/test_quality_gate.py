"""Garde-fou d'affichage : le lecteur ne voit JAMAIS de traduction machine brute.

Cas réel (20/08/2026, article Mundo Deportivo sur les capitaines du Barça) :
l'article n'était pas encore passé par le conseil de rédaction, et le lecteur
voyait le mot-à-mot MyMemory — « أول قائد لبرجة » (Barça massacré en برجة,
masculin pour une joueuse), « première capitaine du Barça et Aitana et Graham
entrent ». Tant que la chaîne n'est pas passée, on affiche le texte ORIGINAL
de la source : honnête, jamais dégradant.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from news_to_html import best_summary, best_title, publishable, render_article


def _item(fr_engine="mymemory", ar_engine="mymemory"):
    return {
        "id": "gate-test",
        "title": "Patri, primera capitana del Barça y entran Aitana y Graham",
        "summary": "Sale Alexia Putellas y entran Aitana Bonmatí y Caroline Graham Hansen.",
        "url": "https://exemple.test/a", "published_at": "2026-08-20T10:00:00Z",
        "kind": "football",
        "primary_source": {"lang": "es", "name": "Mundo Deportivo"},
        "i18n": {
            "es": {"title": "Patri, primera capitana del Barça y entran Aitana y Graham",
                    "summary": "Sale Alexia Putellas y entran Aitana Bonmatí.",
                    "needs_translation": False},
            "fr": {"title": "première capitaine du Barça et Aitana et Graham entrent",
                    "summary": "mot à mot", "engine": fr_engine,
                    "needs_translation": False},
            "ar": {"title": "أول قائد لبرجة", "summary": "مشوّه",
                    "engine": ar_engine, "needs_translation": False},
        },
    }


def test_le_mot_a_mot_mymemory_n_est_pas_publiable():
    it = _item()
    assert not publishable(it, "fr")
    assert not publishable(it, "ar")


def test_la_langue_source_est_toujours_publiable():
    """Le texte original est du journalisme réel, pas une traduction."""
    assert publishable(_item(), "es")


def test_la_sortie_du_conseil_de_redaction_est_publiable():
    it = _item(ar_engine="gemini-editor")
    assert publishable(it, "ar")


def test_la_traduction_gemini_avec_glossaire_est_publiable():
    it = _item(fr_engine="gemini")
    assert publishable(it, "fr")


def test_needs_translation_bloque_meme_un_moteur_accepte():
    it = _item(fr_engine="gemini")
    it["i18n"]["fr"]["needs_translation"] = True
    assert not publishable(it, "fr")


def test_le_titre_affiche_retombe_sur_l_original_pas_le_mot_a_mot():
    it = _item()
    assert best_title(it) == "Patri, primera capitana del Barça y entran Aitana y Graham"
    assert "première capitaine" not in best_title(it)
    assert "mot à mot" not in best_summary(it)


def test_le_titre_enrichi_est_affiche_normalement():
    it = _item(fr_engine="gemini-editor")
    it["i18n"]["fr"]["title"] = "Patri Guijarro devient capitaine n°1 du Barça"
    assert best_title(it) == "Patri Guijarro devient capitaine n°1 du Barça"


def test_le_payload_de_page_article_replie_les_brouillons_sur_la_source():
    html = render_article(_item(), [_item()])
    # le payload arabe ne doit PAS contenir le mot-à-mot
    assert "لبرجة" not in html
    # il porte le repli marqué, avec le texte espagnol original
    assert '"fallback": true' in html.lower() or '"fallback":true' in html.lower()
    assert "primera capitana" in html


def test_le_payload_garde_les_langues_enrichies():
    it = _item(ar_engine="gemini-editor")
    it["i18n"]["ar"]["title"] = "باتري غيخارو القائدة الأولى لبرشلونة"
    html = render_article(it, [it])
    assert "باتري غيخارو القائدة الأولى لبرشلونة" in html
