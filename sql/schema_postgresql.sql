-- ============================================================
-- PROCUREMENT SYSTEM - POSTGRESQL DATABASE SCHEMA
-- Phase 1: Master Data Tables
-- ============================================================

-- Drop existing tables (for clean reinstall)
DROP TABLE IF EXISTS safety_stock CASCADE;
DROP TABLE IF EXISTS replenishment_rules CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS suppliers CASCADE;
DROP TABLE IF EXISTS warehouses CASCADE;
DROP TABLE IF EXISTS product_categories CASCADE;

-- ============================================================
-- TABLE 1: SUPPLIERS (Fournisseurs)
-- ============================================================
CREATE TABLE suppliers (
    supplier_id VARCHAR(20) PRIMARY KEY,
    supplier_name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    address TEXT,
    country VARCHAR(100) DEFAULT 'Morocco',
    default_lead_time_days INTEGER DEFAULT 3,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE suppliers IS 'Catalog of all suppliers providing products';
COMMENT ON COLUMN suppliers.default_lead_time_days IS 'Default delivery time in days';

-- ============================================================
-- TABLE 2: PRODUCT_CATEGORIES (Catégories de produits)
-- ============================================================
CREATE TABLE product_categories (
    category_id VARCHAR(20) PRIMARY KEY,
    category_name VARCHAR(255) NOT NULL,
    parent_category_id VARCHAR(20),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_category_id) REFERENCES product_categories(category_id)
);

COMMENT ON TABLE product_categories IS 'Product classification hierarchy';

-- ============================================================
-- TABLE 3: WAREHOUSES (Entrepôts)
-- ============================================================
CREATE TABLE warehouses (
    warehouse_id VARCHAR(20) PRIMARY KEY,
    warehouse_name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    city VARCHAR(100),
    capacity_cubic_meters DECIMAL(10,2),
    manager_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE warehouses IS 'Physical storage locations';

-- ============================================================
-- TABLE 4: PRODUCTS (Master Data Produits)
-- ============================================================
CREATE TABLE products (
    sku VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    product_description TEXT,
    category_id VARCHAR(20),
    supplier_id VARCHAR(20) NOT NULL,
    unit_of_measure VARCHAR(20) DEFAULT 'UNIT',
    unit_price DECIMAL(10,2),
    barcode VARCHAR(50),
    is_perishable BOOLEAN DEFAULT FALSE,
    shelf_life_days INTEGER,
    weight_kg DECIMAL(8,3),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES product_categories(category_id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);

COMMENT ON TABLE products IS 'Master product catalog with supplier mappings';
COMMENT ON COLUMN products.unit_of_measure IS 'UNIT, KG, LITER, PIECE, etc.';
COMMENT ON COLUMN products.is_perishable IS 'TRUE for fresh products requiring special handling';

-- ============================================================
-- TABLE 5: REPLENISHMENT_RULES (Règles de réapprovisionnement)
-- ============================================================
CREATE TABLE replenishment_rules (
    rule_id SERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL,
    supplier_id VARCHAR(20) NOT NULL,
    moq INTEGER NOT NULL DEFAULT 1,
    pack_size INTEGER NOT NULL DEFAULT 1,
    case_size INTEGER,
    lead_time_days INTEGER NOT NULL DEFAULT 3,
    order_multiple INTEGER DEFAULT 1,
    max_order_quantity INTEGER,
    ordering_calendar VARCHAR(50) DEFAULT 'DAILY',
    effective_from DATE DEFAULT CURRENT_DATE,
    effective_to DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sku) REFERENCES products(sku),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
    CONSTRAINT unique_sku_supplier_effective UNIQUE (sku, supplier_id, effective_from)
);

COMMENT ON TABLE replenishment_rules IS 'Supplier-specific ordering constraints per product';
COMMENT ON COLUMN replenishment_rules.moq IS 'Minimum Order Quantity';
COMMENT ON COLUMN replenishment_rules.pack_size IS 'Units per pack/carton';
COMMENT ON COLUMN replenishment_rules.case_size IS 'Packs per case';
COMMENT ON COLUMN replenishment_rules.order_multiple IS 'Order must be multiple of this value';
COMMENT ON COLUMN replenishment_rules.ordering_calendar IS 'DAILY, MON_WED_FRI, etc.';

-- ============================================================
-- TABLE 6: SAFETY_STOCK (Stock de sécurité par SKU)
-- ============================================================
CREATE TABLE safety_stock (
    safety_stock_id SERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL,
    warehouse_id VARCHAR(20) NOT NULL,
    safety_stock_quantity INTEGER NOT NULL DEFAULT 0,
    reorder_point INTEGER,
    max_stock_level INTEGER,
    calculation_method VARCHAR(50) DEFAULT 'MANUAL',
    last_reviewed_date DATE,
    review_frequency_days INTEGER DEFAULT 30,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sku) REFERENCES products(sku),
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
    CONSTRAINT unique_sku_warehouse UNIQUE (sku, warehouse_id)
);

COMMENT ON TABLE safety_stock IS 'Safety stock levels per SKU per warehouse';
COMMENT ON COLUMN safety_stock.safety_stock_quantity IS 'Minimum stock to maintain';
COMMENT ON COLUMN safety_stock.reorder_point IS 'Trigger level for automatic reorder';
COMMENT ON COLUMN safety_stock.calculation_method IS 'MANUAL, STATISTICAL, FIXED_DAYS_SUPPLY';

-- ============================================================
-- INDEXES for Performance
-- ============================================================

-- Products indexes
CREATE INDEX idx_products_supplier ON products(supplier_id);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_active ON products(is_active) WHERE is_active = TRUE;

-- Replenishment rules indexes
CREATE INDEX idx_replenishment_sku ON replenishment_rules(sku);
CREATE INDEX idx_replenishment_supplier ON replenishment_rules(supplier_id);
CREATE INDEX idx_replenishment_effective ON replenishment_rules(effective_from, effective_to);

-- Safety stock indexes
CREATE INDEX idx_safety_stock_sku ON safety_stock(sku);
CREATE INDEX idx_safety_stock_warehouse ON safety_stock(warehouse_id);

-- ============================================================
-- VIEWS for Easy Queries
-- ============================================================

-- View: Complete product information with supplier and rules
CREATE OR REPLACE VIEW v_product_full_info AS
SELECT 
    p.sku,
    p.product_name,
    p.product_description,
    pc.category_name,
    s.supplier_id,
    s.supplier_name,
    s.contact_email,
    rr.moq,
    rr.pack_size,
    rr.case_size,
    rr.lead_time_days,
    rr.ordering_calendar,
    p.unit_price,
    p.is_perishable,
    p.is_active
FROM products p
LEFT JOIN product_categories pc ON p.category_id = pc.category_id
LEFT JOIN suppliers s ON p.supplier_id = s.supplier_id
LEFT JOIN replenishment_rules rr ON p.sku = rr.sku AND p.supplier_id = rr.supplier_id
WHERE p.is_active = TRUE 
  AND (rr.effective_to IS NULL OR rr.effective_to >= CURRENT_DATE);

COMMENT ON VIEW v_product_full_info IS 'Complete product information for procurement calculations';

-- View: Safety stock summary
CREATE OR REPLACE VIEW v_safety_stock_summary AS
SELECT 
    ss.sku,
    p.product_name,
    ss.warehouse_id,
    w.warehouse_name,
    ss.safety_stock_quantity,
    ss.reorder_point,
    ss.max_stock_level,
    ss.last_reviewed_date
FROM safety_stock ss
JOIN products p ON ss.sku = p.sku
JOIN warehouses w ON ss.warehouse_id = w.warehouse_id
WHERE p.is_active = TRUE;

COMMENT ON VIEW v_safety_stock_summary IS 'Safety stock levels across all warehouses';

-- ============================================================
-- TRIGGERS for automatic timestamp updates
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_replenishment_rules_updated_at BEFORE UPDATE ON replenishment_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_safety_stock_updated_at BEFORE UPDATE ON safety_stock
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_suppliers_updated_at BEFORE UPDATE ON suppliers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- END OF SCHEMA
-- ============================================================