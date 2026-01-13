#!/usr/bin/env python3
"""
Diagnostic de l'accès aux données HDFS/Hive
"""

import subprocess
import pandas as pd
from datetime import datetime

def run_cmd(cmd, description):
    """Exécuter une commande"""
    print(f"\n🔍 {description}")
    print(f"   Commande: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"   ✅ Succès")
        if result.stdout.strip():
            print(f"   Résultat:\n{result.stdout[:500]}")
        return result.stdout
    else:
        print(f"   ❌ Erreur: {result.stderr[:200]}")
        return None

def main():
    print("="*80)
    print("DIAGNOSTIC COMPLET DE L'ACCÈS AUX DONNÉES HDFS/HIVE")
    print("="*80)
    
    # Date du jour pour les tests
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 1. Vérifier HDFS
    print("\n📂 ÉTAPE 1: Vérification HDFS")
    print("-"*40)
    
    # Vérifier la structure
    run_cmd('docker exec namenode hdfs dfs -ls -R /raw', "Structure HDFS /raw")
    run_cmd('docker exec namenode hdfs dfs -ls -R /raw/orders', "Contenu /raw/orders")
    run_cmd(f'docker exec namenode hdfs dfs -ls /raw/orders/{today}', f"Fichiers du {today}")
    
    # Compter les fichiers Parquet
    result = run_cmd(f'docker exec namenode hdfs dfs -ls /raw/orders/{today}/*.parquet | wc -l', "Nombre fichiers Parquet")
    if result:
        print(f"   📊 Nombre de fichiers Parquet: {result.strip()}")
    
    # 2. Vérifier les tables Hive
    print("\n🗄️  ÉTAPE 2: Vérification tables Hive")
    print("-"*40)
    
    # Vérifier les schémas et tables
    run_cmd('docker exec trino trino --catalog hive --execute "SHOW SCHEMAS"', "Schémas disponibles")
    run_cmd('docker exec trino trino --catalog hive --execute "SHOW TABLES IN orders"', "Tables dans orders")
    run_cmd('docker exec trino trino --catalog hive --execute "SHOW TABLES IN stock"', "Tables dans stock")
    run_cmd('docker exec trino trino --catalog hive --execute "SHOW TABLES IN processed"', "Tables dans processed")
    
    # 3. Tester l'accès aux données
    print("\n🔬 ÉTAPE 3: Test d'accès aux données")
    print("-"*40)
    
    # Tester avec différentes approches
    tests = [
        # Approche 1: Compter toutes les lignes
        ("SELECT COUNT(*) as total_rows FROM orders.daily_orders", "Total lignes dans daily_orders"),
        
        # Approche 2: Compter par date
        (f"SELECT COUNT(*) as today_count FROM orders.daily_orders WHERE order_date = '{today}'", f"Lignes pour {today}"),
        
        # Approche 3: Lister les dates disponibles
        ("SELECT DISTINCT order_date FROM orders.daily_orders ORDER BY order_date", "Dates disponibles"),
        
        # Approche 4: Voir un échantillon
        ("SELECT * FROM orders.daily_orders LIMIT 5", "Échantillon de données"),
        
        # Approche 5: Décrire la table
        ("DESCRIBE orders.daily_orders", "Structure de la table"),
    ]
    
    for sql, description in tests:
        cmd = f'docker exec trino trino --catalog hive --execute "{sql}"'
        run_cmd(cmd, description)
    
    # 4. Vérifier la structure des fichiers Parquet
    print("\n📊 ÉTAPE 4: Analyse des fichiers Parquet")
    print("-"*40)
    
    # Télécharger un fichier pour l'analyser
    temp_file = f"/tmp/sample_{today}.parquet"
    
    # Copier un fichier depuis HDFS
    run_cmd(f'docker exec namenode hdfs dfs -get /raw/orders/{today}/STORE01_orders.parquet {temp_file}', 
            f"Copie d'un fichier depuis HDFS")
    
    # Vérifier si le fichier existe et est lisible
    run_cmd(f'docker exec namenode ls -la {temp_file}', "Taille du fichier")
    
    # 5. Solutions possibles
    print("\n💡 ÉTAPE 5: Solutions possibles")
    print("-"*40)
    
    print("""
    Problèmes potentiels et solutions:
    
    1. Problème: Structure de dossiers non reconnue
       Solution: La table Hive doit pointer vers /raw/orders/ (pas /raw/orders/YYYY-MM-DD/)
    
    2. Problème: Schéma Parquet incompatible
       Solution: Vérifier que les colonnes dans le fichier Parquet correspondent à la table Hive
    
    3. Problème: Permissions HDFS
       Solution: Vérifier les permissions avec: hdfs dfs -ls -R /
    
    4. Problème: Format Parquet incompatible
       Solution: Regénérer les fichiers avec le bon schéma
    
    Actions recommandées:
    1. Re-créer les tables Hive avec external_location='/raw/orders/'
    2. Vérifier le schéma des fichiers Parquet
    3. Tester avec un petit fichier d'exemple
    """)
    
    # 6. Créer un fichier de test minimal
    print("\n🧪 ÉTAPE 6: Création d'un fichier de test")
    print("-"*40)
    
    # Créer un dataframe de test
    test_data = pd.DataFrame({
        'order_id': ['TEST-001', 'TEST-002'],
        'store_id': ['STORE01', 'STORE01'],
        'order_date': [today, today],
        'order_timestamp': [f'{today} 10:00:00', f'{today} 11:00:00'],
        'sku': ['SKU0001', 'SKU0002'],
        'quantity': [5, 3],
        'unit_price': [10.5, 15.0],
        'total_price': [52.5, 45.0]
    })
    
    # Sauvegarder localement
    test_file = f'./data/test/test_orders.parquet'
    import os
    os.makedirs('./data/test', exist_ok=True)
    test_data.to_parquet(test_file, index=False)
    print(f"   ✅ Fichier de test créé: {test_file}")
    
    # Upload vers HDFS
    run_cmd(f'docker cp {test_file} namenode:/tmp/test_orders.parquet', "Copie vers namenode")
    run_cmd(f'docker exec namenode hdfs dfs -mkdir -p /raw/test_orders/', "Création dossier test")
    run_cmd(f'docker exec namenode hdfs dfs -put -f /tmp/test_orders.parquet /raw/test_orders/', "Upload vers HDFS")
    
    # Créer une table de test
    sql = f"""
    CREATE TABLE IF NOT EXISTS orders.test_orders (
        order_id VARCHAR,
        store_id VARCHAR,
        order_date VARCHAR,
        order_timestamp VARCHAR,
        sku VARCHAR,
        quantity INTEGER,
        unit_price DOUBLE,
        total_price DOUBLE
    )
    WITH (
        format = 'PARQUET',
        external_location = 'hdfs://namenode:9000/raw/test_orders/'
    )
    """
    run_cmd(f'docker exec trino trino --catalog hive --execute "{sql}"', "Création table test")
    
    # Tester la table de test
    run_cmd('docker exec trino trino --catalog hive --execute "SELECT COUNT(*) FROM orders.test_orders"', 
            "Test de la table test_orders")
    
    print("\n" + "="*80)
    print("DIAGNOSTIC TERMINÉ")
    print("="*80)

if __name__ == "__main__":
    main()