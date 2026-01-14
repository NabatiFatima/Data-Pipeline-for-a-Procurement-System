# ============================================
# Pipeline quotidien - VERSION FINALE
# ============================================

$ErrorActionPreference = "Continue"
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
    Write-Host "`n[1/6] Verification Docker..." -ForegroundColor Yellow
    
    $dockerTest = docker ps 2>&1 | Out-String
    if ($dockerTest -match "CONTAINER ID") {
        Write-Host "  OK Docker operationnel" -ForegroundColor Green
    } else {
        Write-Host "  ERREUR Docker non disponible" -ForegroundColor Red
        throw "Docker n est pas demarre"
    }

    # ===== 2. PYTHON =====
    Write-Host "`n[2/6] Verification Python..." -ForegroundColor Yellow
    
    $pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "python3" }
    $pythonVersion = & $pythonCmd --version 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK $pythonVersion" -ForegroundColor Green
    } else {
        throw "Python non disponible"
    }

    # ===== 3. POSTGRESQL =====
    Write-Host "`n[3/6] Configuration PostgreSQL..." -ForegroundColor Yellow
    
    $env:PGPASSWORD = "postgres"
    
    $pgTest = docker exec postgres-procurement psql -U postgres -d procurement -c "\dt" 2>&1 | Out-String
    
    if ($pgTest -match "products" -or $pgTest -match "table") {
        Write-Host "  OK Base de donnees accessible" -ForegroundColor Green
    } else {
        Write-Host "  ATTENTION Base de donnees peut-etre vide" -ForegroundColor Yellow
    }
    
    # Creer la vue
    $createViewSQL = @"
DROP VIEW IF EXISTS product_suppliers;
CREATE VIEW product_suppliers AS
SELECT 
    ps.product_id,
    ps.supplier_id,
    ps.lead_time_days,
    ps.min_order_qty,
    ps.price_per_unit,
    ps.is_preferred,
    ps.last_delivery_date,
    ps.reliability_score,
    p.name as product_name,
    p.category,
    p.unit_price,
    s.name as supplier_name,
    s.country,
    s.rating
FROM product_supplier ps
JOIN products p ON ps.product_id = p.product_id
JOIN suppliers s ON ps.supplier_id = s.supplier_id
WHERE ps.is_active = true;
"@

    $viewResult = $createViewSQL | docker exec -i postgres-procurement psql -U postgres -d procurement 2>&1 | Out-String
    
    if ($viewResult -match "CREATE VIEW" -or $viewResult -match "DROP VIEW") {
        Write-Host "  OK Vue product_suppliers prete" -ForegroundColor Green
    }

    # ===== 4. GENERATION COMMANDES POS =====
    Write-Host "`n[4/6] Generation commandes POS..." -ForegroundColor Yellow
    
    # Chercher le script existant
    $ordersScript = Join-Path $PROJECT_ROOT "scripts\generate_daily_orders.py"
    if (-not (Test-Path $ordersScript)) {
        $ordersScript = Join-Path $PROJECT_ROOT "scripts\generate_pos_orders.py"
    }
    
    if (-not (Test-Path $ordersScript)) {
        throw "Script orders introuvable"
    }
    
    Write-Host "  Script: $ordersScript" -ForegroundColor Gray
    
    & $pythonCmd $ordersScript --date $TIMESTAMP 2>&1 | ForEach-Object {
        Write-Host "  $_" -ForegroundColor Gray
    }
    
    if ($LASTEXITCODE -ne 0) {
        throw "Erreur generation commandes POS"
    }
    
    # Verifier les fichiers
    $ordersPath = Join-Path $PROJECT_ROOT "data\raw\orders\$TIMESTAMP"
    if (Test-Path $ordersPath) {
        $orderFiles = @(Get-ChildItem $ordersPath -Filter "*.csv")
        if ($orderFiles.Count -gt 0) {
            $totalLines = 0
            foreach ($file in $orderFiles) {
                $lines = (Get-Content $file.FullName | Measure-Object -Line).Lines - 1
                $totalLines += $lines
            }
            Write-Host "  OK $($orderFiles.Count) fichiers, $totalLines commandes" -ForegroundColor Green
        } else {
            throw "Aucun fichier CSV genere"
        }
    } else {
        throw "Dossier orders non cree"
    }

    # ===== 5. GENERATION STOCKS =====
    Write-Host "`n[5/6] Generation stocks entrepots..." -ForegroundColor Yellow
    
    # Chercher le script existant
    $stockScript = Join-Path $PROJECT_ROOT "scripts\generate_daily_stock.py"
    if (-not (Test-Path $stockScript)) {
        $stockScript = Join-Path $PROJECT_ROOT "scripts\generate_warehouse_stock.py"
    }
    
    if (-not (Test-Path $stockScript)) {
        throw "Script stock introuvable"
    }
    
    Write-Host "  Script: $stockScript" -ForegroundColor Gray
    
    & $pythonCmd $stockScript --date $TIMESTAMP 2>&1 | ForEach-Object {
        Write-Host "  $_" -ForegroundColor Gray
    }
    
    if ($LASTEXITCODE -ne 0) {
        throw "Erreur generation stocks"
    }
    
    # Verifier les fichiers
    $stockPath = Join-Path $PROJECT_ROOT "data\raw\stock\$TIMESTAMP"
    if (Test-Path $stockPath) {
        $stockFiles = @(Get-ChildItem $stockPath -Filter "*.csv")
        if ($stockFiles.Count -gt 0) {
            $totalLines = 0
            foreach ($file in $stockFiles) {
                $lines = (Get-Content $file.FullName | Measure-Object -Line).Lines - 1
                $totalLines += $lines
            }
            Write-Host "  OK $($stockFiles.Count) fichiers, $totalLines lignes" -ForegroundColor Green
        } else {
            throw "Aucun fichier CSV genere"
        }
    } else {
        throw "Dossier stock non cree"
    }

    # ===== 6. AIRFLOW (optionnel) =====
    Write-Host "`n[6/6] Declenchement Airflow..." -ForegroundColor Yellow
    
    try {
        $airflowAPI = "http://localhost:8080/api/v1/dags/procurement_pipeline/dagRuns"
        $body = @{
            conf = @{ date = $TIMESTAMP }
        } | ConvertTo-Json
        
        $headers = @{
            Authorization = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("airflow:airflow"))
        }
        
        $response = Invoke-RestMethod -Uri $airflowAPI -Method Post -Body $body -ContentType "application/json" -Headers $headers -TimeoutSec 5
        Write-Host "  OK DAG declenche: $($response.dag_run_id)" -ForegroundColor Green
    } catch {
        Write-Host "  INFO Airflow non disponible (ignore)" -ForegroundColor Yellow
    }

    # ===== GENERATION COMMANDES FOURNISSEURS =====
    Write-Host "`n[7/7] Generation commandes fournisseurs..." -ForegroundColor Yellow
    
    $supplierScript = Join-Path $PROJECT_ROOT "scripts\generate_supplier_orders.py"
    
    if (Test-Path $supplierScript) {
        & $pythonCmd $supplierScript --date $TIMESTAMP 2>&1 | ForEach-Object {
            Write-Host "  $_" -ForegroundColor Gray
        }
        
        if ($LASTEXITCODE -eq 0) {
            $supplierOrdersPath = Join-Path $PROJECT_ROOT "data\processed\supplier_orders\$TIMESTAMP"
            if (Test-Path $supplierOrdersPath) {
                $supplierFiles = @(Get-ChildItem $supplierOrdersPath -Filter "*.json" -ErrorAction SilentlyContinue)
                Write-Host "  OK $($supplierFiles.Count) commandes fournisseurs" -ForegroundColor Green
            }
        }
    } else {
        Write-Host "  INFO Script supplier_orders non trouve (ignore)" -ForegroundColor Yellow
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