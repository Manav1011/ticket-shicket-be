"""empty message

Revision ID: 86361eeddf67
Revises: 7c7609b23301
Create Date: 2026-04-18 14:03:26.341395

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '86361eeddf67'
down_revision = '7c7609b23301'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the enum type first (before column that references it)
    op.execute(
        "CREATE TYPE allocationtype AS ENUM ('b2b', 'purchase', 'transfer', 'refund')"
    )
    # Add as nullable first (existing rows don't have this value yet)
    op.add_column(
        'allocations',
        sa.Column('allocation_type', sa.Enum('allocationtype', name='allocationtype', create_type=False), nullable=True)
    )
    # Backfill existing allocations as b2b (they're all from B2B approval flow)
    op.execute("UPDATE allocations SET allocation_type = 'b2b' WHERE allocation_type IS NULL")
    # Now make it non-nullable
    op.alter_column('allocations', 'allocation_type', nullable=False)


def downgrade() -> None:
    op.drop_column('allocations', 'allocation_type')
    op.execute("DROP TYPE allocationtype")
