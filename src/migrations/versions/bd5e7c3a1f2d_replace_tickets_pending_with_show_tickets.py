"""replace_tickets_pending_with_show_tickets

Revision ID: bd5e7c3a1f2d
Revises: 86eca4b4e294
Create Date: 2026-04-11 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bd5e7c3a1f2d'
down_revision = '86eca4b4e294'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('events', 'tickets_pending')
    op.add_column('events', sa.Column('show_tickets', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade() -> None:
    op.drop_column('events', 'show_tickets')
    op.add_column('events', sa.Column('tickets_pending', sa.Boolean(), server_default=sa.text('false'), nullable=False))
