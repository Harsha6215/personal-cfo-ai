"""
Database seed script.

Creates a test user and sample portfolio data for local development.

Usage:
    docker compose exec backend python -m database.seeds.seed
    OR
    python database/seeds/seed.py  (with DATABASE_URL env set)

Test user credentials:
    Email:    test@personal-cfo.ai
    Password: Test@1234
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from passlib.context import CryptContext  # noqa: E402
from sqlalchemy import text  # noqa: E402

from backend.core.database import AsyncSessionLocal  # noqa: E402

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed():
    """Insert test user, portfolio, holdings, transactions, and watchlist."""

    user_id = str(uuid4())
    portfolio_id = str(uuid4())
    holding_reliance = str(uuid4())
    holding_niftybees = str(uuid4())
    holding_tcs = str(uuid4())

    hashed_pw = pwd_context.hash("Test@1234")
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        # Check if test user already exists
        result = await db.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": "test@personal-cfo.ai"},
        )
        if result.scalar():
            print("✓ Seed data already exists. Skipping.")
            return

        # ── User ───────────────────────────────────────────────────────────────
        await db.execute(
            text("""
                INSERT INTO users (id, email, hashed_password, full_name, is_active, created_at, updated_at)
                VALUES (:id, :email, :pw, :name, true, :now, :now)
            """),
            {"id": user_id, "email": "test@personal-cfo.ai", "pw": hashed_pw, "name": "Test User", "now": now},
        )

        # ── Portfolio ──────────────────────────────────────────────────────────
        await db.execute(
            text("""
                INSERT INTO portfolios (id, user_id, name, currency, created_at, updated_at)
                VALUES (:id, :uid, :name, :curr, :now, :now)
            """),
            {"id": portfolio_id, "uid": user_id, "name": "Long Term", "curr": "INR", "now": now},
        )

        # ── Holdings ───────────────────────────────────────────────────────────
        holdings = [
            {"id": holding_reliance, "sym": "RELIANCE", "qty": 10, "avg": 2450.0, "type": "STOCK"},
            {"id": holding_niftybees, "sym": "NIFTYBEES", "qty": 100, "avg": 225.5, "type": "ETF"},
            {"id": holding_tcs, "sym": "TCS", "qty": 5, "avg": 3800.0, "type": "STOCK"},
        ]
        for h in holdings:
            await db.execute(
                text("""
                    INSERT INTO holdings (id, portfolio_id, symbol, quantity, average_cost, asset_type, created_at, updated_at)
                    VALUES (:id, :pid, :sym, :qty, :avg, :type, :now, :now)
                """),
                {"id": h["id"], "pid": portfolio_id, "sym": h["sym"], "qty": h["qty"],
                 "avg": h["avg"], "type": h["type"], "now": now},
            )

        # ── Transactions ───────────────────────────────────────────────────────
        transactions = [
            {"hid": holding_reliance, "type": "BUY", "qty": 10, "price": 2450.0},
            {"hid": holding_niftybees, "type": "BUY", "qty": 100, "price": 225.5},
            {"hid": holding_tcs, "type": "BUY", "qty": 5, "price": 3800.0},
        ]
        for t in transactions:
            await db.execute(
                text("""
                    INSERT INTO transactions (id, holding_id, type, quantity, price, executed_at, created_at, updated_at)
                    VALUES (:id, :hid, :type, :qty, :price, :at, :now, :now)
                """),
                {"id": str(uuid4()), "hid": t["hid"], "type": t["type"],
                 "qty": t["qty"], "price": t["price"], "at": now, "now": now},
            )

        # ── Watchlist ──────────────────────────────────────────────────────────
        watchlist = ["INFY", "HDFCBANK", "ICICIBANK"]
        for sym in watchlist:
            await db.execute(
                text("""
                    INSERT INTO watchlist (id, user_id, symbol, created_at, updated_at)
                    VALUES (:id, :uid, :sym, :now, :now)
                """),
                {"id": str(uuid4()), "uid": user_id, "sym": sym, "now": now},
            )

        await db.commit()
        print("✓ Seed data created successfully!")
        print(f"  User:      test@personal-cfo.ai / Test@1234")
        print(f"  Portfolio: Long Term (RELIANCE, NIFTYBEES, TCS)")
        print(f"  Watchlist: INFY, HDFCBANK, ICICIBANK")


if __name__ == "__main__":
    asyncio.run(seed())
