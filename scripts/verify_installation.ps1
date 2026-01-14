# Script de vérification de l'installation
$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "VERIFICATION INSTALLATION" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

$allOk = $true

# Vérifier la structure
Write-Host "`nStructure des dossiers:" -ForegroundColor Yellow

$requiredDirs = @(
    "scripts",
    "scripts\python",
    "data\raw\orders",
    "data\raw\stock",
    "data\processed\supplier_orders",
    "data\logs\scheduled"
)

foreach ($dir in $requiredDirs) {
    $path = Join-Path $PROJECT_ROOT $dir
    if (Test-Path $path) {
        Write-Host "  [OK] $dir" -ForegroundColor Green
    } else {
        Write-Host "  [MANQUANT] $dir" -ForegroundColor Red
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-Host "       -> Créé" -ForegroundColor Yellow
    }
}

# Vérifier les scripts avec PLUSIEURS NOMS POSSIBLES
Write-Host "`nScripts requis:" -ForegroundColor Yellow

# Script principal PowerShell
$mainScript = Join-Path $PROJECT_ROOT "scripts\run_daily_pipeline.ps1"
if (Test-Path $mainScript) {
    $size = [math]::Round((Get-Item $mainScript).Length / 1KB, 2)
    Write-Host "  [OK] run_daily_pipeline.ps1 ($size KB)" -ForegroundColor Green
} else {
    Write-Host "  [MANQUANT] run_daily_pipeline.ps1" -ForegroundColor Red
    $allOk = $false
}

# Script génération commandes (plusieurs noms possibles)
$ordersScripts = @(
    "scripts\generate_daily_orders.py",
    "scripts\generate_pos_orders.py"
)

$ordersFound = $false
foreach ($script in $ordersScripts) {
    $path = Join-Path $PROJECT_ROOT $script
    if (Test-Path $path) {
        $size = [math]::Round((Get-Item $path).Length / 1KB, 2)
        Write-Host "  [OK] $script ($size KB)" -ForegroundColor Green
        $ordersFound = $true
        break
    }
}
if (-not $ordersFound) {
    Write-Host "  [MANQUANT] generate_daily_orders.py ou generate_pos_orders.py" -ForegroundColor Red
    $allOk = $false
}

# Script génération stocks (plusieurs noms possibles)
$stockScripts = @(
    "scripts\generate_daily_stock.py",
    "scripts\generate_warehouse_stock.py"
)

$stockFound = $false
foreach ($script in $stockScripts) {
    $path = Join-Path $PROJECT_ROOT $script
    if (Test-Path $path) {
        $size = [math]::Round((Get-Item $path).Length / 1KB, 2)
        Write-Host "  [OK] $script ($size KB)" -ForegroundColor Green
        $stockFound = $true
        break
    }
}
if (-not $stockFound) {
    Write-Host "  [MANQUANT] generate_daily_stock.py ou generate_warehouse_stock.py" -ForegroundColor Red
    $allOk = $false
}

# Script commandes fournisseurs (optionnel)
$supplierScripts = @(
    "scripts\generate_supplier_orders.py",
    "scripts\generate_daily_supplier_orders.py"
)

$supplierFound = $false
foreach ($script in $supplierScripts) {
    $path = Join-Path $PROJECT_ROOT $script
    if (Test-Path $path) {
        $size = [math]::Round((Get-Item $path).Length / 1KB, 2)
        Write-Host "  [OK] $script ($size KB - optionnel)" -ForegroundColor Green
        $supplierFound = $true
        break
    }
}
if (-not $supplierFound) {
    Write-Host "  [ABSENT] generate_supplier_orders.py (optionnel)" -ForegroundColor Yellow
}

# Vérifier Docker
Write-Host "`nServices:" -ForegroundColor Yellow

$dockerTest = docker ps 2>&1 | Out-String
if ($dockerTest -match "CONTAINER ID") {
    Write-Host "  [OK] Docker" -ForegroundColor Green
    
    # Vérifier PostgreSQL
    $pgTest = docker ps --filter "name=postgres-procurement" --format "{{.Names}}" 2>&1
    if ($pgTest -match "postgres-procurement") {
        Write-Host "  [OK] PostgreSQL container actif" -ForegroundColor Green
    } else {
        Write-Host "  [ABSENT] PostgreSQL container" -ForegroundColor Yellow
        Write-Host "    Lancer: docker start postgres-procurement" -ForegroundColor Gray
        Write-Host "    OU créer: .\install_all.ps1" -ForegroundColor Gray
    }
} else {
    Write-Host "  [ERREUR] Docker non disponible" -ForegroundColor Red
    $allOk = $false
}

# Vérifier Python
$pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "python3" }
$pythonVersion = & $pythonCmd --version 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Python: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  [ERREUR] Python non disponible" -ForegroundColor Red
    $allOk = $false
}

# Lister tous les scripts Python trouvés
Write-Host "`nScripts Python détectés:" -ForegroundColor Yellow
$pythonScripts = Get-ChildItem (Join-Path $PROJECT_ROOT "scripts\python") -Filter "*.py" -ErrorAction SilentlyContinue
if ($pythonScripts) {
    foreach ($script in $pythonScripts) {
        $size = [math]::Round($script.Length / 1KB, 2)
        Write-Host "  - $($script.Name) ($size KB)" -ForegroundColor Cyan
    }
} else {
    Write-Host "  Aucun script Python trouvé" -ForegroundColor Gray
}

# Résumé
Write-Host "`n============================================" -ForegroundColor Cyan
if ($allOk) {
    Write-Host "INSTALLATION COMPLETE" -ForegroundColor Green
    Write-Host "Vous pouvez lancer: .\manage_scheduled_task.ps1 test" -ForegroundColor Cyan
} else {
    Write-Host "INSTALLATION INCOMPLETE" -ForegroundColor Red
    Write-Host "Corrigez les erreurs ci-dessus" -ForegroundColor Yellow
}
Write-Host "============================================" -ForegroundColor Cyan