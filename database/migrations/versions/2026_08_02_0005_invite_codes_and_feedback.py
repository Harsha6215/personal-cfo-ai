"""Create invite_codes and feedback tables — Sprint 6.6 Beta Launch

Supports beta invite gating and in-app feedback collection.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── invite_codes table ─────────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS invite_codes (
            id VARCHAR(36) PRIMARY KEY,
            code VARCHAR(20) NOT NULL UNIQUE,
            created_by VARCHAR(36) NOT NULL,
            max_uses INTEGER NOT NULL DEFAULT 1,
            current_uses INTEGER NOT NULL DEFAULT 0,
            expires_at TIMESTAMP WITH TIME ZONE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """))

    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_invite_codes_code ON invite_codes (code)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_invite_codes_created_by ON invite_codes (created_by)"
    ))

    # ── feedback table ─────────────────────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS feedback (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            feedback_type VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            rating INTEGER,
            page VARCHAR(100),
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """))

    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_feedback_user_id ON feedback (user_id)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_feedback_type ON feedback (feedback_type)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_feedback_created_at ON feedback (created_at DESC)"
    ))


def downgrade() -> None:
    op.drop_table("feedback")
    op.drop_table("invite_codes")
