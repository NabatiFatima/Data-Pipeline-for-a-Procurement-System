#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur de commandes POS - Format JSON
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

# Catégories de produits
CATEGORIES = {
    'Electronics': ['Smartphone', 'Laptop', 'Tablet', 'Headphones', 'Camera', 'Smartwatch'],
    'Clothing': ['T-Shirt', 'Jeans', 'Dress', 'Jacket', 'Shoes', 'Hat'],
    'Food': ['Pasta', 'Rice', 'Bread', 'Milk', 'Cheese', 'Coffee'],
    'Books': ['Novel', 'Magazine', 'Comics', 'Textbook', 'Dictionary'],
    'Home': ['Towel', 'Pillow', 'Lamp', 'Rug', 'Clock', 'Mirror'],
    'Sports': ['Ball', 'Racket', 'Weights', 'Yoga Mat', 'Bicycle', 'Sneakers']
}

_PRODUCTS_CACHE = None

def generate_products(num_products=200):
    """Générer une liste de produits réalistes"""
    global _PRODUCTS_CACHE
    
    if _PRODUCTS_CACHE is not None:
        return _PRODUCTS_CACHE
    
    products = []
    for i in range(1, num_products + 1):
        category = random.choice(list(CATEGORIES.keys()))
        product_type = random.choice(CATEGORIES[category])
        brand = fake.company()
        
        product = {
            'sku': f"PROD{i:03d}",
            'product_name': f"{brand} {product_type}",
            'category': category,
            'unit_price': round(random.uniform(5.0, 500.0), 2)
        }
        products.append(product)
    
    _PRODUCTS_CACHE = products
    return products

def generate_stores(num_stores=5):
    """Générer des magasins réalistes"""
    stores = []
    cities = ['Paris', 'Lyon', 'Marseille', 'Toulouse', 'Nice']
    
    for i in range(1, num_stores + 1):
        store = {
            'store_id': f"STORE{i:02d}",
            'store_name': f"{fake.company()} - {cities[i-1]}",
            'city': cities[i-1]
        }
        stores.append(store)
    
    return stores

def generate_daily_orders(target_date=None):
    """Générer les commandes en JSON pour UN SEUL JOUR"""
    if target_date is None:
        target_date = datetime.now().date()
    
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "data" / "raw" / "orders" / str(target_date)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nGeneration des commandes pour {target_date}")
    
    # Générer les produits et magasins
    products = generate_products(200)
    stores = generate_stores(5)
    
    total_orders = 0
    
    for store in stores:
        store_id = store['store_id']
        
        # Nombre de commandes aléatoire
        is_weekend = target_date.weekday() >= 5
        base_orders = 300 if is_weekend else 250
        n_orders = random.randint(base_orders - 50, base_orders + 100)
        
        store_orders = []
        
        for i in range(n_orders):
            product = random.choice(products)
            
            # Heure de commande réaliste
            order_hour = random.randint(8, 22)
            order_minute = random.randint(0, 59)
            order_second = random.randint(0, 59)
            order_time = datetime.combine(
                target_date, 
                datetime.min.time()
            ).replace(hour=order_hour, minute=order_minute, second=order_second)
            
            # Quantité selon le prix
            if product['unit_price'] > 200:
                quantity = random.randint(1, 3)
            elif product['unit_price'] > 50:
                quantity = random.randint(1, 10)
            else:
                quantity = random.randint(1, 50)
            
            order = {
                'order_id': f"{store_id}_{target_date}_{i:05d}",
                'store_id': store_id,
                'order_date': str(target_date),
                'order_timestamp': order_time.isoformat(),
                'sku': product['sku'],
                'quantity': quantity,
                'unit_price': product['unit_price'],
                'total_price': round(quantity * product['unit_price'], 2)
            }
            store_orders.append(order)
        
        # Sauvegarder en JSON par magasin
        output_file = output_dir / f"{store_id}_orders_{target_date}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(store_orders, f, indent=2, ensure_ascii=False)
        
        print(f"  Magasin {store_id}: {len(store_orders)} commandes")
        total_orders += len(store_orders)
    
    print(f"\nTotal: {total_orders} commandes pour {target_date}")
    print(f"Fichiers JSON sauvegardes dans: {output_dir}")
    
    return total_orders

def generate_historical_orders(num_days=7, end_date=None):
    """Générer l'historique"""
    if end_date is None:
        end_date = datetime.now().date()
    
    print(f"\n{'='*60}")
    print(f"Generation de {num_days} jours d'historique")
    print(f"{'='*60}")
    
    for days_back in range(num_days - 1, -1, -1):
        gen_date = end_date - timedelta(days=days_back)
        generate_daily_orders(gen_date)
    
    print(f"\n{'='*60}")
    print("Generation historique terminee!")
    print(f"{'='*60}")

def main():
    parser = argparse.ArgumentParser(description='Generer des commandes POS en JSON')
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
        generate_historical_orders(num_days=args.history_days + 1, end_date=target_date)
    else:
        generate_daily_orders(target_date)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())