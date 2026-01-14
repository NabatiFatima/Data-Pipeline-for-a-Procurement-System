# ============================================
# Script de gestion de la tache planifiee
# ============================================

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('status', 'start', 'stop', 'enable', 'disable', 'logs', 'delete', 'test')]
    [string]$Action
)

$TASK_NAME = "ProcurementPipeline_Daily"
# Le script est dans procurement-project/, donc PSScriptRoot EST le PROJECT_ROOT
$PROJECT_ROOT = $PSScriptRoot
$LOG_DIR = Join-Path $PROJECT_ROOT "data\logs\scheduled"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "GESTION PIPELINE AUTOMATIQUE" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

switch ($Action) {
    'status' {
        Write-Host "`nStatut de la tache:" -ForegroundColor Yellow
        $task = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
        
        if ($task) {
            Write-Host "  Nom: $($task.TaskName)" -ForegroundColor Green
            Write-Host "  Etat: $($task.State)" -ForegroundColor $(if ($task.State -eq 'Ready') { 'Green' } else { 'Yellow' })
            
            $taskInfo = Get-ScheduledTaskInfo -TaskName $TASK_NAME
            Write-Host "  Prochaine execution: $($taskInfo.NextRunTime)" -ForegroundColor Cyan
            Write-Host "  Derniere execution: $($taskInfo.LastRunTime)" -ForegroundColor Gray
            Write-Host "  Dernier resultat: $($taskInfo.LastTaskResult)" -ForegroundColor Gray
            
            $trigger = $task.Triggers[0]
            Write-Host "`n  Configuration:" -ForegroundColor Yellow
            
            # Correction pour l'affichage de l'heure
            if ($trigger.StartBoundary) {
                try {
                    $startTime = [DateTime]::Parse($trigger.StartBoundary)
                    Write-Host "    Heure: $($startTime.ToString('HH:mm'))" -ForegroundColor Gray
                } catch {
                    Write-Host "    Heure: $($trigger.StartBoundary)" -ForegroundColor Gray
                }
            }
            Write-Host "    Frequence: Quotidien" -ForegroundColor Gray
        } else {
            Write-Host "  Tache non trouvee!" -ForegroundColor Red
            Write-Host "  Lancez: .\setup_scheduled_task.ps1" -ForegroundColor Yellow
        }
    }
    
    'start' {
        Write-Host "`nDemarrage immediat de la tache..." -ForegroundColor Yellow
        Start-ScheduledTask -TaskName $TASK_NAME
        Write-Host "Tache demarree! Verifiez les logs dans quelques secondes." -ForegroundColor Green
        Write-Host "Logs: $LOG_DIR" -ForegroundColor Cyan
        
        # Attendre un peu et afficher les premiers logs
        Write-Host "`nAttente de 3 secondes..." -ForegroundColor Gray
        Start-Sleep -Seconds 3
        
        $latestLog = Get-ChildItem $LOG_DIR -Filter "pipeline_*.log" -ErrorAction SilentlyContinue | 
                     Sort-Object LastWriteTime -Descending | 
                     Select-Object -First 1
        
        if ($latestLog) {
            Write-Host "`nDerniers logs:" -ForegroundColor Yellow
            Get-Content $latestLog.FullName -Tail 20
        }
    }
    
    'stop' {
        Write-Host "`nArret de la tache..." -ForegroundColor Yellow
        Stop-ScheduledTask -TaskName $TASK_NAME
        Write-Host "Tache arretee" -ForegroundColor Green
    }
    
    'enable' {
        Write-Host "`nActivation de la tache..." -ForegroundColor Yellow
        Enable-ScheduledTask -TaskName $TASK_NAME | Out-Null
        Write-Host "Tache activee - s'executera a 22h00" -ForegroundColor Green
    }
    
    'disable' {
        Write-Host "`nDesactivation de la tache..." -ForegroundColor Yellow
        Disable-ScheduledTask -TaskName $TASK_NAME | Out-Null
        Write-Host "Tache desactivee - ne s'executera plus automatiquement" -ForegroundColor Yellow
    }
    
    'logs' {
        Write-Host "`nDerniers logs:" -ForegroundColor Yellow
        if (Test-Path $LOG_DIR) {
            $logs = Get-ChildItem $LOG_DIR -Filter "pipeline_*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 5
            
            if ($logs) {
                foreach ($log in $logs) {
                    $size = [math]::Round($log.Length / 1KB, 2)
                    Write-Host "  $($log.Name) - $size KB - $($log.LastWriteTime)" -ForegroundColor Cyan
                }
                
                Write-Host "`nAfficher le dernier log?" -ForegroundColor Yellow
                $response = Read-Host "  (O/N)"
                if ($response -eq 'O' -or $response -eq 'o') {
                    Get-Content $logs[0].FullName -Tail 50
                }
            } else {
                Write-Host "  Aucun log trouve" -ForegroundColor Gray
            }
        } else {
            Write-Host "  Dossier logs inexistant: $LOG_DIR" -ForegroundColor Red
        }
    }
    
    'delete' {
        Write-Host "`nSuppression de la tache planifiee..." -ForegroundColor Yellow
        Write-Host "ATTENTION: Cette action est irreversible!" -ForegroundColor Red
        $confirmation = Read-Host "  Confirmer la suppression? (tapez 'OUI' pour confirmer)"
        
        if ($confirmation -eq 'OUI') {
            Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false
            Write-Host "Tache supprimee" -ForegroundColor Green
            Write-Host "Pour recreer: .\setup_scheduled_task.ps1" -ForegroundColor Yellow
        } else {
            Write-Host "Suppression annulee" -ForegroundColor Yellow
        }
    }
    
    'test' {
        Write-Host "`nTest immediat du pipeline..." -ForegroundColor Yellow
        Write-Host "Execution en cours..." -ForegroundColor Gray
        
        # Correction du chemin
        $scriptPath = Join-Path $PROJECT_ROOT "scripts\run_daily_pipeline.ps1"
        
        Write-Host "Chemin du script: $scriptPath" -ForegroundColor Gray
        
        if (Test-Path $scriptPath) {
            try {
                & $scriptPath
                
                if ($LASTEXITCODE -eq 0 -or $null -eq $LASTEXITCODE) {
                    Write-Host "`nTest reussi!" -ForegroundColor Green
                } else {
                    Write-Host "`nTest echoue (code: $LASTEXITCODE)" -ForegroundColor Red
                }
            } catch {
                Write-Host "`nErreur lors de l'execution: $_" -ForegroundColor Red
            }
        } else {
            Write-Host "`nERREUR: Script introuvable!" -ForegroundColor Red
            Write-Host "Chemin recherche: $scriptPath" -ForegroundColor Yellow
            Write-Host "`nVerification de la structure du projet..." -ForegroundColor Yellow
            Write-Host "PROJECT_ROOT: $PROJECT_ROOT" -ForegroundColor Gray
            
            # Chercher le script
            $possiblePaths = @(
                (Join-Path $PROJECT_ROOT "scripts\run_daily_pipeline.ps1"),
                (Join-Path $PSScriptRoot "scripts\run_daily_pipeline.ps1"),
                (Join-Path (Split-Path -Parent $PSScriptRoot) "scripts\run_daily_pipeline.ps1")
            )
            
            Write-Host "`nChemins possibles:" -ForegroundColor Yellow
            foreach ($path in $possiblePaths) {
                $exists = Test-Path $path
                $status = if ($exists) { "EXISTE" } else { "INTROUVABLE" }
                $color = if ($exists) { "Green" } else { "Red" }
                Write-Host "  [$status] $path" -ForegroundColor $color
            }
        }
    }
}

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "Commandes disponibles:" -ForegroundColor Yellow
Write-Host "  .\manage_scheduled_task.ps1 status   - Voir statut" -ForegroundColor Gray
Write-Host "  .\manage_scheduled_task.ps1 start    - Executer maintenant" -ForegroundColor Gray
Write-Host "  .\manage_scheduled_task.ps1 stop     - Arreter execution" -ForegroundColor Gray
Write-Host "  .\manage_scheduled_task.ps1 enable   - Activer" -ForegroundColor Gray
Write-Host "  .\manage_scheduled_task.ps1 disable  - Desactiver" -ForegroundColor Gray
Write-Host "  .\manage_scheduled_task.ps1 logs     - Voir logs" -ForegroundColor Gray
Write-Host "  .\manage_scheduled_task.ps1 test     - Test immediat" -ForegroundColor Gray
Write-Host "  .\manage_scheduled_task.ps1 delete   - Supprimer" -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Cyan