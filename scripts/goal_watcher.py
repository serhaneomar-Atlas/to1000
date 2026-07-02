"""goal_watcher.py — wrapper manuel de la sync des buts.

Historique :
  - 2026-05-07 : stub de redirection vers goal_watcher_v2.py (migration ESPN).
  - 2026-07-01 : goal_watcher_v2.py n'a JAMAIS été commité → le stub plantait
    (ModuleNotFoundError) et la tâche Windows échouait chaque minute depuis des
    semaines (watcher.log). La détection des buts vit désormais dans
    update_stats_v2.sync_goals(), exécutée par GitHub Actions
    (update-cr7-goals.yml, */5 min en fenêtre de match). Ce wrapper reste pour
    un run manuel local ; la tâche planifiée Windows "CR7GoalWatcher" est
    obsolète et doit être désactivée (voir run_watcher.bat).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from update_stats_v2 import main as _main  # noqa: E402

if __name__ == "__main__":
    sys.exit(_main())
