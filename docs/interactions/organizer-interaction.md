# API Testing Session

**Date:** 2026-04-10
**Purpose:** End-to-end testing of organizer event creation flow with curl, including negative tests
**Base URL:** http://localhost:8080

---

## Known Bugs Found

### BUG-001: Weak Email Validation
- **Severity:** Medium
- **Description:** Email validation accepts non-standard formats
- **Example:** `test-organizer-$(date +%s)@example.com` was accepted (literal shell syntax)
- **Location:** `apps/user/request.py` - `SignUpRequest`

### BUG-002: Weak Phone Validation
- **Severity:** Medium
- **Description:** Phone validation accepts non-standard formats
- **Example:** `+9198765$(date +%S)210` was accepted (literal shell syntax)
- **Location:** `apps/user/request.py` - `SignUpRequest`

### BUG-003: Cookie-based Auth Not Working
- **Severity:** Medium
- **Description:** Auth cookies set by `/sign-in` are not being recognized by protected endpoints
- **Example:** `curl -b cookies.txt` returns "Not authenticated" but Bearer token works
- **Location:** Likely in cookie parsing or SameSite policy

### BUG-004: Empty Title Accepted on Event Creation
- **Severity:** High
- **Description:** Creating an event with `title: ""` is allowed at the draft creation endpoint
- **Example:** Event created with empty title succeeds but publish validation properly rejects it
- **Location:** `apps/event/service.py` - `create_draft_event` - no title validation

---

## Phase 1: Authentication

### 1.1 Create User (Sign Up)

**Request:**
```bash
curl -X POST http://localhost:8080/api/user/create \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Test",
    "last_name": "Organizer",
    "email": "test-org-1699999999@example.com",
    "phone": "+919912345670",
    "password": "SecurePass123!"
  }'
```

**Response:**
```json
{"status":"SUCCESS","code":200,"data":{"id":"128086a3-c419-43b2-9fe8-70d4120c687b","firstName":"Test","lastName":"Organizer"}}
```

### 1.2 Sign In

**Request:**
```bash
curl -X POST http://localhost:8080/api/user/sign-in \
  -H "Content-Type: application/json" \
  -c /tmp/cookies.txt \
  -d '{
    "email": "test-org-1699999999@example.com",
    "password": "SecurePass123!"
  }'
```

**Response:**
```json
{"status":"SUCCESS","code":200,"data":{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...","refresh_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}}
```

### 1.3 Get Self (with Bearer Token)

**Request:**
```bash
curl -X GET http://localhost:8080/api/user/self \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

**Response:**
```json
{"status":"SUCCESS","code":200,"data":{"id":"128086a3-c419-43b2-9fe8-70d4120c687b","firstName":"Test","lastName":"Organizer"}}
```

### 1.4 Get Self (with Cookies - FAILS)

**Request:**
```bash
curl -X GET http://localhost:8080/api/user/self \
  -b /tmp/cookies.txt
```

**Response:**
```json
{"detail":"Not authenticated"}
```

---

## Phase 2: Organizer Page

### 2.1 Create Organizer Page

**Request:**
```bash
curl -X POST http://localhost:8080/api/organizers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{
    "name": "Test Events Co",
    "slug": "test-events-co-1699999",
    "bio": "A test organizer page for API testing"
  }'
```

**Response:**
```json
{"status":"SUCCESS","code":200,"data":{"id":"70f91f72-452c-4fc9-ae4b-5dfcc648dd9e","ownerUserId":"128086a3-c419-43b2-9fe8-70d4120c687b","name":"Test Events Co","slug":"test-events-co-1699999","bio":"A test organizer page for API testing","logoUrl":null,"coverImageUrl":null,"visibility":"private","status":"active"}}
```

### 2.2 Upload Organizer Logo

**Request:**
```bash
curl -X POST http://localhost:8080/api/organizers/70f91f72-452c-4fc9-ae4b-5dfcc648dd9e/logo \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "file=@/tmp/test-banner.png"
```

**Response:**
```json
{"status":"SUCCESS","code":200,"data":{"id":"70f91f72-452c-4fc9-ae4b-5dfcc648dd9e","logoUrl":"http://localhost:4566/ticket-shicket-media/organizers/70f91f72-452c-4fc9-ae4b-5dfcc648dd9e/logo_f5450c1b_test-banner.png",...}}
```

### 2.3 Upload Organizer Cover Image

**Request:**
```bash
curl -X POST http://localhost:8080/api/organizers/70f91f72-452c-4fc9-ae4b-5dfcc648dd9e/cover \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "file=@/tmp/test-banner.png"
```

**Response:**
```json
{"status":"SUCCESS","code":200,"data":{"id":"70f91f72-452c-4fc9-ae4b-5dfcc648dd9e","logoUrl":"...","coverImageUrl":"http://localhost:4566/ticket-shicket-media/organizers/70f91f72-452c-4fc9-ae4b-5dfcc648dd9e/cover_10cd9548_test-banner.png",...}}
```

---

## Phase 3: Event Creation

### 3.1 Create Draft Event

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/drafts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{
    "organizer_page_id": "70f91f72-452c-4fc9-ae4b-5dfcc648dd9e",
    "title": "My Test Event",
    "event_access_type": "ticketed"
  }'
```

**Response:**
```json
{"status":"SUCCESS","code":200,"data":{"id":"716b20d4-994a-4889-a36a-e3ff61751530","status":"draft","eventAccessType":"ticketed","setupStatus":{},...}}
```

### 3.2 Update Basic Info

**Request:**
```bash
curl -X PATCH http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/basic-info \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{
    "title": "My Awesome Tech Conference 2026",
    "event_type": "conference",
    "location_mode": "venue",
    "timezone": "Asia/Kolkata",
    "venue_name": "Tech Convention Center",
    "venue_address": "123 Innovation Street",
    "venue_city": "Bangalore",
    "venue_state": "Karnataka",
    "venue_country": "India"
  }'
```

**Response:**
```json
{"status":"SUCCESS","code":200,"data":{"setupStatus":{"basic_info":true,"schedule":false,"tickets":false,"assets":false},...}}
```

### 3.3 Create Event Day

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/days \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{
    "day_index": 1,
    "date": "2026-06-15",
    "start_time": "2026-06-15T09:00:00",
    "end_time": "2026-06-15T18:00:00"
  }'
```

**Response:**
```json
{"status":"SUCCESS","code":200,"data":{"id":"1f30045e-a75b-4b69-85a1-81dbfcc42e4b","eventId":"716b20d4-994a-4889-a36a-e3ff61751530","dayIndex":1,"date":"2026-06-15","scanStatus":"not_started","nextTicketIndex":1}}
```

### 3.4 Upload Event Banner

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/media-assets \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "file=@/tmp/test-banner.png" \
  -F "asset_type=banner" \
  -F "title=Event Main Banner"
```

**Response:**
```json
{"status":"SUCCESS","code":200,"data":{"id":"83001fa2-0d9c-4c56-aa03-534a0b48ba65","eventId":"716b20d4-994a-4889-a36a-e3ff61751530","assetType":"banner","publicUrl":"http://localhost:4566/ticket-shicket-media/events/716b20d4-994a-4889-a36a-e3ff61751530/banner_91eeb49b_test-banner.png",...}}
```

### 3.5 Check Event Readiness

**Request:**
```bash
curl -X GET http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/readiness \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

**Response:**
```json
{"status":"SUCCESS","code":200,"data":{"completedSections":["assets","schedule","basic_info"],"missingSections":["tickets"],"blockingIssues":["Add ticket types and allocations or switch event to open"]}}
```

---

## Phase 4: Ticketing

### 4.1 Create Ticket Type

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/ticket-types \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{
    "name": "VIP Pass",
    "category": "vip",
    "price": 4999.00,
    "currency": "INR"
  }'
```

**Response:**
```json
{"status":"SUCCESS","code":200,"data":{"id":"9f3e6efa-e9a8-40b2-be67-7f0f17d8763f","eventId":"716b20d4-994a-4889-a36a-e3ff61751530","name":"VIP Pass","category":"vip","price":4999.0,"currency":"INR"}}
```

### 4.2 Create Ticket Allocation

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/ticket-allocations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{
    "event_day_id": "1f30045e-a75b-4b69-85a1-81dbfcc42e4b",
    "ticket_type_id": "9f3e6efa-e9a8-40b2-be67-7f0f17d8763f",
    "quantity": 100
  }'
```

**Response:**
```json
{"status":"SUCCESS","code":200,"data":{"id":"468172a9-856d-4b44-8208-eb31a7755a6c","eventDayId":"1f30045e-a75b-4b69-85a1-81dbfcc42e4b","ticketTypeId":"9f3e6efa-e9a8-40b2-be67-7f0f17d8763f","quantity":100}}
```

---

## Phase 5: Publishing

### 5.1 Check Publish Validations

**Request:**
```bash
curl -X GET http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/publish-validations \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

**Response:**
```json
{"status":"SUCCESS","code":200,"data":{"canPublish":true,"eventId":"716b20d4-994a-4889-a36a-e3ff61751530","sections":{"basic_info":{"complete":true,"errors":[]},"schedule":{"complete":true,"errors":[]},"tickets":{"complete":true,"errors":[]},"assets":{"complete":true,"errors":[]}},"blockingIssues":[]}}
```

### 5.2 Publish Event

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/publish \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

**Response:**
```json
{"status":"SUCCESS","code":200,"data":{"id":"716b20d4-994a-4889-a36a-e3ff61751530","status":"published","isPublished":true,"publishedAt":"2026-04-10T17:02:21.360185",...}}
```

---

## Negative Tests

### N1: Sign In with Wrong Password

**Request:**
```bash
curl -X POST http://localhost:8080/api/user/sign-in \
  -H "Content-Type: application/json" \
  -d '{"email": "test-org-1699999999@example.com", "password": "WrongPassword123!"}'
```

**Response:**
```json
{"status":"Error","code":401,"message":"Invalid credentials"}
```
**Result:** PASS - Properly rejected

---

### N2: Access Without Auth

**Request:**
```bash
curl -X GET http://localhost:8080/api/user/self
```

**Response:**
```json
{"detail":"Not authenticated"}
```
**Result:** PASS - Properly rejected

---

### N3: Create Event with Non-Existent Organizer

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/drafts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{"organizer_page_id": "00000000-0000-0000-0000-000000000000", "title": "Orphan Event", "event_access_type": "ticketed"}'
```

**Response:**
```json
{"status":"Error","code":403,"message":"Organizer does not belong to current user."}
```
**Result:** PASS - Properly rejected

---

### N4: Create Event with Empty Title (BUG-004)

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/drafts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{"organizer_page_id": "70f91f72-452c-4fc9-ae4b-5dfcc648dd9e", "title": "", "event_access_type": "ticketed"}'
```

**Response:**
```json
{"status":"SUCCESS","code":200,"data":{"id":"b68957eb-75e6-453b-a57e-0099f9f76fd8","title":"",...}}
```
**Result:** FAIL - Empty title was accepted (BUG-004)

---

### N5: Publish Event Without Setup (properly blocked)

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/b68957eb-75e6-453b-a57e-0099f9f76fd8/publish \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

**Response:**
```json
{"status":"Error","code":422,"message":{"can_publish":false,"sections":{"basic_info":{"complete":false,"errors":[{"field":"title","message":"Title is required","code":"MISSING_REQUIRED_FIELD"}]},"schedule":{"complete":false,"errors":[{"field":"days","message":"At least 1 event day is required"}]},"tickets":{"complete":false,"errors":[...]},...}}}
```
**Result:** PASS - Publish validation properly rejects incomplete event

---

### N6: Create Allocation with Zero Quantity

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/ticket-allocations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{"event_day_id": "1f30045e-a75b-4b69-85a1-81dbfcc42e4b", "ticket_type_id": "9f3e6efa-e9a8-40b2-be67-7f0f17d8763f", "quantity": 0}'
```

**Response:**
```json
{"status":"Error","code":400,"message":"Allocation quantity must be greater than 0."}
```
**Result:** PASS - Properly rejected

---

### N7: Create Allocation with Negative Quantity

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/ticket-allocations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{"event_day_id": "1f30045e-a75b-4b69-85a1-81dbfcc42e4b", "ticket_type_id": "9f3e6efa-e9a8-40b2-be67-7f0f17d8763f", "quantity": -10}'
```

**Response:**
```json
{"status":"Error","code":400,"message":"Allocation quantity must be greater than 0."}
```
**Result:** PASS - Properly rejected

---

### N8: Upload Invalid File Type for Banner

**Request:**
```bash
curl -X POST http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530/media-assets \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "file=@/tmp/invalid.txt" \
  -F "asset_type=banner"
```

**Response:**
```json
{"detail":"Invalid file type: txt. Allowed types: webp, jpeg, png, jpg"}
```
**Result:** PASS - Properly rejected

---

### N9: Create Duplicate Slug for Organizer

**Request:**
```bash
curl -X POST http://localhost:8080/api/organizers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{"name": "Test Events Co Duplicate", "slug": "test-events-co-1699999", "bio": "Should fail"}'
```

**Response:**
```json
{"status":"Error","code":409,"message":"Organizer slug already exists."}
```
**Result:** PASS - Properly rejected

---

### N10: Access Another User's Event (Cross-User Access Test)

**Setup:** Created second user (other-user-1699999@example.com) and tried to access first user's event.

**Request:**
```bash
curl -X GET http://localhost:8080/api/events/716b20d4-994a-4889-a36a-e3ff61751530 \
  -H "Authorization: Bearer <SECOND_USER_TOKEN>"
```

**Response:**
```json
{"status":"Error","code":404,"message":"Event not found."}
```
**Result:** PASS - Cross-user access properly blocked (returns 404, not leaking event existence)

### N10b: List Another User's Organizer Events

**Request:**
```bash
curl -X GET http://localhost:8080/api/organizers/70f91f72-452c-4fc9-ae4b-5dfcc648dd9e/events \
  -H "Authorization: Bearer <SECOND_USER_TOKEN>"
```

**Response:**
```json
{"status":"SUCCESS","code":200,"data":[]}
```
**Result:** PASS - Returns empty list, no events leaked

---

## Summary

| Test ID | Status | Description |
|---------|--------|-------------|
| 1.1 | PASS | User creation |
| 1.2 | PASS | Sign in |
| 1.3 | PASS | Get self with Bearer token |
| 1.4 | FAIL | Get self with cookies (BUG-003) |
| 2.1 | PASS | Create organizer page |
| 2.2 | PASS | Upload organizer logo |
| 2.3 | PASS | Upload organizer cover |
| 3.1 | PASS | Create draft event |
| 3.2 | PASS | Update basic info |
| 3.3 | PASS | Create event day |
| 3.4 | PASS | Upload event banner |
| 3.5 | PASS | Check event readiness |
| 4.1 | PASS | Create ticket type |
| 4.2 | PASS | Create ticket allocation |
| 5.1 | PASS | Check publish validations |
| 5.2 | PASS | Publish event |
| N1 | PASS | Wrong password - properly rejected |
| N2 | PASS | No auth - properly rejected |
| N3 | PASS | Non-existent organizer - properly rejected |
| N4 | FAIL | Empty title - accepted (BUG-004) |
| N5 | PASS | Publish without setup - properly blocked |
| N6 | PASS | Zero quantity - properly rejected |
| N7 | PASS | Negative quantity - properly rejected |
| N8 | PASS | Invalid file type - properly rejected |
| N9 | PASS | Duplicate slug - properly rejected |
| N10 | PASS | Cross-user event access - properly blocked (404) |
| N10b | PASS | Cross-user organizer events - returns empty |

---

## Bugs Summary

| Bug ID | Severity | Description |
|--------|----------|-------------|
| BUG-001 | Medium | Weak email validation |
| BUG-002 | Medium | Weak phone validation |
| BUG-003 | Medium | Cookie-based auth not working |
| BUG-004 | High | Empty title accepted on event creation |

---

## Files Created During Testing

- `/tmp/test-banner.png` - 800x400 test image
- `/tmp/cookies.txt` - Auth cookies file
- `/tmp/invalid.txt` - Invalid file for testing
