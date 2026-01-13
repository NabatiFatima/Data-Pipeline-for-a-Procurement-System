#!/usr/bin/env python3
"""
Génération des snapshots de stock quotidiens
Simule les niveaux de stock en fin de journée pour chaque entrepôt
"""

import json
import csv
import random
from datetime import datetime, timedelta
import os

random.seed(42)

# Configuration
NUM_PRODUCTS = 100
NUM_WAREHOUSES = 3

def generate_sku_list():
    """Générer la liste des SKUs"""
    return [f"SKU{i:04d}" for i in range(1, NUM_PRODUCTS + 1)]

def generate_stock_snapshot(date_str, warehouse_id, skus):
    """Générer le snapshot de stock pour un entrepôt"""
    stock_data = []
    
    for sku in skus:
        available_stock = random.randint(0, 1000)
        reserved_stock = random.randint(0, min(100, available_stock))
        
        stock_data.append({
            'snapshot_date': date_str,
            'warehouse_id': warehouse_id,
            'sku': sku,
            'available_stock': available_stock,
            'reserved_stock': reserved_stock,
            'free_stock': available_stock - reserved_stock
        })
    
    return stock_data

def save_stock_json(stock_data, output_path):
    """Sauvegarder le stock au format JSON"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(stock_data, f, indent=2)

def save_stock_csv(stock_data, output_path):
    """Sauvegarder le stock au format CSV"""
    if not stock_data:
        return
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=stock_data[0].keys())
        writer.writeheader()
        writer.writerows(stock_data)

def generate_daily_stock(target_date, output_dir='data/raw/stock'):
    """Générer les stocks pour tous les entrepôts pour une date"""
    date_str = target_date.strftime('%Y-%m-%d')
    print(f"\n📅 Génération des stocks pour {date_str}")
    
    # Créer le dossier de sortie
    date_dir = os.path.join(output_dir, date_str)
    os.makedirs(date_dir, exist_ok=True)
    
    skus = generate_sku_list()
    all_stock = []
    
    for wh_num in range(1, NUM_WAREHOUSES + 1):
        warehouse_id = f"WH{wh_num:02d}"
        print(f"  🏢 Entrepôt {warehouse_id}...", end=' ')
        
        stock_data = generate_stock_snapshot(date_str, warehouse_id, skus)
        
        # Sauvegarder JSON
        json_path = os.path.join(date_dir, f"{warehouse_id}_stock.json")
        save_stock_json(stock_data, json_path)
        
        # Sauvegarder CSV
        csv_path = os.path.join(date_dir, f"{warehouse_id}_stock.csv")
        save_stock_csv(stock_data, csv_path)
        
        all_stock.extend(stock_data)
        print(f"✅ {len(stock_data)} SKUs")
    
    # Fichier consolidé
    consolidated_path = os.path.join(date_dir, f"all_stock_{date_str}.json")
    save_stock_json(all_stock, consolidated_path)
    
    print(f"\n✅ Total: {len(all_stock)} lignes de stock pour {date_str}")
    print(f"📁 Fichiers sauvegardés dans: {date_dir}\n")
    
    return all_stock

def generate_historical_stock(num_days=7, output_dir='data/raw/stock'):
    """Générer l'historique de stocks sur plusieurs jours"""
    print(f"\n🗓️  Génération de {num_days} jours d'historique de stock")
    print("="*60)
    
    today = datetime.now().date()
    
    for day_offset in range(num_days, 0, -1):
        target_date = today - timedelta(days=day_offset)
        generate_daily_stock(target_date, output_dir)
    
    print("="*60)
    print("✅ Génération historique terminée!\n")

if __name__ == "__main__":
    # Générer 7 jours d'historique
    generate_historical_stock(num_days=7)