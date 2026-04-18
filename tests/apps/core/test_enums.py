from apps.core.service import EnumService, _to_options
from apps.event.enums import EventAccessType, EventStatus


class TestToOptions:
    def test_converts_enum_to_value_label_pairs(self):
        options = _to_options(EventStatus)
        values = [o["value"] for o in options]
        assert "draft" in values
        assert "published" in values
        assert "archived" in values

    def test_label_is_titlecased(self):
        options = _to_options(EventStatus)
        draft_label = next(o["label"] for o in options if o["value"] == "draft")
        assert draft_label == "Draft"

    def test_underscore_becomes_space(self):
        options = _to_options(EventAccessType)
        ticketed = next(o for o in options if o["value"] == "ticketed")
        assert ticketed["label"] == "Ticketed"


class TestEnumService:
    def test_ticket_category_uses_public_subset(self):
        service = EnumService()
        result = service.list_enums()
        values = [option["value"] for option in result["ticket_category"]]
        assert values == ["online", "public", "vip"]

    def test_list_enums_returns_all_categories(self):
        service = EnumService()
        result = service.list_enums()
        assert "event_status" in result
        assert "event_access_type" in result
        assert "ticket_category" in result
        assert "asset_type" in result
        assert "event_type" in result
        assert "location_mode" in result
        assert "scan_status" in result

    def test_each_category_has_value_and_label(self):
        service = EnumService()
        result = service.list_enums()
        for category, options in result.items():
            assert len(options) > 0, f"{category} is empty"
            for option in options:
                assert "value" in option, f"{category} option missing value"
                assert "label" in option, f"{category} option missing label"
                assert isinstance(option["value"], str)
                assert isinstance(option["label"], str)
