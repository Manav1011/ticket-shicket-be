from db.base import Base
import db.model_registry  # noqa: F401


def test_model_registry_loads_organizer_table():
    assert "organizer_pages" in Base.metadata.tables
