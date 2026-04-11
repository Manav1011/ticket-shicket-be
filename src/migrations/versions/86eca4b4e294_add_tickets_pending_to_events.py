"""add_tickets_pending_to_events

Revision ID: 86eca4b4e294
Revises: aa037cba12e1
Create Date: 2026-04-11 22:52:08.289950

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '86eca4b4e294'
down_revision = 'aa037cba12e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('events', sa.Column('tickets_pending', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade() -> None:
    op.drop_column('events', 'tickets_pending')
