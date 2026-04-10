# Publish Event API Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the publish API with the validation framework and ensure `is_published` field is properly set when an event is published.

**Architecture:** The publish API uses a draft-first workflow where events are created in `draft` status and can only be published when all required sections (basic_info, schedule, tickets) are complete. Validation is performed section-by-section with detailed error reporting.

**Tech Stack:** FastAPI, SQLAlchemy (async), Pydantic, PostgreSQL ENUM types

---

## Current State Assessment

### Already Implemented

| Component | Status | Location |
|-----------|--------|----------|
| `is_published` field on EventModel | ✅ Done | `src/apps/event/models.py:56-58` |
| `published_at` field on EventModel | ✅ Done | `src/apps/event/models.py:55` |
| `publish_event` service method | ✅ Done | `src/apps/event/service.py:202-216` |
| `validate_for_publish` service method | ✅ Done | `src/apps/event/service.py:153-200` |
| `GET /{event_id}/publish-validations` endpoint | ✅ Done | `src/apps/event/urls.py:76-84` |
| `POST /{event_id}/publish` endpoint | ✅ Done | `src/apps/event/urls.py:87-95` |
| Price >= 0 validation (C2) | ✅ Done | `src/apps/ticketing/service.py:30-31` |
| Quantity > 0 validation (I1) | ✅ Done | `src/apps/ticketing/service.py:77-78` |
| Duplicate allocation handling (C3) | ✅ Done | `src/apps/ticketing/service.py:81-88` |
| event_day belongs to event validation (C1) | ✅ Done | `src/apps/ticketing/service.py:69-74` |
| location_mode enum validation (I3) | ✅ Done | `src/apps/event/service.py:88-91` |
| `InvalidPrice` exception | ✅ Done | `src/apps/ticketing/exceptions.py:13-14` |
| `InvalidQuantity` exception | ✅ Done | `src/apps/ticketing/exceptions.py:17-18` |
| `DuplicateAllocation` exception | ✅ Done | `src/apps/ticketing/exceptions.py:21-22` |
| `CannotPublishEvent` exception | ✅ Done | `src/apps/event/exceptions.py:17-18` |

### Verification Needed

Before proceeding, verify the `is_published` field exists in the database by running:

```bash
.venv/bin/python -m pytest tests/apps/event/ -v
```

---

## Files to Verify

| File | Purpose |
|------|---------|
| `src/apps/event/models.py:56-58` | Confirm `is_published` Boolean field exists |
| `src/apps/event/service.py:202-216` | Confirm `publish_event` sets `is_published=True` |
| `src/apps/event/urls.py:87-95` | Confirm publish endpoint exists |

---

## Tasks

### Task 1: Verify `is_published` Field in Model

- [ ] **Step 1: Check EventModel definition**

Verify `src/apps/event/models.py` contains:
```python
is_published: Mapped[bool] = mapped_column(
    Boolean, default=False, server_default=text("false"), nullable=False
)
```

### Task 2: Verify `publish_event` Service Method

- [ ] **Step 1: Check publish_event implementation**

Verify `src/apps/event/service.py` `publish_event` method sets:
```python
event.status = "published"
event.is_published = True
event.published_at = datetime.utcnow()
```

### Task 3: Run Integration Tests

- [ ] **Step 1: Run event service tests**

```bash
.venv/bin/python -m pytest tests/apps/event/test_event_service.py -v
```

Expected: All tests pass including publish-related tests.

- [ ] **Step 2: Run event URL tests**

```bash
.venv/bin/python -m pytest tests/apps/event/test_event_urls.py -v
```

Expected: All tests pass including publish endpoint tests.

---

## Summary

The publish API integration with validations is **already fully implemented**:

1. **`is_published` field** - Added to `EventModel` with default `False`
2. **Publish endpoint** - `POST /{event_id}/publish` calls `service.publish_event()`
3. **Publish validations** - `GET /{event_id}/publish-validations` returns section-by-section errors
4. **Validation framework** - All critical and important validations (C1, C2, C3, I1, I2, I3) are implemented

The system prevents publishing an event until:
- Basic info is complete (title, event_access_type, location_mode, timezone)
- At least one event day exists with required fields
- For ticketed events: at least one ticket type and allocation exists

---

## Not in Scope

- Archive event functionality (future phase)
- Unpublish functionality (events are permanent once published)
- Event deletion after publishing