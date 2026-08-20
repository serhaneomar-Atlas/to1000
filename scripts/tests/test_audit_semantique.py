"""Juge de fond — il relit le source complet contre le publié, et sanctionne.

Le cas qui a motivé ce juge : un résumé fluide, bien traduit, qui ratait le
fait central du source (« le quatuor de capitaines devient un quintette mené
par Patri Guijarro »). Aucun contrôle de forme ne pouvait le voir.
"""
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import audit_semantique
from audit_semantique import _cache_key, juger, sanctionner


class FakeTr:
    gemini_enabled = True

    def __init__(self, verdict):
        self.verdict = verdict
        self.payloads = []

    def _call_gemini(self, system, user, max_tokens=0):
        self.payloads.append((system, user))
        return json.dumps(self.verdict) if self.verdict else None

    def _parse_json_block(self, raw):
        return json.loads(raw)


def _item(engine="gemini-editor"):
    return {
        "id": "abc", "url": "https://exemple.test/a",
        "title": "Patri, primera capitana del Barça y entran Aitana y Graham",
        "summary": "Sale Alexia Putellas.",
        "primary_source": {"lang": "es"},
        "i18n": {
            "es": {"title": "Patri, primera capitana", "summary": "Sale Alexia."},
            "fr": {"title": "t", "summary": "lead", "body": ["p1"], "engine": engine},
            "ar": {"title": "ت", "summary": "س", "engine": engine},
        },
    }


BON = {"fait_central": "Guijarro capitaine n°1", "central_restitue": True,
       "faits_manquants": [], "erreurs": [], "note": 9}
MAUVAIS = {"fait_central": "le quatuor devient un quintette mené par Guijarro",
           "central_restitue": False,
           "faits_manquants": ["quintette de capitaines", "rang de Guijarro"],
           "erreurs": [], "note": 4}


def _no_network():
    return mock.patch.object(audit_semantique, "article_text",
                             return_value=("corps complet du source", "full"))


def test_le_juge_recoit_le_source_et_le_publie():
    tr = FakeTr(BON)
    with _no_network():
        v = juger(tr, _item())
    system, user = tr.payloads[0]
    payload = json.loads(user)
    assert payload["source"]["texte"] == "corps complet du source"
    assert payload["publie"]["lead"] == "lead"
    assert "fait_central" in system
    assert v["note"] == 9


def test_un_verdict_mauvais_sanctionne():
    """Retiré de l'affichage ET cache purgé → sera refait, pas juste noté."""
    it = _item()
    cache = {_cache_key(it): {"publish": True}}
    sanctionner(it, cache)
    assert it["i18n"]["fr"]["engine"] == "retire-par-audit"
    assert it["i18n"]["ar"]["engine"] == "retire-par-audit"
    assert cache == {}


def test_la_sanction_rend_l_article_non_affichable():
    """Le garde-fou de publication doit remplacer le retiré par le source."""
    from news_to_html import publishable
    it = _item()
    sanctionner(it, {})
    assert not publishable(it, "fr")
    assert publishable(it, "es")          # le texte original reste montrable


def test_central_absent_est_mauvais_meme_avec_note_haute():
    """central_restitue=False doit sanctionner quel que soit le chiffre."""
    verdict = dict(MAUVAIS, note=8)
    note = float(verdict["note"])
    mauvais = (note < 7 or not verdict.get("central_restitue")
               or bool(verdict.get("erreurs")))
    assert mauvais


def test_une_erreur_de_fait_est_mauvaise_meme_avec_note_haute():
    verdict = {"central_restitue": True, "faits_manquants": [],
               "erreurs": ["masculin pour une joueuse"], "note": 8}
    mauvais = (float(verdict["note"]) < 7 or not verdict["central_restitue"]
               or bool(verdict["erreurs"]))
    assert mauvais


def test_le_juge_indisponible_rend_none():
    tr = FakeTr(None)
    with _no_network():
        assert juger(tr, _item()) is None


def test_l_audit_deterministe_compte_les_retires():
    from audit_editorial import audite_item
    it = _item()
    it["editorial"] = {"semantique": {"note": 4, "manque": ["quintette"],
                                      "retire": True}}
    sanctionner(it, {})
    defauts = [d for d in audite_item(it) if d["type"] == "infidele"]
    assert len(defauts) == 2              # fr + ar retirées
    assert "quintette" in defauts[0]["detail"]
