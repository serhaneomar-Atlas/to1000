"""Résilience du lot d'enrichissement + chemins de prompt réellement exercés.

Le 20/08, un NameError dans la construction du prompt d'editorialize_pair
(variable de la mauvaise fonction) a tué 24 runs news-editorial d'affilée :
UN item cassé annulait tout le lot, et aucun test n'exerçait ce chemin — les
tests mockaient Gemini AVANT la construction du prompt. Ces tests ferment les
deux trous.
"""
import json
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import enrich_news
from translator import Translator


# ── 1. Les constructions de prompt s'exécutent pour de vrai ────────────────
class GeminiCapture(Translator):
    """Translator avec Gemini 'activé' mais appels capturés : la construction
    du prompt (là où vivait le NameError) s'exécute réellement."""

    def __init__(self):
        super().__init__(cache_path=None)
        self.gemini_enabled = True
        self.mymemory_enabled = False
        self.systems = []

    def _call_gemini(self, system, user, max_tokens=500):
        self.systems.append(system)
        return None          # pas de réponse → replis, mais le prompt est bâti


def test_editorialize_pair_construit_son_prompt_sans_planter():
    """Le NameError des 24 runs : [dst] dans une fonction qui n'a que langs."""
    tr = GeminiCapture()
    tr.editorialize_pair("Patri, primera capitana", "Sale Alexia.",
                         "es", ["fr", "en", "ar"])
    assert tr.systems, "aucun prompt construit"
    assert "NOMS PROPRES" in tr.systems[0]


def test_translate_pair_construit_ses_prompts_sans_planter():
    tr = GeminiCapture()
    tr.translate_pair("Patri, primera capitana", "Sale Alexia.",
                      src="es", targets=["fr", "ar"])
    assert len(tr.systems) == 2
    # la consigne arabe ne part que vers l'arabe
    assert "INVERSE" not in tr.systems[0]     # fr
    assert "INVERSE" in tr.systems[1]         # ar


# ── 2. Un item qui explose ne tue pas le lot ────────────────────────────────
def _fake_tr():
    tr = mock.Mock()
    tr.gemini_enabled = True
    tr._calls_gemini = 0
    tr.stats.return_value = {}
    tr.cache = mock.Mock()
    return tr


def _run_main(monkey_items, traiter):
    data = {"items": monkey_items}
    with mock.patch.object(enrich_news, "NEWS") as news, \
         mock.patch.object(enrich_news, "Translator", return_value=_fake_tr()), \
         mock.patch.object(enrich_news, "_traiter", side_effect=traiter):
        news.exists.return_value = True
        news.read_text.return_value = json.dumps(data)
        news.write_text = mock.Mock()
        code = enrich_news.main()
        return code, news.write_text


def test_un_item_qui_explose_est_saute_et_le_lot_continue():
    items = [{"id": "a"}, {"id": "boom"}, {"id": "c"}]
    vus = []

    def traiter(it, tr):
        vus.append(it["id"])
        if it["id"] == "boom":
            raise NameError("name 'dst' is not defined")
        return True, True, False

    code, write = _run_main(items, traiter)
    assert vus == ["a", "boom", "c"]      # c est traité malgré boom
    assert code == 0
    write.assert_called_once()             # le travail de a et c est sauvé


def test_tous_les_items_en_echec_est_une_vraie_panne():
    items = [{"id": "a"}, {"id": "b"}]

    def traiter(it, tr):
        raise NameError("name 'dst' is not defined")

    code, write = _run_main(items, traiter)
    assert code == 1                       # panne de chaîne signalée
    write.assert_not_called()


def test_aucun_item_est_un_run_vide_normal():
    code, _ = _run_main([], lambda it, tr: (False, False, False))
    assert code == 0
