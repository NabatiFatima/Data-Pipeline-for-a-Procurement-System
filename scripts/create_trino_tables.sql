-- ==============================================
-- TABLES EXTERNES TRINO POUR LE PIPELINE
-- ==============================================

-- Table des commandes brutes (external table pointant vers HDFS)
CREATE TABLE IF NOT EXISTS hive.orders.daily_orders (
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
    format = 'JSON',
    external_location = 'hdfs://namenode:9000/raw/orders/'
);

-- Table des stocks bruts (external table pointant vers HDFS)
CREATE TABLE IF NOT EXISTS hive.stock.daily_stock (
    snapshot_date VARCHAR,
    warehouse_id VARCHAR,
    sku VARCHAR,
    available_stock INTEGER,
    reserved_stock INTEGER,
    free_stock INTEGER
)
WITH (
    format = 'JSON',
    external_location = 'hdfs://namenode:9000/raw/stock/'
);

-- Table des commandes agrégées (managed table)
CREATE TABLE IF NOT EXISTS hive.processed.aggregated_orders (
    order_date VARCHAR,
    sku VARCHAR,
    total_quantity BIGINT,
    num_orders BIGINT,
    total_revenue DOUBLE
)
WITH (
    format = 'PARQUET',
    external_location = 'hdfs://namenode:9000/processed/aggregated_orders/'
);

-- Table du net demand (managed table)
CREATE TABLE IF NOT EXISTS hive.processed.net_demand (
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
    format = 'PARQUET',
    external_location = 'hdfs://namenode:9000/processed/net_demand/'
);