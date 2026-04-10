"""convert_string_columns_to_enum_types

Revision ID: 9bf5b22783b2
Revises: ea0828634684
Create Date: 2026-04-09 22:49:45.125727

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9bf5b22783b2'
down_revision = 'ea0828634684'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First normalize existing data to lowercase for consistent conversion
    op.execute("UPDATE ticket_types SET category = LOWER(category)")
    op.execute("UPDATE organizer_pages SET visibility = LOWER(visibility)")

    # Create ENUM types with lowercase labels
    op.execute("CREATE TYPE scanstatus AS ENUM ('not_started', 'active', 'paused', 'ended')")
    op.execute("CREATE TYPE eventstatus AS ENUM ('draft', 'published', 'archived')")
    op.execute("CREATE TYPE eventaccesstype AS ENUM ('open', 'ticketed')")
    op.execute("CREATE TYPE locationmode AS ENUM ('venue', 'online', 'recorded', 'hybrid')")
    op.execute("CREATE TYPE organizervisibility AS ENUM ('public', 'private')")
    op.execute("CREATE TYPE organizerstatus AS ENUM ('active', 'archived')")
    op.execute("CREATE TYPE ticketcategory AS ENUM ('online', 'b2b', 'public', 'vip')")
    op.execute("CREATE TYPE ticketstatus AS ENUM ('active', 'cancelled', 'used')")

    # Drop defaults first, then alter column types, then add defaults back
    # event_days.scan_status
    op.execute("ALTER TABLE event_days ALTER COLUMN scan_status DROP DEFAULT")
    op.execute("ALTER TABLE event_days ALTER COLUMN scan_status TYPE scanstatus USING scan_status::scanstatus")
    op.execute("ALTER TABLE event_days ALTER COLUMN scan_status SET DEFAULT 'not_started'::scanstatus")

    # events.status
    op.execute("ALTER TABLE events ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE events ALTER COLUMN status TYPE eventstatus USING status::eventstatus")
    op.execute("ALTER TABLE events ALTER COLUMN status SET DEFAULT 'draft'::eventstatus")

    # events.event_access_type
    op.execute("ALTER TABLE events ALTER COLUMN event_access_type DROP DEFAULT")
    op.execute("ALTER TABLE events ALTER COLUMN event_access_type TYPE eventaccesstype USING event_access_type::eventaccesstype")
    op.execute("ALTER TABLE events ALTER COLUMN event_access_type SET DEFAULT 'ticketed'::eventaccesstype")

    # events.location_mode (nullable, no default)
    op.execute("ALTER TABLE events ALTER COLUMN location_mode TYPE locationmode USING location_mode::locationmode")

    # organizer_pages.visibility
    op.execute("ALTER TABLE organizer_pages ALTER COLUMN visibility DROP DEFAULT")
    op.execute("ALTER TABLE organizer_pages ALTER COLUMN visibility TYPE organizervisibility USING visibility::organizervisibility")
    op.execute("ALTER TABLE organizer_pages ALTER COLUMN visibility SET DEFAULT 'private'::organizervisibility")

    # organizer_pages.status
    op.execute("ALTER TABLE organizer_pages ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE organizer_pages ALTER COLUMN status TYPE organizerstatus USING status::organizerstatus")
    op.execute("ALTER TABLE organizer_pages ALTER COLUMN status SET DEFAULT 'active'::organizerstatus")

    # ticket_types.category (nullable, no default)
    op.execute("ALTER TABLE ticket_types ALTER COLUMN category TYPE ticketcategory USING category::ticketcategory")

    # tickets.status
    op.execute("ALTER TABLE tickets ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE tickets ALTER COLUMN status TYPE ticketstatus USING status::ticketstatus")
    op.execute("ALTER TABLE tickets ALTER COLUMN status SET DEFAULT 'active'::ticketstatus")


def downgrade() -> None:
    # Drop defaults first
    op.execute("ALTER TABLE tickets ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE ticket_types ALTER COLUMN category DROP DEFAULT")
    op.execute("ALTER TABLE organizer_pages ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE organizer_pages ALTER COLUMN visibility DROP DEFAULT")
    op.execute("ALTER TABLE events ALTER COLUMN location_mode DROP DEFAULT")
    op.execute("ALTER TABLE events ALTER COLUMN event_access_type DROP DEFAULT")
    op.execute("ALTER TABLE events ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE event_days ALTER COLUMN scan_status DROP DEFAULT")

    # Revert columns back to VARCHAR
    op.execute("ALTER TABLE tickets ALTER COLUMN status TYPE VARCHAR(32) USING status::VARCHAR(32)")
    op.execute("ALTER TABLE ticket_types ALTER COLUMN category TYPE VARCHAR(32) USING category::VARCHAR(32)")
    op.execute("ALTER TABLE organizer_pages ALTER COLUMN status TYPE VARCHAR(32) USING status::VARCHAR(32)")
    op.execute("ALTER TABLE organizer_pages ALTER COLUMN visibility TYPE VARCHAR(32) USING visibility::VARCHAR(32)")
    op.execute("ALTER TABLE events ALTER COLUMN location_mode TYPE VARCHAR(32) USING location_mode::VARCHAR(32)")
    op.execute("ALTER TABLE events ALTER COLUMN event_access_type TYPE VARCHAR(32) USING event_access_type::VARCHAR(32)")
    op.execute("ALTER TABLE events ALTER COLUMN status TYPE VARCHAR(32) USING status::VARCHAR(32)")
    op.execute("ALTER TABLE event_days ALTER COLUMN scan_status TYPE VARCHAR(32) USING scan_status::VARCHAR(32)")

    # Add defaults back
    op.execute("ALTER TABLE tickets ALTER COLUMN status SET DEFAULT 'active'::character varying")
    op.execute("ALTER TABLE organizer_pages ALTER COLUMN status SET DEFAULT 'active'::character varying")
    op.execute("ALTER TABLE organizer_pages ALTER COLUMN visibility SET DEFAULT 'public'::character varying")
    op.execute("ALTER TABLE events ALTER COLUMN event_access_type SET DEFAULT 'ticketed'::character varying")
    op.execute("ALTER TABLE events ALTER COLUMN status SET DEFAULT 'draft'::character varying")
    op.execute("ALTER TABLE event_days ALTER COLUMN scan_status SET DEFAULT 'not_started'::character varying")

    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS ticketstatus")
    op.execute("DROP TYPE IF EXISTS ticketcategory")
    op.execute("DROP TYPE IF EXISTS organizerstatus")
    op.execute("DROP TYPE IF EXISTS organizervisibility")
    op.execute("DROP TYPE IF EXISTS locationmode")
    op.execute("DROP TYPE IF EXISTS eventaccesstype")
    op.execute("DROP TYPE IF EXISTS eventstatus")
    op.execute("DROP TYPE IF EXISTS scanstatus")
