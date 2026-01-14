# ============================================
# Configuration du pipeline automatique quotidien
# Execution a 22h00 chaque jour
# VERSION SANS ADMINISTRATEUR
# ============================================

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "CONFIGURATION PIPELINE AUTOMATIQUE" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Configuration
$TASK_NAME = "ProcurementPipeline_Daily"
$EXECUTION_TIME = "22:00"
$PROJECT_ROOT = $PSScriptRoot
$LOG_DIR = Join-Path $PROJECT_ROOT "data\logs\scheduled"

# Chercher le script run_daily_pipeline.ps1
$SCRIPT_LOCATIONS = @(
    (Join-Path $PROJECT_ROOT "scripts\run_daily_pipeline.ps1"),
    (Join-Path $PROJECT_ROOT "run_daily_pipeline.ps1")
)

$SCRIPT_PATH = $null
foreach ($location in $SCRIPT_LOCATIONS) {
    if (Test-Path $location) {
        $SCRIPT_PATH = $location
        break
    }
}

Write-Host "`nConfiguration:" -ForegroundColor Yellow
Write-Host "  Nom tache: $TASK_NAME" -ForegroundColor Gray
Write-Host "  Heure execution: $EXECUTION_TIME" -ForegroundColor Gray
Write-Host "  Script: $SCRIPT_PATH" -ForegroundColor Gray
Write-Host "  Logs: $LOG_DIR" -ForegroundColor Gray

# Creer le dossier de logs
if (!(Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
    Write-Host "`nDossier logs cree: $LOG_DIR" -ForegroundColor Green
}

# Verifier que le script existe
if (!$SCRIPT_PATH) {
    Write-Host "`nERREUR: Script run_daily_pipeline.ps1 introuvable!" -ForegroundColor Red
    Write-Host "`nCherche dans:" -ForegroundColor Yellow
    foreach ($loc in $SCRIPT_LOCATIONS) {
        Write-Host "  - $loc" -ForegroundColor Gray
    }
    Write-Host "`nCree le script dans scripts\ ou utilise l'artifact fourni" -ForegroundColor Yellow
    exit 1
}

Write-Host "`nScript trouve: $SCRIPT_PATH" -ForegroundColor Green

# Supprimer l'ancienne tache si elle existe
Write-Host "`nVerification de l'ancienne tache..." -ForegroundColor Yellow
$existingTask = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Suppression de l'ancienne tache..." -ForegroundColor Yellow
    try {
        Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false -ErrorAction Stop
        Write-Host "Ancienne tache supprimee" -ForegroundColor Green
    } catch {
        Write-Host "ERREUR: Impossible de supprimer l'ancienne tache" -ForegroundColor Red
        Write-Host "Relancez PowerShell en tant qu'administrateur" -ForegroundColor Yellow
        exit 1
    }
}

# Creer le script wrapper avec logging
$WRAPPER_SCRIPT = Join-Path $PROJECT_ROOT "scripts\scheduled_pipeline_wrapper.ps1"
$wrapperContent = @"
# Wrapper pour execution planifiee avec logging
`$ErrorActionPreference = "Continue"
`$DATE = Get-Date -Format "yyyy-MM-dd_HHmmss"
`$LOG_FILE = "$LOG_DIR\pipeline_`$DATE.log"

# Rediriger la sortie vers le fichier log
Start-Transcript -Path `$LOG_FILE -Append

Write-Host "============================================"
Write-Host "PIPELINE AUTOMATIQUE - `$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "============================================"

try {
    # Changer vers le dossier du projet
    Set-Location "$PROJECT_ROOT"
    
    # Verifier que Docker est demarre
    Write-Host "Verification de Docker..." -ForegroundColor Yellow
    `$dockerTest = docker ps 2>&1
    if (`$LASTEXITCODE -ne 0) {
        Write-Host "Docker n'est pas demarre - tentative de demarrage..." -ForegroundColor Yellow
        
        # Tenter de demarrer Docker Desktop
        `$dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        if (Test-Path `$dockerPath) {
            Start-Process `$dockerPath
            Write-Host "Attente du demarrage de Docker (60 secondes)..." -ForegroundColor Yellow
            Start-Sleep -Seconds 60
            
            # Reverifier
            `$dockerTest = docker ps 2>&1
            if (`$LASTEXITCODE -ne 0) {
                Write-Host "ERREUR: Docker n'a pas demarre correctement" -ForegroundColor Red
                exit 1
            }
        } else {
            Write-Host "ERREUR: Docker Desktop introuvable" -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "Docker operationnel" -ForegroundColor Green
    
    # Activer l'environnement virtuel Python si necessaire
    `$venvPath = Join-Path "$PROJECT_ROOT" "venv\Scripts\Activate.ps1"
    if (Test-Path `$venvPath) {
        Write-Host "Activation environnement Python..." -ForegroundColor Yellow
        & `$venvPath
    }
    
    # Executer le pipeline
    Write-Host "`nExecution du pipeline..." -ForegroundColor Yellow
    & "$SCRIPT_PATH"
    
    `$exitCode = `$LASTEXITCODE
    
    if (`$exitCode -eq 0) {
        Write-Host "`n============================================" -ForegroundColor Green
        Write-Host "PIPELINE TERMINE AVEC SUCCES" -ForegroundColor Green
        Write-Host "============================================" -ForegroundColor Green
    } else {
        Write-Host "`n============================================" -ForegroundColor Red
        Write-Host "PIPELINE TERMINE AVEC ERREURS (code: `$exitCode)" -ForegroundColor Red
        Write-Host "============================================" -ForegroundColor Red
    }
    
    # Afficher le resume des fichiers generes
    `$outputDir = Join-Path "$PROJECT_ROOT" "data\output\supplier_orders"
    if (Test-Path `$outputDir) {
        `$latestDate = Get-ChildItem `$outputDir | Sort-Object Name -Descending | Select-Object -First 1
        if (`$latestDate) {
            `$files = Get-ChildItem `$latestDate.FullName -File
            Write-Host "`nFichiers generes: `$(`$files.Count)" -ForegroundColor Cyan
            foreach (`$file in `$files) {
                Write-Host "  - `$(`$file.Name)" -ForegroundColor Gray
            }
        }
    }
    
    exit `$exitCode
    
} catch {
    Write-Host "`n============================================" -ForegroundColor Red
    Write-Host "ERREUR CRITIQUE: `$(`$_.Exception.Message)" -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Red
    Write-Host `$_.Exception.StackTrace -ForegroundColor Gray
    exit 1
} finally {
    Stop-Transcript
}
"@

$wrapperContent | Out-File -FilePath $WRAPPER_SCRIPT -Encoding UTF8 -Force
Write-Host "`nScript wrapper cree: $WRAPPER_SCRIPT" -ForegroundColor Green

# Creer la tache planifiee (SANS ADMIN)
Write-Host "`nCreation de la tache planifiee..." -ForegroundColor Yellow

try {
    $action = New-ScheduledTaskAction `
        -Execute "PowerShell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$WRAPPER_SCRIPT`""

    $trigger = New-ScheduledTaskTrigger -Daily -At $EXECUTION_TIME

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Hours 2)

    # IMPORTANT: Utiliser l'utilisateur actuel SANS elevation
    $principal = New-ScheduledTaskPrincipal `
        -UserId "$env:USERDOMAIN\$env:USERNAME" `
        -LogonType Interactive

    Register-ScheduledTask `
        -TaskName $TASK_NAME `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "Pipeline automatique de procurement - Execute a $EXECUTION_TIME quotidiennement" `
        -Force

    Write-Host "Tache planifiee creee avec succes!" -ForegroundColor Green

} catch {
    Write-Host "`nERREUR lors de la creation de la tache:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Yellow
    
    if ($_.Exception.Message -match "Access is denied") {
        Write-Host "`nSOLUTION: Relancez PowerShell en tant qu'administrateur:" -ForegroundColor Yellow
        Write-Host "  1. Clic droit sur PowerShell" -ForegroundColor Gray
        Write-Host "  2. Executer en tant qu'administrateur" -ForegroundColor Gray
        Write-Host "  3. Relancer: .\setup_scheduled_task.ps1" -ForegroundColor Gray
    }
    exit 1
}

# Afficher les informations
Write-Host "`n============================================" -ForegroundColor Green
Write-Host "CONFIGURATION TERMINEE" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

Write-Host "`nTache planifiee:" -ForegroundColor Yellow
Write-Host "  Nom: $TASK_NAME" -ForegroundColor Gray
Write-Host "  Heure: $EXECUTION_TIME (chaque jour)" -ForegroundColor Gray
Write-Host "  Utilisateur: $env:USERNAME" -ForegroundColor Gray
Write-Host "  Script: $SCRIPT_PATH" -ForegroundColor Gray
Write-Host "  Logs: $LOG_DIR" -ForegroundColor Gray

Write-Host "`nCommandes utiles:" -ForegroundColor Yellow
Write-Host "  Gestion: .\manage_scheduled_task.ps1 status" -ForegroundColor Cyan
Write-Host "  Test: .\manage_scheduled_task.ps1 test" -ForegroundColor Cyan
Write-Host "  Logs: .\manage_scheduled_task.ps1 logs" -ForegroundColor Cyan

Write-Host "`nIMPORTANT:" -ForegroundColor Yellow
Write-Host "  - Docker doit etre demarre avant 22h" -ForegroundColor Gray
Write-Host "  - L'ordinateur doit etre allume a 22h" -ForegroundColor Gray
Write-Host "  - Les logs sont dans: $LOG_DIR" -ForegroundColor Gray

Write-Host "`nTest immediat:" -ForegroundColor Yellow
Write-Host "  .\manage_scheduled_task.ps1 start" -ForegroundColor Cyan