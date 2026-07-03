"""Tests de la logique d'auto-incrément du compteur de buts (update_stats_v2.sync_goals).

Lancer :  python -m unittest scripts.tests.test_goal_sync  (depuis la racine)
     ou :  cd scripts && python -m unittest tests.test_goal_sync
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import update_stats_v2
from lib.espn_client import GoalEvent, MatchSummary, _competition_to_summary
from update_stats_v2 import select_new_cr7_goals, sync_goals


def _goal(event_id="g1", is_cr7=True, period=2, raw_text="Cristiano Ronaldo (Portugal) Goal at 75'"):
    return GoalEvent(
        event_id=event_id, match_id="m1", minute="75'", minute_int=75,
        period=period, scorer_id="22774" if is_cr7 else "999",
        scorer_name="Cristiano Ronaldo" if is_cr7 else "Autre Joueur",
        team_name="Portugal", is_cr7=is_cr7, raw_text=raw_text,
    )


def _match(goals, date_iso="2026-07-02T23:00Z", finished=True, in_progress=False):
    return MatchSummary(
        event_id="401999999", date_iso=date_iso, competition="FIFA World Cup",
        home_team="Portugal", away_team="Croatia", home_team_id="482",
        away_team_id="449", score_home=1, score_away=0, venue="BMO Field",
        status="STATUS_FULL_TIME" if finished else "STATUS_IN_PROGRESS",
        is_finished=finished, is_in_progress=in_progress, goals=goals,
        league_slug="fifa.world",
    )


BASELINE = "2026-07-02T00:00:00Z"


class TestSelectNewCr7Goals(unittest.TestCase):
    def test_credite_un_nouveau_but_cr7(self):
        g = _goal()
        out = select_new_cr7_goals([g], set(), "2026-07-02T23:00Z", BASELINE)
        self.assertEqual(out, [g])

    def test_ignore_les_event_ids_deja_traites(self):
        g = _goal(event_id="deja-vu")
        out = select_new_cr7_goals([g], {"deja-vu"}, "2026-07-02T23:00Z", BASELINE)
        self.assertEqual(out, [])

    def test_ignore_les_buts_des_autres_joueurs(self):
        out = select_new_cr7_goals([_goal(is_cr7=False)], set(), "2026-07-02T23:00Z", BASELINE)
        self.assertEqual(out, [])

    def test_ignore_les_tirs_au_but(self):
        out = select_new_cr7_goals([_goal(period=5)], set(), "2026-07-02T23:00Z", BASELINE)
        self.assertEqual(out, [])

    def test_ignore_les_buts_contre_son_camp(self):
        g = _goal(raw_text="Cristiano Ronaldo (Portugal) Own Goal at 75'")
        out = select_new_cr7_goals([g], set(), "2026-07-02T23:00Z", BASELINE)
        self.assertEqual(out, [])

    def test_ignore_un_match_anterieur_a_la_baseline(self):
        # Match du 23/06 (buts 974-975 déjà comptés à la main) < baseline
        out = select_new_cr7_goals([_goal()], set(), "2026-06-23T18:00Z", BASELINE)
        self.assertEqual(out, [])

    def test_ignore_les_buts_sans_event_id(self):
        out = select_new_cr7_goals([_goal(event_id="")], set(), "2026-07-02T23:00Z", BASELINE)
        self.assertEqual(out, [])


class TestSyncGoals(unittest.TestCase):
    def setUp(self):
        self._orig_today = update_stats_v2.find_team_match_today_cr7
        self._orig_last = update_stats_v2.find_last_match_cr7
        self.stats = {
            "goals": 975, "remaining": 25, "target": 1000,
            "goal_sync_baseline": BASELINE,
            "last_goal_date": "2026-06-23",
            "last_goal_opponent": "Uzbekistan",
            "last_goal_competition": "FIFA World Cup",
        }

    def tearDown(self):
        update_stats_v2.find_team_match_today_cr7 = self._orig_today
        update_stats_v2.find_last_match_cr7 = self._orig_last

    def test_incremente_le_compteur_sur_un_nouveau_but_en_live(self):
        match = _match([_goal(event_id="live-1")], finished=False, in_progress=True)
        update_stats_v2.find_team_match_today_cr7 = lambda: match
        changed = sync_goals(self.stats)
        self.assertTrue(changed)
        self.assertEqual(self.stats["goals"], 976)
        self.assertEqual(self.stats["remaining"], 24)
        self.assertIn("live-1", self.stats["processed_goal_event_ids"])
        self.assertEqual(self.stats["last_goal_date"], "2026-07-02")
        self.assertEqual(self.stats["last_goal_opponent"], "Croatia")

    def test_deux_buts_dans_le_meme_match(self):
        match = _match([_goal(event_id="a"), _goal(event_id="b")])
        update_stats_v2.find_team_match_today_cr7 = lambda: match
        self.assertTrue(sync_goals(self.stats))
        self.assertEqual(self.stats["goals"], 977)

    def test_idempotent_au_second_passage(self):
        match = _match([_goal(event_id="x")])
        update_stats_v2.find_team_match_today_cr7 = lambda: match
        sync_goals(self.stats)
        changed = sync_goals(self.stats)
        self.assertFalse(changed)
        self.assertEqual(self.stats["goals"], 976)

    def test_noop_sans_match_du_jour_ni_dernier_match(self):
        update_stats_v2.find_team_match_today_cr7 = lambda: None
        update_stats_v2.find_last_match_cr7 = lambda: None
        self.assertFalse(sync_goals(self.stats))
        self.assertEqual(self.stats["goals"], 975)

    def test_desactive_sans_baseline(self):
        del self.stats["goal_sync_baseline"]
        match = _match([_goal(event_id="y")])
        update_stats_v2.find_team_match_today_cr7 = lambda: match
        self.assertFalse(sync_goals(self.stats))
        self.assertEqual(self.stats["goals"], 975)


class TestEspnStatuses(unittest.TestCase):
    """Coupe du Monde à élimination directe : les statuts prolongations / tirs au but
    doivent être reconnus, sinon last_match ne se met jamais à jour."""

    def _summary(self, state):
        comp = {"id": "1", "competitors": [
            {"homeAway": "home", "team": {"displayName": "Portugal", "id": "482"}, "score": "1"},
            {"homeAway": "away", "team": {"displayName": "Croatia", "id": "449"}, "score": "1"},
        ]}
        return _competition_to_summary(comp, {"type": {"name": state}}, "2026-07-02T23:00Z", "FIFA World Cup")

    def test_final_pen_est_termine(self):
        self.assertTrue(self._summary("STATUS_FINAL_PEN").is_finished)

    def test_full_time_reste_termine(self):
        self.assertTrue(self._summary("STATUS_FULL_TIME").is_finished)

    def test_shootout_est_en_cours(self):
        s = self._summary("STATUS_SHOOTOUT")
        self.assertTrue(s.is_in_progress)
        self.assertFalse(s.is_finished)

    def test_prolongations_en_cours(self):
        s = self._summary("STATUS_OVERTIME")
        self.assertTrue(s.is_in_progress)

    def test_scheduled_ni_fini_ni_en_cours(self):
        s = self._summary("STATUS_SCHEDULED")
        self.assertFalse(s.is_finished)
        self.assertFalse(s.is_in_progress)


if __name__ == "__main__":
    unittest.main()


class TestPenaltyScored(unittest.TestCase):
    """Fix 2026-07-03 : un but sur penalty a le type ESPN 'Penalty - Scored'
    (sans le mot 'Goal') — le but #976 de CR7 vs Croatie n'était pas détecté."""

    def _ev(self, type_text, scorer_id="22774"):
        return {"id": "9", "type": {"text": type_text}, "period": {"number": 2},
                "clock": {"displayValue": "68'"},
                "participants": [{"athlete": {"id": scorer_id, "displayName": "Cristiano Ronaldo"}}],
                "team": {"displayName": "Portugal"}, "text": "Goal! ..."}

    def test_penalty_marque_detecte(self):
        from lib.espn_client import _key_event_to_goal
        g = _key_event_to_goal(self._ev("Penalty - Scored"), "m1")
        self.assertIsNotNone(g)
        self.assertTrue(g.is_cr7)

    def test_penalty_rate_ignore(self):
        from lib.espn_client import _key_event_to_goal
        self.assertIsNone(_key_event_to_goal(self._ev("Penalty - Missed"), "m1"))

    def test_but_normal_toujours_detecte(self):
        from lib.espn_client import _key_event_to_goal
        self.assertIsNotNone(_key_event_to_goal(self._ev("Goal"), "m1"))
