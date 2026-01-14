#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PIPELINE PROCUREMENT - VERSION CORRIGÉE
Corrections:
1. Format JSON des commandes
2. Schema Trino (hive.procurement au lieu de hive.default)
3. Serialization JSON (Decimal)
"""

import os
import sys
import json
from decimal import Decimal
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from trino.dbapi import connect as trino_connect

# Force UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ============================================
# CONFIGURATION
# ============================================

TRINO_CONFIG = {
    'host': os.getenv('PRESTO_HOST', 'localhost'),
    'port': int(os.getenv('PRESTO_PORT', 8080)),
    'user': 'trino',
    'catalog': 'hive',
    'schema': 'procurement'  # FIX: schema correct
}

POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'procurement_db'),
    'user': os.getenv('POSTGRES_USER', 'procurement_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'procurement_pass')
}

HDFS_BASE = '/raw'  # FIX: Correspond au LOCATION des tables Trino

# FIX: JSON encoder pour Decimal
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

# ============================================
# PIPELINE
# ============================================

class ProcurementPipeline:
    
    def __init__(self, processing_date=None):
        self.processing_date = processing_date or (datetime.now().date() - timedelta(days=1))
        self.date_str = self.processing_date.strftime('%Y-%m-%d')
        
        print(f"\n{'='*70}")
        print(f"PROCUREMENT PIPELINE - {self.date_str}")
        print(f"{'='*70}\n")
        
        self.trino_conn = None
        self.pg_conn = None
        self.exceptions = []
        self.master_data = {}
    
    def log(self, msg, level='INFO'):
        prefix = {'INFO': '[INFO]', 'SUCCESS': '[OK]', 'WARNING': '[WARN]', 'ERROR': '[ERROR]'}
        print(f"{prefix.get(level, '[INFO]')} {msg}")
    
    def section(self, title):
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}\n")
    
    def connect_databases(self):
        self.section("CONNEXIONS")
        
        try:
            self.trino_conn = trino_connect(**TRINO_CONFIG)
            self.log("Trino OK", 'SUCCESS')
        except Exception as e:
            self.log(f"Erreur Trino: {e}", 'ERROR')
            return False
        
        try:
            self.pg_conn = psycopg2.connect(**POSTGRES_CONFIG)
            self.log("PostgreSQL OK", 'SUCCESS')
        except Exception as e:
            self.log(f"Erreur PostgreSQL: {e}", 'ERROR')
            return False
        
        return True
    
    def load_master_data(self):
        self.log("Chargement master data...")
        
        cursor = self.pg_conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                p.sku,
                p.product_name,
                p.supplier_id,
                s.supplier_name,
                COALESCE(rr.moq, 1) as moq,
                COALESCE(rr.pack_size, 1) as pack_size,
                COALESCE(rr.lead_time_days, 7) as lead_time_days,
                p.unit_price
            FROM products p
            LEFT JOIN suppliers s ON p.supplier_id = s.supplier_id
            LEFT JOIN replenishment_rules rr ON p.sku = rr.sku
            WHERE p.is_active = TRUE
        """)
        
        for row in cursor.fetchall():
            self.master_data[row['sku']] = dict(row)
        
        cursor.execute("""
            SELECT sku, SUM(safety_stock_quantity) as safety_stock
            FROM safety_stock GROUP BY sku
        """)
        
        for row in cursor.fetchall():
            if row['sku'] in self.master_data:
                self.master_data[row['sku']]['safety_stock'] = row['safety_stock'] or 0
        
        cursor.close()
        self.log(f"{len(self.master_data)} produits", 'SUCCESS')
        return True
    
    # FIX: Conversion commandes
    def step1_convert_to_parquet(self):
        self.section("CONVERSION PARQUET")
        
        orders_ok = self._convert_orders()
        stock_ok = self._convert_stock()
        
        if orders_ok and stock_ok:
            self.log("Conversion OK", 'SUCCESS')
            return True
        else:
            self.log("Conversion partielle", 'WARNING')
            return orders_ok or stock_ok
    
    def _convert_orders(self):
        self.log("Conversion commandes...")
        
        input_dir = Path(f'data/raw/orders/{self.date_str}')
        output_dir = Path(f'data/parquet/orders/{self.date_str}')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if not input_dir.exists():
            self.log(f"Dossier manquant: {input_dir}", 'ERROR')
            return False
        
        all_orders = []
        for json_file in input_dir.glob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # FIX: Format tableau JSON direct
                    if isinstance(data, list):
                        for order in data:
                            all_orders.append({
                                'order_id': order.get('order_id', ''),
                                'store_id': order.get('store_id', ''),
                                'order_date': order.get('order_date', self.date_str),
                                'order_timestamp': order.get('order_timestamp', ''),
                                'sku': order.get('sku', ''),
                                'quantity': int(order.get('quantity', 0)),
                                'unit_price': float(order.get('unit_price', 0)),
                                'total_price': float(order.get('total_price', 0))
                            })
                    
            except Exception as e:
                self.log(f"Erreur {json_file.name}: {e}", 'WARNING')
                continue
        
        if not all_orders:
            self.log("Aucune commande", 'ERROR')
            return False
        
        df = pd.DataFrame(all_orders)
        df['dt'] = self.date_str
        
        output_file = output_dir / 'orders.parquet'
        df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
        
        self.log(f"Commandes: {len(df)} lignes", 'SUCCESS')
        return True
    
    def _convert_stock(self):
        self.log("Conversion stocks...")
        
        input_dir = Path(f'data/raw/stock/{self.date_str}')
        output_dir = Path(f'data/parquet/stock/{self.date_str}')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if not input_dir.exists():
            self.log(f"Dossier manquant: {input_dir}", 'ERROR')
            return False
        
        all_stock = []
        for json_file in input_dir.glob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_stock.extend(data)
            except Exception as e:
                self.log(f"Erreur {json_file.name}: {e}", 'WARNING')
                continue
        
        if not all_stock:
            self.log("Aucun stock", 'ERROR')
            return False
        
        df = pd.DataFrame(all_stock)
        
        # Renommer colonnes pour schema Trino
        rename_map = {}
        if 'available_stock' in df.columns:
            rename_map['available_stock'] = 'available_quantity'
        if 'reserved_stock' in df.columns:
            rename_map['reserved_stock'] = 'reserved_quantity'
        
        if rename_map:
            df = df.rename(columns=rename_map)
        
        # Ajouter colonnes manquantes
        if 'available_quantity' not in df.columns:
            df['available_quantity'] = 0
        if 'reserved_quantity' not in df.columns:
            df['reserved_quantity'] = 0
        if 'in_transit_quantity' not in df.columns:
            df['in_transit_quantity'] = 0
        
        # Garder seulement les colonnes necessaires + dt
        df = df[['sku', 'available_quantity', 'reserved_quantity', 'in_transit_quantity']]
        df['dt'] = self.date_str
        
        output_file = output_dir / 'stock.parquet'
        df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
        
        self.log(f"Stocks: {len(df)} lignes", 'SUCCESS')
        return True
    
    def step2_upload_to_hdfs(self):
        self.section("UPLOAD HDFS")
        
        files = [
            (f'data/parquet/orders/{self.date_str}/orders.parquet', 
             f'{HDFS_BASE}/orders/dt={self.date_str}/orders.parquet'),
            (f'data/parquet/stock/{self.date_str}/stock.parquet', 
             f'{HDFS_BASE}/stock/dt={self.date_str}/stock.parquet')
        ]
        
        for local_file, hdfs_path in files:
            if not Path(local_file).exists():
                self.log(f"Fichier manquant: {local_file}", 'WARNING')
                continue
            
            try:
                # FIX: Convertir en chemin Unix pour HDFS
                hdfs_path_unix = hdfs_path.replace('\\', '/')
                hdfs_dir = str(Path(hdfs_path_unix).parent).replace('\\', '/')
                
                result = subprocess.run([
                    'docker', 'exec', 'namenode',
                    'hdfs', 'dfs', '-mkdir', '-p', hdfs_dir
                ], capture_output=True, text=True)
                
                if result.returncode != 0 and 'File exists' not in result.stderr:
                    self.log(f"Erreur mkdir: {result.stderr}", 'WARNING')
                
                # Supprimer l'ancien fichier
                subprocess.run([
                    'docker', 'exec', 'namenode',
                    'hdfs', 'dfs', '-rm', '-f', hdfs_path_unix
                ], capture_output=True)
                
                # Copier vers le conteneur
                tmp_file = f'/tmp/{Path(local_file).name}'
                result = subprocess.run([
                    'docker', 'cp', local_file, f'namenode:{tmp_file}'
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.log(f"Erreur docker cp: {result.stderr}", 'WARNING')
                    continue
                
                # Upload vers HDFS
                result = subprocess.run([
                    'docker', 'exec', 'namenode',
                    'hdfs', 'dfs', '-put', tmp_file, hdfs_dir + '/'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.log(f"Upload OK: {Path(local_file).name}", 'SUCCESS')
                    
                    # Verifier
                    check = subprocess.run([
                        'docker', 'exec', 'namenode',
                        'hdfs', 'dfs', '-test', '-e', hdfs_path_unix
                    ], capture_output=True)
                    
                    if check.returncode == 0:
                        self.log(f"  Fichier verifie dans HDFS", 'SUCCESS')
                    else:
                        self.log(f"  Fichier non trouve (normal si parquet multiple)", 'INFO')
                else:
                    self.log(f"Erreur HDFS put: {result.stderr}", 'WARNING')
                
            except Exception as e:
                self.log(f"Erreur upload: {e}", 'WARNING')
        
        # FIX: Synchroniser les partitions Trino
        self.log("Synchronisation des partitions Trino...")
        try:
            cursor = self.trino_conn.cursor()
            
            # Refresh partitions pour orders
            cursor.execute(f"CALL system.sync_partition_metadata('procurement', 'orders', 'FULL')")
            self.log("  Partitions orders synchronisees", 'SUCCESS')
            
            # Refresh partitions pour stock
            cursor.execute(f"CALL system.sync_partition_metadata('procurement', 'stock', 'FULL')")
            self.log("  Partitions stock synchronisees", 'SUCCESS')
            
            cursor.close()
        except Exception as e:
            self.log(f"  Erreur sync partitions: {e}", 'WARNING')
        
        return True
    
    # FIX: Schema Trino correct
    def step3_aggregate_with_trino(self):
        self.section("AGREGATION TRINO")
        
        cursor = self.trino_conn.cursor()
        
        # COMMANDES
        self.log("Agregation commandes...")
        try:
            cursor.execute(f"""
                SELECT 
                    sku,
                    SUM(quantity) as total_quantity,
                    COUNT(DISTINCT order_id) as num_orders,
                    AVG(unit_price) as avg_price
                FROM hive.procurement.orders
                WHERE dt = '{self.date_str}'
                GROUP BY sku
            """)
            
            orders_agg = {row[0]: {
                'total_quantity': row[1],
                'num_orders': row[2],
                'avg_price': row[3]
            } for row in cursor.fetchall()}
            
            self.log(f"{len(orders_agg)} SKUs commandes", 'SUCCESS')
            
        except Exception as e:
            self.log(f"Erreur commandes: {e}", 'ERROR')
            orders_agg = {}
        
        # STOCKS
        self.log("Agregation stocks...")
        try:
            cursor.execute(f"""
                SELECT 
                    sku,
                    SUM(available_quantity) as total_available,
                    SUM(reserved_quantity) as total_reserved,
                    SUM(in_transit_quantity) as total_in_transit
                FROM hive.procurement.stock
                WHERE dt = '{self.date_str}'
                GROUP BY sku
            """)
            
            stock_agg = {row[0]: {
                'available': row[1],
                'reserved': row[2],
                'in_transit': row[3]
            } for row in cursor.fetchall()}
            
            self.log(f"{len(stock_agg)} SKUs stocks", 'SUCCESS')
            
        except Exception as e:
            self.log(f"Erreur stocks: {e}", 'ERROR')
            stock_agg = {}
        
        cursor.close()
        return orders_agg, stock_agg
    
    def step4_calculate_net_demand(self, orders_agg, stock_agg):
        self.section("CALCUL NET DEMAND")
        
        results = []
        
        for sku, master in self.master_data.items():
            try:
                order_qty = orders_agg.get(sku, {}).get('total_quantity', 0)
                stock = stock_agg.get(sku, {})
                available = stock.get('available', 0)
                reserved = stock.get('reserved', 0)
                safety_stock = master.get('safety_stock', 0)
                
                net_stock = available - reserved
                net_demand = max(0, order_qty + safety_stock - net_stock)
                
                pack_size = master.get('pack_size', 1)
                if net_demand > 0:
                    order_qty_rounded = ((net_demand + pack_size - 1) // pack_size) * pack_size
                else:
                    order_qty_rounded = 0
                
                moq = master.get('moq', 0)
                if 0 < order_qty_rounded < moq:
                    order_qty_rounded = moq
                
                supplier_id = master.get('supplier_id')
                if not supplier_id and order_qty_rounded > 0:
                    continue
                
                if order_qty_rounded > 0:
                    # FIX: Convertir Decimal en float
                    unit_price = float(master.get('unit_price', 0))
                    
                    results.append({
                        'calculation_date': self.date_str,
                        'sku': sku,
                        'product_name': master.get('product_name', ''),
                        'supplier_id': supplier_id,
                        'supplier_name': master.get('supplier_name', ''),
                        'total_demand': int(order_qty),
                        'available_stock': int(available),
                        'reserved_stock': int(reserved),
                        'safety_stock': int(safety_stock),
                        'net_demand': int(net_demand),
                        'pack_size': int(pack_size),
                        'moq': int(moq),
                        'final_order_qty': int(order_qty_rounded),
                        'unit_price': unit_price,
                        'order_value': float(order_qty_rounded * unit_price)
                    })
            
            except Exception as e:
                self.exceptions.append(f"Erreur {sku}: {e}")
        
        total_units = sum(r['final_order_qty'] for r in results)
        total_value = sum(r['order_value'] for r in results)
        
        self.log(f"{len(results)} SKUs a reapprovisionner", 'SUCCESS')
        self.log(f"Total: {total_units} unites, {total_value:,.2f} EUR", 'INFO')
        
        return results
    
    # FIX: Serialization JSON
    def step5_generate_supplier_orders(self, net_demand_results):
        self.section("COMMANDES FOURNISSEURS")
        
        if not net_demand_results:
            self.log("Aucune commande", 'INFO')
            return True
        
        output_dir = Path(f'data/output/supplier_orders/{self.date_str}')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        suppliers = {}
        for item in net_demand_results:
            supplier_id = item['supplier_id']
            if supplier_id not in suppliers:
                suppliers[supplier_id] = []
            suppliers[supplier_id].append(item)
        
        for supplier_id, items in suppliers.items():
            order = {
                'order_header': {
                    'order_id': f"PO-{supplier_id}-{self.date_str}",
                    'supplier_id': supplier_id,
                    'supplier_name': items[0]['supplier_name'],
                    'order_date': self.date_str,
                    'generated_at': datetime.now().isoformat(),
                    'total_items': len(items),
                    'total_units': sum(i['final_order_qty'] for i in items),
                    'total_value': sum(i['order_value'] for i in items),
                    'status': 'PENDING'
                },
                'order_lines': [
                    {
                        'line_number': idx,
                        'sku': item['sku'],
                        'product_name': item['product_name'],
                        'order_quantity': item['final_order_qty'],
                        'pack_size': item['pack_size'],
                        'unit_price': item['unit_price'],
                        'line_value': item['order_value']
                    } for idx, item in enumerate(items, 1)
                ]
            }
            
            filename = output_dir / f"{supplier_id}_order_{self.date_str}.json"
            # FIX: Utiliser DecimalEncoder
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(order, f, indent=2, ensure_ascii=False, cls=DecimalEncoder)
            
            self.log(f"{supplier_id}: {len(items)} SKUs, {order['order_header']['total_units']} unites", 'SUCCESS')
        
        return True
    
    def step6_generate_report(self):
        self.section("RAPPORT")
        
        if self.exceptions:
            Path('data/logs').mkdir(parents=True, exist_ok=True)
            with open(f'data/logs/exceptions_{self.date_str}.json', 'w') as f:
                json.dump({'date': self.date_str, 'exceptions': self.exceptions}, f, indent=2)
            self.log(f"{len(self.exceptions)} exception(s)", 'WARNING')
        else:
            self.log("Aucune exception", 'SUCCESS')
        
        return True
    
    def run(self):
        start = datetime.now()
        
        try:
            if not self.connect_databases():
                return False
            if not self.load_master_data():
                return False
            
            if not self.step1_convert_to_parquet():
                self.log("Conversion echouee", 'ERROR')
                return False
            
            self.step2_upload_to_hdfs()
            
            orders_agg, stock_agg = self.step3_aggregate_with_trino()
            net_demand = self.step4_calculate_net_demand(orders_agg, stock_agg)
            self.step5_generate_supplier_orders(net_demand)
            self.step6_generate_report()
            
            duration = (datetime.now() - start).total_seconds()
            print(f"\n{'='*70}")
            print(f"[OK] PIPELINE TERMINE - {duration:.2f}s")
            print(f"{'='*70}\n")
            
            return True
            
        except Exception as e:
            self.log(f"ERREUR: {e}", 'ERROR')
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            if self.trino_conn:
                self.trino_conn.close()
            if self.pg_conn:
                self.pg_conn.close()

def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', type=str, help='Date YYYY-MM-DD')
    
    args = parser.parse_args()
    
    if args.date:
        processing_date = datetime.strptime(args.date, '%Y-%m-%d').date()
    else:
        processing_date = datetime.now().date() - timedelta(days=1)
    
    pipeline = ProcurementPipeline(processing_date=processing_date)
    success = pipeline.run()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()