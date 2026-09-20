-- ============================================================================
-- KiranaOS — Zero-Click Store Operator
-- Supabase PostgreSQL Schema & Seed Migration
-- Conforms to Supabase & Postgres Best Practices
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. PRODUCTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.products (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    brand VARCHAR(100) NOT NULL,
    category VARCHAR(100) NOT NULL,
    size VARCHAR(50) NOT NULL,
    unit VARCHAR(20) NOT NULL DEFAULT 'packet',
    price DOUBLE PRECISION NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    low_stock_threshold INTEGER NOT NULL DEFAULT 5,
    aliases JSONB NOT NULL DEFAULT '[]'::jsonb,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_stock_non_negative CHECK (stock >= 0)
);

CREATE INDEX IF NOT EXISTS idx_products_brand ON public.products (brand);
CREATE INDEX IF NOT EXISTS idx_products_category ON public.products (category);
CREATE INDEX IF NOT EXISTS idx_products_name ON public.products (name);
CREATE INDEX IF NOT EXISTS idx_products_active_stock ON public.products (active, stock);

-- ============================================================================
-- 2. CUSTOMERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.customers (
    id VARCHAR(50) PRIMARY KEY,
    phone VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    default_address TEXT,
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customers_phone ON public.customers (phone);

-- ============================================================================
-- 3. ORDERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.orders (
    id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES public.customers (id) ON DELETE CASCADE,
    status VARCHAR(30) NOT NULL DEFAULT 'confirmed',
    subtotal DOUBLE PRECISION NOT NULL,
    delivery_charge DOUBLE PRECISION NOT NULL DEFAULT 20.0,
    total DOUBLE PRECISION NOT NULL,
    idempotency_key VARCHAR(100) UNIQUE,
    delivery_status VARCHAR(30) NOT NULL DEFAULT 'requested',
    delivery_address TEXT,
    approval_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON public.orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON public.orders (status);
CREATE INDEX IF NOT EXISTS idx_orders_idempotency_key ON public.orders (idempotency_key);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON public.orders (created_at DESC);

-- ============================================================================
-- 4. ORDER ITEMS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.order_items (
    id BIGSERIAL PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL REFERENCES public.orders (id) ON DELETE CASCADE,
    product_id VARCHAR(50) NOT NULL REFERENCES public.products (id) ON DELETE RESTRICT,
    product_name VARCHAR(200) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DOUBLE PRECISION NOT NULL,
    line_total DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON public.order_items (order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON public.order_items (product_id);

-- ============================================================================
-- 5. INVENTORY LOGS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.inventory_logs (
    id BIGSERIAL PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL REFERENCES public.products (id) ON DELETE CASCADE,
    order_id VARCHAR(50),
    change_amount INTEGER NOT NULL,
    previous_stock INTEGER NOT NULL,
    new_stock INTEGER NOT NULL,
    reason VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inventory_logs_product_id ON public.inventory_logs (product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_logs_order_id ON public.inventory_logs (order_id);
CREATE INDEX IF NOT EXISTS idx_inventory_logs_timestamp ON public.inventory_logs (timestamp DESC);

-- ============================================================================
-- 6. AGENT RUNS TABLE (OBSERVABILITY & AUDIT TRAIL)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.agent_runs (
    id VARCHAR(50) PRIMARY KEY,
    request_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(50),
    status VARCHAR(30) NOT NULL,
    events JSONB NOT NULL DEFAULT '[]'::jsonb,
    input_text TEXT NOT NULL,
    structured_intent JSONB NOT NULL DEFAULT '{}'::jsonb,
    tool_calls JSONB NOT NULL DEFAULT '[]'::jsonb,
    final_output JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_request_id ON public.agent_runs (request_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_created_at ON public.agent_runs (created_at DESC);

-- ============================================================================
-- 7. CUSTOMER PREFERENCES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.customer_preferences (
    id BIGSERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES public.customers (id) ON DELETE CASCADE,
    product_id VARCHAR(50) NOT NULL REFERENCES public.products (id) ON DELETE CASCADE,
    frequency INTEGER NOT NULL DEFAULT 1,
    preferred_quantity INTEGER NOT NULL DEFAULT 1,
    last_ordered_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_customer_product_pref UNIQUE (customer_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_customer_prefs_lookup ON public.customer_preferences (customer_id, frequency DESC);

-- ============================================================================
-- 8. LOW STOCK EVENTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.low_stock_events (
    id BIGSERIAL PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL REFERENCES public.products (id) ON DELETE CASCADE,
    stock_at_event INTEGER NOT NULL,
    threshold INTEGER NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'alert_triggered',
    triggered_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_low_stock_events_product_id ON public.low_stock_events (product_id);
CREATE INDEX IF NOT EXISTS idx_low_stock_events_triggered_at ON public.low_stock_events (triggered_at DESC);

-- ============================================================================
-- 9. DELIVERY REQUESTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.delivery_requests (
    id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL REFERENCES public.orders (id) ON DELETE CASCADE,
    address TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'dispatched',
    delivery_partner VARCHAR(100) NOT NULL DEFAULT 'Kirana Express Rider',
    estimated_time VARCHAR(50) NOT NULL DEFAULT '15-25 mins',
    tracking_id VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_delivery_requests_order_id ON public.delivery_requests (order_id);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inventory_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customer_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.low_stock_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.delivery_requests ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS for full backend agent mutations
-- Read access for anonymous & authenticated users (Data API)
DO $$
DECLARE
    tbl text;
BEGIN
    FOR tbl IN 
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS "Allow service_role full access" ON public.%I', tbl);
        EXECUTE format('CREATE POLICY "Allow service_role full access" ON public.%I TO service_role USING (true) WITH CHECK (true)', tbl);
        
        EXECUTE format('DROP POLICY IF EXISTS "Allow anon read access" ON public.%I', tbl);
        EXECUTE format('CREATE POLICY "Allow anon read access" ON public.%I FOR SELECT TO anon USING (true)', tbl);

        EXECUTE format('DROP POLICY IF EXISTS "Allow authenticated read access" ON public.%I', tbl);
        EXECUTE format('CREATE POLICY "Allow authenticated read access" ON public.%I FOR SELECT TO authenticated USING (true)', tbl);
    END LOOP;
END $$;

-- Explicit Grants for PostgREST Data API
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon, authenticated;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;

-- ============================================================================
-- SEED DATA: AUTHENTIC KIRANA CATALOG & DEFAULT CUSTOMER
-- ============================================================================

INSERT INTO public.customers (id, phone, name, default_address, preferences)
VALUES (
    'cust_default_001',
    '+919876543210',
    'Pratham Sharma',
    'Flat 402, Shanti Kunj, Sector 14, Gurugram',
    '{"preferred_payment": "COD", "frequent_buyer": true}'::jsonb
)
ON CONFLICT (id) DO UPDATE SET
    phone = EXCLUDED.phone,
    name = EXCLUDED.name,
    default_address = EXCLUDED.default_address;

INSERT INTO public.products (id, name, brand, category, size, unit, price, stock, low_stock_threshold, aliases, active)
VALUES
(
    'prod_atta_aashirvaad_5kg',
    'Aashirvaad Shudh Chakki Atta 5kg',
    'Aashirvaad',
    'Atta & Flours',
    '5kg',
    'bag',
    240.0,
    25,
    5,
    '["aashirvaad atta", "aashirwad aata", "aata", "atta", "wheat flour", "आटा", "5 kilo wala aata", "5kg atta", "aashirvad", "ashirwad", "5 kilo wheat flour", "aata 5kg"]'::jsonb,
    true
),
(
    'prod_atta_aashirvaad_10kg',
    'Aashirvaad Shudh Chakki Atta 10kg',
    'Aashirvaad',
    'Atta & Flours',
    '10kg',
    'bag',
    460.0,
    10,
    3,
    '["10 kilo aata", "10kg atta", "bada atta packet", "aashirvaad 10kg", "10 kilo wheat flour", "aata 10kg"]'::jsonb,
    true
),
(
    'prod_oil_fortune_1l',
    'Fortune Sunlite Refined Sunflower Oil 1L',
    'Fortune',
    'Edible Oils',
    '1L',
    'pouch',
    145.0,
    15,
    4,
    '["fortune oil", "fortune refined oil", "refined tel", "sunflower oil", "fortune 1 litre", "tel", "tel ka packet", "1l oil"]'::jsonb,
    true
),
(
    'prod_maggi_70g',
    'Maggi 2-Minute Masala Instant Noodles 70g',
    'Maggi',
    'Instant Food',
    '70g',
    'packet',
    14.0,
    50,
    10,
    '["maggi", "maggie", "magi", "2 minute noodles", "masala noodles", "maggi packet", "choti maggi"]'::jsonb,
    true
),
(
    'prod_milk_amul_taaza_500ml',
    'Amul Taaza Homogenised Toned Milk 500ml',
    'Amul',
    'Dairy & Eggs',
    '500ml',
    'pouch',
    27.0,
    30,
    6,
    '["amul doodh", "amul taaza", "toned milk", "doodh", "doodh ki theli", "blue amul", "amul milk"]'::jsonb,
    true
),
(
    'prod_surf_excel_1kg',
    'Surf Excel Quick Wash Detergent Powder 1kg',
    'Surf Excel',
    'Cleaning & Laundry',
    '1kg',
    'packet',
    150.0,
    20,
    3,
    '["surf excel", "surf", "washing powder", "surf excel 1kg", "surf powder", "kapde dhone ka powder"]'::jsonb,
    true
),
(
    'prod_ariel_matic_1kg',
    'Ariel Matic Top Load Detergent Powder 1kg',
    'Ariel',
    'Cleaning & Laundry',
    '1kg',
    'packet',
    195.0,
    15,
    3,
    '["ariel", "ariel matic", "ariel powder", "ariel detergent"]'::jsonb,
    true
),
(
    'prod_salt_tata_1kg',
    'Tata Salt Vacuum Evaporated Iodised Salt 1kg',
    'Tata',
    'Salt & Spices',
    '1kg',
    'packet',
    28.0,
    40,
    8,
    '["tata salt", "tata namak", "namak", "salt", "desh ka namak", "tata salt 1kg"]'::jsonb,
    true
),
(
    'prod_biscuit_parle_g_250g',
    'Parle-G Gluco Biscuits 250g',
    'Parle',
    'Snacks & Biscuits',
    '250g',
    'packet',
    25.0,
    35,
    8,
    '["parle g", "parle-g", "glucose biscuit", "parle biscuit", "biskut", "chai biscuit"]'::jsonb,
    true
),
(
    'prod_soap_dettol_75g',
    'Dettol Original Bathing Soap Bar 75g',
    'Dettol',
    'Personal Care',
    '75g',
    'bar',
    38.0,
    25,
    5,
    '["dettol", "dettol soap", "dettol sabun", "sabun", "bathing soap", "dettol bar"]'::jsonb,
    true
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    price = EXCLUDED.price,
    stock = EXCLUDED.stock,
    aliases = EXCLUDED.aliases;

INSERT INTO public.customer_preferences (customer_id, product_id, frequency, preferred_quantity)
VALUES
('cust_default_001', 'prod_atta_aashirvaad_5kg', 5, 2),
('cust_default_001', 'prod_oil_fortune_1l', 4, 1),
('cust_default_001', 'prod_maggi_70g', 8, 3),
('cust_default_001', 'prod_salt_tata_1kg', 3, 1),
('cust_default_001', 'prod_surf_excel_1kg', 2, 1),
('cust_default_001', 'prod_ariel_matic_1kg', 2, 1)
ON CONFLICT (customer_id, product_id) DO UPDATE SET
    frequency = EXCLUDED.frequency,
    preferred_quantity = EXCLUDED.preferred_quantity;
