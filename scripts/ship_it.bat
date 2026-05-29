@echo off
REM ship_it.bat — push immediat avec log complet pour debug.
REM Log: to1000/ship_it.log

setlocal
cd /d "%~dp0\.."
set "LOG=%CD%\ship_it.log"

> "%LOG%" echo === ship_it %DATE% %TIME% ===
>> "%LOG%" echo CWD: %CD%
>> "%LOG%" echo PATH check:
>> "%LOG%" where git 2>&1

REM Nettoyer un eventuel lock stale (.git/index.lock peut bloquer git add)
if exist ".git\index.lock" (
  >> "%LOG%" echo Removing stale .git\index.lock
  del /f /q ".git\index.lock" >> "%LOG%" 2>&1
)

>> "%LOG%" echo.
>> "%LOG%" echo --- git status avant ---
>> "%LOG%" git status --short 2>&1

>> "%LOG%" echo.
>> "%LOG%" echo --- git add ---
>> "%LOG%" git add ^
  .github/workflows/ai-editorial.yml ^
  .github/workflows/news-sync.yml ^
  .github/workflows/stats-sync.yml ^
  .github/workflows/indexnow-ping.yml ^
  EDITORIAL/ ^
  public/world-cup/ ^
  public/news/ ^
  public/wc.json ^
  public/_polls.js ^
  public/_comments.js ^
  public/sitemap.xml ^
  scripts/news_to_html.py ^
  scripts/sitemap_generator.py ^
  scripts/wc_countdown_update.py ^
  scripts/claude_journalist.py ^
  scripts/ship_it.bat ^
  firestore.rules ^
  DEPLOY_INSTRUCTIONS.md ^
  KAIZEN.md 2>&1

>> "%LOG%" echo.
>> "%LOG%" echo --- staged stat ---
>> "%LOG%" git diff --cached --stat 2>&1

>> "%LOG%" echo.
>> "%LOG%" echo --- git commit ---
>> "%LOG%" git commit -m "feat: WC 2026 hub + Maroc/Portugal pages + AI editorial + GH Actions cron" 2>&1

>> "%LOG%" echo.
>> "%LOG%" echo --- git remote ---
>> "%LOG%" git remote -v 2>&1

>> "%LOG%" echo.
>> "%LOG%" echo --- git push ---
>> "%LOG%" git push 2>&1
set ERR=%ERRORLEVEL%

>> "%LOG%" echo.
>> "%LOG%" echo === FIN ship_it (exit=%ERR%) ===
exit /b %ERR%
