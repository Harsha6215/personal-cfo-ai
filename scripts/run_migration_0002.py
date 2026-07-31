"""Run Epic 2 migration — create assets, financial_events, import_jobs tables."""
import psycopg2

conn = psycopg2.connect(host="127.0.0.1", port=5432, user="postgres", password="postgres", dbname="personal_cfo")
conn.autocommit = True
cur = conn.cursor()

sql = """
-- Asset type enum (v2 with more types)
DO $$ BEGIN
    CREATE TYPE assettype_v2 AS ENUM ('STOCK','ETF','MF','CRYPTO','BOND','FD','GOLD','OTHER');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE exchange_enum AS ENUM ('NSE','BSE','MCX','NCDEX','OTHER');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE importstatus_enum AS ENUM ('PENDING','PREVIEWING','IMPORTING','COMPLETED','PARTIAL','FAILED','CANCELLED');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE importsource_enum AS ENUM ('ZERODHA','ICICI','GROWW','INDMONEY','ETMONEY','CAS_PDF','CSV_GENERIC','MANUAL');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE eventtype_enum AS ENUM ('BUY','SELL','BONUS','SPLIT','DIVIDEND','SIP','TRANSFER','MERGER','INTEREST','TAX');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Assets table
CREATE TABLE IF NOT EXISTS assets (
    id VARCHAR(36) PRIMARY KEY,
    isin VARCHAR(12) UNIQUE,
    ticker VARCHAR(50) NOT NULL,
    exchange exchange_enum NOT NULL DEFAULT 'NSE',
    name VARCHAR(255) NOT NULL,
    asset_type assettype_v2 NOT NULL DEFAULT 'STOCK',
    sector VARCHAR(100),
    industry VARCHAR(100),
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Import jobs table
CREATE TABLE IF NOT EXISTS import_jobs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    portfolio_id VARCHAR(36) NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    source importsource_enum NOT NULL,
    filename VARCHAR(255),
    status importstatus_enum NOT NULL DEFAULT 'PENDING',
    rows_total INTEGER NOT NULL DEFAULT 0,
    rows_imported INTEGER NOT NULL DEFAULT 0,
    rows_failed INTEGER NOT NULL DEFAULT 0,
    rows_duplicate INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    error_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Financial events (the ledger)
CREATE TABLE IF NOT EXISTS financial_events (
    id VARCHAR(36) PRIMARY KEY,
    portfolio_id VARCHAR(36) NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    asset_id VARCHAR(36) NOT NULL REFERENCES assets(id) ON DELETE RESTRICT,
    import_job_id VARCHAR(36) REFERENCES import_jobs(id) ON DELETE SET NULL,
    event_type eventtype_enum NOT NULL,
    quantity NUMERIC(18,6) NOT NULL,
    price NUMERIC(18,4) NOT NULL DEFAULT 0,
    amount NUMERIC(18,4) NOT NULL DEFAULT 0,
    fees NUMERIC(18,4) NOT NULL DEFAULT 0,
    executed_at TIMESTAMPTZ NOT NULL,
    source VARCHAR(50),
    exchange VARCHAR(10),
    notes TEXT,
    split_ratio_from NUMERIC(10,4),
    split_ratio_to NUMERIC(10,4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Add description to portfolios if not exists
DO $$ BEGIN
    ALTER TABLE portfolios ADD COLUMN description VARCHAR(500);
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- Indexes
CREATE INDEX IF NOT EXISTS ix_assets_ticker ON assets(ticker);
CREATE INDEX IF NOT EXISTS ix_assets_isin ON assets(isin);
CREATE INDEX IF NOT EXISTS ix_import_jobs_user ON import_jobs(user_id);
CREATE INDEX IF NOT EXISTS ix_import_jobs_portfolio ON import_jobs(portfolio_id);
CREATE INDEX IF NOT EXISTS ix_financial_events_portfolio ON financial_events(portfolio_id);
CREATE INDEX IF NOT EXISTS ix_financial_events_asset ON financial_events(asset_id);
CREATE INDEX IF NOT EXISTS ix_financial_events_executed ON financial_events(executed_at);
CREATE INDEX IF NOT EXISTS ix_financial_events_type ON financial_events(event_type);
CREATE INDEX IF NOT EXISTS ix_financial_events_import ON financial_events(import_job_id);

-- Seed reference data: some well-known Indian stocks
INSERT INTO assets (id, ticker, name, isin, exchange, asset_type, sector)
VALUES
    ('asset-reliance', 'RELIANCE', 'Reliance Industries Ltd', 'INE002A01018', 'NSE', 'STOCK', 'Energy'),
    ('asset-tcs', 'TCS', 'Tata Consultancy Services Ltd', 'INE467B01029', 'NSE', 'STOCK', 'IT'),
    ('asset-infy', 'INFY', 'Infosys Ltd', 'INE009A01021', 'NSE', 'STOCK', 'IT'),
    ('asset-hdfcbank', 'HDFCBANK', 'HDFC Bank Ltd', 'INE040A01034', 'NSE', 'STOCK', 'Banking'),
    ('asset-icicibank', 'ICICIBANK', 'ICICI Bank Ltd', 'INE090A01021', 'NSE', 'STOCK', 'Banking'),
    ('asset-niftybees', 'NIFTYBEES', 'Nippon India ETF Nifty 50 BeES', 'INF204KB14I2', 'NSE', 'ETF', 'Index'),
    ('asset-goldbees', 'GOLDBEES', 'Nippon India ETF Gold BeES', 'INF204KB17I5', 'NSE', 'ETF', 'Gold')
ON CONFLICT (id) DO NOTHING;
"""

cur.execute(sql)
print("✓ Epic 2 domain model tables created")
print("✓ Enums: assettype_v2, exchange_enum, importstatus_enum, importsource_enum, eventtype_enum")
print("✓ Tables: assets, import_jobs, financial_events")
print("✓ Indexes: ticker, isin, portfolio, asset, executed_at, event_type")
print("✓ Seed data: 7 reference assets (RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, NIFTYBEES, GOLDBEES)")
conn.close()
