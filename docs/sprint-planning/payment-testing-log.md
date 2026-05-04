# Payment Gateway Testing Log

Date: 2026-05-04
Purpose: End-to-end manual testing of Razorpay payment gateway integration (Phases 1-5)

## Users Created

| User | Email | Phone | ID |
|------|-------|-------|----|
| Organizer | organizer@test.com | +919876543210 | 5baeda54-6bbe-4ff6-9936-7a461ba0233b |
| Reseller | reseller@test.com | +919876543211 | 09397718-94d9-4abc-8536-1b30e763f39b |
| Customer | customer@test.com | +919876543212 | e59fceef-4b0b-4b6b-a4a9-69007f4ac1a2 |

## Auth Tokens

| User | Access Token |
|------|-------------|
| Organizer | (see /tmp/token_organizer) |
| Reseller | (see /tmp/token_reseller) |
| Customer | (see /tmp/token_customer) |
| Superadmin | (new login required, token differs each session) |

## Superadmin Creation

```bash
uv run main.py create-super-admin 2b233c03-060f-412b-ab1b-d703373c0387 "Test Superadmin"
```

**Output:** `✅ Super admin created: 3c6c2e55-9f94-4555-85f6-374e8ff117fa (Test Superadmin)`

---

## Step 1: Create Users

### Organizer User

```bash
curl -s -X POST http://0.0.0.0:8080/api/user/create \
  -H "Content-Type: application/json" \
  -d '{
    "firstName": "Test",
    "lastName": "Organizer",
    "email": "organizer@test.com",
    "phone": "+919876543210",
    "password": "Test@1234"
  }'
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "id": "5baeda54-6bbe-4ff6-9936-7a461ba0233b",
        "firstName": "Test",
        "lastName": "Organizer"
    }
}
```

### Reseller User

```bash
curl -s -X POST http://0.0.0.0:8080/api/user/create \
  -H "Content-Type: application/json" \
  -d '{
    "firstName": "Test",
    "lastName": "Reseller",
    "email": "reseller@test.com",
    "phone": "+919876543211",
    "password": "Test@1234"
  }'
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "id": "09397718-94d9-4abc-8536-1b30e763f39b",
        "firstName": "Test",
        "lastName": "Reseller"
    }
}
```

### Customer User

```bash
curl -s -X POST http://0.0.0.0:8080/api/user/create \
  -H "Content-Type: application/json" \
  -d '{
    "firstName": "Test",
    "lastName": "Customer",
    "email": "customer@test.com",
    "phone": "+919876543212",
    "password": "Test@1234"
  }'
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "id": "e59fceef-4b0b-4b6b-a4a9-69007f4ac1a2",
        "firstName": "Test",
        "lastName": "Customer"
    }
}
```

### DB Verification After User Creation

```bash
uv run python scripts/db_query_engine.py "SELECT id, first_name, last_name, email, phone, created_at FROM users WHERE email LIKE '%@test.com'"
```

**Response:**
```
id                                   | first_name | last_name | email              | phone         | created_at
-------------------------------------+------------+-----------+--------------------+---------------+---------------------------
5baeda54-6bbe-4ff6-9936-7a461ba0233b | Test       | Organizer | organizer@test.com | +919876543210 | 2026-05-04 12:00:56.729077
09397718-94d9-4abc-8536-1b30e763f39b | Test       | Reseller  | reseller@test.com  | +919876543211 | 2026-05-04 12:00:56.957731
e59fceef-4b0b-4b6b-a4a9-69007f4ac1a2 | Test       | Customer  | customer@test.com  | +919876543212 | 2026-05-04 12:00:57.173366
```

✅ All 3 users created successfully

---

## Step 2: Login All Users

### Login Organizer

```bash
curl -s -X POST http://0.0.0.0:8080/api/user/sign-in \
  -H "Content-Type: application/json" \
  -d '{
    "email": "organizer@test.com",
    "password": "Test@1234"
  }'
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1YmFlZGE1NC02YmJlLTRmZjYtOTkzNi03YTQ2MWJhMDIzM2IiLCJ1c2VyX3R5cGUiOiJ1c2VyIiwianRpIjoiNzc4MzFkMWYtYTI2Mi00MzMwLTllMjAtMjllM2RhYzQ0MzljIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTc3Nzg5OTY2MX0.pB3fctRmpkQA80Cq5t6YtIdsX5_-bIHwShscHplaseo",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1YmFlZGE1NC02YmJlLTRmZjYtOTkzNi03YTQ2MWJhMDIzM2IiLCJ1c2VyX3R5cGUiOiJ1c2VyIiwianRpIjoiNzc4MzFkMWYtYTI2Mi00MzMwLTllMjAtMjllM2RhYzQ0MzljIiwidHlwZSI6InJlZnJlc2giLCJleHAiOjE3Nzc5ODI0NjF9.C-QCOxcXMvA0okz68bVz4PV-cww5ZttTHau4NFhu228"
    }
}
```

Tokens saved to:
- Organizer: `/tmp/token_organizer`
- Reseller: `/tmp/token_reseller`
- Customer: `/tmp/token_customer`

---

## Step 3: Create Organizer Page

### Create Organizer Page

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)

curl -s -X POST http://0.0.0.0:8080/api/organizers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{
    "name": "Test Organizer Page",
    "bio": "Test bio for payment gateway testing"
  }'
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "id": "058fcbcc-586d-4fc7-842f-e59f4b602fc4",
        "ownerUserId": "5baeda54-6bbe-4ff6-9936-7a461ba0233b",
        "name": "Test Organizer Page",
        "slug": "test-organizer-page",
        "bio": "Test bio for payment gateway testing",
        "visibility": "private",
        "status": "active"
    }
}
```

**DB Verification:**
```bash
uv run python scripts/db_query_engine.py "SELECT id, name, slug, owner_user_id, created_at FROM organizer_pages WHERE owner_user_id = '5baeda54-6bbe-4ff6-9936-7a461ba0233b'"
```

**Response:**
```
id                                   | name                | slug                | owner_user_id                        | created_at
-------------------------------------+---------------------+---------------------+--------------------------------------+---------------------------
058fcbcc-586d-4fc7-842f-e59f4b602fc4 | Test Organizer Page | test-organizer-page | 5baeda54-6bbe-4ff6-9936-7a461ba0233b | 2026-05-04 12:03:28.121776
```

✅ Organizer page created

---

## Step 4b: Invite Reseller to Event

### Invite Reseller

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
EVENT_ID="c252eec3-726f-4352-8b3f-7ea0a5e5bef2"
RESELLER_ID="09397718-94d9-4abc-8536-1b30e763f39b"

curl -s -X POST "http://0.0.0.0:8080/api/events/${EVENT_ID}/reseller-invites" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{
    "userIds": ["'$RESELLER_ID'"],
    "permissions": ["view_sales", "issue_tickets"]
  }'
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": [{
        "id": "d0f12f2e-f82d-438c-a180-10aa10531664",
        "targetUserId": "09397718-94d9-4abc-8536-1b30e763f39b",
        "status": "pending",
        "inviteType": "reseller"
    }]
}
```

### Reseller Accepts Invite

```bash
RESELLER_TOKEN=$(cat /tmp/token_reseller)
INVITE_ID="d0f12f2e-f82d-438c-a180-10aa10531664"

curl -s -X POST "http://0.0.0.0:8080/api/user/invites/${INVITE_ID}/accept" \
  -H "Authorization: Bearer $RESELLER_TOKEN"
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "id": "9eefa2ea-d794-4a6e-b3b1-5b57655bed4b",
        "userId": "09397718-94d9-4abc-8536-1b30e763f39b",
        "eventId": "c252eec3-726f-4352-8b3f-7ea0a5e5bef2",
        "permissions": ["view_sales", "issue_tickets"]
    }
}
```

✅ Reseller invited and accepted

---

## Step 4: Create Event + Event Days

### Create Draft Event

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
ORG_PAGE_ID="058fcbcc-586d-4fc7-842f-e59f4b602fc4"

curl -s -X POST http://0.0.0.0:8080/api/events/drafts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{
    "organizerPageId": "'$ORG_PAGE_ID'",
    "title": "Razorpay Payment Test Event",
    "eventAccessType": "ticketed"
  }'
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "id": "c252eec3-726f-4352-8b3f-7ea0a5e5bef2",
        "organizerPageId": "058fcbcc-586d-4fc7-842f-e59f4b602fc4",
        "title": "Razorpay Payment Test Event",
        "status": "draft",
        "eventAccessType": "ticketed"
    }
}
```

### Create Event Days

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
EVENT_ID="c252eec3-726f-4352-8b3f-7ea0a5e5bef2"

# Day 1
curl -s -X POST "http://0.0.0.0:8080/api/events/${EVENT_ID}/days" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"date": "2026-06-01"}'

# Day 2
curl -s -X POST "http://0.0.0.0:8080/api/events/${EVENT_ID}/days" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"date": "2026-06-02"}'
```

**Response (Day 1):**
```json
{"status": "SUCCESS", "code": 200, "data": {"id": "efdac189-417b-488c-82a2-52765667f238", "eventId": "c252eec3-726f-4352-8b3f-7ea0a5e5bef2", "dayIndex": 0, "date": "2026-06-01"}}

**Response (Day 2):**
```json
{"status": "SUCCESS", "code": 200, "data": {"id": "1e4fabb5-d2e8-4543-a2b0-f5f261ef5496", "eventId": "c252eec3-726f-4352-8b3f-7ea0a5e5bef2", "dayIndex": 1, "date": "2026-06-02"}}
```

---

## Step 5: Organizer Requests B2B Tickets from Superadmin

### Create B2B Request

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
EVENT_ID="c252eec3-726f-4352-8b3f-7ea0a5e5bef2"
DAY1_ID="efdac189-417b-488c-82a2-52765667f238"

curl -s -X POST "http://0.0.0.0:8080/api/organizers/b2b/events/${EVENT_ID}/requests" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{
    "eventId": "'$EVENT_ID'",
    "eventDayId": "'$DAY1_ID'",
    "quantity": 20
  }'
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "id": "272aa334-1fb9-431e-9230-4754e7bdd07a",
        "requesting_user_id": "5baeda54-6bbe-4ff6-9936-7a461ba0233b",
        "event_id": "c252eec3-726f-4352-8b3f-7ea0a5e5bef2",
        "event_day_id": "efdac189-417b-488c-82a2-52765667f238",
        "quantity": 20,
        "status": "pending"
    }
}
```

---

## Step 6: Superadmin Approves B2B Request (FREE)

### Approve B2B Request

```bash
SUPERADMIN_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyYjIzM2MwMy0wNjBmLTQxMmItYWIxYi1kNzAzMzczYzAzODciLCJ1c2VyX3R5cGUiOiJ1c2VyIiwianRpIjoiMTgwZThiNzktNmU5YS00NjFjLWE2ZTgtYzFmM2ViYmQ5ZWFhIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTc3NzkwMDY3OX0.XfDT4RE2bFjwW__iSHqwxJPBRKk-VYQ_PHV-HzoDKCI"
REQUEST_ID="272aa334-1fb9-431e-9230-4754e7bdd07a"

curl -s -X POST "http://0.0.0.0:8080/api/superadmin/b2b/requests/${REQUEST_ID}/approve-free" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SUPERADMIN_TOKEN" \
  -d '{}'
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "id": "272aa334-1fb9-431e-9230-4754e7bdd07a",
        "status": "approved_free",
        "allocation_id": "2fdceeb6-c4ff-4d96-b47b-7a7da37f96af",
        "order_id": "76e83c06-e13e-4a34-bdb8-829f8e9d6b15"
    }
}
```

---

## Step 7: Verify Organizer's B2B Tickets

### Get Organizer's B2B Tickets

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
EVENT_ID="c252eec3-726f-4352-8b3f-7ea0a5e5bef2"

curl -s "http://0.0.0.0:8080/api/organizers/b2b/events/${EVENT_ID}/my-tickets" \
  -H "Authorization: Bearer $ORG_TOKEN"
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "eventId": "c252eec3-726f-4352-8b3f-7ea0a5e5bef2",
        "holderId": "ce4b68b4-49d1-4cee-8234-107c573c13d6",
        "tickets": [
            {"eventDayId": "efdac189-417b-488c-82a2-52765667f238", "count": 20}
        ],
        "total": 20
    }
}
```

### DB Verification

```bash
uv run python scripts/db_query_engine.py "SELECT count(*) FROM tickets WHERE event_id = 'c252eec3-726f-4352-8b3f-7ea0a5e5bef2'"
```

**Response:**
```
count
-----
20
```

✅ Organizer now has 20 B2B tickets for Day 1

---

## Step 8: Transfer B2B Tickets to Reseller (FREE)

### Transfer 5 B2B Tickets to Reseller

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
EVENT_ID="c252eec3-726f-4352-8b3f-7ea0a5e5bef2"
DAY1_ID="efdac189-417b-488c-82a2-52765667f238"
RESELLER_ID="09397718-94d9-4abc-8536-1b30e763f39b"

curl -s -X POST "http://0.0.0.0:8080/api/organizers/b2b/events/${EVENT_ID}/transfers/reseller" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{
    "resellerId": "'$RESELLER_ID'",
    "quantity": 5,
    "eventDayId": "'$DAY1_ID'",
    "mode": "free"
  }'
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "transferId": "85890716-4954-48ef-8577-505c11f9708b",
        "status": "completed",
        "ticketCount": 5,
        "resellerId": "09397718-94d9-4abc-8536-1b30e763f39b",
        "mode": "free"
    }
}
```

### DB Verification

Organizer's remaining B2B tickets:
```bash
curl -s "http://0.0.0.0:8080/api/organizers/b2b/events/c252eec3-726f-4352-8b3f-7ea0a5e5bef2/my-tickets" \
  -H "Authorization: Bearer $ORG_TOKEN"
```
**Response:** `{"eventId":"c252eec3-726f-4352-8b3f-7ea0a5e5bef2","holderId":"ce4b68b4-49d1-4cee-8234-107c573c13d6","tickets":[{"eventDayId":"efdac189-417b-488c-82a2-52765667f238","count":15}],"total":15}`

Reseller's B2B tickets:
```bash
curl -s "http://0.0.0.0:8080/api/resellers/events/c252eec3-726f-4352-8b3f-7ea0a5e5bef2/tickets" \
  -H "Authorization: Bearer $RESELLER_TOKEN"
```
**Response:** `{"event_id":"c252eec3-726f-4352-8b3f-7ea0a5e5bef2","holder_id":"062b0d95-b019-48cc-bdea-811e32d75bcd","tickets":[{"event_day_id":"efdac189-417b-488c-82a2-52765667f238","count":5}],"total":5}`

✅ Organizer transferred 5 B2B tickets to Reseller (Organizer: 15 remaining, Reseller: 5)

---

## Step 9: Transfer B2B Tickets to Reseller (PAID - Razorpay)

### Transfer 10 B2B Tickets to Reseller (PAID - ₹50)

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
EVENT_ID="c252eec3-726f-4352-8b3f-7ea0a5e5bef2"
DAY1_ID="efdac189-417b-488c-82a2-52765667f238"
RESELLER_ID="09397718-94d9-4abc-8536-1b30e763f39b"

curl -s -X POST "http://0.0.0.0:8080/api/organizers/b2b/events/${EVENT_ID}/transfers/reseller" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{
    "resellerId": "'$RESELLER_ID'",
    "quantity": 10,
    "eventDayId": "'$DAY1_ID'",
    "mode": "paid",
    "price": 50
  }'
```

**Response:**
```json
{
    "status": "SUCCESS",
    "code": 200,
    "data": {
        "transferId": "8a3c0a82-f2d1-435c-838a-58aa558c9a83",
        "status": "pending_payment",
        "ticketCount": 10,
        "resellerId": "09397718-94d9-4abc-8536-1b30e763f39b",
        "mode": "paid",
        "paymentUrl": "https://rzp.io/rzp/GzBhowq1"
    }
}
```

### Payment Webhook Events (4 events fired, only 1 processed)

Razorpay fired 4 events for the single payment:

| Event | Status | Action |
|-------|--------|--------|
| `payment.authorized` | 200 OK | **Ignored** — intermediate event |
| `payment.captured` | 200 OK | **Ignored** — intermediate event |
| `order.paid` | 200 OK | **Ignored** — gateway_type routing: `RAZORPAY_PAYMENT_LINK` order ignores `order.paid` |
| `payment_link.paid` | 200 OK | **Processed** ✅ — correct event for payment link |

### DB Verification

**Order:**
```bash
uv run python scripts/db_query_engine.py "SELECT id, status, gateway_type, final_amount, gateway_payment_id, captured_at FROM orders WHERE id = '8a3c0a82-f2d1-435c-838a-58aa558c9a83'"
```
```
id                                   | status | gateway_type          | final_amount | gateway_payment_id   | captured_at
-------------------------------------+--------+----------------------+--------------+--------------------+--------------------------
8a3c0a82-f2d1-435c-838a-58aa558c9a83 | paid   | RAZORPAY_PAYMENT_LINK | 50           | pay_SlPWCPWKoRRlwO | 2026-05-04 19:58:03.053438
```

**Allocation:**
```bash
uv run python scripts/db_query_engine.py "SELECT id, status, from_holder_id, to_holder_id, ticket_count FROM allocations WHERE order_id = '8a3c0a82-f2d1-435c-838a-58aa558c9a83'"
```
```
id                                   | status    | from_holder_id                       | to_holder_id                         | ticket_count
-------------------------------------+-----------+--------------------------------------+--------------------------------------+-------------
573ec5fe-b453-4402-a3c7-e9e1cc92caec | completed | ce4b68b4-49d1-4cee-8234-107c573c13d6 | 062b0d95-b019-48cc-bdea-811e32d75bcd | 10
```

**Ticket ownership:**
- Reseller (062b0d95): 15 tickets total (5 free + 10 paid)
- Organizer (ce4b68b4): 5 tickets remaining

✅ Step 9 complete — PAID B2B transfer to reseller working via Razorpay payment link

---

## Step 10: Transfer B2B Tickets to Customer (FREE)

<!-- To be filled -->

---

## Step 11: Transfer B2B Tickets to Customer (PAID - Razorpay)

<!-- To be filled -->

---

## Step 12: Reseller Transfer to Customer (FREE)

<!-- To be filled -->

---

## Step 13: Reseller Transfer to Customer (PAID - Razorpay)

<!-- To be filled -->

---

## Step 14: Webhook Registration

Razorpay webhook URL to register:
```
https://<ngrok-id>.ngrok-free.app/api/payment_gateway/webhooks/razorpay
```

Events to subscribe:
- `payment_link.paid`
- `payment_link.cancelled`
