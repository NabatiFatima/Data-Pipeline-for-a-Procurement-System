-- ============================================================
-- SCHEMA
-- ============================================================
DROP TABLE IF EXISTS hive.procurement.stock;

CREATE TABLE hive.procurement.stock (
    sku varchar,
    available_quantity integer,
    reserved_quantity integer,
    in_transit_quantity integer,
    dt varchar
)
WITH (
    format = 'PARQUET',
    external_location = 'hdfs://namenode:9000/raw/stock',
    partitioned_by = ARRAY['dt']
);
DROP TABLE IF EXISTS hive.procurement.orders;

CREATE TABLE hive.procurement.orders (
    order_id varchar,
    store_id varchar,
    order_date varchar,
    order_timestamp varchar,
    sku varchar,
    quantity integer,
    unit_price double,
    total_price double,
    dt varchar
)
WITH (
    format = 'PARQUET',
    external_location = 'hdfs://namenode:9000/raw/orders',
    partitioned_by = ARRAY['dt']
);
CALL "hive"."system"."sync_partition_metadata"('procurement', 'stock', 'FULL');
CALL "hive"."system"."sync_partition_metadata"('procurement', 'orders', 'FULL');
