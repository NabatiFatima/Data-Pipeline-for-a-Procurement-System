#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur de stocks entrepôts avec Faker
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import argparse
from faker import Faker

# Forcer l'encodage UTF-8 pour Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Initialiser Faker (une seule locale)
fake = Faker('fr_FR')
# Importer random standard
import random

def generate_warehouses(num_warehouses=3):
    """Générer des entrepôts réalistes"""
    cities = ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Lille']
    
    warehouses = []
    for i in range(1, num_warehouses + 1):
        warehouse = {
            'warehouse_id': f"WH{i:02d}",
            'name': f"Entrepot {cities[i-1]}",
            'address': fake.street_address(),
            'city': cities[i-1],
            'postal_code': fake.postcode(),
            'capacity_m3': np.random.randint(1000, 5000),
            'manager': fake.name(),
            'phone': fake.phone_number()
        }
        warehouses.append(warehouse)
    
    return warehouses

def generate_daily_stock(target_date=None):
    """Générer les stocks pour UN SEUL JOUR avec Faker"""
    if target_date is None:
        target_date = datetime.now().date()
    
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "data" / "raw" / "stock" / str(target_date)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nGeneration des stocks pour {target_date}")
    
    # Générer les entrepôts
    warehouses = generate_warehouses(3)
    
    # Produits (200 SKUs)
    num_products = 200
    
    all_stock = []
    
    for warehouse in warehouses:
        wh_id = warehouse['warehouse_id']
        
        warehouse_stock = []
        
        for i in range(1, num_products + 1):
            product_id = f"PROD{i:03d}"
            
            # Stock selon type de produit
            # Produits haute valeur = stock faible
            # Produits courante = stock élevé
            if i <= 50:  # Haute valeur (electronics, etc)
                base_qty = np.random.randint(10, 200)
            elif i <= 150:  # Moyenne valeur
                base_qty = np.random.randint(100, 500)
            else:  # Faible valeur (commodités)
                base_qty = np.random.randint(200, 1000)
            
            # Variation aléatoire
            quantity = base_qty + np.random.randint(-50, 50)
            quantity = max(0, quantity)
            
            # Réservations (commandes en cours)
            reserved_qty = int(quantity * random.uniform(0.05, 0.25))
            available_qty = max(0, quantity - reserved_qty)
            
            # Indicateurs de gestion
            reorder_point = int(base_qty * 0.2)
            needs_reorder = available_qty < reorder_point
            
            # Dernière réception
            days_since_receipt = np.random.randint(1, 30)
            last_receipt_date = target_date - timedelta(days=days_since_receipt)
            
            stock = {
                'warehouse_id': wh_id,
                'warehouse_name': warehouse['name'],
                'product_id': product_id,
                'quantity': quantity,
                'reserved_qty': reserved_qty,
                'available_qty': available_qty,
                'reorder_point': reorder_point,
                'needs_reorder': needs_reorder,
                'last_receipt_date': str(last_receipt_date),
                'days_since_receipt': days_since_receipt,
                'location': f"A{np.random.randint(1,20):02d}-R{np.random.randint(1,10):02d}-S{np.random.randint(1,5):02d}",
                'date': str(target_date),
                'timestamp': datetime.now().isoformat()
            }
            warehouse_stock.append(stock)
        
        # Sauvegarder par entrepôt
        df = pd.DataFrame(warehouse_stock)
        output_file = output_dir / f"{wh_id}_stock_{target_date}.csv"
        df.to_csv(output_file, index=False, encoding='utf-8')
        
        # Statistiques
        total_qty = df['quantity'].sum()
        total_available = df['available_qty'].sum()
        need_reorder_count = df['needs_reorder'].sum()
        
        print(f"  Entrepot {wh_id} ({warehouse['city']})...")
        print(f"    - {len(df)} SKUs")
        print(f"    - Stock total: {total_qty:,} unites")
        print(f"    - Disponible: {total_available:,} unites")
        print(f"    - A reapprovisionner: {need_reorder_count} produits")
        
        all_stock.extend(warehouse_stock)
    
    # Statistiques globales
    df_all = pd.DataFrame(all_stock)
    
    print(f"\n{'='*60}")
    print(f"Total: {len(all_stock)} lignes de stock pour {target_date}")
    print(f"Stock total: {df_all['quantity'].sum():,} unites")
    print(f"Disponible: {df_all['available_qty'].sum():,} unites")
    print(f"Reserve: {df_all['reserved_qty'].sum():,} unites")
    print(f"Fichiers sauvegardes dans: {output_dir}")
    print(f"{'='*60}")
    
    return df_all

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
    parser = argparse.ArgumentParser(description='Generer des stocks entrepots avec Faker')
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