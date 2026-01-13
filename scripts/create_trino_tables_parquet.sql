-- ============================================================
-- CRÉATION DES TABLES TRINO AVEC FORMAT PARQUET
-- ============================================================

-- Supprimer les anciennes tables si elles existent
DROP TABLE IF EXISTS hive.orders.daily_orders;
DROP TABLE IF EXISTS hive.stock.daily_stock;
DROP TABLE IF EXISTS hive.processed.aggregated_orders;
DROP TABLE IF EXISTS hive.processed.net_demand;

-- Supprimer les schémas et les recréer
DROP SCHEMA IF EXISTS hive.orders CASCADE;
DROP SCHEMA IF EXISTS hive.stock CASCADE;
DROP SCHEMA IF EXISTS hive.processed CASCADE;

CREATE SCHEMA IF NOT EXISTS hive.orders;
CREATE SCHEMA IF NOT EXISTS hive.stock;
CREATE SCHEMA IF NOT EXISTS hive.processed;

-- ============================================================
-- TABLES EXTERNES (pointent vers HDFS Parquet)
-- ============================================================

-- Table des commandes (format Parquet)
CREATE TABLE hive.orders.daily_orders (
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
    external_location = 'hdfs://namenode:9000/parquet/orders/'
);

-- Table des stocks (format Parquet)
CREATE TABLE hive.stock.daily_stock (
    snapshot_date VARCHAR,
    warehouse_id VARCHAR,
    sku VARCHAR,
    available_stock INTEGER,
    reserved_stock INTEGER,
    free_stock INTEGER
)
WITH (
    format = 'PARQUET',
    external_location = 'hdfs://namenode:9000/parquet/stock/'
);

-- ============================================================
-- TABLES MANAGED (données traitées, stockées par Trino)
-- ============================================================

-- Table des commandes agrégées
CREATE TABLE hive.processed.aggregated_orders (
    order_date VARCHAR,
    sku VARCHAR,
    total_quantity BIGINT,
    num_orders BIGINT,
    total_revenue DOUBLE
)
WITH (
    format = 'PARQUET'
);

-- Table du net demand
CREATE TABLE hive.processed.net_demand (
    calculation_date VARCHAR,
    sku VARCHAR,
    total_demand BIGINT,
    available_stock BIGINT,
    reserved_stock BIGINT,
    safety_stock INTEGER,
    net_demand BIGINT,
    supplier_id VARCHAR,
    minimum_order_qty INTEGER,
    pack_size INTEGER,
    final_order_qty BIGINT
)
WITH (
    format = 'PARQUET'
);

-- Vérifier les tables
SHOW TABLES IN hive.orders;
SHOW TABLES IN hive.stock;
SHOW TABLES IN hive.processed;