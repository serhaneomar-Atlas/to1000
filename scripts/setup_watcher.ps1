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

# --- Cle API ---
Write-Host ""
Write-Host "-> Configuration de la cle API-Football" -ForegroundColor Yellow
Write-Host "  (Gratuit sur https://dashboard.api-football.com/profile?access)" -ForegroundColor Gray
Write-Host ""

$existingKey = [System.Environment]::GetEnvironmentVariable("APIFOOTBALL_KEY", "Machine")
if ($existingKey) {
    Write-Host "  Cle existante trouvee : $($existingKey.Substring(0, [Math]::Min(8, $existingKey.Length)))..." -ForegroundColor Gray
    $change = Read-Host "  Veux-tu la remplacer ? (o/N)"
    if ($change -eq "o" -or $change -eq "O") {
        $apiKey = Read-Host "  Entre ta nouvelle cle API"
    } else {
        $apiKey = $existingKey
        Write-Host "  -> Cle existante conservee" -ForegroundColor Green
    }
} else {
    $apiKey = Read-Host "  Entre ta cle API-Football"
}

if (-not $apiKey -or $apiKey.Trim() -eq "") {
    Write-Host "  [ERREUR] Cle API vide -- setup annule" -ForegroundColor Red
    exit 1
}
$apiKey = $apiKey.Trim()

# Stocker comme variable systeme persistante
[System.Environment]::SetEnvironmentVariable("APIFOOTBALL_KEY", $apiKey, "Machine")
Write-Host "  [OK] Cle API enregistree comme variable systeme" -ForegroundColor Green

# --- Creer le fichier .bat ---
$batLines = @(
    "@echo off",
    "REM Lance par Windows Task Scheduler toutes les 5 minutes",
    "set APIFOOTBALL_KEY=$apiKey",
    "python `"$WatcherScript`" >> `"$LogFile`" 2>&1"
)
Set-Content -Path $BatchFile -Value $batLines -Encoding ASCII
Write-Host "  [OK] Fichier run_watcher.bat cree" -ForegroundColor Green

# --- Creer la tache Task Scheduler ---
Write-Host ""
Write-Host "-> Enregistrement de la tache Windows Task Scheduler..." -ForegroundColor Yellow

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$trigger  = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 5) -Once -At (Get-Date)
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

# --- Test immediat ---
Write-Host ""
Write-Host "-> Test de connexion API..." -ForegroundColor Yellow
$env:APIFOOTBALL_KEY = $apiKey
& python $WatcherScript 2>&1 | Select-Object -First 25 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
Write-Host "  [OK] Voir watcher.log pour les details complets" -ForegroundColor Green

# --- Resume ---
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "[OK] CR7 Goal Watcher installe avec succes !" -ForegroundColor Green
Write-Host ""
Write-Host "  - Verifie les buts toutes les 5 min pendant les matchs"
Write-Host "  - Deploie automatiquement sur to1000.com"
Write-Host "  - T'envoie une notification Windows sur ton PC"
Write-Host ""
Write-Host "  Logs      : $LogFile"
Write-Host "  Tache     : Gestionnaire de taches Windows -> '$TaskName'"
Write-Host ""
Write-Host "  Pour voir les logs en direct :"
Write-Host "  Get-Content '$LogFile' -Tail 50 -Wait"
Write-Host ""
