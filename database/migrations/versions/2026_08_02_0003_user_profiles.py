"""Create user_profiles table — Epic 6 Sprint 6.4

Stores onboarding data: risk appetite, goals, income, experience,
and onboarding progress tracking.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Create enum types (checkfirst to handle idempotency)
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE risk_appetite_enum AS ENUM ('CONSERVATIVE', 'MODERATE', 'AGGRESSIVE', 'VERY_AGGRESSIVE');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE investment_horizon_enum AS ENUM ('SHORT', 'MEDIUM', 'LONG', 'VERY_LONG');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE experience_level_enum AS ENUM ('BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) UNIQUE NOT NULL,
            risk_appetite risk_appetite_enum,
            investment_horizon investment_horizon_enum,
            monthly_income FLOAT,
            age INTEGER,
            primary_goals JSONB,
            experience_level experience_level_enum,
            onboarding_step INTEGER NOT NULL DEFAULT 0,
            onboarding_completed_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_user_profiles_user_id ON user_profiles (user_id)"
    ))


def downgrade() -> None:
    op.drop_table("user_profiles")
    op.execute("DROP TYPE IF EXISTS risk_appetite_enum")
    op.execute("DROP TYPE IF EXISTS investment_horizon_enum")
    op.execute("DROP TYPE IF EXISTS experience_level_enum")
