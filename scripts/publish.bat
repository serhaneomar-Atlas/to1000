@echo off
REM ============================================================
REM  publish.bat — REPARE + MET EN LIGNE la refonte to1000.com
REM
REM  Pourquoi : la refonte (22 commits) est sur ce PC mais pas sur
REM  GitHub. Les bots GitHub deploient l'ANCIEN code -> le site
REM  revient a l'ancien. Ce script pousse ta refonte sur GitHub
REM  (force, car le depot a diverge a cause des donnees auto des
REM  bots qui se regenerent) PUIS deploie sur Cloudflare.
REM
REM  Double-clic = GitHub + site synchronises sur la nouvelle version.
REM  Log : to1000\scripts\publish.log
REM ============================================================
setlocal
cd /d "%~dp0\.."
set "LOG=%CD%\scripts\publish.log"

echo ============================================
echo  PUBLISH to1000  -  %DATE% %TIME%
echo ============================================
echo Dossier : %CD%
echo.

if exist ".git\index.lock" del /f /q ".git\index.lock"

echo [1/2] Envoi de la refonte vers GitHub (git push --force)...
> "%LOG%" echo === publish %DATE% %TIME% ===
git push --force origin main >> "%LOG%" 2>&1
if errorlevel 1 (
  echo.
  echo   X  ECHEC du push. Details :
  type "%LOG%"
  echo.
  echo   - Verifie ta connexion Internet et tes acces GitHub.
  echo   - Si on te demande un identifiant : connecte-toi a GitHub Desktop
  echo     une fois, ou lance "gh auth login".
  pause
  exit /b 1
)
echo   OK : refonte poussee sur GitHub.
echo.

echo [2/2] Deploiement immediat sur Cloudflare Pages...
npx wrangler@latest pages deploy public/ --project-name to1000 --branch main --commit-dirty=true >> "%LOG%" 2>&1
set ERR=%ERRORLEVEL%
if "%ERR%"=="0" (
  echo   OK : deploye.
  echo.
  echo   ============================================
  echo    TERMINE : GitHub + site sont a jour.
  echo    -^> https://to1000.com  (nouvelle version)
  echo   ============================================
) else (
  echo   Push OK, mais le deploiement Cloudflare a echoue (exit=%ERR%).
  echo   Pas grave : GitHub a la refonte, le prochain workflow deploiera.
  echo   Pour forcer maintenant : scripts\deploy_now.bat  (ou: npx wrangler login)
)
echo.
pause
exit /b %ERR%
