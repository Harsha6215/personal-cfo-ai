"""Seed script for beta launch — creates admin user (if needed) and 10 invite codes."""

import asyncio
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text  # noqa: E402

from backend.core.database import AsyncSessionLocal  # noqa: E402

ADMIN_EMAIL = "harsha.coolguy@gmail.com"
INVITE_COUNT = 10


def generate_code() -> str:
    """Generate an 8-char uppercase alphanumeric invite code."""
    return secrets.token_urlsafe(6).upper()[:8]


async def seed():
    """Ensure admin exists and generate beta invite codes."""
    async with AsyncSessionLocal() as db:
        # ── Ensure admin user ──────────────────────────────────────────────────
        result = await db.execute(
            text("SELECT id, role FROM users WHERE email = :email"),
            {"email": ADMIN_EMAIL},
        )
        row = result.first()

        if row is None:
            print(f"⚠  Admin user {ADMIN_EMAIL} not found. Please register first.")
            print("   Run: POST /api/v1/auth/register with this email, then re-run this script.")
        else:
            user_id = row[0]
            current_role = row[1]
            if current_role != "ADMIN":
                await db.execute(
                    text("UPDATE users SET role = 'ADMIN' WHERE id = :id"),
                    {"id": user_id},
                )
                print(f"✓ Promoted {ADMIN_EMAIL} to ADMIN")
            else:
                print(f"✓ Admin user {ADMIN_EMAIL} already has ADMIN role")

            # ── Generate invite codes ──────────────────────────────────────────
            now = datetime.now(timezone.utc)
            codes = []

            for _ in range(INVITE_COUNT):
                code = generate_code()
                code_id = str(uuid4())
                await db.execute(
                    text("""
                        INSERT INTO invite_codes (id, code, created_by, max_uses, current_uses, is_active, created_at, updated_at)
                        VALUES (:id, :code, :created_by, 1, 0, TRUE, :now, :now)
                    """),
                    {"id": code_id, "code": code, "created_by": user_id, "now": now},
                )
                codes.append(code)

            await db.commit()

            print(f"\n✓ Generated {INVITE_COUNT} invite codes (max 1 use each):")
            print("─" * 40)
            for i, code in enumerate(codes, 1):
                print(f"  {i:2d}. {code}")
            print("─" * 40)
            print("\nShare these with beta users for registration.")


if __name__ == "__main__":
    asyncio.run(seed())
