"""drop b2b recipient fields

Revision ID: 6603c7296914
Revises: 0a32de8db265
Create Date: 2026-04-15 13:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6603c7296914'
down_revision = '0a32de8db265'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('b2b_requests', 'recipient_phone')
    op.drop_column('b2b_requests', 'recipient_email')


def downgrade() -> None:
    op.add_column('b2b_requests', sa.Column('recipient_phone', sa.String(length=32), nullable=True))
    op.add_column('b2b_requests', sa.Column('recipient_email', sa.String(length=255), nullable=True))
