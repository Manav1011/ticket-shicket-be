# Organizer Flow Test Log

**Organizer:** Priya Sharma
**Date:** 2026-04-07
**Purpose:** Walk through the complete Phase 1 organizer workflow using curl, simulating a real organizer creating a full event.

---

## Step 1: Organizer Signs Up

Priya is a new user and signs up on the platform.

**API Call:**
```bash
curl -X POST http://localhost:8080/api/user/create \
  -H "Content-Type: application/json" \
  -d '{
    "firstName": "Priya",
    "lastName": "Sharma",
    "email": "priya.sharma@example.com",
    "phone": "+919876543211",
    "password": "SecurePass123!"
  }'
```

**Actual Response:**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "id": "ab8d0968-a8fa-4a72-9526-274bf0092118",
    "firstName": "Priya",
    "lastName": "Sharma"
  }
}
```

---

## Step 2: Organizer Signs In

Priya signs in to get her access token.

**API Call:**
```bash
curl -X POST http://localhost:8080/api/user/sign-in \
  -H "Content-Type: application/json" \
  -c /tmp/cookies_priya.txt \
  -d '{
    "email": "priya.sharma@example.com",
    "password": "SecurePass123!"
  }'
```

**Actual Response:**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

**Access Token used:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhYjhkMDk2OC1hOGZhLTRhNzItOTUyNi0yNzRiZjAwOTIxMTgiLCJ1c2VyX3R5cGUiOiJ1c2VyIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTc3NTU4ODQ0Mn0.nhYRltyJj8pa5m-2qz_Bql3Yianm2aebQdUNWlqVWMg`

---

## Step 3: Check Existing Organizer Pages

**API Call:**
```bash
curl -X GET http://localhost:8080/api/organizers \
  -H "Authorization: Bearer <TOKEN>"
```

**Actual Response:**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": []
}
```

Empty list — first time user.

---

## Step 4: Create Organizer Page

Priya creates "Pune Design Collective".

**API Call:**
```bash
curl -X POST http://localhost:8080/api/organizers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "name": "Pune Design Collective",
    "slug": "Pune Design Collective",
    "bio": "Design community in Pune",
    "visibility": "public"
  }'
```

**Actual Response:**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "id": "f234b406-72f6-439e-8e4d-33f65d69c7f6",
    "ownerUserId": "ab8d0968-a8fa-4a72-9526-274bf0092118",
    "name": "Pune Design Collective",
    "slug": "pune-design-collective",
    "bio": "Design community in Pune",
    "visibility": "public",
    "status": "active"
  }
}
```

Note: slug normalized to lowercase kebab-case.

**Organizer Page ID:** `f234b406-72f6-439e-8e4d-33f65d69c7f6`

---

## Step 5: Create Draft Event (with title and event_access_type)

Priya creates "Design Systems Workshop" as a ticketed event.

**API Call:**
```bash
curl -X POST http://localhost:8080/api/events/drafts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "organizerPageId": "f234b406-72f6-439e-8e4d-33f65d69c7f6",
    "title": "Design Systems Workshop",
    "eventAccessType": "ticketed"
  }'
```

**Actual Response:**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "id": "7d6f3226-7c95-4099-8331-618c8de328db",
    "organizerPageId": "f234b406-72f6-439e-8e4d-33f65d69c7f6",
    "createdByUserId": "ab8d0968-a8fa-4a72-9526-274bf0092118",
    "title": "Design Systems Workshop",
    "status": "draft",
    "eventAccessType": "ticketed",
    "setupStatus": {},
    ...
  }
}
```

**Event ID:** `7d6f3226-7c95-4099-8331-618c8de328db`

---

## Step 6: Check Initial Readiness

**API Call:**
```bash
curl -X GET http://localhost:8080/api/events/7d6f3226-7c95-4099-8331-618c8de328db/readiness \
  -H "Authorization: Bearer <TOKEN>"
```

**Actual Response:**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "completedSections": [],
    "missingSections": ["basic_info", "schedule", "tickets"],
    "blockingIssues": [
      "Complete basic event information",
      "Add at least one event day",
      "Add ticket types and allocations or switch event to open"
    ]
  }
}
```

---

## Step 7: Add Basic Info (location_mode + timezone)

**API Call:**
```bash
curl -X PATCH http://localhost:8080/api/events/7d6f3226-7c95-4099-8331-618c8de328db/basic-info \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "locationMode": "venue",
    "timezone": "Asia/Kolkata"
  }'
```

**Actual Response:**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "setupStatus": {
      "basic_info": true,
      "schedule": false,
      "tickets": false
    },
    "locationMode": "venue",
    "timezone": "Asia/Kolkata",
    ...
  }
}
```

`basic_info` is now `true`.

---

## Step 8: Add Event Day 1

**API Call:**
```bash
curl -X POST http://localhost:8080/api/events/7d6f3226-7c95-4099-8331-618c8de328db/days \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "dayIndex": 1,
    "date": "2026-07-20",
    "startTime": "2026-07-20T10:00:00",
    "endTime": "2026-07-20T17:00:00"
  }'
```

**Actual Response:**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "id": "d062aff3-2e69-4c2b-b658-9cacc1c8759a",
    "dayIndex": 1,
    "scanStatus": "not_started",
    "nextTicketIndex": 1,
    ...
  }
}
```

**Day 1 ID:** `d062aff3-2e69-4c2b-b658-9cacc1c8759a`

---

## Step 9: Add Event Day 2

**API Call:**
```bash
curl -X POST http://localhost:8080/api/events/7d6f3226-7c95-4099-8331-618c8de328db/days \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "dayIndex": 2,
    "date": "2026-07-21",
    "startTime": "2026-07-21T10:00:00",
    "endTime": "2026-07-21T16:00:00"
  }'
```

**Actual Response:**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "id": "09c70761-9547-4408-afe1-d0b43a4377db",
    "dayIndex": 2,
    "scanStatus": "not_started",
    "nextTicketIndex": 1,
    ...
  }
}
```

**Day 2 ID:** `09c70761-9547-4408-afe1-d0b43a4377db`

---

## Step 10: Readiness After Adding Days

**API Call:**
```bash
curl -X GET http://localhost:8080/api/events/7d6f3226-7c95-4099-8331-618c8de328db/readiness
```

**Actual Response:**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "completedSections": ["schedule", "basic_info"],
    "missingSections": ["tickets"],
    "blockingIssues": [
      "Add ticket types and allocations or switch event to open"
    ]
  }
}
```

`schedule` is now `true`. Only `tickets` missing.

---

## Step 11: Create Ticket Types

**API Call (Workshop - Free):**
```bash
curl -X POST http://localhost:8080/api/events/7d6f3226-7c95-4099-8331-618c8de328db/ticket-types \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "name": "Workshop",
    "category": "PUBLIC",
    "price": 0,
    "currency": "INR"
  }'
```

**Actual Response:**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "id": "93b9e75c-3bb4-4327-ad01-d1ce10c2b202",
    "name": "Workshop",
    "price": 0.0,
    ...
  }
}
```

**API Call (Masterclass - Paid):**
```bash
curl -X POST http://localhost:8080/api/events/7d6f3226-7c95-4099-8331-618c8de328db/ticket-types \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "name": "Masterclass",
    "category": "VIP",
    "price": 2999,
    "currency": "INR"
  }'
```

**Actual Response:**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "id": "900ec2e2-ee8c-4584-9c53-31ede122e2b5",
    "name": "Masterclass",
    "price": 2999.0,
    ...
  }
}
```

**Workshop ID:** `93b9e75c-3bb4-4327-ad01-d1ce10c2b202`
**Masterclass ID:** `900ec2e2-ee8c-4584-9c53-31ede122e2b5`

---

## Step 12: Allocate Tickets

**Workshop 50 tickets → Day 1:**
```bash
curl -X POST http://localhost:8080/api/events/7d6f3226-7c95-4099-8331-618c8de328db/ticket-allocations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "eventDayId": "d062aff3-2e69-4c2b-b658-9cacc1c8759a",
    "ticketTypeId": "93b9e75c-3bb4-4327-ad01-d1ce10c2b202",
    "quantity": 50
  }'
```
→ `{"status":"SUCCESS","code":200,"data":{"id":"99dedb52-608f-413f-858a-2e0459d0a20d",...}}`

**Masterclass 20 tickets → Day 1:**
→ `{"status":"SUCCESS","code":200,"data":{"id":"ff3bde58-41d9-4179-a2f4-7a53ab5a64ba",...}}`

**Workshop 80 tickets → Day 2:**
→ `{"status":"SUCCESS","code":200,"data":{"id":"344e0dde-8e1f-4cbb-95d8-e9bd5351cfe2",...}}`

**Masterclass 30 tickets → Day 2:**
→ `{"status":"SUCCESS","code":200,"data":{"id":"a982634c-a113-451c-a435-a717607e0b08",...}}`

**Total tickets allocated: 180 (50+20+80+30)**

---

## Step 13: Readiness After Allocations (Stale State)

**API Call:**
```bash
curl -X GET http://localhost:8080/api/events/7d6f3226-7c95-4099-8331-618c8de328db/readiness
```

**Actual Response:**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "completedSections": ["schedule", "basic_info"],
    "missingSections": ["tickets"],
    "blockingIssues": [
      "Add ticket types and allocations or switch event to open"
    ]
  }
}
```

**Stale!** `tickets` still shows as missing even though we have ticket types and allocations. This is the documented limitation.

---

## Step 14: Trigger Readiness Recomputation

**API Call:**
```bash
curl -X PATCH http://localhost:8080/api/events/7d6f3226-7c95-4099-8331-618c8de328db/basic-info \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "description": "A hands-on workshop about design systems for product teams."
  }'
```

**Actual Response:**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "setupStatus": {
      "basic_info": true,
      "schedule": true,
      "tickets": true
    },
    ...
  }
}
```

`setupStatus` now shows all `true`.

---

## Step 15: Final Readiness

**Actual Response:**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "completedSections": ["tickets", "schedule", "basic_info"],
    "missingSections": [],
    "blockingIssues": []
  }
}
```

**All sections complete!**

---

## Step 16: Scan Lifecycle Control

**Start scan on Day 1:**
```bash
curl -X POST http://localhost:8080/api/events/days/d062aff3-2e69-4c2b-b658-9cacc1c8759a/start-scan
```
→ `{"status":"SUCCESS","code":200,"data":{"scanStatus":"active","scanStartedAt":"2026-04-07T18:07:40.029073",...}}`

**Pause scan on Day 1:**
```bash
curl -X POST http://localhost:8080/api/events/days/d062aff3-2e69-4c2b-b658-9cacc1c8759a/pause-scan
```
→ `{"status":"SUCCESS","code":200,"data":{"scanStatus":"paused","scanPausedAt":"2026-04-07T18:07:40.059763",...}}`

**Resume scan on Day 1:**
```bash
curl -X POST http://localhost:8080/api/events/days/d062aff3-2e69-4c2b-b658-9cacc1c8759a/resume-scan
```
→ `{"status":"SUCCESS","code":200,"data":{"scanStatus":"active",...}}`

**End scan on Day 2:**
```bash
curl -X POST http://localhost:8080/api/events/days/09c70761-9547-4408-afe1-d0b43a4377db/end-scan
```
→ `{"status":"SUCCESS","code":200,"data":{"scanStatus":"ended","scanEndedAt":"2026-04-07T18:08:45.434076",...}}`

**Try to start scan on ended day:**
```bash
curl -X POST http://localhost:8080/api/events/days/09c70761-9547-4408-afe1-d0b43a4377db/start-scan
```
→ `{"status":"Error","code":422,"message":"Invalid scan state transition."}`

Correctly rejected.

---

## Step 17: Progressive Patching

**Update Day 2 start time:**
```bash
curl -X PATCH http://localhost:8080/api/events/days/09c70761-9547-4408-afe1-d0b43a4377db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"startTime": "2026-07-21T09:30:00"}'
```
→ `{"status":"SUCCESS","code":200,"data":{"startTime":"2026-07-21T09:30:00",...}}`
Only `startTime` was updated, other fields preserved.

**Update organizer page:**
```bash
curl -X PATCH http://localhost:8080/api/organizers/f234b406-72f6-439e-8e4d-33f65d69c7f6 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"websiteUrl": "https://punedesign.co", "instagramUrl": "https://instagram.com/punedesign"}'
```
→ `{"status":"SUCCESS","code":200,"data":{"websiteUrl":"https://punedesign.co","instagramUrl":"https://instagram.com/punedesign",...}}`
Only provided fields updated.

---

## Step 18: Delete Event Day

**Add Day 3, then delete it:**
```bash
curl -X POST http://localhost:8080/api/events/7d6f3226-7c95-4099-8331-618c8de328db/days \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"dayIndex": 3, "date": "2026-07-22", "startTime": "2026-07-22T10:00:00", "endTime": "2026-07-22T14:00:00"}'
```
→ Created Day 3 with ID `17359fb4-d821-411f-b05d-649ca14ad81d`

```bash
curl -X DELETE http://localhost:8080/api/events/days/17359fb4-d821-411f-b05d-649ca14ad81d
  -H "Authorization: Bearer <TOKEN>"
```
→ `{"status":"SUCCESS","code":200,"data":{"deleted":true}}`

Day deleted successfully.

---

## Step 19: List Events Under Organizer

**API Call:**
```bash
curl -X GET http://localhost:8080/api/organizers/f234b406-72f6-439e-8e4d-33f65d69c7f6/events \
  -H "Authorization: Bearer <TOKEN>"
```

**Actual Response:**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": [
    {
      "id": "7d6f3226-7c95-4099-8331-618c8de328db",
      "title": "Design Systems Workshop",
      "status": "draft",
      "eventAccessType": "ticketed",
      "setupStatus": {
        "tickets": true,
        "schedule": true,
        "basic_info": true
      },
      "createdAt": "2026-04-07T18:01:21.131211"
    }
  ]
}
```

---

## Summary

| Step | Action | Result |
|------|--------|--------|
| 1 | Sign up | User ID: `ab8d0968-a8fa-4a72-9526-274bf0092118` |
| 2 | Sign in | JWT token received |
| 3 | Check organizers | Empty (first time) |
| 4 | Create organizer page | ID: `f234b406-...`, slug: `pune-design-collective` |
| 5 | Create draft event | ID: `7d6f3226-...`, title + type set upfront |
| 6 | Initial readiness | All sections missing |
| 7 | Add location + timezone | `basic_info: true` |
| 8-9 | Add 2 event days | `schedule: true` |
| 10 | Readiness check | `tickets` still missing (stale) |
| 11 | Create ticket types | Workshop (free), Masterclass (₹2999) |
| 12 | Allocate tickets | 180 total tickets |
| 13 | Readiness | `tickets` still stale |
| 14 | Patch description | Triggers recomputation |
| 15 | Final readiness | **All sections complete** |
| 16 | Scan lifecycle | start/pause/resume/end all work, ended→start rejected |
| 17 | Progressive patching | Organizer page + event day partial updates work |
| 18 | Delete event day | Works |
| 19 | List events | Shows the complete draft |

**All Phase 1 APIs verified working correctly.**
