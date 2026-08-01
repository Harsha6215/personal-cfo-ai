"""Add CRAMC (ICICI Direct) to portfolio."""
import uuid
from datetime import datetime, timezone
import psycopg2

conn = psycopg2.connect(host="127.0.0.1", port=5432, user="postgres", password="postgres", dbname="personal_cfo")
conn.autocommit = True
cur = conn.cursor()

# Get portfolio_id
cur.execute("SELECT id FROM portfolios LIMIT 1")
portfolio_id = cur.fetchone()[0]
print(f"Portfolio: {portfolio_id}")

# Create CRAMC asset
asset_id = str(uuid.uuid4())
cur.execute(
    "INSERT INTO assets (id, ticker, name, exchange, asset_type, currency) "
    "VALUES (%s, 'CRAMC', 'Craftsman Automation Ltd', 'NSE', 'STOCK', 'INR') "
    "ON CONFLICT DO NOTHING",
    (asset_id,)
)
# Check if it was inserted or already exists
cur.execute("SELECT id FROM assets WHERE ticker = 'CRAMC'")
asset_id = cur.fetchone()[0]
print(f"Asset: {asset_id}")

# Create financial event (BUY from ICICI Direct)
event_id = str(uuid.uuid4())
now = datetime.now(timezone.utc)
cur.execute(
    "INSERT INTO financial_events (id, portfolio_id, asset_id, event_type, quantity, price, amount, fees, executed_at, source, exchange) "
    "VALUES (%s, %s, %s, 'BUY', 46, 266, 12236, 0, %s, 'icici', 'NSE')",
    (event_id, portfolio_id, asset_id, now)
)

print("✓ CRAMC added: 46 shares @ ₹266 = ₹12,236 invested (source: ICICI Direct)")
conn.close()
