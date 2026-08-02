"""Add user role column — Epic 6 Sprint 6.1

Adds `role` column to users table with enum (USER, ADMIN).
Default is USER for all existing records.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type
    userrole_enum = sa.Enum("USER", "ADMIN", name="userrole_enum")
    userrole_enum.create(op.get_bind(), checkfirst=True)

    # Add column with default
    op.add_column(
        "users",
        sa.Column(
            "role",
            userrole_enum,
            nullable=False,
            server_default="USER",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "role")
    op.execute("DROP TYPE IF EXISTS userrole_enum")
