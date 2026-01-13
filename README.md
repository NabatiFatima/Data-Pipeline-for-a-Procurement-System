# Créer le fichier README.md avec le bon encodage
$readmeContent = @'
#  Procurement Pipeline Project

Pipeline d'approvisionnement automatisé avec Trino et Parquet.

## Description
Système complet de gestion d'approvisionnement qui :
- Agrège les ventes quotidiennes
- Calcule la demande nette
- Génère automatiquement les commandes fournisseurs
- Produit des rapports d'analyse

##  Architecture
- **Pipeline Principal** : `scripts/procurement_pipeline.py`
- **Générateur de Données** : `scripts/generate_daily_*.py`
- **Orchestrateur** : `scripts/orchestrate_pipeline.py`
- **Sorties** : `data/output/`

## Installation
```bash
# Cloner le projet
git clone https://github.com/votre-username/procurement-project.git

# Installer les dépendances
pip install -r requirements.txt

# Exécuter le pipeline
python scripts/orchestrate_pipeline.py