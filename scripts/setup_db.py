"""Setup native PostgreSQL for Personal CFO AI."""
import psycopg2

conn = psycopg2.connect(host="127.0.0.1", port=5432, user="postgres", password="postgres", dbname="postgres")
conn.autocommit = True
cur = conn.cursor()

# Set password
cur.execute("ALTER USER postgres WITH PASSWORD 'postgres'")
print("✓ Password set to 'postgres'")

# Create database if not exists
cur.execute("SELECT 1 FROM pg_database WHERE datname = 'personal_cfo'")
if not cur.fetchone():
    cur.execute("CREATE DATABASE personal_cfo")
    print("✓ Database 'personal_cfo' created")
else:
    print("✓ Database 'personal_cfo' already exists")

conn.close()

# Now create tables in personal_cfo
conn2 = psycopg2.connect(host="127.0.0.1", port=5432, user="postgres", password="postgres", dbname="personal_cfo")
conn2.autocommit = True
cur2 = conn2.cursor()

sql = """
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$ BEGIN
    CREATE TYPE assettype AS ENUM ('STOCK','ETF','MF','CRYPTO','BOND','OTHER');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE transactiontype AS ENUM ('BUY','SELL');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS portfolios (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS holdings (
    id VARCHAR(36) PRIMARY KEY,
    portfolio_id VARCHAR(36) NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    quantity NUMERIC(18,6) NOT NULL DEFAULT 0,
    average_cost NUMERIC(18,4) NOT NULL DEFAULT 0,
    asset_type assettype NOT NULL DEFAULT 'STOCK',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS transactions (
    id VARCHAR(36) PRIMARY KEY,
    holding_id VARCHAR(36) NOT NULL REFERENCES holdings(id) ON DELETE CASCADE,
    type transactiontype NOT NULL,
    quantity NUMERIC(18,6) NOT NULL,
    price NUMERIC(18,4) NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL,
    notes VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS watchlist (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    notes VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, symbol)
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_portfolios_user ON portfolios(user_id);
CREATE INDEX IF NOT EXISTS ix_holdings_portfolio ON holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS ix_holdings_symbol ON holdings(symbol);
CREATE INDEX IF NOT EXISTS ix_transactions_holding ON transactions(holding_id);
CREATE INDEX IF NOT EXISTS ix_watchlist_user ON watchlist(user_id);
CREATE INDEX IF NOT EXISTS ix_watchlist_symbol ON watchlist(symbol);
"""

cur2.execute(sql)
print("✓ All tables and indexes created")
conn2.close()

# Test asyncpg too
import asyncio
import asyncpg

async def test_async():
    c = await asyncpg.connect("postgresql://postgres:postgres@127.0.0.1:5432/personal_cfo")
    val = await c.fetchval("SELECT COUNT(*) FROM users")
    print(f"✓ asyncpg connection works (users count: {val})")
    await c.close()

asyncio.run(test_async())
print("\n🎉 Database is ready! Backend can now connect.")
