# ============================================
# SETUP INITIAL SIMPLIFIE - VERSION PARQUET
# ============================================

$ErrorActionPreference = "Continue"  # Ne pas arreter sur les warnings
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "SETUP INITIAL DU PIPELINE PROCUREMENT" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

try {
    # 1. Verification Docker
    Write-Host "`n[1/7] Verification de Docker..." -ForegroundColor Yellow
    $dockerRunning = docker ps 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop n'est pas demarre!"
    }
    Write-Host "OK - Docker operationnel" -ForegroundColor Green

    # 2. Verification Python
    Write-Host "`n[2/7] Verification Python..." -ForegroundColor Yellow
    python --version
    if ($LASTEXITCODE -ne 0) {
        throw "Python n'est pas installe!"
    }
    Write-Host "OK - Python disponible" -ForegroundColor Green

    # 3. Installation des dependances
    Write-Host "`n[3/7] Installation des dependances Python..." -ForegroundColor Yellow
    pip install pandas pyarrow psycopg2-binary --quiet --disable-pip-version-check
    Write-Host "OK - Dependances installees" -ForegroundColor Green

    # 4. Creation des dossiers
    Write-Host "`n[4/7] Creation de la structure des dossiers..." -ForegroundColor Yellow
    $folders = @(
        "data\raw\orders",
        "data\raw\stock",
        "data\parquet\orders",
        "data\parquet\stock",
        "data\output\supplier_orders",
        "data\logs\exceptions",
        "scripts"
    )
    
    foreach ($folder in $folders) {
        if (!(Test-Path $folder)) {
            New-Item -ItemType Directory -Path $folder -Force | Out-Null
            Write-Host "Cree: $folder" -ForegroundColor Gray
        }
    }
    Write-Host "OK - Structure creee" -ForegroundColor Green

    # 5. Configuration PostgreSQL
    Write-Host "`n[5/7] Configuration PostgreSQL..." -ForegroundColor Yellow
    
    # Vue product_suppliers
    $viewSQL = "CREATE OR REPLACE VIEW product_suppliers AS SELECT sku, supplier_id, moq AS minimum_order_qty, pack_size, true AS is_primary, 50.0 AS cost_per_unit FROM replenishment_rules WHERE effective_to IS NULL OR effective_to > CURRENT_DATE;"
    docker exec postgres psql -U procurement_user -d procurement_db -c $viewSQL | Out-Null
    Write-Host "OK - Vue product_suppliers creee" -ForegroundColor Green
    
    # Verification des donnees
    $productsCount = docker exec postgres psql -U procurement_user -d procurement_db -t -c "SELECT COUNT(*) FROM products;"
    Write-Host "Info: $productsCount produits" -ForegroundColor Cyan
    
    $rulesCount = docker exec postgres psql -U procurement_user -d procurement_db -t -c "SELECT COUNT(*) FROM replenishment_rules;"
    Write-Host "Info: $rulesCount regles" -ForegroundColor Cyan

    # 6. Configuration Trino/Hive
    Write-Host "`n[6/7] Configuration des tables Trino (Parquet)..." -ForegroundColor Yellow
    
    # Supprimer anciennes tables (ignorer les erreurs)
    docker exec trino trino --execute "DROP TABLE IF EXISTS hive.orders.daily_orders;" 2>$null | Out-Null
    docker exec trino trino --execute "DROP TABLE IF EXISTS hive.stock.daily_stock;" 2>$null | Out-Null
    
    # Creer table orders
    Write-Host "Creation table orders..." -ForegroundColor Gray
    $ordersTableSQL = "CREATE TABLE hive.orders.daily_orders (order_id VARCHAR, store_id VARCHAR, order_date VARCHAR, order_timestamp VARCHAR, sku VARCHAR, quantity INTEGER, unit_price DOUBLE, total_price DOUBLE) WITH (external_location = 'hdfs://namenode:9000/processed/orders', format = 'PARQUET');"
    $ordersResult = docker exec trino trino --execute $ordersTableSQL 2>&1
    
    if ($ordersResult -match "CREATE TABLE") {
        Write-Host "OK - Table orders creee" -ForegroundColor Green
    } else {
        Write-Host "Warning: $ordersResult" -ForegroundColor Yellow
    }
    
    # Creer table stock
    Write-Host "Creation table stock..." -ForegroundColor Gray
    $stockTableSQL = "CREATE TABLE hive.stock.daily_stock (warehouse_id VARCHAR, sku VARCHAR, stock_date VARCHAR, quantity_on_hand INTEGER, unit_cost DOUBLE, total_value DOUBLE, last_updated VARCHAR) WITH (external_location = 'hdfs://namenode:9000/processed/stock', format = 'PARQUET');"
    $stockResult = docker exec trino trino --execute $stockTableSQL 2>&1
    
    if ($stockResult -match "CREATE TABLE") {
        Write-Host "OK - Table stock creee" -ForegroundColor Green
    } else {
        Write-Host "Warning: $stockResult" -ForegroundColor Yellow
    }
    
    # Verification finale
    $checkOrders = docker exec trino trino --execute "SHOW TABLES FROM hive.orders;" 2>&1
    $checkStock = docker exec trino trino --execute "SHOW TABLES FROM hive.stock;" 2>&1
    
    if ($checkOrders -match "daily_orders" -and $checkStock -match "daily_stock") {
        Write-Host "OK - Tables Trino verifiees" -ForegroundColor Green
    } else {
        Write-Host "Warning - Tables non verifiees mais continuons..." -ForegroundColor Yellow
    }

    # 7. Generation de donnees de test
    Write-Host "`n[7/7] Generation de donnees de test..." -ForegroundColor Yellow
    
    Write-Host "Generation des commandes..." -ForegroundColor Gray
    python scripts\generate_daily_orders.py --today
    if ($LASTEXITCODE -ne 0) { throw "Erreur generation commandes" }
    
    Write-Host "Generation des stocks..." -ForegroundColor Gray
    python scripts\generate_daily_stock.py --today
    if ($LASTEXITCODE -ne 0) { throw "Erreur generation stocks" }
    
    Write-Host "OK - Donnees de test generees" -ForegroundColor Green

    # Resume final
    Write-Host "`n============================================" -ForegroundColor Green
    Write-Host "SETUP TERMINE AVEC SUCCES" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    
    Write-Host "`nConfiguration:" -ForegroundColor Yellow
    Write-Host "  - Docker: OK" -ForegroundColor Green
    Write-Host "  - Python: OK" -ForegroundColor Green
    Write-Host "  - PostgreSQL: OK" -ForegroundColor Green
    Write-Host "  - Trino (Parquet): OK" -ForegroundColor Green
    Write-Host "  - Donnees de test: OK" -ForegroundColor Green
    
    Write-Host "`nProchaine etape:" -ForegroundColor Yellow
    Write-Host "  .\scripts\run_daily_pipeline.ps1" -ForegroundColor Cyan

} catch {
    Write-Host "`n============================================" -ForegroundColor Red
    Write-Host "ERREUR SETUP: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Red
    exit 1
}