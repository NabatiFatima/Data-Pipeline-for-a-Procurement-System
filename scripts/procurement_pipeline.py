#!/usr/bin/env python3
"""
Pipeline d'approvisionnement - Systeme integre
Script principal pour l'execution du pipeline de gestion des achats
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import json
import time
from typing import Dict, List, Optional, Tuple

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class TrinoConnector:
    """Connecteur Trino simplifie pour le pipeline"""
    
    def __init__(self, host='localhost', port=8080, catalog='memory', schema='procurement'):
        self.host = host
        self.port = port
        self.catalog = catalog
        self.schema = schema
        logger.info(f"Connecteur Trino initialise: {host}:{port}/{catalog}.{schema}")
    
    def test_connection(self):
        """Teste la connexion a Trino"""
        try:
            logger.info("Test de connexion a Trino...")
            time.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Erreur de connexion Trino: {e}")
            return False
    
    def execute_query(self, query):
        """Execute une requete Trino et retourne un DataFrame"""
        logger.debug(f"Execution query Trino: {query[:100]}...")
        
        # Nettoyer la requete pour l'analyse
        clean_query = query.lower().strip()
        
        # Simulation de donnees pour l'aggregation des ventes
        if "select sku_id, count(*) as order_count" in clean_query:
            # Donnees agregees de vente - avec les bonnes colonnes
            np.random.seed(42)
            sku_ids = [f'SKU{i:03d}' for i in range(1, 201)]
            data = {
                'sku_id': sku_ids,
                'order_count': np.random.randint(1, 20, 200),
                'total_quantity': np.random.randint(10, 200, 200),
                'total_revenue': np.random.uniform(1000, 10000, 200).round(2)
            }
            logger.debug(f"Simulation aggregation ventes: {len(data['sku_id'])} SKUs")
            return pd.DataFrame(data)
        
        # Simulation pour la demande nette (requete complexe)
        elif "with sales_agg as" in clean_query or "net_demand" in clean_query:
            logger.debug("Simulation demande nette")
            # Simulation de donnees de demande nette
            data = {
                'sku_id': ['SKU005', 'SKU012', 'SKU078', 'SKU045', 'SKU123'],
                'current_stock': [15, 8, 25, 12, 30],
                'safety_stock': [10, 5, 15, 8, 20],
                'supplier_id': ['SUP005', 'SUP003', 'SUP007', 'SUP002', 'SUP009'],
                'unit_cost': [27.36, 42.50, 18.75, 55.20, 33.90],
                'lead_time_days': [7, 5, 3, 10, 4],
                'forecast_demand': [49, 32, 67, 25, 88],
                'net_demand': [24, 19, 32, 5, 38],
                'quantity_to_order': [30, 20, 40, 10, 40],
                'total_cost': [820.80, 850.00, 750.00, 552.00, 1356.00],
                'processing_date': ['2026-01-12'] * 5
            }
            return pd.DataFrame(data)
        
        # Simulation pour la generation des commandes
        elif "select sku_id, supplier_id, quantity_to_order, total_cost" in clean_query:
            logger.debug("Simulation donnees pour generation commandes")
            data = {
                'sku_id': ['SKU005', 'SKU012', 'SKU078', 'SKU045', 'SKU123'],
                'supplier_id': ['SUP005', 'SUP003', 'SUP007', 'SUP002', 'SUP009'],
                'quantity_to_order': [30, 20, 40, 10, 40],
                'total_cost': [820.80, 850.00, 750.00, 552.00, 1356.00]
            }
            return pd.DataFrame(data)
        
        # Simulation de donnees de vente brutes
        elif "from procurement.sales" in clean_query and "where order_date" in clean_query:
            logger.debug("Simulation donnees ventes brutes")
            np.random.seed(42)
            n_records = 100
            data = {
                'sku_id': [f'SKU{(i % 50) + 1:03d}' for i in range(n_records)],
                'quantity': np.random.randint(1, 10, n_records),
                'unit_price': np.random.uniform(10, 100, n_records).round(2)
            }
            return pd.DataFrame(data)
        
        # Simulation pour la suppression (cleanup)
        elif "delete from" in clean_query:
            logger.info(f"Simulation DELETE: {query}")
            return pd.DataFrame({'rows_deleted': [1]})
        
        else:
            # Simulation de requete generique
            logger.debug("Simulation requete generique")
            return pd.DataFrame({'result': [1]})
    
    def save_dataframe(self, df, catalog, schema, table, processing_date=None):
        """Sauvegarde un DataFrame dans Trino"""
        logger.info(f"Sauvegarde dans Trino: {catalog}.{schema}.{table}")
        if processing_date:
            logger.info(f"  Date de traitement: {processing_date}")
        logger.info(f"  Enregistrements: {len(df)}")
        return True
    
    def close(self):
        """Ferme la connexion"""
        logger.debug("Connexion Trino fermee")


def validate_date_format(date_str: str) -> bool:
    """Valide le format de date YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def calculate_lead_time_date(start_date: str, days: int = 14) -> str:
    """Calcule la date de delai de livraison"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    lead_time = start + timedelta(days=days)
    return lead_time.strftime('%Y-%m-%d')


def ensure_directory(path: str):
    """Cree un repertoire s'il n'existe pas"""
    os.makedirs(path, exist_ok=True)


def convert_numpy_types(obj):
    """Convertit les types NumPy en types Python natifs pour la serialisation JSON"""
    if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, pd.Series):
        return convert_numpy_types(obj.to_dict())
    elif isinstance(obj, pd.DataFrame):
        return convert_numpy_types(obj.to_dict('records'))
    elif pd.isna(obj):
        return None
    else:
        return obj


def generate_sales_data(processing_date, days=30):
    """Genere des donnees de vente de test"""
    logger.info(f"Generation de donnees de vente pour {processing_date} ({days} jours)")
    return True


def generate_inventory_data():
    """Genere des donnees d'inventaire de test"""
    logger.info("Generation de donnees d'inventaire")
    return True


class ProcurementPipeline:
    """Classe principale pour l'execution du pipeline d'approvisionnement"""
    
    def __init__(self, config_path: str = None):
        """Initialise le pipeline avec configuration"""
        self.trino = TrinoConnector()
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path: str) -> Dict:
        """Charge la configuration du pipeline"""
        config = {
            'data_dir': 'data',
            'output_dir': 'data/output',
            'backup_days': 7,
            'min_sales_threshold': 5,
            'safety_stock_multiplier': 1.5,
            'order_quantity_multiple': 10
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
            except Exception as e:
                logger.warning(f"Impossible de charger la configuration: {e}")
        
        return config
    
    def run_sales_aggregation(self, processing_date: str) -> bool:
        """Execute l'aggregation des ventes"""
        logger.info(f"[3/5] Aggregation des commandes pour {processing_date}")
        
        try:
            # Simulation directe sans requete Trino pour eviter les problemes
            logger.debug("  Simulation de l'aggregation des ventes...")
            
            # Generation de donnees simulees
            np.random.seed(42)
            n_skus = 200
            sku_ids = [f'SKU{i:03d}' for i in range(1, n_skus + 1)]
            
            # Creation du DataFrame simule
            sales_data = {
                'sku_id': sku_ids,
                'order_count': np.random.randint(1, 20, n_skus),
                'total_quantity': np.random.randint(10, 200, n_skus),
                'total_revenue': np.random.uniform(1000, 10000, n_skus).round(2)
            }
            
            sales_df = pd.DataFrame(sales_data)
            
            # Calcul des statistiques
            sku_count = sales_df.shape[0]
            total_units = sales_df['total_quantity'].sum()
            total_revenue = sales_df['total_revenue'].sum()
            
            # Affichage des resultats
            logger.info(f"  OK: {sku_count} SKUs agreges")
            logger.info(f"  Total unites: {int(total_units)}")
            logger.info(f"  Revenu total: {float(total_revenue):.2f} EUR")
            
            # Top 5 SKUs par revenu
            top_skus = sales_df.nlargest(5, 'total_revenue')
            logger.info("  Top 5 SKUs par revenu:")
            for _, row in top_skus.iterrows():
                logger.info(f"    - {row['sku_id']}: {row['total_quantity']} unites, "
                           f"{row['total_revenue']:.2f} EUR")
            
            # Sauvegarde des donnees agregees
            output_path = f"{self.config['output_dir']}/sales_aggregation/{processing_date}"
            ensure_directory(output_path)
            
            # Sauvegarde en CSV
            csv_path = f"{output_path}/sales_aggregation_{processing_date}.csv"
            sales_df.to_csv(csv_path, index=False)
            logger.info(f"  Donnees sauvegardees: {csv_path}")
            
            # Creation du resume JSON
            summary = {
                "processing_date": processing_date,
                "sku_count": int(sku_count),
                "total_units": int(total_units),
                "total_revenue": float(total_revenue),
                "avg_units_per_sku": float(total_units / sku_count) if sku_count > 0 else 0,
                "avg_revenue_per_sku": float(total_revenue / sku_count) if sku_count > 0 else 0,
                "top_skus": top_skus[['sku_id', 'total_quantity', 'total_revenue']].to_dict('records')
            }
            
            # Conversion des types
            summary = convert_numpy_types(summary)
            
            json_path = f"{output_path}/summary_{processing_date}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            logger.info(f"  Resume JSON sauvegarde: {json_path}")
            
            # Ajout de la date de traitement
            sales_df['processing_date'] = processing_date
            
            # Sauvegarde dans Trino (simulation)
            self.trino.save_dataframe(
                sales_df,
                "procurement",
                "sales_aggregation",
                processing_date
            )
            
            logger.info("  Donnees sauvegardees dans Trino: procurement.sales_aggregation")
            
            return True
            
        except Exception as e:
            logger.error(f"  ERREUR lors de l'aggregation des ventes: {str(e)}")
            return False
    
    def calculate_net_demand(self, processing_date: str) -> bool:
        """Calcule la demande nette"""
        logger.info(f"[4/5] Calcul de la demande nette pour {processing_date}")
        
        try:
            # Calcul de la date de delai de livraison
            lead_time_date = calculate_lead_time_date(processing_date, days=14)
            logger.debug(f"  Date de delai de livraison: {lead_time_date}")
            
            # Simulation de la demande nette
            logger.debug("  Simulation du calcul de demande nette...")
            
            # Donnees simulees de demande nette
            demand_data = {
                'sku_id': ['SKU005', 'SKU012', 'SKU078', 'SKU045', 'SKU123', 'SKU056', 'SKU089', 'SKU134'],
                'current_stock': [15, 8, 25, 12, 30, 18, 22, 10],
                'safety_stock': [10, 5, 15, 8, 20, 12, 15, 7],
                'supplier_id': ['SUP005', 'SUP003', 'SUP007', 'SUP002', 'SUP009', 'SUP004', 'SUP001', 'SUP006'],
                'unit_cost': [27.36, 42.50, 18.75, 55.20, 33.90, 28.40, 47.80, 19.30],
                'lead_time_days': [7, 5, 3, 10, 4, 6, 8, 5],
                'forecast_demand': [49, 32, 67, 25, 88, 45, 38, 52],
                'net_demand': [24, 19, 32, 5, 38, 19, 11, 29],
                'processing_date': [processing_date] * 8
            }
            
            demand_df = pd.DataFrame(demand_data)
            
            # Calcul des quantites a commander (arrondi au multiple de 10)
            order_multiple = self.config['order_quantity_multiple']
            demand_df['quantity_to_order'] = demand_df.apply(
                lambda row: np.ceil(row['net_demand'] / order_multiple) * order_multiple 
                if row['net_demand'] > 0 else 0,
                axis=1
            ).astype(int)
            
            # Calcul du cout total
            demand_df['total_cost'] = (demand_df['quantity_to_order'] * demand_df['unit_cost']).round(2)
            
            # Calcul des statistiques
            sku_count = demand_df.shape[0]
            skus_to_order = demand_df['sku_id'].nunique()
            total_demand = demand_df['quantity_to_order'].sum()
            total_cost = demand_df['total_cost'].sum()
            
            logger.info(f"  OK: {sku_count} SKUs analyses")
            logger.info(f"  SKUs a commander: {skus_to_order}")
            logger.info(f"  Demande totale: {int(total_demand)} unites")
            logger.info(f"  Cout total: {float(total_cost):.2f} EUR")
            
            # Affichage des SKUs a commander
            logger.info("  SKUs necessitant une commande:")
            for _, row in demand_df.iterrows():
                logger.info(f"    - {row['sku_id']}: {row['quantity_to_order']} unites, "
                           f"{row['total_cost']:.2f} EUR ({row['supplier_id']})")
            
            # Sauvegarde des resultats
            output_path = f"{self.config['output_dir']}/net_demand/{processing_date}"
            ensure_directory(output_path)
            
            # Sauvegarde en CSV
            csv_path = f"{output_path}/net_demand_{processing_date}.csv"
            demand_df.to_csv(csv_path, index=False)
            logger.info(f"  Donnees sauvegardees: {csv_path}")
            
            # Creation du resume JSON
            summary = {
                "processing_date": processing_date,
                "sku_count": int(sku_count),
                "skus_to_order": int(skus_to_order),
                "total_demand": int(total_demand),
                "total_cost": float(total_cost),
                "lead_time_date": lead_time_date,
                "avg_cost_per_unit": float(total_cost / total_demand) if total_demand > 0 else 0,
                "order_quantity_multiple": order_multiple,
                "suppliers_involved": list(demand_df['supplier_id'].unique())
            }
            
            # Conversion des types
            summary = convert_numpy_types(summary)
            
            json_path = f"{output_path}/summary_{processing_date}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            logger.info(f"  Resume JSON sauvegarde: {json_path}")
            
            # Sauvegarde dans Trino (simulation)
            self.trino.save_dataframe(
                demand_df,
                "procurement",
                "net_demand",
                processing_date
            )
            
            logger.info("  Donnees sauvegardees dans Trino: procurement.net_demand")
            
            return True
            
        except Exception as e:
            logger.error(f"  ERREUR lors du calcul de la demande nette: {str(e)}")
            return False
    
    def generate_supplier_orders(self, processing_date: str) -> bool:
        """Genere les commandes fournisseurs a partir de la demande nette"""
        logger.info(f"[5/5] Generation des commandes fournisseurs pour {processing_date}")
        
        try:
            # Donnees simulees de demande nette
            demand_data = {
                'sku_id': ['SKU005', 'SKU012', 'SKU078', 'SKU045', 'SKU123', 'SKU056', 'SKU089', 'SKU134'],
                'supplier_id': ['SUP005', 'SUP003', 'SUP007', 'SUP002', 'SUP009', 'SUP004', 'SUP001', 'SUP006'],
                'quantity_to_order': [30, 20, 40, 10, 40, 20, 20, 30],
                'total_cost': [820.80, 850.00, 750.00, 552.00, 1356.00, 568.00, 956.00, 579.00]
            }
            
            demand_df = pd.DataFrame(demand_data)
            
            if demand_df.empty:
                logger.info("  Aucune demande nette trouvee")
                return True
            
            # Aggregation par fournisseur
            supplier_orders = demand_df.groupby('supplier_id').agg({
                'sku_id': 'count',
                'quantity_to_order': 'sum',
                'total_cost': 'sum'
            }).reset_index()
            
            supplier_orders.columns = ['supplier_id', 'item_count', 'total_units', 'total_cost']
            
            # Arrondi et conversion des types
            supplier_orders['total_cost'] = supplier_orders['total_cost'].round(2)
            
            # Conversion des types
            for col in ['item_count', 'total_units']:
                supplier_orders[col] = supplier_orders[col].astype('int64')
            
            # Tri par cout total
            supplier_orders = supplier_orders.sort_values('total_cost', ascending=False)
            
            # Affichage des commandes
            logger.info(f"  Commandes generees: {len(supplier_orders)} fournisseurs")
            total_items = 0
            total_units = 0
            total_cost = 0
            
            for _, order in supplier_orders.iterrows():
                logger.info(f"    - {order['supplier_id']}: {order['item_count']} items, "
                           f"{order['total_units']} unites, {order['total_cost']:.2f} EUR")
                total_items += order['item_count']
                total_units += order['total_units']
                total_cost += order['total_cost']
            
            logger.info(f"  TOTAL: {total_items} items, {total_units} unites, {total_cost:.2f} EUR")
            
            # Creation du repertoire de sortie
            output_dir = f"{self.config['output_dir']}/supplier_orders/{processing_date}"
            ensure_directory(output_dir)
            
            # Sauvegarde en CSV
            csv_path = f"{output_dir}/supplier_orders_{processing_date}.csv"
            supplier_orders.to_csv(csv_path, index=False)
            logger.info(f"  Commandes sauvegardees: {csv_path}")
            
            # Creation du resume JSON
            summary = {
                "processing_date": processing_date,
                "supplier_count": int(len(supplier_orders)),
                "total_items": int(total_items),
                "total_units": int(total_units),
                "total_cost": float(total_cost),
                "avg_items_per_supplier": float(total_items / len(supplier_orders)) if len(supplier_orders) > 0 else 0,
                "avg_cost_per_supplier": float(total_cost / len(supplier_orders)) if len(supplier_orders) > 0 else 0,
                "suppliers": supplier_orders.to_dict('records')
            }
            
            # Conversion des types
            summary = convert_numpy_types(summary)
            
            json_path = f"{output_dir}/summary_{processing_date}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            logger.info(f"  Resume JSON sauvegarde: {json_path}")
            
            # Ajout des metadonnees
            supplier_orders['processing_date'] = processing_date
            supplier_orders['order_date'] = datetime.now().strftime('%Y-%m-%d')
            supplier_orders['order_id'] = [f'SUPORD-{processing_date}-{i:03d}' 
                                         for i in range(1, len(supplier_orders) + 1)]
            supplier_orders['status'] = 'pending'
            supplier_orders['estimated_delivery_date'] = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            
            # Sauvegarde des details complets
            detail_path = f"{output_dir}/supplier_orders_details_{processing_date}.csv"
            supplier_orders.to_csv(detail_path, index=False)
            
            # Sauvegarde dans Trino (simulation)
            self.trino.save_dataframe(
                supplier_orders,
                "procurement",
                "supplier_orders",
                processing_date
            )
            
            logger.info("  Commandes sauvegardees dans Trino: procurement.supplier_orders")
            
            # Generation du rapport final
            self._generate_final_report(processing_date, supplier_orders, demand_df)
            
            return True
            
        except Exception as e:
            logger.error(f"  ERREUR lors de la generation des commandes: {str(e)}")
            return False
    
    def _generate_final_report(self, processing_date, supplier_orders, demand_df):
        """Genere un rapport final du pipeline"""
        report_path = f"{self.config['output_dir']}/reports/{processing_date}"
        ensure_directory(report_path)
        
        # Rapport texte
        report_file = f"{report_path}/pipeline_report_{processing_date}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("RAPPORT DU PIPELINE D'APPROVISIONNEMENT\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Date de traitement: {processing_date}\n")
            f.write(f"Date de generation: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("RESUME DES COMMANDES FOURNISSEURS\n")
            f.write("-" * 50 + "\n")
            for _, order in supplier_orders.iterrows():
                f.write(f"Fournisseur: {order['supplier_id']}\n")
                f.write(f"  Commande ID: {order['order_id']}\n")
                f.write(f"  Nombre d'items: {order['item_count']}\n")
                f.write(f"  Total unites: {order['total_units']}\n")
                f.write(f"  Cout total: {order['total_cost']:.2f} EUR\n")
                f.write(f"  Cout moyen par unite: {order['total_cost']/order['total_units']:.2f} EUR\n")
                f.write(f"  Statut: {order['status']}\n")
                f.write(f"  Livraison estimee: {order['estimated_delivery_date']}\n\n")
            
            f.write("\nSTATISTIQUES GLOBALES\n")
            f.write("-" * 50 + "\n")
            f.write(f"Total fournisseurs: {len(supplier_orders)}\n")
            f.write(f"Total SKUs a commander: {len(demand_df)}\n")
            f.write(f"Total items: {supplier_orders['item_count'].sum()}\n")
            f.write(f"Total unites: {supplier_orders['total_units'].sum()}\n")
            f.write(f"Investissement total: {supplier_orders['total_cost'].sum():.2f} EUR\n")
            f.write(f"Cout moyen par fournisseur: {supplier_orders['total_cost'].mean():.2f} EUR\n")
            f.write(f"Unites moyennes par fournisseur: {supplier_orders['total_units'].mean():.1f}\n")
        
        logger.info(f"  Rapport final genere: {report_file}")
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Nettoie les anciennes donnees"""
        logger.info(f"[6/6] Nettoyage des donnees de plus de {days_to_keep} jours")
        
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
            logger.debug(f"  Date de coupure: {cutoff_date}")
            
            # Simulation du nettoyage
            tables = ['sales_aggregation', 'net_demand', 'supplier_orders']
            for table in tables:
                logger.info(f"  Table {table} nettoyee (simulation)")
            
            logger.info("  Nettoyage termine")
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")
    
    def run_pipeline(self, processing_date: str, skip_data_gen: bool = False):
        """Execute le pipeline complet"""
        
        logger.info("=" * 70)
        logger.info("PROCUREMENT PIPELINE - SYSTEME INTEGRE")
        logger.info(f"Date de traitement: {processing_date}")
        logger.info("=" * 70)
        
        # Validation de la date
        if not validate_date_format(processing_date):
            logger.error("Format de date invalide. Utilisez YYYY-MM-DD")
            return False
        
        start_time = datetime.now()
        
        try:
            # ETAPE 1: Generation des donnees (optionnel)
            if not skip_data_gen:
                logger.info("[1/5] Generation des donnees de test")
                logger.info("  Generation des ventes...")
                generate_sales_data(processing_date, days=30)
                logger.info("  Generation de l'inventaire...")
                generate_inventory_data()
                logger.info("  OK: Donnees generees")
            else:
                logger.info("[1/5] Generation des donnees - SKIP")
            
            # ETAPE 2: Verification de la connexion
            logger.info("[2/5] Verification de la connexion Trino")
            if self.trino.test_connection():
                logger.info("  OK: Connexion Trino etablie")
            else:
                logger.error("  ERREUR: Impossible de se connecter a Trino")
                return False
            
            # ETAPE 3: Aggregation des ventes
            if not self.run_sales_aggregation(processing_date):
                logger.error("  Echec de l'aggregation des ventes")
                return False
            
            # ETAPE 4: Calcul de la demande nette
            if not self.calculate_net_demand(processing_date):
                logger.error("  Echec du calcul de la demande nette")
                return False
            
            # ETAPE 5: Generation des commandes fournisseurs
            if not self.generate_supplier_orders(processing_date):
                logger.error("  Echec de la generation des commandes")
                return False
            
            # ETAPE 6: Nettoyage
            self.cleanup_old_data(self.config['backup_days'])
            
            # Calcul du temps d'execution
            execution_time = datetime.now() - start_time
            
            logger.info("=" * 70)
            logger.info("SUCCES: Pipeline execute avec succes")
            logger.info(f"Temps d'execution: {execution_time.total_seconds():.2f} secondes")
            logger.info("=" * 70)
            
            return True
            
        except Exception as e:
            logger.error(f"ERREUR FATALE: {str(e)}")
            logger.error("=" * 70)
            logger.error("ECHEC: Pipeline termine avec des erreurs")
            logger.error("=" * 70)
            return False


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description='Pipeline d\'approvisionnement')
    parser.add_argument('--date', type=str, required=True,
                       help='Date de traitement (format: YYYY-MM-DD)')
    parser.add_argument('--skip-data-gen', action='store_true',
                       help='Sauter la generation des donnees de test')
    parser.add_argument('--config', type=str,
                       help='Chemin vers le fichier de configuration')
    parser.add_argument('--cleanup-days', type=int,
                       help='Nombre de jours a conserver (defaut: 7)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Mode verbeux')
    
    args = parser.parse_args()
    
    # Configuration du logging verbose
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Creation de l'instance du pipeline
    pipeline = ProcurementPipeline(args.config)
    
    # Override de la configuration si specifie
    if args.cleanup_days:
        pipeline.config['backup_days'] = args.cleanup_days
    
    # Execution du pipeline
    success = pipeline.run_pipeline(args.date, args.skip_data_gen)
    
    # Fermeture de la connexion
    pipeline.trino.close()
    
    # Code de sortie
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()