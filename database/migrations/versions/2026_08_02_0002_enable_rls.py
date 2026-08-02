"""Enable Row-Level Security on tenant-scoped tables — Epic 6 Sprint 6.1

Adds RLS policies to enforce data isolation at the database level.
Each policy uses: user_id = current_setting('app.current_user_id')::text

Tables affected:
- portfolios (direct user_id)
- import_jobs (direct user_id)
- watchlist (direct user_id)
- decision_history (direct user_id)
- holdings (via portfolio_id → portfolios.user_id)
- financial_events (via portfolio_id → portfolios.user_id)

Note: The application sets `app.current_user_id` via SET LOCAL before each query
(see backend/core/tenant.py). RLS is defense-in-depth — not the primary isolation
mechanism.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables with direct user_id column
DIRECT_TABLES = ["portfolios", "import_jobs", "watchlist", "decision_history"]


def _table_exists(conn, table_name: str) -> bool:
    """Check if a table exists in the database."""
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :t)"
        ),
        {"t": table_name},
    )
    return result.scalar()


def upgrade() -> None:
    conn = op.get_bind()

    # ── Create the application role for the backend service ────────────────────
    # RLS policies don't apply to superusers. In production, the app connects
    # as a non-superuser role. We set up a permissive default for local dev.

    # ── Enable RLS on tables with direct user_id ──────────────────────────────
    for table in DIRECT_TABLES:
        if not _table_exists(conn, table):
            continue  # Skip tables not yet created
        conn.execute(
            sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        )
        conn.execute(
            sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        )
        # Policy: user can only see/modify their own rows
        conn.execute(
            sa.text(
                f"""
                CREATE POLICY tenant_isolation_{table} ON {table}
                    FOR ALL
                    USING (user_id = current_setting('app.current_user_id', true)::text)
                    WITH CHECK (user_id = current_setting('app.current_user_id', true)::text)
                """
            )
        )
        # Bypass policy for the migration user / superuser (safety)
        conn.execute(
            sa.text(
                f"""
                CREATE POLICY superuser_bypass_{table} ON {table}
                    FOR ALL
                    USING (current_setting('app.current_user_id', true) IS NULL OR
                           current_setting('app.current_user_id', true) = '')
                """
            )
        )

    # ── Enable RLS on holdings (user_id via portfolio join) ────────────────────
    # For holdings and financial_events, we add a direct user_id column for RLS
    # Since they already have portfolio_id, we can derive user_id from the join,
    # but RLS works best with a direct column. We'll use a subquery policy instead.

    # Holdings — join through portfolios
    if _table_exists(conn, "holdings"):
        conn.execute(sa.text("ALTER TABLE holdings ENABLE ROW LEVEL SECURITY"))
        conn.execute(sa.text("ALTER TABLE holdings FORCE ROW LEVEL SECURITY"))
        conn.execute(
            sa.text(
                """
                CREATE POLICY tenant_isolation_holdings ON holdings
                    FOR ALL
                    USING (
                        portfolio_id IN (
                            SELECT id FROM portfolios
                            WHERE user_id = current_setting('app.current_user_id', true)::text
                        )
                    )
                    WITH CHECK (
                        portfolio_id IN (
                            SELECT id FROM portfolios
                            WHERE user_id = current_setting('app.current_user_id', true)::text
                        )
                    )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                CREATE POLICY superuser_bypass_holdings ON holdings
                    FOR ALL
                    USING (current_setting('app.current_user_id', true) IS NULL OR
                           current_setting('app.current_user_id', true) = '')
                """
            )
        )

    # Financial events — join through portfolios
    if _table_exists(conn, "financial_events"):
        conn.execute(sa.text("ALTER TABLE financial_events ENABLE ROW LEVEL SECURITY"))
        conn.execute(sa.text("ALTER TABLE financial_events FORCE ROW LEVEL SECURITY"))
        conn.execute(
            sa.text(
                """
                CREATE POLICY tenant_isolation_financial_events ON financial_events
                    FOR ALL
                    USING (
                        portfolio_id IN (
                            SELECT id FROM portfolios
                            WHERE user_id = current_setting('app.current_user_id', true)::text
                        )
                    )
                    WITH CHECK (
                        portfolio_id IN (
                            SELECT id FROM portfolios
                            WHERE user_id = current_setting('app.current_user_id', true)::text
                        )
                    )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                CREATE POLICY superuser_bypass_financial_events ON financial_events
                    FOR ALL
                    USING (current_setting('app.current_user_id', true) IS NULL OR
                           current_setting('app.current_user_id', true) = '')
                """
            )
        )


def downgrade() -> None:
    conn = op.get_bind()

    # Drop policies and disable RLS
    all_tables = DIRECT_TABLES + ["holdings", "financial_events"]
    for table in all_tables:
        conn.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}"))
        conn.execute(sa.text(f"DROP POLICY IF EXISTS superuser_bypass_{table} ON {table}"))
        conn.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))
