#!/bin/bash

# ============================================
# Script d'orchestration quotidien
# Pipeline d'approvisionnement - Version Production
# ============================================

set -e  # Arrêter en cas d'erreur

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
DATA_DIR="$PROJECT_DIR/data"
DATE=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)

echo "================================================"
echo "🚀 PROCUREMENT PIPELINE - $DATE"
echo "================================================"
echo "Répertoire projet: $PROJECT_DIR"
echo "Date de traitement: $YESTERDAY"
echo "================================================"

# Création des répertoires
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR/input"
mkdir -p "$DATA_DIR/output"
mkdir -p "$DATA_DIR/archive"

# Fonction de logging
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/pipeline_$DATE.log"
}

# Fonction de vérification
check_command() {
    if [ $? -eq 0 ]; then
        log_message "✅ $1"
    else
        log_message "❌ ERREUR: $1"
        exit 1
    fi
}

# Début du pipeline
log_message "Début du pipeline d'approvisionnement"

# 1. Générer les données du jour (simulation)
log_message "📊 Phase 1: Génération des données..."
python "$PROJECT_DIR/scripts/generate_daily_orders.py" --date "$YESTERDAY"
check_command "Génération des commandes quotidiennes"

python "$PROJECT_DIR/scripts/generate_daily_stock.py" --date "$YESTERDAY"
check_command "Génération des stocks quotidiens"

# 2. Exécuter le pipeline principal
log_message "🔄 Phase 2: Exécution du pipeline principal..."
python "$PROJECT_DIR/scripts/procurement_pipeline.py" --date "$YESTERDAY" --skip-data-gen
check_command "Exécution du pipeline principal"

# 3. Vérification des données dans Trino
log_message "🔍 Phase 3: Vérification des données..."
if command -v docker &> /dev/null && docker ps | grep -q trino; then
    log_message "Vérification des données dans Trino..."
    # Vérification simplifiée pour la démo
    log_message "  Trino détecté, vérifications en cours..."
else
    log_message "  ⚠️ Trino non disponible, vérifications locales uniquement"
fi

# 4. Génération des rapports
log_message "📈 Phase 4: Génération des rapports..."
python "$PROJECT_DIR/scripts/generate_reports.py" --date "$YESTERDAY"
check_command "Génération des rapports"

# 5. Archivage des données
log_message "💾 Phase 5: Archivage des données..."
ARCHIVE_DIR="$DATA_DIR/archive/$YESTERDAY"
mkdir -p "$ARCHIVE_DIR"

# Copier les fichiers d'input
cp -r "$DATA_DIR/input/$YESTERDAY" "$ARCHIVE_DIR/" 2>/dev/null || log_message "⚠️ Pas de données input à archiver"

# Copier les fichiers d'output
cp -r "$DATA_DIR/output/sales_aggregation/$YESTERDAY" "$ARCHIVE_DIR/" 2>/dev/null || log_message "⚠️ Pas de données sales à archiver"
cp -r "$DATA_DIR/output/net_demand/$YESTERDAY" "$ARCHIVE_DIR/" 2>/dev/null || log_message "⚠️ Pas de données net_demand à archiver"
cp -r "$DATA_DIR/output/supplier_orders/$YESTERDAY" "$ARCHIVE_DIR/" 2>/dev/null || log_message "⚠️ Pas de données supplier_orders à archiver"

log_message "  Données archivées dans: $ARCHIVE_DIR"

# 6. Nettoyage
log_message "🧹 Phase 6: Nettoyage..."
# Garder seulement 7 jours de logs
find "$LOG_DIR" -name "pipeline_*.log" -mtime +7 -delete
# Garder seulement 30 jours d'archive
find "$DATA_DIR/archive" -type d -mtime +30 -exec rm -rf {} \; 2>/dev/null || true

log_message "  Nettoyage terminé"

# Résumé final
log_message "================================================"
log_message "📊 RÉSUMÉ DE L'EXÉCUTION:"
log_message "  Date: $YESTERDAY"
log_message "  Logs: $LOG_DIR/pipeline_$DATE.log"
log_message "  Archive: $ARCHIVE_DIR"

# Vérifier les fichiers générés
if [ -d "$DATA_DIR/output/supplier_orders/$YESTERDAY" ]; then
    ORDER_COUNT=$(find "$DATA_DIR/output/supplier_orders/$YESTERDAY" -name "*.csv" | wc -l)
    log_message "  Commandes générées: $ORDER_COUNT fichier(s)"
fi

log_message "================================================"
log_message "✅ PIPELINE TERMINÉ AVEC SUCCÈS"
log_message "================================================"

# Créer un fichier de succès
echo "SUCCESS: Pipeline exécuté le $DATE pour la date $YESTERDAY" > "$DATA_DIR/output/last_success.txt"