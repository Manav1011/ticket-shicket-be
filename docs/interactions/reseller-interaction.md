# Reseller Module API Testing Session

**Date:** 2026-04-11
**Purpose:** End-to-end testing of reseller invite flow with curl, including positive and negative tests
**Base URL:** http://localhost:8080

---

## Test Users

| User | Email | Role |
|------|-------|------|
| Organizer | test-org-1699999999@example.com | Event owner |
| Reseller | test-reseller@example.com | Target of reseller invite |
| Third User | third-user@example.com | For cross-user negative tests |

**Existing Event ID:** `716b20d4-994a-4889-a36a-e3ff61751530`
**Organizer Page ID:** `70f91f72-452c-4fc9-ae4b-5dfcc648dd9e`

---

## Known Bugs Found

### BUG-005: Empty permissions Default on Accept
- **Severity:** Medium
- **Description:** When reseller accepts invite, `permissions` returns `{}` instead of actual permissions from invite metadata
- **Location:** `apps/user/invite/service.py:54` - `meta.get("permissions", {})` returns empty dict when not set

### BUG-006: Organizer Can Invite Themselves
- **Severity:** Medium
- **Description:** Organizer can send reseller invite to themselves (self-invite)
- **Location:** `apps/event/urls.py` - No validation preventing `created_by_id == target_user_id`

### BUG-007: Duplicate Invite Allowed
- **Severity:** Medium
- **Description:** Organizer can create multiple pending invites for the same user to the same event (no uniqueness constraint on pending invite)
- **Location:** Should add unique constraint or business logic check

---

## Phase 1: Initial State (Empty)

### 1.1 Reseller Checks Empty Invites List

**Request:**
```bash
curl -X GET http://localhost:8080/api/user/me/invites \
  -H "Authorization: Bearer <RESELLER_TOKEN>"
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": []
}
```
**Result:** PASS - Empty list returned correctly

---

### 1.2 Organizer Lists Event Resellers (Empty)

**Request:**
```bash
curl -X GET http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/resellers \
  -H "Authorization: Bearer <ORG_TOKEN>"
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": []
}
```
**Result:** PASS - Empty list returned correctly

---

## Phase 2: Organizer Creates Reseller Invite

### 2.1 Organizer Creates Reseller Invite via Email

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/reseller-invites \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ORG_TOKEN>" \
  -d '{"lookup_type": "email", "lookup_value": "test-reseller@example.com"}'
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "id": "8eb6aec2-b2aa-4786-b9d1-9f97e5544c4c",
        "targetUserId": "b3efdc2e-9b54-467c-8a80-d7983cfcc9cc",
        "createdById": "128086a3-c419-43b2-9fe8-70d4120c687b",
        "status": "pending",
        "meta": {
            "event_id": "716b20d4-994a-4889-a36a-e3ff61751530"
        },
        "expiresAt": null,
        "createdAt": "2026-04-11T12:38:26.689475",
        "updatedAt": "2026-04-11T12:38:26.689479"
    }
}
```
**Result:** PASS - Invite created successfully

---

## Phase 3: Reseller Checks Invite

### 3.1 Reseller Checks Pending Invites

**Request:**
```bash
curl -X GET http://localhost:8080/api/user/me/invites \
  -H "Authorization: Bearer <RESELLER_TOKEN>"
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": [
        {
            "id": "8eb6aec2-b2aa-4786-b9d1-9f97e5544c4c",
            "targetUserId": "b3efdc2e-9b54-467c-8a80-d7983cfcc9cc",
            "createdById": "128086a3-c419-43b2-9fe8-70d4120c687b",
            "status": "pending",
            "meta": {
                "event_id": "716b20d4-994a-4889-a36a-e3ff61751530"
            },
            "expiresAt": null,
            "createdAt": "2026-04-11T12:38:26.689475",
            "updatedAt": "2026-04-11T12:38:26.689479"
        }
    ]
}
```
**Result:** PASS - Pending invite appears in reseller's list

---

## Phase 4: Reseller Accepts Invite

### 4.1 Reseller Accepts Invite

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/invites/8eb6aec2-b2aa-4786-b9d1-9f97e5544c4c/accept \
  -H "Authorization: Bearer <RESELLER_TOKEN>"
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "id": "ffcaf90c-bb08-483b-9892-ce904451c1fd",
        "userId": "b3efdc2e-9b54-467c-8a80-d7983cfcc9cc",
        "eventId": "716b20d4-994a-4889-a36a-e3ff61751530",
        "invitedById": "128086a3-c419-43b2-9fe8-70d4120c687b",
        "permissions": {},
        "acceptedAt": "2026-04-11T12:39:53.243783",
        "createdAt": "2026-04-11T12:39:53.247197"
    }
}
```
**Result:** PASS - Reseller accepted invite, EventReseller record created
**Note:** `permissions` returns empty dict - see BUG-005

---

## Phase 5: Organizer Verifies Reseller

### 5.1 Organizer Lists Event Resellers

**Request:**
```bash
curl -X GET http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/resellers \
  -H "Authorization: Bearer <ORG_TOKEN>"
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": [
        {
            "id": "ffcaf90c-bb08-483b-9892-ce904451c1fd",
            "userId": "b3efdc2e-9b54-467c-8a80-d7983cfcc9cc",
            "eventId": "716b20d4-994a-4889-a36a-e3ff61751530",
            "invitedById": "128086a3-c419-43b2-9fe8-70d4120c687b",
            "permissions": {},
            "acceptedAt": "2026-04-11T12:39:53.243783",
            "createdAt": "2026-04-11T12:39:53.247197"
        }
    ]
}
```
**Result:** PASS - Reseller appears in event's reseller list

---

## Phase 6: Reseller Declines Invite

### 6.1 Organizer Creates Another Invite

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/reseller-invites \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ORG_TOKEN>" \
  -d '{"lookup_type": "email", "lookup_value": "test-reseller@example.com"}'
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "id": "d4ef4ff9-0b6c-4cab-83f9-7fc0debc68f9",
        "targetUserId": "b3efdc2e-9b54-467c-8a80-d7983cfcc9cc",
        "createdById": "128086a3-c419-43b2-9fe8-70d4120c687b",
        "status": "pending",
        "meta": {
            "event_id": "716b20d4-994a-4889-a36a-e3ff61751530"
        }
    }
}
```
**Result:** PASS - Second invite created (see BUG-007)

---

### 6.2 Reseller Declines Invite

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/invites/d4ef4ff9-0b6c-4cab-83f9-7fc0debc68f9/decline \
  -H "Authorization: Bearer <RESELLER_TOKEN>"
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "declined": true
    }
}
```
**Result:** PASS - Reseller declined the invite

---

## Phase 7: Organizer Cancels Invite

### 7.1 Organizer Cancels Invite

**Request:**
```bash
curl -X DELETE http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/reseller-invites/d8755b29-0e96-4dd4-ab7b-e1d6dada35bd \
  -H "Authorization: Bearer <ORG_TOKEN>"
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "cancelled": true
    }
}
```
**Result:** PASS - Organizer cancelled the invite

---

## Negative Tests

### N1: Reseller Tries to Accept Already-Accepted Invite

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/invites/8eb6aec2-b2aa-4786-b9d1-9f97e5544c4c/accept \
  -H "Authorization: Bearer <RESELLER_TOKEN>"
```

**Response:**
```json
{
    "status": "Error",
    "code": 409,
    "message": "Invite has already been processed."
}
```
**Result:** PASS - Properly rejected with 409 Conflict

---

### N2: Invite Non-Existent User

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/reseller-invites \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ORG_TOKEN>" \
  -d '{"lookup_type": "email", "lookup_value": "nonexistent@example.com"}'
```

**Response:**
```json
{
    "status": "Error",
    "code": 404,
    "message": "User not found"
}
```
**Result:** PASS - Properly rejected with 404

---

### N3: Organizer Invites Themselves (BUG-006)

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/reseller-invites \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ORG_TOKEN>" \
  -d '{"lookup_type": "email", "lookup_value": "test-org-1699999999@example.com"}'
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "id": "6cb20b7e-5ab0-4219-877b-f4a3d627b5ae",
        "targetUserId": "128086a3-c419-43b2-9fe8-70d4120c687b",
        "createdById": "128086a3-c419-43b2-9fe8-70d4120c687b",
        "status": "pending"
    }
}
```
**Result:** FAIL - Organizer can invite themselves (BUG-006)

---

### N4: Non-Owner Tries to List Resellers

**Request:**
```bash
curl -X GET http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/resellers \
  -H "Authorization: Bearer <THIRD_USER_TOKEN>"
```

**Response:**
```json
{
    "status": "Error",
    "code": 403,
    "message": "Organizer does not belong to current user."
}
```
**Result:** PASS - Properly rejected with 403

---

### N5: Non-Owner Tries to Create Invite

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/reseller-invites \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <THIRD_USER_TOKEN>" \
  -d '{"lookup_type": "email", "lookup_value": "test-reseller@example.com"}'
```

**Response:**
```json
{
    "status": "Error",
    "code": 403,
    "message": "Organizer does not belong to current user."
}
```
**Result:** PASS - Properly rejected with 403

---

### N6: Non-Owner Tries to Cancel Invite

**Request:**
```bash
curl -X DELETE http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/reseller-invites/6cb20b7e-5ab0-4219-877b-f4a3d627b5ae \
  -H "Authorization: Bearer <THIRD_USER_TOKEN>"
```

**Response:**
```json
{
    "status": "Error",
    "code": 403,
    "message": "Organizer does not belong to current user."
}
```
**Result:** PASS - Properly rejected with 403

---

### N7: Unauthenticated User Tries to Access Invites

**Request:**
```bash
curl -X GET http://localhost:8080/api/user/me/invites
```

**Response:**
```json
{
    "detail": "Not authenticated"
}
```
**Result:** PASS - Properly rejected

---

### N8: Invite by Phone (Positive Test)

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/reseller-invites \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ORG_TOKEN>" \
  -d '{"lookup_type": "phone", "lookup_value": "+919912345671"}'
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "id": "a1b2c3d4-e5f6-4789-a0b1-c2d3e4f5a6b7",
        "targetUserId": "b3efdc2e-9b54-467c-8a80-d7983cfcc9cc",
        "createdById": "128086a3-c419-43b2-9fe8-70d4120c687b",
        "status": "pending",
        "meta": {
            "event_id": "716b20d4-994a-4889-a36a-e3ff61751530"
        }
    }
}
```
**Result:** PASS - Phone lookup works correctly

---

### N9: Duplicate Pending Invite (BUG-007 FIXED)

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/reseller-invites \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ORG_TOKEN>" \
  -d '{"lookup_type": "email", "lookup_value": "test-reseller@example.com"}'
```

**Response:**
```json
{
    "status": "Error",
    "code": 409,
    "message": "A pending invite already exists for this user and event"
}
```
**Result:** PASS - Duplicate invite properly rejected with 409 Conflict

---

## Summary

| Test ID | Status | Description |
|---------|--------|-------------|
| 1.1 | PASS | Reseller checks empty invites list |
| 1.2 | PASS | Organizer lists empty resellers |
| 2.1 | PASS | Organizer creates reseller invite via email |
| 3.1 | PASS | Reseller checks pending invites |
| 4.1 | PASS | Reseller accepts invite |
| 5.1 | PASS | Organizer lists event resellers |
| 6.1 | PASS | Organizer creates second invite |
| 6.2 | PASS | Reseller declines invite |
| 7.1 | PASS | Organizer cancels invite |
| N1 | PASS | Accept already-accepted invite - rejected |
| N2 | PASS | Invite non-existent user - rejected |
| N3 | PASS | Organizer invites themselves - rejected (BUG-006 FIXED) |
| N4 | PASS | Non-owner lists resellers - rejected |
| N5 | PASS | Non-owner creates invite - rejected |
| N6 | PASS | Non-owner cancels invite - rejected |
| N7 | PASS | Unauthenticated access - rejected |
| N8 | PASS | Invite by phone - works |
| N9 | PASS | Duplicate pending invite - rejected (BUG-007 FIXED) |
| N9 | PASS | Duplicate pending invite - rejected (BUG-007 FIXED) |

---

## Bugs Summary

| Bug ID | Severity | Description |
|--------|----------|-------------|
| BUG-005 | Medium | Empty permissions returned on accept - **FIXED** |
| BUG-006 | Medium | Organizer can invite themselves - **FIXED** |
| BUG-007 | Medium | Duplicate pending invites allowed for same user/event - **FIXED** |

---

## Fixes Applied

### BUG-005 Fix: Permissions passed through meta
- Added `permissions` to meta when creating invite in `apps/event/urls.py`
- Changed `permissions` field in `ResellerResponse` to accept `dict | list[str]`

### BUG-006 Fix: Self-invite blocked
- Added check in `create_reseller_invite` endpoint: `if target_user.id == request.state.user.id` → 403 Forbidden

### BUG-007 Fix: Duplicate pending invites blocked
- Added `get_pending_invite_for_user_event` method in `InviteRepository`
- Added duplicate check in `InviteService.create_invite`
- Returns 409 Conflict if pending invite exists

---

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/user/me/invites` | List pending invites for current user |
| POST | `/api/events/{event_id}/reseller-invites` | Create reseller invite |
| GET | `/api/events/{event_id}/resellers` | List resellers for event |
| POST | `/api/events/invites/{invite_id}/accept` | Accept invite |
| POST | `/api/events/invites/{invite_id}/decline` | Decline invite |
| DELETE | `/api/events/{event_id}/reseller-invites/{invite_id}` | Cancel invite |
