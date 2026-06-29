"""
update_stats.py — STUB DE REDIRECTION (migré vers update_stats_v2.py)

Migration : 2026-05-07
Source originale : voir update_stats_legacy.py.bak

Ancienne version basée sur API-Football, qui refusait la saison 2025-26 sur
le tier gratuit. Nouvelle version basée sur ESPN.

Variable FORCE_GOALS toujours supportée par le successeur.
Ce stub maintient la compatibilité avec .github/workflows/update-cr7-goals.yml.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from update_stats_v2 import main as _main  # noqa: E402

if __name__ == "__main__":
    sys.exit(_main())
