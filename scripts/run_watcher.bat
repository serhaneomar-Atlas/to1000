@echo off
REM [2026-07-01] OBSOLETE — la detection des buts tourne sur GitHub Actions
REM (workflow update-cr7-goals.yml, toutes les 5 min en fenetre de match, via
REM update_stats_v2.sync_goals). Ce .bat ne fait plus rien pour eviter que la
REM tache planifiee "CR7GoalWatcher" ecrive un stats.json local divergent du
REM remote (et remplisse watcher.log — 13 Mo d'erreurs avant ce fix).
REM A FAIRE (Omar) : desactiver la tache planifiee, par ex. dans un cmd admin :
REM   schtasks /Change /TN "CR7GoalWatcher" /DISABLE
REM Pour un run manuel local : python scripts\goal_watcher.py
exit /b 0
