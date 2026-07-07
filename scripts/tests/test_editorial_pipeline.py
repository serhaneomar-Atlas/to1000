"""Chaîne éditoriale en 4 étapes (demande Omar 2026-07-06) :
  1. RÉDACTEUR EN CHEF (tri)      — l'article mérite-t-il publication ?
  2. EXPERT EN RÉDACTION (résumé) — extraire L'ESSENTIEL, pas n'importe quel §
  3. EXPERT EN TRADUCTION         — transcréation naturelle, pas de mot-à-mot
  4. RÉDACTEUR EN CHEF (validation finale) — contrôle avant publication

Lancer :  cd scripts && python -m unittest tests.test_editorial_pipeline
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from editorial import chief_editor_review


class FakeTranslator:
    """Simule Gemini : rejoue des réponses par étape et journalise les appels."""
    gemini_enabled = True
    cache = None

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []          # [(system_extrait, user)]

    def _call_gemini(self, system, user, max_tokens=0):
        self.calls.append(system[:60])
        if not self.responses:
            return None
        r = self.responses.pop(0)
        return json.dumps(r, ensure_ascii=False) if r is not None else None

    def _parse_json_block(self, raw):
        try:
            return json.loads(raw)
        except Exception:
            return None


JUDGE_OK = {"publish": True, "reason": "fait fort", "quality": 8}
JUDGE_NO = {"publish": False, "reason": "listicle creux", "quality": 2}
SUMMARY = {"title": "Mbappé qualifie la France", "summary": "Doublé de Mbappé, la France file en quarts."}
TRANSLATION = {"fr": {"title": "Mbappé qualifie la France", "summary": "Doublé de Mbappé, la France file en quarts."},
               "en": {"title": "Mbappé sends France through", "summary": "A Mbappé brace puts France into the quarters."},
               "es": {"title": "Mbappé clasifica a Francia", "summary": "Doblete de Mbappé y Francia a cuartos."},
               "ar": {"title": "مبابي يقود فرنسا إلى ربع النهائي", "summary": "ثنائية مبابي تضع فرنسا في ربع النهائي."}}
VALIDATE_OK = {"publish": True, "i18n": TRANSLATION}


class TestChaineEditoriale(unittest.TestCase):
    def test_rejet_du_redacteur_en_chef_arrete_tout(self):
        tr = FakeTranslator([JUDGE_NO])
        out = chief_editor_review(tr, "10 maillots à acheter cet été", "…", "fr", ["fr", "en", "es", "ar"])
        self.assertIsNotNone(out)
        self.assertFalse(out["publish"])
        self.assertEqual(len(tr.calls), 1)  # UNE seule étape : pas de résumé/traduction payés pour rien

    def test_chaine_complete_quatre_etapes(self):
        tr = FakeTranslator([JUDGE_OK, SUMMARY, TRANSLATION, VALIDATE_OK])
        out = chief_editor_review(tr, "France-X 2-0", "Mbappé a inscrit un doublé…", "fr", ["fr", "en", "es", "ar"])
        self.assertTrue(out["publish"])
        self.assertEqual(len(tr.calls), 4)
        self.assertEqual(out["i18n"]["ar"]["title"], "مبابي يقود فرنسا إلى ربع النهائي")
        for lang in ("fr", "en", "es", "ar"):
            self.assertEqual(out["i18n"][lang]["engine"], "gemini-editor")

    def test_validation_finale_peut_corriger(self):
        fixed = json.loads(json.dumps(TRANSLATION))
        fixed["en"]["title"] = "Mbappé fires France into the quarter-finals"
        tr = FakeTranslator([JUDGE_OK, SUMMARY, TRANSLATION, {"publish": True, "i18n": fixed}])
        out = chief_editor_review(tr, "t", "s", "fr", ["fr", "en", "es", "ar"])
        self.assertEqual(out["i18n"]["en"]["title"], "Mbappé fires France into the quarter-finals")

    def test_validation_finale_peut_rejeter(self):
        tr = FakeTranslator([JUDGE_OK, SUMMARY, TRANSLATION, {"publish": False, "i18n": None}])
        out = chief_editor_review(tr, "t", "s", "fr", ["fr", "en", "es", "ar"])
        self.assertFalse(out["publish"])

    def test_echec_d_une_etape_rend_none(self):
        tr = FakeTranslator([JUDGE_OK, None])  # le résumeur ne répond pas
        out = chief_editor_review(tr, "t", "s", "fr", ["fr", "en", "es", "ar"])
        self.assertIsNone(out)  # le caller retombe sur le pipeline de trad classique

    def test_gemini_coupe_rend_none_sans_appel(self):
        tr = FakeTranslator([])
        tr.gemini_enabled = False
        out = chief_editor_review(tr, "t", "s", "fr", ["fr"])
        self.assertIsNone(out)
        self.assertEqual(tr.calls, [])


if __name__ == "__main__":
    unittest.main()
