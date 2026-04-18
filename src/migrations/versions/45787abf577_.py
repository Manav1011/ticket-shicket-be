"""add days_count to events

Revision ID: 45787abf577
Revises: 86361eeddf67
Create Date: 2026-04-18 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '45787abf577'
down_revision = '86361eeddf67'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'events',
        sa.Column('days_count', sa.Integer(), server_default='0', nullable=False)
    )


def downgrade() -> None:
    op.drop_column('events', 'days_count')
