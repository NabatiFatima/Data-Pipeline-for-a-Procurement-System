#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur de commandes POS avec Faker
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

# Initialiser Faker (une seule locale pour éviter les erreurs)
fake = Faker('fr_FR')
# Importer random standard
import random

# Catégories de produits
CATEGORIES = {
    'Electronics': ['Smartphone', 'Laptop', 'Tablet', 'Headphones', 'Camera', 'Smartwatch'],
    'Clothing': ['T-Shirt', 'Jeans', 'Dress', 'Jacket', 'Shoes', 'Hat'],
    'Food': ['Pasta', 'Rice', 'Bread', 'Milk', 'Cheese', 'Coffee'],
    'Books': ['Novel', 'Magazine', 'Comics', 'Textbook', 'Dictionary'],
    'Home': ['Towel', 'Pillow', 'Lamp', 'Rug', 'Clock', 'Mirror'],
    'Sports': ['Ball', 'Racket', 'Weights', 'Yoga Mat', 'Bicycle', 'Sneakers']
}

# Cache de produits
_PRODUCTS_CACHE = None

def generate_products(num_products=200):
    """Générer une liste de produits réalistes"""
    global _PRODUCTS_CACHE
    
    if _PRODUCTS_CACHE is not None:
        return _PRODUCTS_CACHE
    
    products = []
    for i in range(1, num_products + 1):
        category = fake.random_element(list(CATEGORIES.keys()))
        product_type = fake.random_element(CATEGORIES[category])
        brand = fake.company()
        
        product = {
            'product_id': f"PROD{i:03d}",
            'name': f"{brand} {product_type}",
            'category': category,
            'unit_price': round(random.uniform(5.0, 500.0), 2),
            'weight_kg': round(random.uniform(0.1, 20.0), 2),
            'barcode': fake.ean13()
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
            'name': f"{fake.company()} - {cities[i-1]}",
            'address': fake.street_address(),
            'city': cities[i-1],
            'postal_code': fake.postcode(),
            'manager': fake.name(),
            'phone': fake.phone_number(),
            'email': fake.email()
        }
        stores.append(store)
    
    return stores

def generate_daily_orders(target_date=None):
    """Générer les commandes pour UN SEUL JOUR avec Faker"""
    if target_date is None:
        target_date = datetime.now().date()
    
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "data" / "raw" / "orders" / str(target_date)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nGeneration des commandes pour {target_date}")
    
    # Générer les produits et magasins
    products = generate_products(200)
    stores = generate_stores(5)
    
    all_orders = []
    
    for store in stores:
        store_id = store['store_id']
        
        # Nombre de commandes aléatoire selon le jour
        is_weekend = target_date.weekday() >= 5
        base_orders = 300 if is_weekend else 250
        n_orders = np.random.randint(base_orders - 50, base_orders + 100)
        
        store_orders = []
        
        for i in range(n_orders):
            product = fake.random_element(products)
            
            # Heure de commande réaliste (8h-22h)
            order_hour = np.random.randint(8, 23)
            order_minute = np.random.randint(0, 60)
            order_time = datetime.combine(target_date, datetime.min.time()) + timedelta(hours=order_hour, minutes=order_minute)
            
            # Quantité selon le prix (produits chers = petites quantités)
            if product['unit_price'] > 200:
                quantity = np.random.randint(1, 3)
            elif product['unit_price'] > 50:
                quantity = np.random.randint(1, 10)
            else:
                quantity = np.random.randint(1, 50)
            
            order = {
                'order_id': f"{store_id}_{target_date}_{i:05d}",
                'store_id': store_id,
                'store_name': store['name'],
                'product_id': product['product_id'],
                'product_name': product['name'],
                'category': product['category'],
                'quantity': quantity,
                'unit_price': product['unit_price'],
                'total_amount': round(quantity * product['unit_price'], 2),
                'order_date': str(target_date),
                'order_time': order_time.strftime('%H:%M:%S'),
                'timestamp': order_time.isoformat(),
                'customer_type': fake.random_element(['Regular', 'Premium', 'New']),
                'payment_method': fake.random_element(['Card', 'Cash', 'Mobile'])
            }
            store_orders.append(order)
        
        # Sauvegarder par magasin
        df = pd.DataFrame(store_orders)
        output_file = output_dir / f"{store_id}_orders_{target_date}.csv"
        df.to_csv(output_file, index=False, encoding='utf-8')
        
        print(f"  Magasin {store_id} ({store['city']})... {len(df)} commandes | Total: {df['total_amount'].sum():,.2f} EUR")
        all_orders.extend(store_orders)
    
    # Statistiques globales
    df_all = pd.DataFrame(all_orders)
    total_revenue = df_all['total_amount'].sum()
    avg_order = df_all['total_amount'].mean()
    
    print(f"\n{'='*60}")
    print(f"Total: {len(all_orders)} commandes pour {target_date}")
    print(f"Revenu total: {total_revenue:,.2f} EUR")
    print(f"Panier moyen: {avg_order:.2f} EUR")
    print(f"Fichiers sauvegardes dans: {output_dir}")
    print(f"{'='*60}")
    
    return df_all

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
    parser = argparse.ArgumentParser(description='Generer des commandes POS avec Faker')
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