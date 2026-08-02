"""Create audit_logs table — Epic 6 Sprint 6.5

Records all admin actions for compliance and auditability.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id VARCHAR(36) PRIMARY KEY,
            admin_user_id VARCHAR(36) NOT NULL,
            action VARCHAR(100) NOT NULL,
            target_type VARCHAR(50) NOT NULL,
            target_id VARCHAR(36) NOT NULL,
            details JSONB,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """))

    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_admin_user_id ON audit_logs (admin_user_id)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs (created_at DESC)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_target ON audit_logs (target_type, target_id)"
    ))


def downgrade() -> None:
    op.drop_table("audit_logs")
