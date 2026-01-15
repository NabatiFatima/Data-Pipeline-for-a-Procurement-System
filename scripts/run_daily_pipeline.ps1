# ============================================
# Pipeline quotidien - Appelle pipeline.py
# ============================================

$ErrorActionPreference = "Continue"
# CORRECTION: $PSScriptRoot pointe vers scripts/, on remonte d'un niveau
$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot
$TIMESTAMP = Get-Date -Format "yyyy-MM-dd"
$LOG_FILE = Join-Path $PROJECT_ROOT "data\logs\scheduled\pipeline_$TIMESTAMP.log"

# Creer le dossier de logs
$logDir = Split-Path -Parent $LOG_FILE
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

Start-Transcript -Path $LOG_FILE -Append

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "PROCUREMENT PIPELINE - $TIMESTAMP" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

$globalSuccess = $true

try {
    # ===== 1. DOCKER =====
    Write-Host "`n[1/5] Verification Docker..." -ForegroundColor Yellow
    
    $dockerTest = docker ps 2>&1 | Out-String
    if ($dockerTest -match "CONTAINER ID") {
        Write-Host "  OK Docker operationnel" -ForegroundColor Green
    } else {
        Write-Host "  ERREUR Docker non disponible" -ForegroundColor Red
        throw "Docker n est pas demarre"
    }

    # Vérifier les containers nécessaires
    $containers = @('postgres-procurement', 'namenode', 'trino')
    foreach ($container in $containers) {
        $running = docker ps --filter "name=$container" --format "{{.Names}}" 2>&1
        if ($running -match $container) {
            Write-Host "  OK Container $container actif" -ForegroundColor Green
        } else {
            Write-Host "  ATTENTION Container $container non trouve" -ForegroundColor Yellow
        }
    }

    # ===== 2. PYTHON =====
    Write-Host "`n[2/5] Verification Python..." -ForegroundColor Yellow
    
    $pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "python3" }
    $pythonVersion = & $pythonCmd --version 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK $pythonVersion" -ForegroundColor Green
    } else {
        throw "Python non disponible"
    }

    # ===== 3. GENERATION DONNEES JSON =====
    Write-Host "`n[3/5] Generation des donnees JSON..." -ForegroundColor Yellow
    
    # Chercher les scripts
    $ordersScript = Join-Path $PROJECT_ROOT "scripts\generate_daily_orders.py"
    $stockScript = Join-Path $PROJECT_ROOT "scripts\generate_daily_stock.py"
    
    if (-not (Test-Path $ordersScript)) {
        throw "Script orders introuvable: $ordersScript"
    }
    
    if (-not (Test-Path $stockScript)) {
        throw "Script stock introuvable: $stockScript"
    }
    
    # Générer commandes
    Write-Host "  Generation commandes POS..." -ForegroundColor Cyan
    & $pythonCmd $ordersScript --date $TIMESTAMP 2>&1 | ForEach-Object {
        if ($_ -match "Total:|Fichiers") {
            Write-Host "    $_" -ForegroundColor Gray
        }
    }
    
    if ($LASTEXITCODE -ne 0) {
        throw "Erreur generation commandes"
    }
    
    # Générer stocks
    Write-Host "  Generation stocks..." -ForegroundColor Cyan
    & $pythonCmd $stockScript --date $TIMESTAMP 2>&1 | ForEach-Object {
        if ($_ -match "Total:|Fichier") {
            Write-Host "    $_" -ForegroundColor Gray
        }
    }
    
    if ($LASTEXITCODE -ne 0) {
        throw "Erreur generation stocks"
    }
    
    # Vérifier les fichiers JSON
    $ordersPath = Join-Path $PROJECT_ROOT "data\raw\orders\$TIMESTAMP"
    $stockPath = Join-Path $PROJECT_ROOT "data\raw\stock\$TIMESTAMP"
    
    if (Test-Path $ordersPath) {
        $jsonFiles = @(Get-ChildItem $ordersPath -Filter "*.json")
        Write-Host "  OK Orders: $($jsonFiles.Count) fichiers JSON" -ForegroundColor Green
    } else {
        throw "Dossier orders non cree"
    }
    
    if (Test-Path $stockPath) {
        $jsonFiles = @(Get-ChildItem $stockPath -Filter "*.json")
        Write-Host "  OK Stock: $($jsonFiles.Count) fichiers JSON" -ForegroundColor Green
    } else {
        throw "Dossier stock non cree"
    }

    # ===== 4. EXECUTION PROCUREMENT_PIPELINE.PY =====
    Write-Host "`n[4/5] Execution du pipeline principal..." -ForegroundColor Yellow
    
    $pipelineScript = Join-Path $PROJECT_ROOT "scripts\procurement_pipeline.py"
    
    if (-not (Test-Path $pipelineScript)) {
        Write-Host "  ATTENTION procurement_pipeline.py non trouve" -ForegroundColor Yellow
        Write-Host "  Chemin recherche: $pipelineScript" -ForegroundColor Gray
        Write-Host "  Les donnees JSON sont generees mais le traitement complet n est pas execute" -ForegroundColor Yellow
    } else {
        Write-Host "  Lancement procurement_pipeline.py..." -ForegroundColor Cyan
        
        # Exécuter procurement_pipeline.py avec la date
        & $pythonCmd $pipelineScript --date $TIMESTAMP 2>&1 | ForEach-Object {
            Write-Host "  $_"
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  OK Pipeline execute avec succes" -ForegroundColor Green
        } else {
            Write-Host "  ERREUR Pipeline echoue (code: $LASTEXITCODE)" -ForegroundColor Red
            throw "procurement_pipeline.py a echoue"
        }
    }

    # ===== 5. VERIFICATION RESULTATS =====
    Write-Host "`n[5/5] Verification des resultats..." -ForegroundColor Yellow
    
    # Vérifier les commandes fournisseurs générées
    $supplierOrdersPath = Join-Path $PROJECT_ROOT "data\output\supplier_orders\$TIMESTAMP"
    
    if (Test-Path $supplierOrdersPath) {
        $supplierFiles = @(Get-ChildItem $supplierOrdersPath -Filter "*.json")
        if ($supplierFiles.Count -gt 0) {
            Write-Host "  OK Commandes fournisseurs: $($supplierFiles.Count) fichiers" -ForegroundColor Green
            
            # Afficher un résumé
            $totalOrders = 0
            foreach ($file in $supplierFiles) {
                try {
                    $content = Get-Content $file.FullName -Raw | ConvertFrom-Json
                    if ($content.order_header) {
                        $totalOrders += $content.order_header.total_units
                    }
                } catch {
                    # Ignorer les erreurs de lecture
                }
            }
            if ($totalOrders -gt 0) {
                Write-Host "  Total unites commandees: $totalOrders" -ForegroundColor Cyan
            }
        } else {
            Write-Host "  INFO Aucune commande fournisseur generee" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  INFO Dossier commandes fournisseurs non cree" -ForegroundColor Yellow
    }

    # ===== SUCCES =====
    Write-Host "`n================================================" -ForegroundColor Green
    Write-Host "SUCCESS - PIPELINE TERMINE" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "Date:      $TIMESTAMP" -ForegroundColor Cyan
    Write-Host "Orders:    $ordersPath" -ForegroundColor Cyan
    Write-Host "Stock:     $stockPath" -ForegroundColor Cyan
    Write-Host "Log:       $LOG_FILE" -ForegroundColor Cyan
    Write-Host "================================================" -ForegroundColor Green

} catch {
    $globalSuccess = $false
    
    Write-Host "`n================================================" -ForegroundColor Red
    Write-Host "ERREUR - PIPELINE ECHOUE" -ForegroundColor Red
    Write-Host "================================================" -ForegroundColor Red
    Write-Host "Message: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "Ligne:   $($_.InvocationInfo.ScriptLineNumber)" -ForegroundColor Yellow
    Write-Host "Log:     $LOG_FILE" -ForegroundColor Cyan
    Write-Host "================================================" -ForegroundColor Red
}

Stop-Transcript

if ($globalSuccess) {
    exit 0
} else {
    exit 1
}