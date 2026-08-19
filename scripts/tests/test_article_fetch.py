"""Extraction du corps d'article — testée sur du HTML synthétique.

Le réseau n'est volontairement pas sollicité : ces tests valident le parsing,
pas la connectivité (le fetch réel tourne sur le runner GitHub).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.article_fetch import article_text, extract_text  # noqa: E402


LONG = ("Le Portugal s'est imposé face à la Croatie au terme d'une rencontre "
        "serrée, portée par un doublé de son capitaine en seconde période. ")


def test_extrait_les_paragraphes_de_l_article():
    html = f"""
    <html><body>
      <nav><p>{LONG}Menu de navigation à ignorer.</p></nav>
      <article>
        <p>{LONG}Premier paragraphe du corps.</p>
        <p>{LONG}Deuxième paragraphe du corps.</p>
      </article>
      <footer><p>{LONG}Tous droits réservés.</p></footer>
    </body></html>"""
    text = extract_text(html)
    assert "Premier paragraphe" in text
    assert "Deuxième paragraphe" in text
    assert "navigation" not in text
    assert "droits réservés" not in text


def test_ignore_scripts_et_styles():
    html = f"""<article>
      <script>var x = "{LONG} code à ne pas lire";</script>
      <style>.p {{ content: "{LONG}"; }}</style>
      <p>{LONG}Le vrai texte.</p>
    </article>"""
    text = extract_text(html)
    assert "Le vrai texte" in text
    assert "var x" not in text
    assert "content:" not in text


def test_ignore_les_paragraphes_trop_courts():
    html = f"<article><p>Photo : Reuters</p><p>{LONG}Corps réel.</p></article>"
    text = extract_text(html)
    assert "Corps réel" in text
    assert "Reuters" not in text


def test_decode_les_entites_html():
    html = f"<article><p>{LONG}L&#39;&eacute;quipe a gagn&eacute; 2&ndash;1.</p></article>"
    text = extract_text(html)
    assert "L'équipe" in text
    assert "2–1" in text


def test_deduplique_les_paragraphes_repetes():
    html = f"<article><p>{LONG}Unique.</p><p>{LONG}Unique.</p></article>"
    assert extract_text(html).count("Unique.") == 1


def test_html_vide_rend_une_chaine_vide():
    assert extract_text("") == ""
    assert extract_text("<html><body></body></html>") == ""


def test_article_text_retombe_sur_le_rss_si_l_url_est_injoignable():
    text, origin = article_text("not-a-url", fallback="extrait RSS de secours")
    assert origin == "rss"
    assert text == "extrait RSS de secours"


def test_article_text_signale_l_origine():
    """Le contrat : l'appelant doit pouvoir distinguer corps complet et amorce."""
    text, origin = article_text("", fallback="")
    assert origin == "rss"
    assert text == ""
