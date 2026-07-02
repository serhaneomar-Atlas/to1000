"""Flux RSS multilingues (rss.xml FR + rss-ar/en/es.xml) — demande WORKLOG 2026-07-02
(alimenter la Page FB arabe Pchaaakh TV via Make).

Lancer :  cd scripts && python -m unittest tests.test_rss_langs
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from rss_generator import FEEDS, social_caption, tr

ITEM = {
    "id": "abc123", "kind": "cr7",
    "title": "Ronaldo scores again", "summary": "CR7 nets his 975th career goal.",
    "i18n": {
        "fr": {"title": "Ronaldo marque encore", "summary": "CR7 inscrit son 975e but en carrière."},
        "ar": {"title": "رونالدو يسجل من جديد", "summary": "رونالدو يسجل هدفه رقم 975 في مسيرته."},
        "es": {"title": "Ronaldo marca de nuevo", "summary": "CR7 anota su gol 975."},
    },
}


class TestTraduction(unittest.TestCase):
    def test_titre_arabe(self):
        self.assertEqual(tr(ITEM, "ar", "title"), "رونالدو يسجل من جديد")

    def test_fallback_fr_si_langue_absente(self):
        item = {"i18n": {"fr": {"summary": "Résumé FR"}}, "summary": "src"}
        self.assertEqual(tr(item, "ar", "summary"), "Résumé FR")

    def test_fallback_source_en_dernier(self):
        self.assertEqual(tr({"title": "Plain"}, "ar", "title"), "Plain")


class TestCaptionArabe(unittest.TestCase):
    def test_resume_et_hashtags_arabes(self):
        cap = social_caption(ITEM, "ar")
        self.assertIn("رونالدو يسجل هدفه رقم 975", cap)
        self.assertIn("#رونالدو", cap)
        self.assertIn("#هدف_1000", cap)

    def test_caption_fr_inchangee(self):
        cap = social_caption(ITEM, "fr")
        self.assertIn("975e but", cap)
        self.assertIn("#", cap)


class TestFeeds(unittest.TestCase):
    def test_quatre_flux_configures(self):
        self.assertEqual(set(FEEDS), {"fr", "ar", "en", "es"})
        self.assertEqual(FEEDS["fr"]["file"], "rss.xml")   # URL FR historique inchangée (Make y est branché)
        self.assertEqual(FEEDS["ar"]["file"], "rss-ar.xml")
        self.assertEqual(FEEDS["ar"]["language"], "ar")


if __name__ == "__main__":
    unittest.main()


class TestFiltreArabe(unittest.TestCase):
    """Le flux AR ne doit contenir que des items réellement en arabe : le pipeline
    stocke le texte SOURCE en passthrough tant que Gemini n'a pas enrichi."""

    def test_detecte_ecriture_arabe(self):
        from rss_generator import has_arabic
        self.assertTrue(has_arabic("رونالدو يسجل من جديد"))
        self.assertFalse(has_arabic("Croacia avisa: Ronaldo no está acabado"))
        self.assertFalse(has_arabic(""))
