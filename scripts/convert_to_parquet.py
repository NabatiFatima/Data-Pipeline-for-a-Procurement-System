#!/usr/bin/env python3
"""
Convertit les fichiers CSV en Parquet pour Trino/Hive
"""

import os
import pandas as pd
from datetime import datetime
import glob

def convert_csv_to_parquet(csv_path, parquet_path):
    """Convertit un fichier CSV en Parquet"""
    try:
        # Lire le CSV
        df = pd.read_csv(csv_path)
        
        # Créer le dossier de sortie si nécessaire
        os.makedirs(os.path.dirname(parquet_path), exist_ok=True)
        
        # Écrire en Parquet
        df.to_parquet(parquet_path, engine='pyarrow', index=False)
        
        return len(df)
    except Exception as e:
        print(f"❌ Erreur conversion {csv_path}: {e}")
        return 0

def convert_orders():
    """Convertir tous les fichiers de commandes CSV en Parquet"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    csv_dir = f"data/raw/orders/{date_str}"
    parquet_dir = f"data/parquet/orders/{date_str}"
    
    if not os.path.exists(csv_dir):
        print(f"⚠️  Dossier {csv_dir} inexistant")
        return 0
    
    csv_files = glob.glob(f"{csv_dir}/*.csv")
    total_rows = 0
    
    print(f"\n📊 Conversion des commandes...")
    for csv_file in csv_files:
        filename = os.path.basename(csv_file)
        parquet_file = os.path.join(parquet_dir, filename.replace('.csv', '.parquet'))
        
        rows = convert_csv_to_parquet(csv_file, parquet_file)
        total_rows += rows
        print(f"  ✅ {filename} → {rows} lignes")
    
    return total_rows

def convert_stock():
    """Convertir tous les fichiers de stock CSV en Parquet"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    csv_dir = f"data/raw/stock/{date_str}"
    parquet_dir = f"data/parquet/stock/{date_str}"
    
    if not os.path.exists(csv_dir):
        print(f"⚠️  Dossier {csv_dir} inexistant")
        return 0
    
    csv_files = glob.glob(f"{csv_dir}/*.csv")
    total_rows = 0
    
    print(f"\n📦 Conversion des stocks...")
    for csv_file in csv_files:
        filename = os.path.basename(csv_file)
        parquet_file = os.path.join(parquet_dir, filename.replace('.csv', '.parquet'))
        
        rows = convert_csv_to_parquet(csv_file, parquet_file)
        total_rows += rows
        print(f"  ✅ {filename} → {rows} lignes")
    
    return total_rows

if __name__ == "__main__":
    print("=" * 50)
    print("🔄 CONVERSION CSV → PARQUET")
    print("=" * 50)
    
    orders_rows = convert_orders()
    stock_rows = convert_stock()
    
    print(f"\n" + "=" * 50)
    print(f"✅ CONVERSION TERMINÉE")
    print(f"   Commandes: {orders_rows} lignes")
    print(f"   Stocks: {stock_rows} lignes")
    print("=" * 50)