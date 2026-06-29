@echo off
REM Lance par Windows Task Scheduler — fréquence recommandée: 1 minute.
REM Le script Python décide lui-même s'il agit (smart polling): action chaque
REM minute pendant la fenêtre match (-30min à +2h30 du kickoff), sinon refresh
REM léger 1x/h. Plus besoin de clé API-Football depuis la migration ESPN du 07/05/2026.
python "C:\Users\serha\Desktop\To1000.com\to1000\scripts\goal_watcher_v2.py" >> "C:\Users\serha\Desktop\To1000.com\to1000\scripts\watcher.log" 2>&1
