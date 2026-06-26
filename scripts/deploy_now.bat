@echo off
REM deploy_now.bat - deploie le dossier public/ sur Cloudflare Pages (projet to1000)
REM Double-clic pour mettre le site en ligne. Necessite l'auth wrangler (deja faite sur ce PC).
REM Log: to1000\scripts\deploy2.log

setlocal
cd /d "%~dp0\.."
set "LOG=%CD%\scripts\deploy2.log"

echo === deploy_now %DATE% %TIME% ===
echo Dossier deploye : %CD%\public
echo Projet Cloudflare : to1000
echo.
echo Deploiement en cours... (log : %LOG%)

> "%LOG%" echo === deploy_now %DATE% %TIME% ===
npx wrangler@latest pages deploy public/ --project-name to1000 --branch main --commit-dirty=true >> "%LOG%" 2>&1
set ERR=%ERRORLEVEL%

type "%LOG%"
echo.
if "%ERR%"=="0" (
  echo ✅ Deploiement reussi — le site est en ligne : https://to1000.com
) else (
  echo ❌ Echec (exit=%ERR%). Verifie l'auth wrangler : npx wrangler login
)
echo === FIN (exit=%ERR%) ===
pause
exit /b %ERR%
