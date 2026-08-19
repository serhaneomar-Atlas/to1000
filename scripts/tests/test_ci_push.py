"""Le push d'un bot ne doit jamais perdre son travail en silence.

Constaté le 19/08/2026 : news-editorial a produit un enrichissement réel
(35 fichiers, 1096 insertions), l'a commité sur le runner, puis a poussé avec

    git push origin HEAD:main 2>/dev/null || git push 2>/dev/null || true

Un autre workflow avait poussé à la même seconde. Le push a été rejeté en
non-fast-forward, la sortie partait dans /dev/null, le `|| true` a rendu
l'étape verte — et le commit n'a jamais atteint le dépôt. Le site déployé
avait l'enrichissement, le dépôt non, et rien dans les logs.

Ces tests montent deux clones sur un dépôt nu et rejouent la collision.
"""
import subprocess
from pathlib import Path

import pytest

CI_PUSH = Path(__file__).resolve().parents[1] / "ci_push.sh"


def sh(cmd, cwd, check=True):
    return subprocess.run(cmd, cwd=cwd, shell=True, check=check,
                          capture_output=True, text=True)


@pytest.fixture
def depots(tmp_path):
    """(bot, autre, remote) — deux clones qui poussent sur le même dépôt nu."""
    remote = tmp_path / "remote.git"
    sh(f"git init -q --bare -b main {remote}", tmp_path)

    clones = {}
    for nom in ("bot", "autre"):
        chemin = tmp_path / nom
        sh(f"git clone -q {remote} {chemin}", tmp_path)
        sh("git config user.email t@t && git config user.name test", chemin)
        clones[nom] = chemin

    bot = clones["bot"]
    sh("git checkout -q -B main", bot)
    (bot / "base.txt").write_text("base")
    sh("git add -A && git commit -qm base && git push -q origin HEAD:main", bot)

    autre = clones["autre"]
    sh("git fetch -q origin main && git checkout -q -B main origin/main", autre)
    return bot, autre, remote


def _commits_distants(remote):
    return sh("git log --oneline main", remote).stdout


def _commit_concurrent(autre):
    (autre / "concurrent.txt").write_text("poussé par un autre workflow")
    sh("git add -A && git commit -qm concurrent && git push -q origin HEAD:main", autre)


def _travail_du_bot(bot):
    (bot / "enrichi.txt").write_text("35 fichiers, 1096 insertions")
    sh("git add -A && git commit -qm enrichissement", bot)


def test_le_push_naif_perd_le_travail_en_silence(depots):
    """Le comportement d'avant — documenté pour qu'il ne revienne pas."""
    bot, autre, remote = depots
    _commit_concurrent(autre)
    _travail_du_bot(bot)

    r = sh("git push origin HEAD:main 2>/dev/null "
           "|| git push 2>/dev/null || true", bot, check=False)
    assert r.returncode == 0                       # vert…
    assert "enrichissement" not in _commits_distants(remote)   # …et rien poussé


def test_ci_push_rebase_et_conserve_le_travail(depots):
    bot, autre, remote = depots
    _commit_concurrent(autre)
    _travail_du_bot(bot)

    r = sh(f"bash {CI_PUSH} main", bot, check=False)
    assert r.returncode == 0, r.stdout + r.stderr

    distants = _commits_distants(remote)
    assert "enrichissement" in distants
    assert "concurrent" in distants               # sans écraser l'autre workflow


def test_ci_push_pousse_directement_quand_il_n_y_a_pas_de_collision(depots):
    bot, _, remote = depots
    _travail_du_bot(bot)

    r = sh(f"bash {CI_PUSH} main", bot, check=False)
    assert r.returncode == 0
    assert "tentative 1/" in r.stdout
    assert "enrichissement" in _commits_distants(remote)


def test_ci_push_signale_l_echec_au_lieu_de_le_taire(depots, tmp_path):
    """Perdre le travail est acceptable ; le perdre sans le savoir ne l'est pas."""
    bot, _, remote = depots
    _travail_du_bot(bot)
    # Remote injoignable : plus aucun push ni fetch ne peut aboutir.
    sh(f"git remote set-url origin {tmp_path / 'nexistepas.git'}", bot)

    r = sh(f"CI_PUSH_TENTATIVES=1 bash {CI_PUSH} main", bot, check=False)
    assert r.returncode == 1
    assert "::error::" in r.stdout
    assert "PAS dans le dépôt" in r.stdout
