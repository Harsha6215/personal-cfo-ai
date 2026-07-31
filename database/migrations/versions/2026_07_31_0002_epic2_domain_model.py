"""Epic 2 Story 2.1 — Portfolio Domain Model (Event-Sourced Ledger)

New tables: assets, financial_events, import_jobs
The portfolio is now an event-sourced ledger. Holdings are derived, not stored.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── assets (master reference) ──────────────────────────────────────────────
    asset_type_enum = sa.Enum("STOCK", "ETF", "MF", "CRYPTO", "BOND", "FD", "GOLD", "OTHER", name="assettype_v2")
    exchange_enum = sa.Enum("NSE", "BSE", "MCX", "NCDEX", "OTHER", name="exchange_enum")

    op.create_table(
        "assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("isin", sa.String(12), unique=True, nullable=True, index=True),
        sa.Column("ticker", sa.String(50), nullable=False, index=True),
        sa.Column("exchange", exchange_enum, nullable=False, server_default="NSE"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("asset_type", asset_type_enum, nullable=False, server_default="STOCK"),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── import_jobs (audit trail) ──────────────────────────────────────────────
    import_status_enum = sa.Enum("PENDING", "PREVIEWING", "IMPORTING", "COMPLETED", "PARTIAL", "FAILED", "CANCELLED", name="importstatus_enum")
    import_source_enum = sa.Enum("ZERODHA", "ICICI", "GROWW", "INDMONEY", "ETMONEY", "CAS_PDF", "CSV_GENERIC", "MANUAL", name="importsource_enum")

    op.create_table(
        "import_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("portfolio_id", sa.String(36), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("source", import_source_enum, nullable=False),
        sa.Column("filename", sa.String(255), nullable=True),
        sa.Column("status", import_status_enum, nullable=False, server_default="PENDING"),
        sa.Column("rows_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_imported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_duplicate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── financial_events (the immutable ledger) ────────────────────────────────
    event_type_enum = sa.Enum("BUY", "SELL", "BONUS", "SPLIT", "DIVIDEND", "SIP", "TRANSFER", "MERGER", "INTEREST", "TAX", name="eventtype_enum")

    op.create_table(
        "financial_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("portfolio_id", sa.String(36), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("import_job_id", sa.String(36), sa.ForeignKey("import_jobs.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("event_type", event_type_enum, nullable=False, index=True),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("price", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("fees", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("exchange", sa.String(10), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("split_ratio_from", sa.Numeric(10, 4), nullable=True),
        sa.Column("split_ratio_to", sa.Numeric(10, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Add description column to portfolios
    op.add_column("portfolios", sa.Column("description", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_table("financial_events")
    op.drop_table("import_jobs")
    op.drop_table("assets")
    op.drop_column("portfolios", "description")
    op.execute("DROP TYPE IF EXISTS eventtype_enum")
    op.execute("DROP TYPE IF EXISTS importstatus_enum")
    op.execute("DROP TYPE IF EXISTS importsource_enum")
    op.execute("DROP TYPE IF EXISTS exchange_enum")
    op.execute("DROP TYPE IF EXISTS assettype_v2")
