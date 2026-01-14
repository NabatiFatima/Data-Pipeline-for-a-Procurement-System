#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONVERSION JSON -> PARQUET
==========================
Compatible Windows (sans emojis)
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd

# Force UTF-8 pour Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ============================================
# CONFIGURATION
# ============================================

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'

# ============================================
# FONCTIONS
# ============================================

def log(msg, level='INFO'):
    """Logger sans emojis pour Windows"""
    prefix = {
        'INFO': '[INFO]',
        'SUCCESS': '[OK]',
        'ERROR': '[ERROR]',
        'WARNING': '[WARN]'
    }
    print(f"{prefix.get(level, '[INFO]')} {msg}")

def convert_orders_to_parquet(date_str):
    """Convertir les commandes JSON en Parquet"""
    log(f"Conversion commandes pour {date_str}...")
    
    # Chemins
    input_dir = DATA_DIR / 'raw' / 'orders' / date_str
    output_dir = DATA_DIR / 'parquet' / 'orders' / date_str
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_dir.exists():
        log(f"Repertoire manquant: {input_dir}", 'ERROR')
        return False
    
    # Lire tous les JSON
    all_orders = []
    json_files = list(input_dir.glob('*.json'))
    
    if not json_files:
        log(f"Aucun fichier JSON dans {input_dir}", 'ERROR')
        return False
    
    log(f"Traitement de {len(json_files)} fichier(s) JSON...")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Si c'est une liste de commandes
                if isinstance(data, list):
                    orders = data
                # Si c'est un dict avec une clé 'orders'
                elif isinstance(data, dict) and 'orders' in data:
                    orders = data['orders']
                else:
                    orders = [data]
                
                # Aplatir la structure
                for order in orders:
                    if 'items' in order:
                        for item in order['items']:
                            all_orders.append({
                                'order_id': order.get('order_id'),
                                'store_id': order.get('store_id'),
                                'order_date': order.get('order_date'),
                                'order_time': order.get('order_time', ''),
                                'customer_id': order.get('customer_id', ''),
                                'sku': item.get('sku'),
                                'quantity': item.get('quantity'),
                                'unit_price': item.get('unit_price')
                            })
        except Exception as e:
            log(f"Erreur lecture {json_file.name}: {e}", 'ERROR')
            continue
    
    if not all_orders:
        log("Aucune commande trouvee", 'ERROR')
        return False
    
    # Créer DataFrame
    df = pd.DataFrame(all_orders)
    
    # Ajouter colonne de partition
    df['dt'] = date_str
    
    # Sauvegarder en Parquet
    output_file = output_dir / 'orders.parquet'
    df.to_parquet(
        output_file,
        engine='pyarrow',
        compression='snappy',
        index=False
    )
    
    log(f"Commandes: {len(df)} lignes -> {output_file}", 'SUCCESS')
    return True

def convert_stock_to_parquet(date_str):
    """Convertir les stocks JSON en Parquet"""
    log(f"Conversion stocks pour {date_str}...")
    
    # Chemins
    input_dir = DATA_DIR / 'raw' / 'stock' / date_str
    output_dir = DATA_DIR / 'parquet' / 'stock' / date_str
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_dir.exists():
        log(f"Repertoire manquant: {input_dir}", 'ERROR')
        return False
    
    # Lire tous les JSON
    all_stock = []
    json_files = list(input_dir.glob('*.json'))
    
    if not json_files:
        log(f"Aucun fichier JSON dans {input_dir}", 'ERROR')
        return False
    
    log(f"Traitement de {len(json_files)} fichier(s) JSON...")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Si c'est une liste
                if isinstance(data, list):
                    all_stock.extend(data)
                # Si c'est un dict avec une clé 'stock'
                elif isinstance(data, dict) and 'stock' in data:
                    all_stock.extend(data['stock'])
                else:
                    all_stock.append(data)
        except Exception as e:
            log(f"Erreur lecture {json_file.name}: {e}", 'ERROR')
            continue
    
    if not all_stock:
        log("Aucun stock trouve", 'ERROR')
        return False
    
    # Créer DataFrame
    df = pd.DataFrame(all_stock)
    
    # Ajouter colonne de partition
    df['dt'] = date_str
    
    # Sauvegarder en Parquet
    output_file = output_dir / 'stock.parquet'
    df.to_parquet(
        output_file,
        engine='pyarrow',
        compression='snappy',
        index=False
    )
    
    log(f"Stocks: {len(df)} lignes -> {output_file}", 'SUCCESS')
    return True

# ============================================
# MAIN
# ============================================

def main():
    """Point d'entree principal"""
    parser = argparse.ArgumentParser(description='Conversion JSON vers Parquet')
    parser.add_argument('--date', type=str, required=True, 
                       help='Date au format YYYY-MM-DD')
    
    args = parser.parse_args()
    date_str = args.date
    
    # Valider la date
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        log(f"Format de date invalide: {date_str}", 'ERROR')
        log("Format attendu: YYYY-MM-DD", 'ERROR')
        return False
    
    print("=" * 60)
    print(f"  CONVERSION JSON -> PARQUET")
    print(f"  Date: {date_str}")
    print("=" * 60)
    print()
    
    # Conversion commandes
    success_orders = convert_orders_to_parquet(date_str)
    
    # Conversion stocks
    success_stock = convert_stock_to_parquet(date_str)
    
    # Résumé
    print()
    print("=" * 60)
    if success_orders and success_stock:
        log("CONVERSION TERMINEE AVEC SUCCES", 'SUCCESS')
        return True
    else:
        log("CONVERSION TERMINEE AVEC ERREURS", 'WARNING')
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)