"""Garde-fous sur les workflows GitHub.

Un workflow ne se teste pas facilement, mais certaines erreurs y sont
silencieuses ET répétables — elles méritent un test.

Cas vécu : l'étape d'audit se terminait par `| tee audit.txt`. En bash, le code
de sortie d'un pipeline est celui de la DERNIÈRE commande, et `tee` réussit
toujours. L'audit sortait donc 1 sur un score sous le seuil sans que l'étape
échoue — et l'alerte n'était jamais levée. Le workflow censé détecter les
pannes silencieuses en était lui-même une.
"""
import re
from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def _steps_avec_tee(contenu: str) -> list[str]:
    """Blocs `run:` dont une commande est pipée vers tee."""
    blocs = re.split(r"\n      - name: ", contenu)
    return [b for b in blocs if "| tee " in b]


@pytest.mark.parametrize("fichier", sorted(WORKFLOWS.glob("*.yml")),
                         ids=lambda p: p.name)
def test_un_pipe_vers_tee_exige_pipefail(fichier):
    """Sinon le code de sortie de la commande utile est perdu."""
    contenu = fichier.read_text(encoding="utf-8")
    for bloc in _steps_avec_tee(contenu):
        titre = bloc.split("\n", 1)[0].strip()
        assert "set -o pipefail" in bloc, (
            f"{fichier.name} · étape « {titre} » : une commande est pipée vers "
            "tee sans `set -o pipefail`. Son code de sortie sera masqué et "
            "l'étape passera au vert quoi qu'il arrive."
        )


def test_le_workflow_d_audit_lance_les_tests_avant_d_auditer():
    """Auditer avec du code cassé ne prouve rien."""
    contenu = (WORKFLOWS / "editorial-audit.yml").read_text(encoding="utf-8")
    # On compare les COMMANDES, pas les premières occurrences du nom : le script
    # est aussi cité dans les `paths:` du déclencheur, bien plus haut.
    pos_tests = contenu.index("python -m pytest")
    pos_audit = contenu.index("python scripts/audit_editorial.py")
    assert pos_tests < pos_audit


def test_le_seuil_d_alerte_est_explicite():
    contenu = (WORKFLOWS / "editorial-audit.yml").read_text(encoding="utf-8")
    assert "--seuil" in contenu
    assert "steps.audit.outcome == 'failure'" in contenu, (
        "l'alerte doit se déclencher sur l'échec de l'étape d'audit"
    )
