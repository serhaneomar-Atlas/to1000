"""Tests du contrôle de fraîcheur, sans réseau ni secret."""
import sys
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from news_health import evaluate


class NewsHealthTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 24, 20, tzinfo=timezone.utc)
        self.repo = {
            "generated_at": (self.now - timedelta(minutes=5)).isoformat(),
            "stats": {"feeds_fetched": 18},
            "items": [],
        }
        self.live = {
            "generated_at": (self.now - timedelta(minutes=7)).isoformat(),
            "items": [],
        }

    def test_fil_frais(self):
        self.assertEqual(evaluate(self.repo, self.live, self.now), [])

    def test_pipeline_absent_detecte(self):
        self.repo["generated_at"] = (self.now - timedelta(hours=4)).isoformat()
        self.assertTrue(any("dépôt obsolète" in e for e in
                            evaluate(self.repo, self.live, self.now)))

    def test_deploiement_en_retard_detecte(self):
        self.live["generated_at"] = (self.now - timedelta(hours=1)).isoformat()
        self.assertTrue(any("Déploiement" in e for e in
                            evaluate(self.repo, self.live, self.now)))

    def test_tous_les_flux_echoues_detectes(self):
        self.repo["stats"]["feeds_fetched"] = 0
        self.assertTrue(any("Aucun flux RSS" in e for e in
                            evaluate(self.repo, self.live, self.now)))

    def test_horodatage_absent_detecte(self):
        del self.live["generated_at"]
        self.assertTrue(evaluate(self.repo, self.live, self.now))


if __name__ == "__main__":
    unittest.main()
