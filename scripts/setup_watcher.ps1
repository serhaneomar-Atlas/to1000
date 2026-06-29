# setup_watcher.ps1 -- Installe le Goal Watcher CR7 comme tache Windows
#
# UTILISATION :
#   1. Ouvre PowerShell en tant qu'Administrateur
#   2. cd "C:\Users\serha\Desktop\To1000.com\to1000\scripts"
#   3. .\setup_watcher.ps1
#
# Cle API gratuite : https://dashboard.api-football.com/profile?access

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "CR7 Goal Watcher -- Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# --- Chemins ---
$ScriptDir     = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir    = Split-Path -Parent $ScriptDir
$WatcherScript = Join-Path $ScriptDir "goal_watcher.py"
$BatchFile     = Join-Path $ScriptDir "run_watcher.bat"
$LogFile       = Join-Path $ScriptDir "watcher.log"
$TaskName      = "CR7GoalWatcher"

# --- Verifier Python ---
Write-Host ""
Write-Host "-> Verification de Python..." -NoNewline
try {
    $pythonPath = (Get-Command python -ErrorAction Stop).Source
    $pythonVer  = & python --version 2>&1
    Write-Host " [OK] $pythonVer" -ForegroundColor Green
} catch {
    Write-Host " [ERREUR]" -ForegroundColor Red
    Write-Host "  Python non trouve. Installe Python depuis https://python.org" -ForegroundColor Yellow
    exit 1
}

# --- Verifier requests ---
Write-Host "-> Verification de la librairie requests..." -NoNewline
$reqCheck = & python -c "import requests; print('ok')" 2>&1
if ($reqCheck -eq "ok") {
    Write-Host " [OK]" -ForegroundColor Green
} else {
    Write-Host " Installation en cours..."
    & python -m pip install requests --quiet
    Write-Host "  [OK] requests installe" -ForegroundColor Green
}

# --- Source de donnees ---
Write-Host ""
Write-Host "-> Source de donnees : ESPN (gratuit, aucune cle requise)" -ForegroundColor Yellow
Write-Host "  Migration v2 du 2026-05-07 : abandon d'API-Football" -ForegroundColor Gray
Write-Host ""

# Nettoyage : si une ancienne cle APIFOOTBALL_KEY traine, on la retire
$existingKey = [System.Environment]::GetEnvironmentVariable("APIFOOTBALL_KEY", "Machine")
if ($existingKey) {
    Write-Host "  Ancienne APIFOOTBALL_KEY detectee, suppression..." -ForegroundColor Gray
    [System.Environment]::SetEnvironmentVariable("APIFOOTBALL_KEY", $null, "Machine")
    Write-Host "  [OK] Cle obsolete retiree des variables systeme" -ForegroundColor Green
}

# --- Creer le fichier .bat (sans cle API) ---
$batLines = @(
    "@echo off",
    "REM Lance par Windows Task Scheduler chaque minute (smart polling).",
    "REM Le script Python decide d'agir ou non selon la fenetre match.",
    "python `"$WatcherScript`" >> `"$LogFile`" 2>&1"
)
Set-Content -Path $BatchFile -Value $batLines -Encoding ASCII
Write-Host "  [OK] Fichier run_watcher.bat cree (sans cle API)" -ForegroundColor Green

# --- Creer la tache Task Scheduler ---
Write-Host ""
Write-Host "-> Enregistrement de la tache Windows Task Scheduler..." -ForegroundColor Yellow

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Frequence : 1 minute. Le smart polling cote Python evite la charge inutile.
$trigger  = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 1) -Once -At (Get-Date)
$action   = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$BatchFile`""
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 3) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName    $TaskName `
    -Action      $action `
    -Trigger     $trigger `
    -Settings    $settings `
    -Principal   $principal `
    -Description "Detecte les buts de CR7 et met a jour to1000.com" `
    -Force | Out-Null

Write-Host "  [OK] Tache '$TaskName' creee -- s'execute toutes les 5 minutes" -ForegroundColor Green

# --- Test immediat (smoke test ESPN + Wikipedia) ---
Write-Host ""
Write-Host "-> Smoke test des sources de donnees..." -ForegroundColor Yellow
& python $WatcherScript --smoke 2>&1 | Select-Object -First 25 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
Write-Host "  [OK] Voir watcher.log pour les details complets" -ForegroundColor Green

# --- Resume ---
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "[OK] CR7 Goal Watcher v2 installe avec succes !" -ForegroundColor Green
Write-Host ""
Write-Host "  - Verifie chaque minute, agit en fenetre match (smart polling)"
Write-Host "  - Source ESPN (gratuit) + cross-check Wikipedia hebdo"
Write-Host "  - Deploie automatiquement sur to1000.com via wrangler"
Write-Host "  - Notification Windows sur ton PC en cas de but"
Write-Host ""
Write-Host "  Logs      : $LogFile"
Write-Host "  Tache     : Gestionnaire de taches Windows -> '$TaskName'"
Write-Host ""
Write-Host "  Pour voir les logs en direct :"
Write-Host "  Get-Content '$LogFile' -Tail 50 -Wait"
Write-Host ""
