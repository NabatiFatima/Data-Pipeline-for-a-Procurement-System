#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur de stocks entrepôts - Format JSON
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json
import argparse
from faker import Faker
import random

# Forcer l'encodage UTF-8 pour Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Initialiser Faker
fake = Faker('fr_FR')

def generate_daily_stock(target_date=None):
    """Générer les stocks en JSON pour UN SEUL JOUR"""
    if target_date is None:
        target_date = datetime.now().date()
    
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "data" / "raw" / "stock" / str(target_date)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nGeneration des stocks pour {target_date}")
    
    # Entrepôts
    warehouses = [
        {'warehouse_id': 'WH01', 'name': 'Entrepot Paris'},
        {'warehouse_id': 'WH02', 'name': 'Entrepot Lyon'},
        {'warehouse_id': 'WH03', 'name': 'Entrepot Marseille'}
    ]
    
    # Produits (200 SKUs)
    num_products = 200
    total_lines = 0
    
    # Générer UN SEUL fichier JSON consolidé pour tous les entrepôts
    all_stock = []
    
    for warehouse in warehouses:
        wh_id = warehouse['warehouse_id']
        
        for i in range(1, num_products + 1):
            sku = f"PROD{i:03d}"
            
            # Stock selon type de produit
            if i <= 50:  # Haute valeur
                base_qty = random.randint(10, 200)
            elif i <= 150:  # Moyenne valeur
                base_qty = random.randint(100, 500)
            else:  # Faible valeur
                base_qty = random.randint(200, 1000)
            
            # Variation aléatoire
            quantity = base_qty + random.randint(-50, 50)
            quantity = max(0, quantity)
            
            # Réservations
            reserved_qty = int(quantity * random.uniform(0.05, 0.25))
            available_qty = max(0, quantity - reserved_qty)
            
            # En transit (optionnel)
            in_transit_qty = random.randint(0, int(quantity * 0.1))
            
            stock = {
                'sku': sku,
                'available_quantity': available_qty,
                'reserved_quantity': reserved_qty,
                'in_transit_quantity': in_transit_qty
            }
            all_stock.append(stock)
        
        print(f"  Entrepot {wh_id}: {num_products} SKUs")
        total_lines += num_products
    
    # Sauvegarder UN SEUL fichier JSON
    output_file = output_dir / f"stock_{target_date}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_stock, f, indent=2, ensure_ascii=False)
    
    print(f"\nTotal: {total_lines} lignes de stock pour {target_date}")
    print(f"Fichier JSON sauvegarde: {output_file}")
    
    return total_lines

def generate_historical_stock(num_days=7, end_date=None):
    """Générer l'historique"""
    if end_date is None:
        end_date = datetime.now().date()
    
    print(f"\n{'='*60}")
    print(f"Generation de {num_days} jours d'historique de stock")
    print(f"{'='*60}")
    
    for days_back in range(num_days - 1, -1, -1):
        gen_date = end_date - timedelta(days=days_back)
        generate_daily_stock(gen_date)
    
    print(f"\n{'='*60}")
    print("Generation historique terminee!")
    print(f"{'='*60}")

def main():
    parser = argparse.ArgumentParser(description='Generer des stocks entrepots en JSON')
    parser.add_argument('--date', type=str, help='Date au format YYYY-MM-DD (defaut: aujourd\'hui)')
    parser.add_argument('--history-days', type=int, default=0,
                       help='Nombre de jours d\'historique (defaut: 0 = aujourd\'hui uniquement)')
    args = parser.parse_args()
    
    # Date cible
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
    else:
        target_date = datetime.now().date()
    
    # Générer
    if args.history_days > 0:
        generate_historical_stock(num_days=args.history_days + 1, end_date=target_date)
    else:
        generate_daily_stock(target_date)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())