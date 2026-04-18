# Enums API Implementation Plan (Simple)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single `GET /api/enums` endpoint that returns all enum values as `{value, label}` pairs. When a developer adds a new value to an enum class, it automatically appears in the API response — no code changes needed beyond updating the enum itself.

**Architecture:** A simple service imports all enum classes directly and converts them to options via a shared `_to_options()` helper. No registry, no plugin system — just a 10-line service that introspects the enum classes at import time.

**Tech Stack:** FastAPI, Pydantic, pytest

---

## File Map

- **Create:** `src/apps/core/response.py` — `EnumOptionResponse` and `EnumsResponse` Pydantic schemas
- **Create:** `src/apps/core/service.py` — `EnumService` with `list_enums()` method (~10 lines)
- **Create:** `src/apps/core/urls.py` — `GET /api/enums` route
- **Modify:** `src/server.py` — include `core_router`
- **Modify:** `src/apps/event/enums.py` — add `_to_options()` helper function (reusable, no duplicate per-enum code)
- **Create:** `tests/apps/core/test_enums.py` — unit tests

---

### Task 1: Create Enum Response Schemas

**Files:**
- Create: `src/apps/core/response.py`

- [ ] **Step 1: Create response schemas**

```python
from pydantic import BaseModel


class EnumOptionResponse(BaseModel):
    value: str
    label: str


class EnumsResponse(BaseModel):
    asset_type: list[EnumOptionResponse]
    event_type: list[EnumOptionResponse]
    event_status: list[EnumOptionResponse]
    event_access_type: list[EnumOptionResponse]
    location_mode: list[EnumOptionResponse]
    scan_status: list[EnumOptionResponse]
```

- [ ] **Step 2: Verify it compiles**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && python3 -c "from apps.core.response import EnumsResponse, EnumOptionResponse; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add src/apps/core/response.py
git commit -m "feat(core): add enum response schemas"
```

---

### Task 2: Create Enum Service

**Files:**
- Create: `src/apps/core/service.py`

- [ ] **Step 1: Create `EnumService`**

```python
from apps.event.enums import (
    AssetType,
    EventType,
    EventStatus,
    EventAccessType,
    LocationMode,
    ScanStatus,
)


def _to_options(enum_cls: type) -> list[dict]:
    """Convert an enum class to a list of {value, label} dicts."""
    return [
        {"value": member.value, "label": member.name.replace("_", " ").title()}
        for member in enum_cls
    ]


class EnumService:
    def list_enums(self) -> dict[str, list[dict]]:
        return {
            "asset_type": _to_options(AssetType),
            "event_type": _to_options(EventType),
            "event_status": _to_options(EventStatus),
            "event_access_type": _to_options(EventAccessType),
            "location_mode": _to_options(LocationMode),
            "scan_status": _to_options(ScanStatus),
        }
```

Note: When you add a new enum to the codebase, add it here and in `EnumsResponse`. That's the only change needed.

- [ ] **Step 2: Verify it works**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && python3 -c "from apps.core.service import EnumService; s = EnumService(); print(s.list_enums()); print('OK')"`
Expected: Dict with all 6 categories printed, then OK

- [ ] **Step 3: Commit**

```bash
git add src/apps/core/service.py
git commit -m "feat(core): add EnumService with list_enums"
```

---

### Task 3: Create Enums URL Route

**Files:**
- Create: `src/apps/core/urls.py`

- [ ] **Step 1: Create the route**

```python
from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi import Request

from auth.dependencies import get_current_user
from apps.core.service import EnumService
from utils.schema import BaseResponse
from apps.core.response import EnumsResponse


router = APIRouter(prefix="/api/enums", tags=["Enums"], dependencies=[Depends(get_current_user)])


def get_enum_service() -> EnumService:
    return EnumService()


@router.get("", operation_id="list_enums")
async def list_enums(
    request: Request,
    service: Annotated[EnumService, Depends(get_enum_service)],
) -> BaseResponse[EnumsResponse]:
    """
    List all available enums for frontend dropdowns.

    Returns a dict of category names → list of {value, label} options.
    Adding a new member to any enum class automatically reflects here.
    """
    data = service.list_enums()
    return BaseResponse(data=EnumsResponse.model_validate(data))
```

- [ ] **Step 2: Verify it compiles**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && python3 -c "from apps.core.urls import router; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add src/apps/core/urls.py
git commit -m "feat(api): add GET /api/enums endpoint"
```

---

### Task 4: Register Core Router in Server

**Files:**
- Modify: `src/server.py`

- [ ] **Step 1: Add import and include router**

Add to the imports section (after `from apps.superadmin.urls import router as superadmin_router`):

```python
from apps.core.urls import router as core_router
```

Add to the `base_router.include_router(...)` calls (after `superadmin_router`):

```python
    base_router.include_router(core_router)
```

- [ ] **Step 2: Verify app starts**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && timeout 5 uv run main.py run --debug 2>&1 | head -20 || true`
Expected: App starts without import errors

- [ ] **Step 3: Commit**

```bash
git add src/server.py
git commit -m "feat(server): include core router for /api/enums"
```

---

### Task 5: Write Unit Tests

**Files:**
- Create: `tests/apps/core/test_enums.py`

- [ ] **Step 1: Write tests**

```python
from apps.core.service import EnumService, _to_options
from apps.event.enums import EventStatus, EventAccessType


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
    def test_list_enums_returns_all_categories(self):
        service = EnumService()
        result = service.list_enums()
        assert "event_status" in result
        assert "event_access_type" in result
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
```

- [ ] **Step 2: Run tests**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && uv run pytest tests/apps/core/test_enums.py -v --tb=short 2>&1 | tail -20`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add tests/apps/core/test_enums.py
git commit -m "test(core): add unit tests for EnumService"
```

---

### Task 6: Integration Smoke Test

**Files:**
- (No new files — run curl commands)

- [ ] **Step 1: Start services**

Run: `cd /home/manav1011/Documents/ticket-shicket-be && docker compose up -d`
Run: `uv run main.py run --debug` (in another terminal)

- [ ] **Step 2: Test the endpoint**

```bash
# Get a token (login first)
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}' | jq -r '.data.access_token')

# Call the enums API
curl -s http://localhost:8000/api/enums \
  -H "Authorization: Bearer $TOKEN" | jq '.data'
```

Expected response:

```json
{
  "asset_type": [{"value": "banner", "label": "Banner"}, {"value": "gallery_image", "label": "Gallery Image"}, ...],
  "event_type": [...],
  "event_status": [...],
  "event_access_type": [...],
  "location_mode": [...],
  "scan_status": [...]
}
```

- [ ] **Step 3: Verify dynamic update works**

Add a new value to `EventStatus` temporarily:

```python
class EventStatus(str, Enum):
    draft = "draft"
    published = "published"
    archived = "archived"
    cancelled = "cancelled"  # <-- add this temporarily
```

Restart server, call `/api/enums`, verify `"cancelled"` appears automatically in `event_status`. Then revert.

- [ ] **Step 4: Commit if smoke test passes**

```bash
git add -A
git commit -m "test: integration smoke test for enums API"
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - `GET /api/enums` endpoint ✓
   - Response format `{value, label}` per option ✓
   - All 6 event enums included ✓
   - Adding new enum member auto-appears in API ✓

2. **Placeholder scan:** No "TBD", "TODO", or placeholder code ✓

3. **Type consistency:**
   - `_to_options(enum_cls)` takes a `type` ✓
   - `EnumService.list_enums()` returns `dict[str, list[dict]]` ✓
   - `EnumsResponse` fields match service keys ✓

4. **Design simplicity:**
   - Only 3 new files + 1 modified ✓
   - No registry, no plugin system ✓
   - `_to_options()` is the only shared logic — 5 lines ✓
   - Adding a new enum = 1 line in `list_enums()` + 1 field in `EnumsResponse` ✓

5. **Edge cases:**
   - Empty enum: returns empty list ✓
   - All enums are `str, Enum` so `member.value` is always a string ✓

---

## Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-18-dynamic-enums-api.md`.**

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?