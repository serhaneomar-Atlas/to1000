"""
goal_watcher.py — STUB DE REDIRECTION (migré vers goal_watcher_v2.py)

Migration : 2026-05-07
Source originale : voir goal_watcher_legacy.py.bak

L'ancien watcher dépendait d'API-Football (plan gratuit), qui refusait la
saison 2025-26 et le paramètre 'next'. Migration vers ESPN (gratuit, sans clé,
pas de quota visible).

Ce stub redirige tous les appels vers le nouveau watcher pour ne pas casser
la tâche Windows existante (Task Scheduler "CR7GoalWatcher").
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from goal_watcher_v2 import main as _main  # noqa: E402

if __name__ == "__main__":
    sys.exit(_main())
