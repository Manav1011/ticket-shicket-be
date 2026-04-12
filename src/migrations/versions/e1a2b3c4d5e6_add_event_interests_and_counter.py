"""Add event interests table and interested counter

Revision ID: e1a2b3c4d5e6
Revises: bd5e7c3a1f2d
Create Date: 2026-04-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e1a2b3c4d5e6"
down_revision = "bd5e7c3a1f2d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("interested_counter", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.create_table(
        "event_interests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("guest_id", sa.UUID(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["guest_id"], ["guests.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_interests_event_user"),
        sa.UniqueConstraint("event_id", "guest_id", name="uq_event_interests_event_guest"),
    )


def downgrade() -> None:
    op.drop_table("event_interests")
    op.drop_column("events", "interested_counter")
