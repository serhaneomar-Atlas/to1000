"""Conseil de rédaction en 5 étapes (refonte 2026-08-19) :
  1. RÉDACTEUR EN CHEF (tri)       — l'article mérite-t-il publication ?
  2. LECTURE DU SOURCE             — l'article COMPLET, pas l'amorce RSS
  3. EXPERT EN RÉDACTION           — LA nouvelle + développement au bon format
  4. EXPERT EN TRADUCTION          — transcréation, noms propres verrouillés
  5. RÉDACTEUR EN CHEF (validation)— fidélité, ton humain, contrôle final

Lancer :  cd scripts && python -m unittest tests.test_editorial_pipeline
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import editorial  # noqa: E402
from editorial import chief_editor_review  # noqa: E402

LANGS = ["fr", "en", "es", "ar"]


class FakeTranslator:
    """Simule Gemini : rejoue des réponses par étape et journalise les appels."""
    gemini_enabled = True
    cache = None

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []          # [(system_extrait, user)]
        self.prompts = []        # systèmes complets, pour inspecter les consignes

    def _call_gemini(self, system, user, max_tokens=0):
        self.calls.append(system[:60])
        self.prompts.append(system)
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

WRITE = {
    "title": "Mbappé qualifie la France",
    "lead": "Doublé de Mbappé, la France file en quarts.",
    "format": "deep",
    "body": ["Le premier but tombe à la 12e minute.",
             "Le second scelle la rencontre juste avant l'heure de jeu."],
}

TRANSLATION = {
    "fr": {"title": "Mbappé qualifie la France",
           "lead": "Doublé de Mbappé, la France file en quarts.",
           "body": ["Le premier but tombe à la 12e minute.",
                    "Le second scelle la rencontre avant l'heure de jeu."]},
    "en": {"title": "Mbappé sends France through",
           "lead": "A Mbappé brace puts France into the quarters.",
           "body": ["The opener came in the 12th minute.",
                    "The second settled it just before the hour."]},
    "es": {"title": "Mbappé clasifica a Francia",
           "lead": "Doblete de Mbappé y Francia a cuartos.",
           "body": ["El primero llegó en el minuto 12.",
                    "El segundo sentenció antes de la hora."]},
    "ar": {"title": "مبابي يقود فرنسا إلى ربع النهائي",
           "lead": "ثنائية مبابي تضع فرنسا في ربع النهائي.",
           "body": ["جاء الهدف الأول في الدقيقة 12.", "والثاني حسم اللقاء."]},
}
VALIDATE_OK = {"publish": True, "i18n": TRANSLATION}

FULL_CHAIN = [JUDGE_OK, WRITE, TRANSLATION, VALIDATE_OK]


def _no_network(body="Corps complet de l'article, récupéré.", origin="full"):
    """Neutralise la lecture réseau : les tests valident la chaîne, pas le fetch."""
    return mock.patch.object(editorial, "article_text",
                             return_value=(body, origin))


class TestChaineEditoriale(unittest.TestCase):
    def test_rejet_du_redacteur_en_chef_arrete_tout(self):
        tr = FakeTranslator([JUDGE_NO])
        with _no_network():
            out = chief_editor_review(tr, "10 maillots à acheter cet été", "…", "fr", LANGS)
        self.assertIsNotNone(out)
        self.assertFalse(out["publish"])
        # UNE seule étape : ni lecture, ni rédaction, ni traduction payées pour rien
        self.assertEqual(len(tr.calls), 1)
        self.assertEqual(out["source_read"], "skipped")

    def test_le_rejet_n_appelle_jamais_la_lecture_du_source(self):
        """La lecture coûte une requête HTTP : elle ne se paie qu'après le tri."""
        tr = FakeTranslator([JUDGE_NO])
        with mock.patch.object(editorial, "article_text") as fetch:
            chief_editor_review(tr, "cotes du match", "…", "fr", LANGS,
                                url="https://exemple.test/a")
        fetch.assert_not_called()

    def test_chaine_complete_cinq_etapes(self):
        tr = FakeTranslator(FULL_CHAIN)
        with _no_network():
            out = chief_editor_review(tr, "France-X 2-0", "Mbappé a inscrit un doublé…",
                                      "fr", LANGS, url="https://exemple.test/a")
        self.assertTrue(out["publish"])
        self.assertEqual(len(tr.calls), 4)   # 4 appels modèle + 1 lecture non facturée
        self.assertEqual(out["source_read"], "full")
        self.assertEqual(out["i18n"]["ar"]["title"], "مبابي يقود فرنسا إلى ربع النهائي")
        for lang in LANGS:
            self.assertEqual(out["i18n"][lang]["engine"], "gemini-editor")

    def test_le_lead_alimente_le_champ_summary_historique(self):
        """Les cartes, le RSS et les balises OG lisent `summary` : ne pas le vider."""
        tr = FakeTranslator(FULL_CHAIN)
        with _no_network():
            out = chief_editor_review(tr, "t", "s", "fr", LANGS)
        self.assertEqual(out["i18n"]["fr"]["summary"],
                         "Doublé de Mbappé, la France file en quarts.")

    def test_le_developpement_est_conserve_par_langue(self):
        tr = FakeTranslator(FULL_CHAIN)
        with _no_network():
            out = chief_editor_review(tr, "t", "s", "fr", LANGS)
        self.assertEqual(len(out["i18n"]["en"]["body"]), 2)
        self.assertIn("12th minute", out["i18n"]["en"]["body"][0])
        self.assertEqual(out["i18n"]["fr"]["format"], "deep")

    def test_format_inconnu_retombe_sur_brief(self):
        write = dict(WRITE, format="poème")
        tr = FakeTranslator([JUDGE_OK, write, TRANSLATION, VALIDATE_OK])
        with _no_network():
            out = chief_editor_review(tr, "t", "s", "fr", LANGS)
        self.assertEqual(out["i18n"]["fr"]["format"], "brief")

    def test_format_bullets_est_accepte(self):
        write = dict(WRITE, format="bullets")
        tr = FakeTranslator([JUDGE_OK, write, TRANSLATION, VALIDATE_OK])
        with _no_network():
            out = chief_editor_review(tr, "t", "s", "fr", LANGS)
        self.assertEqual(out["i18n"]["fr"]["format"], "bullets")

    def test_validation_finale_peut_corriger(self):
        fixed = json.loads(json.dumps(TRANSLATION))
        fixed["en"]["title"] = "Mbappé fires France into the quarter-finals"
        tr = FakeTranslator([JUDGE_OK, WRITE, TRANSLATION, {"publish": True, "i18n": fixed}])
        with _no_network():
            out = chief_editor_review(tr, "t", "s", "fr", LANGS)
        self.assertEqual(out["i18n"]["en"]["title"],
                         "Mbappé fires France into the quarter-finals")

    def test_validation_finale_peut_rejeter(self):
        tr = FakeTranslator([JUDGE_OK, WRITE, TRANSLATION, {"publish": False, "i18n": None}])
        with _no_network():
            out = chief_editor_review(tr, "t", "s", "fr", LANGS)
        self.assertFalse(out["publish"])

    def test_echec_d_une_etape_rend_none(self):
        tr = FakeTranslator([JUDGE_OK, None])  # le rédacteur ne répond pas
        with _no_network():
            out = chief_editor_review(tr, "t", "s", "fr", LANGS)
        self.assertIsNone(out)  # le caller retombe sur la traduction classique

    def test_gemini_coupe_rend_none_sans_appel(self):
        tr = FakeTranslator([])
        tr.gemini_enabled = False
        out = chief_editor_review(tr, "t", "s", "fr", ["fr"])
        self.assertIsNone(out)
        self.assertEqual(tr.calls, [])


class TestConsignesInjectees(unittest.TestCase):
    """Les garde-fous doivent atteindre le modèle, pas seulement le code."""

    def _prompts(self, title="Real Madrid bat Girona", summary="Le Real Madrid s'impose."):
        tr = FakeTranslator(FULL_CHAIN)
        with _no_network(body=f"{title}. {summary} Córdoba CF suivait le match."):
            chief_editor_review(tr, title, summary, "fr", LANGS)
        return tr.prompts

    def test_les_noms_propres_sont_verrouilles_a_la_traduction(self):
        trad_prompt = self._prompts()[2]
        self.assertIn("NOMS PROPRES", trad_prompt)
        self.assertIn("Real Madrid", trad_prompt)

    def test_la_consigne_d_humanisation_atteint_redaction_et_validation(self):
        prompts = self._prompts()
        self.assertIn("HUMANISATION", prompts[1])   # rédaction
        self.assertIn("HUMANISATION", prompts[3])   # validation finale

    def test_le_modele_sait_s_il_lit_l_article_ou_l_amorce(self):
        url = "https://exemple.test/a"
        tr = FakeTranslator(FULL_CHAIN)
        with _no_network(body="amorce courte", origin="rss"):
            chief_editor_review(tr, "t", "s", "fr", LANGS, url=url)
        self.assertIn("AMORCE", tr.prompts[1])

        tr = FakeTranslator(FULL_CHAIN)
        with _no_network(body="corps complet", origin="full"):
            chief_editor_review(tr, "t", "s", "fr", LANGS, url=url)
        self.assertIn("ARTICLE COMPLET", tr.prompts[1])

    def test_sans_url_on_travaille_sur_l_amorce_et_le_modele_le_sait(self):
        """Un item sans URL ne peut pas être lu : le prompt doit le refléter."""
        tr = FakeTranslator(FULL_CHAIN)
        with mock.patch.object(editorial, "article_text") as fetch:
            out = chief_editor_review(tr, "t", "s", "fr", LANGS)
        fetch.assert_not_called()
        self.assertIn("AMORCE", tr.prompts[1])
        self.assertEqual(out["source_read"], "rss")

    def test_les_calques_sont_repares_apres_le_modele(self):
        """Filet déterministe : même si le modèle dérape, « Royal Madrid » ne sort pas."""
        bad = json.loads(json.dumps(TRANSLATION))
        bad["fr"]["title"] = "Le Royal Madrid s'impose"
        bad["fr"]["lead"] = "Cordoue CF n'a pas existé face au Réel Madrid."
        tr = FakeTranslator([JUDGE_OK, WRITE, TRANSLATION, {"publish": True, "i18n": bad}])
        with _no_network():
            out = chief_editor_review(tr, "t", "s", "fr", LANGS)
        self.assertEqual(out["i18n"]["fr"]["title"], "Le Real Madrid s'impose")
        self.assertIn("Córdoba CF", out["i18n"]["fr"]["summary"])
        self.assertNotIn("Réel Madrid", out["i18n"]["fr"]["summary"])


if __name__ == "__main__":
    unittest.main()


class TestConsigneArabe(unittest.TestCase):
    """La consigne « reproduis à l'identique » est toxique pour l'arabe."""

    def _prompt_traduction(self, langs):
        tr = FakeTranslator(FULL_CHAIN)
        with _no_network(body="Arsenal confirme la prolongation de Mikel Arteta."):
            chief_editor_review(tr, "Arsenal et Mikel Arteta", "Prolongation.",
                                "fr", langs)
        return tr.prompts[2]

    def test_l_arabe_recoit_la_consigne_de_translitteration(self):
        prompt = self._prompt_traduction(["fr", "en", "es", "ar"])
        self.assertIn("INVERSE", prompt)
        self.assertIn("ريال مدريد", prompt)

    def test_sans_arabe_la_consigne_de_translitteration_est_absente(self):
        """Elle n'aurait aucun sens et gaspillerait des tokens."""
        self.assertNotIn("INVERSE", self._prompt_traduction(["fr", "en", "es"]))

    def test_le_lexique_sportif_arabe_atteint_le_traducteur(self):
        """« capitaine » ne doit jamais devenir قبطان (capitaine de navire)."""
        prompt = self._prompt_traduction(["fr", "en", "es", "ar"])
        self.assertIn("قبطان", prompt)      # l'interdit est nommé
        self.assertIn("قائدة", prompt)      # le féminin (foot féminin) aussi

    def test_un_qobtan_produit_par_le_modele_est_repare(self):
        """Filet déterministe : même si le modèle sort le mauvais registre."""
        bad = json.loads(json.dumps(TRANSLATION))
        bad["ar"]["title"] = "باتري، أول قبطان لبرشلونة"
        tr = FakeTranslator([JUDGE_OK, WRITE, TRANSLATION, {"publish": True, "i18n": bad}])
        with _no_network():
            out = chief_editor_review(tr, "t", "s", "fr", LANGS)
        self.assertIn("قائد", out["i18n"]["ar"]["title"])
        self.assertNotIn("قبطان", out["i18n"]["ar"]["title"])

    def test_la_validation_finale_refuse_un_arabe_mi_latin(self):
        tr = FakeTranslator(FULL_CHAIN)
        with _no_network():
            chief_editor_review(tr, "t", "s", "fr", LANGS)
        self.assertIn("AUCUN mot en alphabet latin", tr.prompts[3])
