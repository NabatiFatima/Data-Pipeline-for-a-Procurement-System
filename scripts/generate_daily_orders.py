#!/usr/bin/env python3
"""
Génération des commandes quotidiennes (fichiers POS) – CORRIGÉ
Simule des commandes pour 200 SKUs et force quelques besoins de réapprovisionnement.
"""

import json
import csv
import random
from datetime import datetime, timedelta
import os
import sys

# -----------------------------
# Configuration
# -----------------------------
NUM_STORES = 5          # Nombre de points de vente
ORDERS_PER_STORE = 50   # Commandes par magasin par jour
NUM_PRODUCTS = 200      # Nombre total de SKUs (correspond à ta base products)
FORCE_HIGH_QUANTITY = 10 # Nombre de SKUs forcés pour dépasser le stock de sécurité

random.seed(42)

# -----------------------------
# Fonctions
# -----------------------------
def generate_sku_list():
    """Générer la liste des SKUs disponibles"""
    return [f"SKU{i:04d}" for i in range(1, NUM_PRODUCTS + 1)]

def generate_orders_for_date(date_str, store_id, skus):
    """Générer les commandes pour un magasin à une date donnée"""
    orders = []

    # SKUs forcés pour tester le pipeline
    forced_skus = random.sample(skus, FORCE_HIGH_QUANTITY)

    for order_num in range(1, ORDERS_PER_STORE + 1):
        order_id = f"ORD-{store_id}-{date_str}-{order_num:04d}"
        timestamp = f"{date_str} {random.randint(8, 20):02d}:{random.randint(0, 59):02d}:00"

        # Nombre de produits dans la commande (1-10)
        num_items = random.randint(1, 10)
        selected_skus = random.sample(skus, num_items)

        for sku in selected_skus:
            # Si SKU forcé, quantite plus grande pour dépasser le stock de sécurité
            if sku in forced_skus:
                quantity = random.randint(10, 20)
            else:
                quantity = random.randint(1, 5)
            unit_price = round(random.uniform(5.0, 100.0), 2)

            orders.append({
                'order_id': order_id,
                'store_id': store_id,
                'order_date': date_str,
                'order_timestamp': timestamp,
                'sku': sku,
                'quantity': quantity,
                'unit_price': unit_price,
                'total_price': round(quantity * unit_price, 2)
            })

    return orders

def save_orders_json(orders, output_path):
    """Sauvegarder les commandes au format JSON"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(orders, f, indent=2, ensure_ascii=False)

def save_orders_csv(orders, output_path):
    """Sauvegarder les commandes au format CSV"""
    if not orders:
        return
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=orders[0].keys())
        writer.writeheader()
        writer.writerows(orders)

def generate_daily_orders(target_date, output_dir='data/raw/orders'):
    """Générer les commandes pour tous les magasins pour une date"""
    date_str = target_date.strftime('%Y-%m-%d')
    print(f"\n📅 Génération des commandes pour {date_str}")

    # Créer le dossier de sortie
    date_dir = os.path.join(output_dir, date_str)
    os.makedirs(date_dir, exist_ok=True)

    skus = generate_sku_list()
    all_orders = []

    for store_num in range(1, NUM_STORES + 1):
        store_id = f"STORE{store_num:02d}"
        print(f"  🏪 Magasin {store_id}...", end=' ')

        orders = generate_orders_for_date(date_str, store_id, skus)

        # Sauvegarder au format JSON (un fichier par magasin)
        json_path = os.path.join(date_dir, f"{store_id}_orders.json")
        save_orders_json(orders, json_path)

        # Sauvegarder au format CSV
        csv_path = os.path.join(date_dir, f"{store_id}_orders.csv")
        save_orders_csv(orders, csv_path)

        all_orders.extend(orders)
        print(f"✅ {len(orders)} lignes de commande")

    # Fichier consolidé
    consolidated_path = os.path.join(date_dir, f"all_orders_{date_str}.json")
    save_orders_json(all_orders, consolidated_path)

    print(f"\n✅ Total: {len(all_orders)} lignes de commande pour {date_str}")
    print(f"📁 Fichiers sauvegardés dans: {date_dir}\n")
    return all_orders

def generate_historical_orders(num_days=7, output_dir='data/raw/orders'):
    """Générer l'historique de commandes sur plusieurs jours"""
    today = datetime.now().date()
    for day_offset in range(num_days, 0, -1):
        target_date = today - timedelta(days=day_offset)
        generate_daily_orders(target_date, output_dir)
    print("✅ Génération historique terminée!\n")

# -----------------------------
# Exécution principale - CORRIGÉ
# -----------------------------
if __name__ == "__main__":
    # Vérifier si on veut générer UNIQUEMENT aujourd'hui
    if len(sys.argv) > 1 and sys.argv[1] == '--today':
        # Mode pipeline quotidien : générer AUJOURD'HUI
        today = datetime.now().date()
        generate_daily_orders(today)
        print(f"✅ Commandes générées pour AUJOURD'HUI : {today}")
    else:
        # Mode initial/historique : générer les 7 derniers jours
        generate_historical_orders(num_days=7)
        print("✅ Génération historique terminée!")