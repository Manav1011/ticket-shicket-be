from server import create_app


def test_phase_one_routes_are_registered():
    app = create_app()
    paths = {route.path for route in app.routes}

    assert "/api/organizers" in paths
    assert "/api/events/drafts" in paths
    assert "/api/events/days/{event_day_id}/start-scan" in paths
    assert "/api/events/{event_id}/ticket-types" in paths
    assert "/api/events/{event_id}/ticket-allocations" in paths
