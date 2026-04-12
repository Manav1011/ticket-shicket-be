from server import create_app


def test_phase_one_routes_are_registered():
    app = create_app()
    paths = {route.path for route in app.routes}

    assert "/api/organizers" in paths
    assert "/api/organizers/{organizer_id}" in paths
    assert "/api/organizers/{organizer_id}/events" in paths
    assert "/api/events/drafts" in paths
    assert "/api/events/{event_id}" in paths
    assert "/api/events/{event_id}/basic-info" in paths
    assert "/api/events/{event_id}/interest" in paths
    assert "/api/events/{event_id}/readiness" in paths
    assert "/api/events/{event_id}/days" in paths
    assert "/api/events/days/{event_day_id}" in paths
    assert "/api/events/days/{event_day_id}/start-scan" in paths
    assert "/api/events/days/{event_day_id}/pause-scan" in paths
    assert "/api/events/days/{event_day_id}/resume-scan" in paths
    assert "/api/events/days/{event_day_id}/end-scan" in paths
    assert "/api/events/{event_id}/ticket-types" in paths
    assert "/api/events/{event_id}/ticket-allocations" in paths
