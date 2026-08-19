"""Résilience de la synchro stats face à une panne ESPN.

Contexte : ESPN a renvoyé 403 sur l'endpoint `summary` tous les jours à partir
du 12/08/2026. L'exception remontait de `refresh_last_match` jusqu'à `main`, ce
qui tuait le script AVANT `refresh_next_match` et AVANT l'écriture — donc même
les buts déjà synchronisés avec succès étaient jetés. Résultat : stats.json
figé au 26/07 pendant trois semaines, avec un workflow rouge chaque matin.

Ces tests fixent le contrat : une source qui tombe n'empêche ni les autres de
tourner, ni le fichier d'être écrit.
"""
import sys
from pathlib import Path
from unittest import mock

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

update_stats_v2 = pytest.importorskip(
    "update_stats_v2", reason="requests non installé")


BOUM = RuntimeError(
    "ESPN GET failed after 3 attempts: .../ksa.1/summary?event=401900402 | "
    "403 Client Error: Forbidden")


@pytest.fixture
def stats_fictives():
    return {"goals": 976, "remaining": 24, "version": 37,
            "last_match": {"home_team": "Portugal"},
            "next_match": {"home_team": "Portugal"}}


def _run(monkeypatch, stats, *, goals, last, next_, dry_run=True):
    """Exécute main() avec les trois sources simulées. Renvoie (code, sauvés)."""
    sauves = []
    monkeypatch.setattr(update_stats_v2, "load_stats", lambda: stats)
    monkeypatch.setattr(update_stats_v2, "save_stats", lambda s: sauves.append(s))
    monkeypatch.setattr(update_stats_v2, "sync_goals", goals)
    monkeypatch.setattr(update_stats_v2, "refresh_last_match", last)
    monkeypatch.setattr(update_stats_v2, "refresh_next_match", next_)
    monkeypatch.setenv("FORCE_GOALS", "")
    argv = ["update_stats_v2.py"] + (["--dry-run"] if dry_run else [])
    with mock.patch.object(sys, "argv", argv):
        return update_stats_v2.main(), sauves


def _boum(_stats):
    raise BOUM


def _rien(_stats):
    return False


def _change(_stats):
    return True


def test_un_echec_sur_le_dernier_match_ne_bloque_pas_le_prochain(monkeypatch, stats_fictives):
    """Le bug exact : le prochain match n'était plus jamais rafraîchi."""
    appele = []
    code, _ = _run(monkeypatch, stats_fictives,
                   goals=_rien, last=_boum,
                   next_=lambda s: appele.append("next") or True)
    assert appele == ["next"]
    assert code == 0


def test_un_echec_partiel_n_empeche_pas_l_ecriture(monkeypatch, stats_fictives):
    """Les buts synchronisés avec succès doivent survivre à la panne du reste."""
    code, sauves = _run(monkeypatch, stats_fictives,
                        goals=_change, last=_boum, next_=_rien,
                        dry_run=False)
    assert code == 0
    assert len(sauves) == 1
    assert sauves[0]["version"] == 38


def test_un_echec_partiel_ne_fait_pas_echouer_le_workflow(monkeypatch, stats_fictives):
    """Un workflow rouge tous les matins pour une panne externe finit ignoré."""
    code, _ = _run(monkeypatch, stats_fictives,
                   goals=_rien, last=_boum, next_=_rien)
    assert code == 0


def test_toutes_les_sources_tombees_est_une_vraie_panne(monkeypatch, stats_fictives):
    code, _ = _run(monkeypatch, stats_fictives,
                   goals=_boum, last=_boum, next_=_boum)
    assert code == 1


def test_aucun_echec_rend_zero(monkeypatch, stats_fictives):
    code, _ = _run(monkeypatch, stats_fictives,
                   goals=_rien, last=_rien, next_=_rien)
    assert code == 0


def test_les_donnees_precedentes_sont_conservees_quand_une_source_tombe(monkeypatch, stats_fictives):
    """Mieux vaut un dernier match daté qu'un dernier match effacé."""
    avant = dict(stats_fictives["last_match"])
    _run(monkeypatch, stats_fictives, goals=_rien, last=_boum, next_=_change)
    assert stats_fictives["last_match"] == avant
