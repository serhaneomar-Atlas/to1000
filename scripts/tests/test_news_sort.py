"""Tri du feed : les plus récents D'ABORD (demande Omar 2026-07-02 —
« ça s'appelle des nouvelles pour une raison »). L'ancien tri mettait
CR7 puis le score d'importance avant la fraîcheur.

Lancer :  cd scripts && python -m unittest tests.test_news_sort
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from news_aggregator import recency_sort_key


class TestTriFraicheur(unittest.TestCase):
    def _sorted(self, items):
        return sorted(items, key=recency_sort_key, reverse=True)

    def test_plus_recent_en_premier(self):
        a = {"published_at": "2026-07-02T11:00:00Z", "kind": "foot", "score": 0}
        b = {"published_at": "2026-07-02T07:00:00Z", "kind": "cr7", "score": 9}
        self.assertEqual(self._sorted([b, a])[0], a)  # même face à un CR7 mieux scoré

    def test_egalite_de_date_departagee_par_le_score(self):
        a = {"published_at": "2026-07-02T11:00:00Z", "score": 1}
        b = {"published_at": "2026-07-02T11:00:00Z", "score": 5}
        self.assertEqual(self._sorted([a, b])[0], b)

    def test_date_absente_en_dernier(self):
        a = {"published_at": "", "score": 9}
        b = {"published_at": "2026-06-01T00:00:00Z", "score": 0}
        self.assertEqual(self._sorted([a, b])[0], b)


if __name__ == "__main__":
    unittest.main()


class TestCustomItems(unittest.TestCase):
    """Items éditoriaux maison (scripts/custom_news.json) injectés dans le feed."""

    def test_expiration_et_id_requis(self):
        import json, tempfile
        from news_aggregator import load_custom_items
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump([{"id": "vieux", "expires_at": "2020-01-01T00:00:00Z"},
                       {"id": "valide", "expires_at": "2999-01-01T00:00:00Z"},
                       {"expires_at": "2999-01-01T00:00:00Z"}], f)
            p = f.name
        self.assertEqual([i["id"] for i in load_custom_items(p)], ["valide"])

    def test_fichier_absent_ne_casse_rien(self):
        from news_aggregator import load_custom_items
        self.assertEqual(load_custom_items("/chemin/inexistant.json"), [])
