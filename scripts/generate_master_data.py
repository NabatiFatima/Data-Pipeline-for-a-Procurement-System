"""
Procurement System - Master Data Generator
Generates test data for PostgreSQL tables using Faker
"""

import random
from datetime import datetime, timedelta
from faker import Faker
import psycopg2
from psycopg2.extras import execute_values

# Initialize Faker
fake = Faker('fr_FR')  # French locale for more realistic Moroccan-style names

# Database connection parameters
DB_CONFIG = {
    "host": "localhost",            # ou l'IP du conteneur si distant
    "port": 5432,                   # port par défaut PostgreSQL
    "database": "procurement_db",   # base que tu as initialisée
    "user": "procurement_user",     # utilisateur du conteneur
    "password": "procurement_pass"
}


# ============================================================
# CONFIGURATION PARAMETERS
# ============================================================
NUM_SUPPLIERS = 15
NUM_CATEGORIES = 10
NUM_WAREHOUSES = 3
NUM_PRODUCTS = 200

# Product categories for a grocery store
GROCERY_CATEGORIES = [
    ('CAT001', 'Fruits & Légumes', None, 'Fresh produce'),
    ('CAT002', 'Produits Laitiers', None, 'Dairy products'),
    ('CAT003', 'Viandes & Poissons', None, 'Meat and seafood'),
    ('CAT004', 'Épicerie Salée', None, 'Savory groceries'),
    ('CAT005', 'Épicerie Sucrée', None, 'Sweet groceries'),
    ('CAT006', 'Boissons', None, 'Beverages'),
    ('CAT007', 'Surgelés', None, 'Frozen foods'),
    ('CAT008', 'Hygiène & Beauté', None, 'Personal care'),
    ('CAT009', 'Entretien Ménager', None, 'Household cleaning'),
    ('CAT010', 'Boulangerie', None, 'Bakery products')
]

# Sample product names by category
PRODUCTS_BY_CATEGORY = {
    'CAT001': ['Pommes Golden', 'Bananes', 'Tomates', 'Carottes', 'Oranges', 'Laitue', 
               'Poivrons', 'Oignons', 'Pommes de terre', 'Citrons'],
    'CAT002': ['Lait demi-écrémé', 'Yaourt nature', 'Fromage blanc', 'Beurre doux', 
               'Crème fraîche', 'Fromage râpé', 'Yaourt aux fruits'],
    'CAT003': ['Poulet fermier', 'Bœuf haché', 'Filet de saumon', 'Merguez', 
               'Côtelettes d\'agneau', 'Crevettes'],
    'CAT004': ['Pâtes spaghetti', 'Riz basmati', 'Huile d\'olive', 'Conserve tomates', 
               'Thon en boîte', 'Farine', 'Sel fin', 'Couscous'],
    'CAT005': ['Sucre blanc', 'Chocolat noir', 'Confiture fraise', 'Biscuits', 
               'Céréales petit-déjeuner', 'Miel'],
    'CAT006': ['Eau minérale 1.5L', 'Jus d\'orange', 'Coca-Cola', 'Thé vert', 
               'Café moulu', 'Lait chocolaté'],
    'CAT007': ['Pizza surgelée', 'Légumes surgelés', 'Glace vanille', 'Frites surgelées'],
    'CAT008': ['Shampooing', 'Savon liquide', 'Dentifrice', 'Déodorant', 'Papier toilette'],
    'CAT009': ['Liquide vaisselle', 'Lessive liquide', 'Javel', 'Éponges'],
    'CAT010': ['Pain de campagne', 'Croissants', 'Baguette', 'Pain de mie']
}

# Moroccan cities for warehouses
MOROCCAN_CITIES = [
    ('WH001', 'Entrepôt Principal Casablanca', 'Casablanca', 'Zone Industrielle Ain Sebaa'),
    ('WH002', 'Entrepôt Régional Rabat', 'Rabat', 'Technopolis'),
    ('WH003', 'Entrepôt Fès', 'Fès', 'Route de Sefrou')
]

# ============================================================
# GENERATOR FUNCTIONS
# ============================================================

def generate_suppliers(num_suppliers):
    """Generate supplier data"""
    suppliers = []
    supplier_types = ['Fresh Ltd', 'Distribution SA', 'Import Export', 'Wholesale Co', 
                      'Products SARL', 'Trading', 'Supply Chain']
    
    for i in range(1, num_suppliers + 1):
        supplier_id = f'SUP{i:03d}'
        company_name = f"{fake.company()} {random.choice(supplier_types)}"
        
        suppliers.append({
            'supplier_id': supplier_id,
            'supplier_name': company_name,
            'contact_email': fake.company_email(),
            'contact_phone': fake.phone_number(),
            'address': fake.address().replace('\n', ', '),
            'country': random.choice(['Morocco', 'Morocco', 'Morocco', 'France', 'Spain', 'Turkey']),
            'default_lead_time_days': random.choice([1, 2, 3, 5, 7]),
            'is_active': random.choice([True, True, True, False])  # 75% active
        })
    
    return suppliers

def generate_products(num_products, suppliers):
    """Generate product master data"""
    products = []
    sku_counter = 1
    
    for category_id, products_list in PRODUCTS_BY_CATEGORY.items():
        for product_name in products_list:
            if sku_counter > num_products:
                break
                
            sku = f'SKU{sku_counter:05d}'
            supplier = random.choice(suppliers)
            
            # Determine if perishable based on category
            is_perishable = category_id in ['CAT001', 'CAT002', 'CAT003', 'CAT007', 'CAT010']
            
            products.append({
                'sku': sku,
                'product_name': product_name,
                'product_description': fake.sentence(),
                'category_id': category_id,
                'supplier_id': supplier['supplier_id'],
                'unit_of_measure': random.choice(['UNIT', 'KG', 'LITER', 'PIECE']),
                'unit_price': round(random.uniform(5.0, 150.0), 2),
                'barcode': fake.ean13(),
                'is_perishable': is_perishable,
                'shelf_life_days': random.choice([3, 7, 14, 30, 90, 180, 365]) if is_perishable else None,
                'weight_kg': round(random.uniform(0.1, 5.0), 3),
                'is_active': True
            })
            
            sku_counter += 1
    
    # Fill remaining products if needed
    while sku_counter <= num_products:
        sku = f'SKU{sku_counter:05d}'
        category_id = random.choice([c[0] for c in GROCERY_CATEGORIES])
        supplier = random.choice(suppliers)
        
        products.append({
            'sku': sku,
            'product_name': f'{fake.word().capitalize()} {fake.word()}',
            'product_description': fake.sentence(),
            'category_id': category_id,
            'supplier_id': supplier['supplier_id'],
            'unit_of_measure': random.choice(['UNIT', 'KG', 'LITER']),
            'unit_price': round(random.uniform(5.0, 100.0), 2),
            'barcode': fake.ean13(),
            'is_perishable': random.choice([True, False]),
            'shelf_life_days': random.choice([7, 14, 30, 90]) if random.choice([True, False]) else None,
            'weight_kg': round(random.uniform(0.1, 3.0), 3),
            'is_active': True
        })
        
        sku_counter += 1
    
    return products

def generate_replenishment_rules(products):
    """Generate replenishment rules for each product"""
    rules = []
    
    for product in products:
        # Common pack sizes for retail
        pack_size = random.choice([6, 12, 24, 48])
        moq = pack_size * random.choice([1, 2, 4])
        
        rules.append({
            'sku': product['sku'],
            'supplier_id': product['supplier_id'],
            'moq': moq,
            'pack_size': pack_size,
            'case_size': random.choice([2, 4, 6, 10]),
            'lead_time_days': random.choice([1, 2, 3, 5, 7]),
            'order_multiple': pack_size,
            'max_order_quantity': moq * random.choice([20, 50, 100]),
            'ordering_calendar': random.choice(['DAILY', 'DAILY', 'MON_WED_FRI', 'WEEKLY']),
            'effective_from': datetime.now().date() - timedelta(days=random.randint(0, 180)),
            'effective_to': None,
            'notes': 'Auto-generated rule'
        })
    
    return rules

def generate_safety_stock(products, warehouses):
    """Generate safety stock levels for products in warehouses"""
    safety_stocks = []
    
    for product in products:
        # Not all products in all warehouses
        num_warehouses = random.choice([1, 2, 3])
        selected_warehouses = random.sample(warehouses, num_warehouses)
        
        for warehouse in selected_warehouses:
            # Safety stock typically 3-7 days of average demand
            safety_qty = random.choice([12, 24, 48, 72, 96, 120, 200])
            
            safety_stocks.append({
                'sku': product['sku'],
                'warehouse_id': warehouse[0],
                'safety_stock_quantity': safety_qty,
                'reorder_point': int(safety_qty * 1.5),
                'max_stock_level': safety_qty * random.choice([3, 5, 10]),
                'calculation_method': random.choice(['MANUAL', 'STATISTICAL', 'FIXED_DAYS_SUPPLY']),
                'last_reviewed_date': datetime.now().date() - timedelta(days=random.randint(1, 30)),
                'review_frequency_days': 30,
                'notes': 'Initial setup'
            })
    
    return safety_stocks

# ============================================================
# DATABASE INSERTION FUNCTIONS
# ============================================================

def insert_suppliers(conn, suppliers):
    """Insert suppliers into database"""
    with conn.cursor() as cur:
        query = """
            INSERT INTO suppliers 
            (supplier_id, supplier_name, contact_email, contact_phone, address, 
             country, default_lead_time_days, is_active)
            VALUES %s
            ON CONFLICT (supplier_id) DO NOTHING
        """
        values = [
            (s['supplier_id'], s['supplier_name'], s['contact_email'], s['contact_phone'],
             s['address'], s['country'], s['default_lead_time_days'], s['is_active'])
            for s in suppliers
        ]
        execute_values(cur, query, values)
        conn.commit()
        print(f"✓ Inserted {len(suppliers)} suppliers")

def insert_categories(conn):
    """Insert product categories"""
    with conn.cursor() as cur:
        query = """
            INSERT INTO product_categories (category_id, category_name, parent_category_id, description)
            VALUES %s
            ON CONFLICT (category_id) DO NOTHING
        """
        execute_values(cur, query, GROCERY_CATEGORIES)
        conn.commit()
        print(f"✓ Inserted {len(GROCERY_CATEGORIES)} categories")

def insert_warehouses(conn):
    """Insert warehouses"""
    with conn.cursor() as cur:
        query = """
            INSERT INTO warehouses (warehouse_id, warehouse_name, city, location, capacity_cubic_meters, is_active)
            VALUES %s
            ON CONFLICT (warehouse_id) DO NOTHING
        """
        values = [
            (wh[0], wh[1], wh[2], wh[3], random.uniform(500, 2000), True)
            for wh in MOROCCAN_CITIES
        ]
        execute_values(cur, query, values)
        conn.commit()
        print(f"✓ Inserted {len(MOROCCAN_CITIES)} warehouses")

def insert_products(conn, products):
    """Insert products"""
    with conn.cursor() as cur:
        query = """
            INSERT INTO products 
            (sku, product_name, product_description, category_id, supplier_id, 
             unit_of_measure, unit_price, barcode, is_perishable, shelf_life_days, 
             weight_kg, is_active)
            VALUES %s
            ON CONFLICT (sku) DO NOTHING
        """
        values = [
            (p['sku'], p['product_name'], p['product_description'], p['category_id'],
             p['supplier_id'], p['unit_of_measure'], p['unit_price'], p['barcode'],
             p['is_perishable'], p['shelf_life_days'], p['weight_kg'], p['is_active'])
            for p in products
        ]
        execute_values(cur, query, values)
        conn.commit()
        print(f"✓ Inserted {len(products)} products")

def insert_replenishment_rules(conn, rules):
    """Insert replenishment rules"""
    with conn.cursor() as cur:
        query = """
            INSERT INTO replenishment_rules 
            (sku, supplier_id, moq, pack_size, case_size, lead_time_days, 
             order_multiple, max_order_quantity, ordering_calendar, effective_from, 
             effective_to, notes)
            VALUES %s
            ON CONFLICT (sku, supplier_id, effective_from) DO NOTHING
        """
        values = [
            (r['sku'], r['supplier_id'], r['moq'], r['pack_size'], r['case_size'],
             r['lead_time_days'], r['order_multiple'], r['max_order_quantity'],
             r['ordering_calendar'], r['effective_from'], r['effective_to'], r['notes'])
            for r in rules
        ]
        execute_values(cur, query, values)
        conn.commit()
        print(f"✓ Inserted {len(rules)} replenishment rules")

def insert_safety_stock(conn, safety_stocks):
    """Insert safety stock levels"""
    with conn.cursor() as cur:
        query = """
            INSERT INTO safety_stock 
            (sku, warehouse_id, safety_stock_quantity, reorder_point, max_stock_level,
             calculation_method, last_reviewed_date, review_frequency_days, notes)
            VALUES %s
            ON CONFLICT (sku, warehouse_id) DO NOTHING
        """
        values = [
            (ss['sku'], ss['warehouse_id'], ss['safety_stock_quantity'], ss['reorder_point'],
             ss['max_stock_level'], ss['calculation_method'], ss['last_reviewed_date'],
             ss['review_frequency_days'], ss['notes'])
            for ss in safety_stocks
        ]
        execute_values(cur, query, values)
        conn.commit()
        print(f"✓ Inserted {len(safety_stocks)} safety stock records")

# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    """Main execution function"""
    print("=" * 60)
    print("PROCUREMENT SYSTEM - MASTER DATA GENERATOR")
    print("=" * 60)
    
    # Generate data
    print("\n[1/6] Generating suppliers...")
    suppliers = generate_suppliers(NUM_SUPPLIERS)
    
    print("[2/6] Generating products...")
    products = generate_products(NUM_PRODUCTS, suppliers)
    
    print("[3/6] Generating replenishment rules...")
    rules = generate_replenishment_rules(products)
    
    print("[4/6] Generating safety stock levels...")
    safety_stocks = generate_safety_stock(products, MOROCCAN_CITIES)
    
    # Connect to database
    print("\n[5/6] Connecting to PostgreSQL...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✓ Connected to database")
        
        # Insert data
        print("\n[6/6] Inserting data into database...")
        insert_categories(conn)
        insert_warehouses(conn)
        insert_suppliers(conn, suppliers)
        insert_products(conn, products)
        insert_replenishment_rules(conn, rules)
        insert_safety_stock(conn, safety_stocks)
        
        conn.close()
        print("\n" + "=" * 60)
        print("✓ SUCCESS: All master data has been generated and inserted!")
        print("=" * 60)
        
        # Summary
        print("\nSUMMARY:")
        print(f"  • Suppliers: {NUM_SUPPLIERS}")
        print(f"  • Categories: {len(GROCERY_CATEGORIES)}")
        print(f"  • Warehouses: {len(MOROCCAN_CITIES)}")
        print(f"  • Products: {NUM_PRODUCTS}")
        print(f"  • Replenishment Rules: {len(rules)}")
        print(f"  • Safety Stock Records: {len(safety_stocks)}")
        
    except psycopg2.Error as e:
        print(f"\n✗ DATABASE ERROR: {e}")
        print("\nMake sure PostgreSQL is running and the database exists.")
        print("You can create it with: CREATE DATABASE procurement_db;")
    
    except Exception as e:
        print(f"\n✗ ERROR: {e}")

if __name__ == "__main__":
    main()