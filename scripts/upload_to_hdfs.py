#!/usr/bin/env python3
"""
Upload des fichiers vers HDFS
"""

import os
import subprocess
from datetime import datetime, timedelta

def upload_directory_to_hdfs(local_path, hdfs_path):
    """Uploader un dossier local vers HDFS"""
    print(f"📤 Upload: {local_path} → {hdfs_path}")
    
    # Créer le dossier HDFS si nécessaire
    subprocess.run([
        'docker', 'exec', 'namenode', 
        'hdfs', 'dfs', '-mkdir', '-p', hdfs_path
    ])
    
    # Uploader les fichiers
    cmd = [
        'docker', 'exec', 'namenode',
        'hdfs', 'dfs', '-put', '-f',
        local_path, hdfs_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ Upload réussi")
    else:
        print(f"❌ Erreur: {result.stderr}")

def upload_daily_data(date):
    """Uploader les données d'une journée"""
    date_str = date.strftime('%Y-%m-%d')
    print(f"\n📅 Upload des données du {date_str}")
    print("="*60)
    
    # Upload commandes
    local_orders = f"/data/raw/orders/{date_str}"
    hdfs_orders = f"/raw/orders/{date_str}"
    upload_directory_to_hdfs(local_orders, hdfs_orders)
    
    # Upload stocks
    local_stock = f"/data/raw/stock/{date_str}"
    hdfs_stock = f"/raw/stock/{date_str}"
    upload_directory_to_hdfs(local_stock, hdfs_stock)
    
    print("="*60 + "\n")

if __name__ == "__main__":
    # Uploader les 7 derniers jours
    today = datetime.now().date()
    
    for day_offset in range(7, 0, -1):
        target_date = today - timedelta(days=day_offset)
        upload_daily_data(target_date)