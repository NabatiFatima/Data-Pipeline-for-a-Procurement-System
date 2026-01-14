-- ============================================================
-- SCHEMA
-- ============================================================
CREATE SCHEMA IF NOT EXISTS hive.procurement;

-- ============================================================
-- ORDERS (EXTERNAL)
-- ============================================================
CREATE TABLE IF NOT EXISTS hive.procurement.orders (
    order_id VARCHAR,
    store_id VARCHAR,
    order_date VARCHAR,
    order_timestamp VARCHAR,
    sku VARCHAR,
    quantity INTEGER,
    unit_price DOUBLE,
    total_price DOUBLE,
    dt VARCHAR
)
WITH (
    format = 'PARQUET',
    external_location = 'hdfs://namenode:9000/warehouse/procurement/orders/',
    partitioned_by = ARRAY['dt']
);

-- ============================================================
-- STOCK (EXTERNAL)
-- ============================================================
CREATE TABLE IF NOT EXISTS hive.procurement.stock (
    snapshot_date VARCHAR,
    warehouse_id VARCHAR,
    sku VARCHAR,
    available_quantity INTEGER,
    reserved_quantity INTEGER,
    in_transit_quantity INTEGER,
    dt VARCHAR
)
WITH (
    format = 'PARQUET',
    external_location = 'hdfs://namenode:9000/warehouse/procurement/stock/',
    partitioned_by = ARRAY['dt']
);
