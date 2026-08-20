"""Le cache de traduction ne doit pas resservir les erreurs d'avant les règles.

Cas concret : un « قبطان » MyMemory mis en cache en juillet reviendrait à
chaque refresh du fil, même après l'ajout de la règle قبطان → قائد — le cache
n'est pas versionné par règle de réparation. On répare donc aussi à la lecture.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from translator import Translator


class FakeCache:
    def __init__(self, store):
        self.store = store

    def get(self, key):
        # Toute clé demandée renvoie l'entrée polluée — on teste la lecture,
        # pas le hachage.
        return dict(self.store) if self.store else None

    def set(self, key, value):
        pass


def _tr(store):
    tr = Translator(cache_path=None)
    tr.cache = FakeCache(store)
    tr.gemini_enabled = False
    tr.mymemory_enabled = False
    return tr


def test_un_qobtan_en_cache_est_repare_a_la_lecture():
    tr = _tr({"title": "باتري، أول قبطان لبرشلونة",
              "summary": "حارس البوابة تألق", "engine": "mymemory",
              "needs_translation": False})
    out = tr.translate_pair("t", "s", src="es", targets=["ar"])
    assert "قائد" in out["ar"]["title"]
    assert "قبطان" not in out["ar"]["title"]
    assert out["ar"]["summary"] == "حارس المرمى تألق"


def test_un_royal_madrid_en_cache_est_repare_a_la_lecture():
    tr = _tr({"title": "Le Royal Madrid s'impose", "summary": "Victoire du Réel Madrid.",
              "engine": "mymemory", "needs_translation": False})
    out = tr.translate_pair("t", "s", src="es", targets=["fr"])
    assert out["fr"]["title"] == "Le Real Madrid s'impose"
    assert "Réel" not in out["fr"]["summary"]


def test_une_entree_propre_ressort_inchangee():
    tr = _tr({"title": "ريال مدريد يفوز", "summary": "قائد الفريق سجّل هدفين.",
              "engine": "gemini", "needs_translation": False})
    out = tr.translate_pair("t", "s", src="es", targets=["ar"])
    assert out["ar"]["title"] == "ريال مدريد يفوز"
    assert out["ar"]["summary"] == "قائد الفريق سجّل هدفين."
