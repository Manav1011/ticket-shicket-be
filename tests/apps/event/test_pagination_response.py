# tests/apps/event/test_pagination_response.py
from apps.event.response import PaginationMeta, PaginatedEventResponse


def test_pagination_meta_fields():
    meta = PaginationMeta(total=100, limit=20, offset=0, has_more=True)
    assert meta.total == 100
    assert meta.has_more is True


def test_paginated_event_response_fields():
    resp = PaginatedEventResponse(events=[], pagination=PaginationMeta(total=0, limit=20, offset=0, has_more=False))
    assert resp.events == []
    assert resp.pagination.has_more is False
