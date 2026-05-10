"""add payment_done to b2brequeststatus enum

Revision ID: d41f8e2b3c5a
Revises: ccfeeac9c9f2
Create Date: 2026-05-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd41f8e2b3c5a'
down_revision = 'ccfeeac9c9f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add payment_done value to b2brequeststatus enum
    # PostgreSQL enum values can only be added, not removed safely
    op.execute("ALTER TYPE b2brequeststatus ADD VALUE 'payment_done'")


def downgrade() -> None:
    # Downgrade is a no-op since we can't safely remove enum values in PostgreSQL
    pass