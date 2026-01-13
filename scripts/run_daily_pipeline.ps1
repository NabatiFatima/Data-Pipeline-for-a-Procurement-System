# ============================================
# Script orchestration quotidien - PowerShell
# Pipeline de Procurement - Version finale
# ============================================

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['*:Encoding'] = 'utf8'

$ErrorActionPreference = "Stop"

$DATE = Get-Date -Format "yyyy-MM-dd"
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "PROCUREMENT PIPELINE - $DATE" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

try {
    # ------------------------------------------------
    # 0) Verification Docker
    # ------------------------------------------------
    Write-Host "`nVerification de Docker..." -ForegroundColor Yellow
    $dockerTest = docker ps 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker n'est pas demarre!"
    }
    Write-Host "OK - Docker operationnel" -ForegroundColor Green

    # ------------------------------------------------
    # 1) Verification des dependances Python
    # ------------------------------------------------
    Write-Host "`nVerification des dependances Python..." -ForegroundColor Yellow
    
    $pythonPackages = @{
        "pandas" = "pandas"
        "pyarrow" = "pyarrow"
        "psycopg2" = "psycopg2-binary"
    }
    
    foreach ($pkg in $pythonPackages.GetEnumerator()) {
        Write-Host "-> Verification $($pkg.Key)..." -NoNewline -ForegroundColor Gray
        $testCmd = "import $($pkg.Key)"
        python -c $testCmd 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host " OK" -ForegroundColor Green
        } else {
            Write-Host " Installation..." -ForegroundColor Yellow
            pip install $pkg.Value --quiet
            if ($LASTEXITCODE -ne 0) {
                throw "Impossible d'installer $($pkg.Value)"
            }
            Write-Host "   Installe" -ForegroundColor Green
        }
    }

    # ------------------------------------------------
    # 2) Configuration PostgreSQL
    # ------------------------------------------------
    Write-Host "`nConfiguration PostgreSQL..." -ForegroundColor Yellow
    
    # Vue product_suppliers
    Write-Host "-> Creation vue product_suppliers..." -ForegroundColor Gray
    $viewSQL = "CREATE OR REPLACE VIEW product_suppliers AS SELECT sku, supplier_id, moq AS minimum_order_qty, pack_size, true AS is_primary, 50.0 AS cost_per_unit FROM replenishment_rules WHERE effective_to IS NULL OR effective_to > CURRENT_DATE;"
    docker exec postgres psql -U procurement_user -d procurement_db -c $viewSQL | Out-Null
    Write-Host "   Vue creee" -ForegroundColor Green
    
    # Verification donnees
    $productsCount = docker exec postgres psql -U procurement_user -d procurement_db -t -c "SELECT COUNT(*) FROM products;"
    Write-Host "-> Produits: $productsCount" -ForegroundColor Cyan
    
    $rulesCount = docker exec postgres psql -U procurement_user -d procurement_db -t -c "SELECT COUNT(*) FROM replenishment_rules;"
    Write-Host "-> Regles: $rulesCount" -ForegroundColor Cyan

    # ------------------------------------------------
    # 3) Generation des donnees
    # ------------------------------------------------
    Write-Host "`nGeneration des donnees operationnelles..." -ForegroundColor Yellow

    Write-Host "-> Commandes POS..." -ForegroundColor Gray
    python "$PSScriptRoot\generate_daily_orders.py" --today
    if ($LASTEXITCODE -ne 0) { 
        throw "Erreur generation commandes" 
    }
    Write-Host "   OK" -ForegroundColor Green

    Write-Host "-> Stocks entrepots..." -ForegroundColor Gray
    python "$PSScriptRoot\generate_daily_stock.py" --today
    if ($LASTEXITCODE -ne 0) { 
        throw "Erreur generation stocks" 
    }
    Write-Host "   OK" -ForegroundColor Green

    # ------------------------------------------------
    # 4) Verification fichiers generes
    # ------------------------------------------------
    Write-Host "`nVerification des fichiers generes..." -ForegroundColor Yellow

    $ordersPath = "data\raw\orders\$DATE"
    $stockPath = "data\raw\stock\$DATE"

    # Compter les fichiers CSV
    if (Test-Path $ordersPath) {
        $orderFiles = Get-ChildItem "$ordersPath\*.csv" -ErrorAction SilentlyContinue
        if ($orderFiles) {
            Write-Host "-> Orders: $($orderFiles.Count) fichiers CSV" -ForegroundColor Green
            $totalLines = 0
            foreach ($file in $orderFiles) {
                $lines = (Get-Content $file.FullName).Count - 1
                $totalLines += $lines
            }
            Write-Host "   Total: $totalLines lignes" -ForegroundColor Cyan
        } else {
            throw "Aucun fichier CSV dans $ordersPath"
        }
    } else {
        throw "Dossier $ordersPath inexistant"
    }

    if (Test-Path $stockPath) {
        $stockFiles = Get-ChildItem "$stockPath\*.csv" -ErrorAction SilentlyContinue
        if ($stockFiles) {
            Write-Host "-> Stock: $($stockFiles.Count) fichiers CSV" -ForegroundColor Green
            $totalLines = 0
            foreach ($file in $stockFiles) {
                $lines = (Get-Content $file.FullName).Count - 1
                $totalLines += $lines
            }
            Write-Host "   Total: $totalLines lignes" -ForegroundColor Cyan
        } else {
            throw "Aucun fichier CSV dans $stockPath"
        }
    } else {
        throw "Dossier $stockPath inexistant"
    }

    # ------------------------------------------------
    # 5) Execution du pipeline principal
    # ------------------------------------------------
    Write-Host "`nExecution du pipeline de traitement..." -ForegroundColor Yellow
    python "$PSScriptRoot\procurement_pipeline.py"
    if ($LASTEXITCODE -ne 0) { 
        throw "Erreur pipeline principal" 
    }

    # ------------------------------------------------
    # 6) Verifications finales
    # ------------------------------------------------
    Write-Host "`nVerifications finales..." -ForegroundColor Yellow

    # Stats PostgreSQL
    Write-Host "-> Base PostgreSQL:" -ForegroundColor Gray
    $productsCount = docker exec postgres psql -U procurement_user -d procurement_db -t -c "SELECT COUNT(*) FROM products;"
    Write-Host "   Produits: $productsCount" -ForegroundColor Cyan
    
    $suppliersCount = docker exec postgres psql -U procurement_user -d procurement_db -t -c "SELECT COUNT(*) FROM suppliers WHERE is_active = true;"
    Write-Host "   Fournisseurs actifs: $suppliersCount" -ForegroundColor Cyan
    
    $safetyStockCount = docker exec postgres psql -U procurement_user -d procurement_db -t -c "SELECT COUNT(*) FROM safety_stock;"
    Write-Host "   Safety stocks: $safetyStockCount" -ForegroundColor Cyan

    # Fichiers generes
    Write-Host "-> Fichiers de sortie:" -ForegroundColor Gray
    $outputPath = "data\output\supplier_orders\$DATE"
    if (Test-Path $outputPath) {
        $outputFiles = Get-ChildItem -Path $outputPath -ErrorAction SilentlyContinue
        if ($outputFiles) {
            Write-Host "   $($outputFiles.Count) fichiers generes" -ForegroundColor Green
            foreach ($file in $outputFiles) {
                $sizeKB = [math]::Round($file.Length / 1KB, 2)
                Write-Host "   - $($file.Name) ($sizeKB Ko)" -ForegroundColor Cyan
            }
        } else {
            Write-Host "   0 fichiers (dossier vide)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   Dossier de sortie non cree" -ForegroundColor Yellow
    }

    Write-Host "`n================================================" -ForegroundColor Green
    Write-Host "PIPELINE TERMINE AVEC SUCCES" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green

} catch {
    Write-Host "`n================================================" -ForegroundColor Red
    Write-Host "ERREUR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "================================================" -ForegroundColor Red
    Write-Host "`nDetails:" -ForegroundColor Yellow
    Write-Host $_.Exception -ForegroundColor Gray
    exit 1
}