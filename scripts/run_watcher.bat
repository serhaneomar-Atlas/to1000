@echo off
REM Lance par Windows Task Scheduler toutes les 5 minutes
set APIFOOTBALL_KEY=aa61f27b1f241c5b2ce6a8a0098fc57f
python "C:\Users\serha\Desktop\To1000.com\to1000\scripts\goal_watcher.py" >> "C:\Users\serha\Desktop\To1000.com\to1000\scripts\watcher.log" 2>&1
