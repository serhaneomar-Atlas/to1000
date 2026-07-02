"""Section Coupe du Monde 2026 — helpers du générateur de pages.

Lancer :  cd scripts && python -m unittest tests.test_wc_pages
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from lib.wc_teams import TEAMS, is_placeholder, team_by_espn_id
from lib.wc_data import date_fr_et, match_slug, round_label, time_fr_et


class TestTeams(unittest.TestCase):
    def test_48_equipes(self):
        self.assertEqual(len(TEAMS), 48)

    def test_maroc(self):
        t = team_by_espn_id("2869")
        self.assertEqual((t["fr"], t["slug"], t["iso2"]), ("Maroc", "maroc", "ma"))

    def test_angleterre_drapeau_gb_eng(self):
        self.assertEqual(team_by_espn_id("448")["iso2"], "gb-eng")

    def test_cote_divoire_slug_ascii(self):
        t = team_by_espn_id("4789")
        self.assertEqual(t["slug"], "cote-divoire")

    def test_placeholders_detectes(self):
        self.assertTrue(is_placeholder("Quarterfinal 1 Winner"))
        self.assertTrue(is_placeholder("Round of 16 5 Winner"))
        self.assertTrue(is_placeholder("Semifinal 2 Loser"))
        self.assertFalse(is_placeholder("Morocco"))
        self.assertFalse(is_placeholder("Winnipeg FC"))  # 'Winner' seul en mot entier


class TestSlugEtDates(unittest.TestCase):
    def test_match_slug_en_heure_de_l_est(self):
        # 2026-07-04 23:00 UTC = 19:00 heure de l'Est → le 4 juillet
        self.assertEqual(match_slug("canada", "maroc", "2026-07-04T23:00Z"),
                         "canada-vs-maroc-4-juillet-2026")

    def test_match_slug_bascule_de_jour(self):
        # 2026-07-03 03:00 UTC = 2 juillet 23:00 ET → le 2 juillet
        self.assertEqual(match_slug("suisse", "algerie", "2026-07-03T03:00Z"),
                         "suisse-vs-algerie-2-juillet-2026")

    def test_date_fr(self):
        self.assertEqual(date_fr_et("2026-07-04T23:00Z"), "4 juillet 2026")

    def test_heure_fr_et(self):
        self.assertEqual(time_fr_et("2026-07-04T23:00Z"), "19 h 00")


class TestRounds(unittest.TestCase):
    def test_labels(self):
        self.assertEqual(round_label("round-of-16"), "Huitièmes de finale")
        self.assertEqual(round_label("round-of-32"), "32es de finale")
        self.assertEqual(round_label("quarterfinals"), "Quarts de finale")
        self.assertEqual(round_label("final"), "Finale")

    def test_slug_inconnu_passthrough(self):
        self.assertEqual(round_label("mystery-round"), "mystery-round")


if __name__ == "__main__":
    unittest.main()


class TestLiveWindow(unittest.TestCase):
    """Fenêtre live : un match entre kickoff-20min et kickoff+3h30 → le cron */5 doit agir."""

    def _m(self, date_iso, state="scheduled"):
        return {"date_iso": date_iso, "state": state}

    def test_pendant_un_match(self):
        from datetime import datetime, timezone
        from lib.wc_data import is_live_window
        now = datetime(2026, 7, 2, 23, 40, tzinfo=timezone.utc)  # 40 min après kickoff
        self.assertTrue(is_live_window([self._m("2026-07-02T23:00Z")], now))

    def test_juste_avant_kickoff(self):
        from datetime import datetime, timezone
        from lib.wc_data import is_live_window
        now = datetime(2026, 7, 2, 22, 45, tzinfo=timezone.utc)
        self.assertTrue(is_live_window([self._m("2026-07-02T23:00Z")], now))

    def test_hors_fenetre(self):
        from datetime import datetime, timezone
        from lib.wc_data import is_live_window
        now = datetime(2026, 7, 2, 10, 0, tzinfo=timezone.utc)
        self.assertFalse(is_live_window([self._m("2026-07-02T23:00Z")], now))

    def test_match_deja_fini_ignore(self):
        from datetime import datetime, timezone
        from lib.wc_data import is_live_window
        now = datetime(2026, 7, 2, 23, 40, tzinfo=timezone.utc)
        self.assertFalse(is_live_window([self._m("2026-07-02T23:00Z", state="finished")], now))
