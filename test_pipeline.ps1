# ============================================
# TEST COMPLET DU PIPELINE
# Verifie chaque composant du systeme
# ============================================

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "TEST COMPLET DU PIPELINE PROCUREMENT" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

$testsPassed = 0
$testsFailed = 0

function Test-Component {
    param(
        [string]$Name,
        [scriptblock]$Test
    )
    
    Write-Host "`n[$Name]" -ForegroundColor Yellow
    try {
        & $Test
        Write-Host "  PASS" -ForegroundColor Green
        $script:testsPassed++
    } catch {
        Write-Host "  FAIL: $($_.Exception.Message)" -ForegroundColor Red
        $script:testsFailed++
    }
}

# TEST 1: Docker containers
Test-Component "Docker - Containers actifs" {
    $containers = docker ps --format "{{.Names}}"
    if ($containers -notcontains "namenode") { throw "namenode non actif" }
    if ($containers -notcontains "trino") { throw "trino non actif" }
    if ($containers -notcontains "postgres") { throw "postgres non actif" }
    Write-Host "  -> namenode, trino, postgres: actifs" -ForegroundColor Gray
}

# TEST 2: PostgreSQL
Test-Component "PostgreSQL - Tables et donnees" {
    $productsCount = docker exec postgres psql -U procurement_user -d procurement_db -t -c "SELECT COUNT(*) FROM products;" 2>$null
    if ([int]$productsCount -lt 100) { throw "Moins de 100 produits" }
    Write-Host "  -> $productsCount produits" -ForegroundColor Gray
    
    $suppliersCount = docker exec postgres psql -U procurement_user -d procurement_db -t -c "SELECT COUNT(*) FROM suppliers;" 2>$null
    if ([int]$suppliersCount -lt 1) { throw "Aucun fournisseur" }
    Write-Host "  -> $suppliersCount fournisseurs" -ForegroundColor Gray
    
    $rulesCount = docker exec postgres psql -U procurement_user -d procurement_db -t -c "SELECT COUNT(*) FROM replenishment_rules;" 2>$null
    if ([int]$rulesCount -lt 100) { throw "Moins de 100 regles d'appro" }
    Write-Host "  -> $rulesCount regles d'approvisionnement" -ForegroundColor Gray
}

# TEST 3: Vue product_suppliers
Test-Component "PostgreSQL - Vue product_suppliers" {
    $viewExists = docker exec postgres psql -U procurement_user -d procurement_db -t -c "SELECT COUNT(*) FROM information_schema.views WHERE table_name = 'product_suppliers';" 2>$null
    if ([int]$viewExists -eq 0) { throw "Vue product_suppliers n'existe pas" }
    
    $viewCount = docker exec postgres psql -U procurement_user -d procurement_db -t -c "SELECT COUNT(*) FROM product_suppliers;" 2>$null
    if ([int]$viewCount -lt 100) { throw "Vue product_suppliers vide" }
    Write-Host "  -> Vue existe avec $viewCount lignes" -ForegroundColor Gray
}

# TEST 4: Trino - Connexion
Test-Component "Trino - Connexion et catalogues" {
    $catalogs = docker exec trino trino --execute "SHOW CATALOGS;" 2>$null
    if ($catalogs -notmatch "hive") { throw "Catalogue hive manquant" }
    if ($catalogs -notmatch "postgresql") { throw "Catalogue postgresql manquant" }
    Write-Host "  -> Catalogues hive et postgresql presents" -ForegroundColor Gray
}

# TEST 5: Trino - Tables
Test-Component "Trino - Tables Hive" {
    $tables = docker exec trino trino --execute "SHOW TABLES IN hive.orders;" 2>$null
    if ($tables -notmatch "daily_orders") { throw "Table daily_orders manquante" }
    Write-Host "  -> Table hive.orders.daily_orders existe" -ForegroundColor Gray
    
    $tables = docker exec trino trino --execute "SHOW TABLES IN hive.stock;" 2>$null
    if ($tables -notmatch "daily_stock") { throw "Table daily_stock manquante" }
    Write-Host "  -> Table hive.stock.daily_stock existe" -ForegroundColor Gray
}

# TEST 6: Structure des dossiers
Test-Component "Systeme de fichiers - Structure" {
    $folders = @(
        "data/raw/orders",
        "data/raw/stock",
        "data/parquet/orders",
        "data/parquet/stock",
        "data/output/supplier_orders",
        "scripts"
    )
    
    foreach ($folder in $folders) {
        if (!(Test-Path $folder)) { throw "Dossier manquant: $folder" }
    }
    Write-Host "  -> Tous les dossiers existent" -ForegroundColor Gray
}

# TEST 7: Scripts Python
Test-Component "Scripts Python - Presence" {
    $scripts = @(
        "scripts/generate_daily_orders.py",
        "scripts/generate_daily_stock.py",
        "scripts/convert_to_parquet.py",
        "scripts/procurement_pipeline_parquet.py"
    )
    
    foreach ($script in $scripts) {
        if (!(Test-Path $script)) { throw "Script manquant: $script" }
    }
    Write-Host "  -> Tous les scripts presents" -ForegroundColor Gray
}

# TEST 8: Dependances Python
Test-Component "Python - Dependances" {
    $packages = @("pandas", "pyarrow", "trino", "psycopg2")
    foreach ($pkg in $packages) {
        $module = $pkg.Replace("-", "_")
        python -c "import $module" 2>$null
        if ($LASTEXITCODE -ne 0) { throw "Package Python manquant: $pkg" }
    }
    Write-Host "  -> pandas, pyarrow, trino, psycopg2 installes" -ForegroundColor Gray
}

# TEST 9: HDFS
Test-Component "HDFS - Accessibilite" {
    $result = docker exec namenode hdfs dfs -ls / 2>&1
    if ($LASTEXITCODE -ne 0) { throw "HDFS non accessible" }
    Write-Host "  -> HDFS accessible" -ForegroundColor Gray
}

# TEST 10: Generation de donnees test
Test-Component "Generation - Donnees de test" {
    $today = Get-Date -Format "yyyy-MM-dd"
    
    # Nettoyer les anciennes donnees du jour
    if (Test-Path "data/raw/orders/$today") {
        Remove-Item -Path "data/raw/orders/$today" -Recurse -Force
    }
    if (Test-Path "data/raw/stock/$today") {
        Remove-Item -Path "data/raw/stock/$today" -Recurse -Force
    }
    
    # Generer
    python scripts/generate_daily_orders.py --today 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Erreur generation commandes" }
    
    python scripts/generate_daily_stock.py --today 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Erreur generation stocks" }
    
    # Verifier
    if (!(Test-Path "data/raw/orders/$today")) { throw "Dossier commandes non cree" }
    if (!(Test-Path "data/raw/stock/$today")) { throw "Dossier stocks non cree" }
    
    $orderFiles = Get-ChildItem "data/raw/orders/$today/*.json"
    if ($orderFiles.Count -lt 5) { throw "Moins de 5 fichiers de commandes" }
    Write-Host "  -> $($orderFiles.Count) fichiers de commandes generes" -ForegroundColor Gray
    
    $stockFiles = Get-ChildItem "data/raw/stock/$today/*.json"
    if ($stockFiles.Count -lt 3) { throw "Moins de 3 fichiers de stocks" }
    Write-Host "  -> $($stockFiles.Count) fichiers de stocks generes" -ForegroundColor Gray
}

# Resume
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "RESUME DES TESTS" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Tests reussis : $testsPassed" -ForegroundColor Green
Write-Host "Tests echoues : $testsFailed" -ForegroundColor $(if ($testsFailed -gt 0) { "Red" } else { "Gray" })

if ($testsFailed -eq 0) {
    Write-Host "`nTOUS LES TESTS PASSES!" -ForegroundColor Green
    Write-Host "Vous pouvez executer le pipeline:" -ForegroundColor Yellow
    Write-Host "  python scripts\procurement_pipeline_parquet.py" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "`nCERTAINS TESTS ONT ECHOUE" -ForegroundColor Red
    Write-Host "Veuillez corriger les erreurs avant d'executer le pipeline" -ForegroundColor Yellow
    exit 1
}