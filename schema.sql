-- 1. Create the Database
CREATE DATABASE tiktok_shopify_bridge;

-- 2. SKU Mapping Table
CREATE TABLE sku_mapping (
    id SERIAL PRIMARY KEY,
    tiktok_sku VARCHAR(100) UNIQUE NOT NULL,
    shopify_sku VARCHAR(100) UNIQUE NOT NULL,
    product_name VARCHAR(255)
);

-- 3. Courier Mapping (For TikTok Italy requirements)
CREATE TABLE courier_mapping (
    shopify_name VARCHAR(100) PRIMARY KEY,
    tiktok_code VARCHAR(100) NOT NULL
);

-- 4. Orders Table
CREATE TABLE orders_integration (
    tiktok_order_id VARCHAR(50) PRIMARY KEY,
    shopify_order_id VARCHAR(50),
    customer_email VARCHAR(255),
    customer_phone VARCHAR(50),
    gross_sales NUMERIC(10, 2),
    tiktok_fees NUMERIC(10, 2),
    affiliate_commissions NUMERIC(10, 2),
    net_revenue NUMERIC(10, 2),
    sync_status VARCHAR(20) DEFAULT 'pending', -- pending, synced, fulfilled
    shipping_status VARCHAR(20),
    tracking_number VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Some Example Data
INSERT INTO sku_mapping (tiktok_sku, shopify_sku, product_name) VALUES 
('TK-IT-BLUE-S', 'SH-BLU-SML', 'Blue T-Shirt Small'),
('TK-IT-BLUE-M', 'SH-BLU-MED', 'Blue T-Shirt Medium');

INSERT INTO courier_mapping VALUES ('DHL Express', 'DHL'), ('Poste Italiane', 'POSTE_IT');

-- Table to track Ad Spend (GMV Max) per day
CREATE TABLE ad_spend (
    spend_date DATE PRIMARY KEY,
    gmv_max_cost NUMERIC(10, 2) DEFAULT 0.00
);

-- Adding a column to track if an order came from an Affiliate
ALTER TABLE orders_integration 
ADD COLUMN is_affiliate_order BOOLEAN DEFAULT FALSE,
ADD COLUMN affiliate_revenue NUMERIC(10, 2) DEFAULT 0.00; -- The portion of sale attributed to the affiliate

-- Example Ad Spend Data
INSERT INTO ad_spend (spend_date, gmv_max_cost) VALUES ('2026-01-11', 15.50);

-- Update our existing order to simulate it was an Affiliate order
UPDATE orders_integration 
SET is_affiliate_order = TRUE, affiliate_revenue = 50.00 
WHERE tiktok_order_id = 'TT-ORDER-101';

-- Thorough Dashboard Query
SELECT 
    -- 1. Sales Overview
    SUM(gross_sales) AS total_gmv,
    
    -- 2. GMV Max Spending (Ad Spend)
    (SELECT SUM(gmv_max_cost) FROM ad_spend) AS gmv_max_spending,
    
    -- 3. Affiliate Metrics
    SUM(CASE WHEN is_affiliate_order THEN affiliate_revenue ELSE 0 END) AS affiliates_total_revenue,
    SUM(affiliate_commissions) AS affiliates_commissions_paid,
    
    -- 4. Revenue Generated (Net Profit after ALL costs)
    -- Formula: GMV - TikTok Fees - Affiliate Commissions - Ad Spend (GMV Max)
    (SUM(net_revenue) - (SELECT SUM(gmv_max_cost) FROM ad_spend)) AS total_net_profit

FROM orders_integration;