"""Régression : une équipe de football connue ne rend pas le basket pertinent."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from news_aggregator import classify


class TestFiltreSport(unittest.TestCase):
    def classify_boca(self, title, summary):
        return classify(title, summary, [], [], ["Boca Juniors"], [], [], [])

    def test_competition_fiba_avec_club_de_football_exclue(self):
        self.assertIsNone(self.classify_boca(
            "Boca Juniors remporte la Coupe intercontinentale",
            "L'équipe de Boca Juniors gagne la FIBA Intercontinental Cup.",
        ))

    def test_basket_mentionne_apres_le_titre_exclu(self):
        for marker in ("NBA G League", "basketball", "basket-ball"):
            with self.subTest(marker=marker):
                self.assertIsNone(self.classify_boca(
                    "Boca Juniors remporte la finale",
                    f"Boca Juniors s'impose dans un match de {marker}.",
                ))

    def test_vrai_football_boca_conserve(self):
        self.assertEqual(self.classify_boca(
            "Boca Juniors marque en football",
            "Boca Juniors gagne son match de championnat.",
        ), "football")


if __name__ == "__main__":
    unittest.main()

