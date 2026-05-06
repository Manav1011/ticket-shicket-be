# Payment Gateway Testing Log

Date: 2026-05-06
Purpose: End-to-end manual testing of Razorpay payment gateway integration (Phases 1-5)

## Test Environment

- Server: `http://0.0.0.0:8080`
- Database queries: `uv run python scripts/db_query_engine.py "<sql>"`

---

## Users Created

| User | Email | Phone | ID |
|------|-------|-------|----|
| Organizer | organizer@test.com | +919876543210 | b0d77100-11eb-47f1-874d-f8a36f1b79d9 |
| Reseller | reseller@test.com | +919876543211 | 78f0538e-0b41-4cf4-a9f2-f4dcf8062639 |
| Customer | customer@test.com | +919876543212 | 55f84a0c-4b91-4fdd-ba76-177f33a61648 |
| Superadmin | superadmin@test.com | +919876543299 | d75608b9-8c39-4943-b25d-13445a41f250 |

**Create Superadmin:**
```bash
# 1. Create user
curl -s -X POST http://0.0.0.0:8080/api/user/create \
  -H "Content-Type: application/json" \
  -d '{"firstName": "Super", "lastName": "Admin", "email": "superadmin@test.com", "phone": "+919876543299", "password": "Test@1234"}'

# 2. Make superadmin (use user ID from step 1)
uv run main.py create-super-admin d75608b9-8c39-4943-b25d-13445a41f250 "Test Superadmin"
```

## Auth Tokens

| User | Token File |
|------|-----------|
| Organizer | `/tmp/token_organizer` |
| Reseller | `/tmp/token_reseller` |
| Customer | `/tmp/token_customer` |
| Superadmin | `/tmp/token_superadmin` |

---

## Entities Created

| Entity | ID |
|--------|-----|
| Organizer Page | `9e85f818-9325-41b1-9d64-8d6778ba8b24` |
| Event | `48fec5ac-2142-4b27-9f64-e87c021070e7` |
| Day 1 (June 1) | `35f2ccd7-fa30-4e29-861e-500be7ad91eb` |
| Day 2 (June 2) | `e2d1c37b-fe88-4319-bcb1-1aed982be98b` |

---

## Step 1: Create Users

### Organizer User
```bash
curl -s -X POST http://0.0.0.0:8080/api/user/create \
  -H "Content-Type: application/json" \
  -d '{"firstName": "Test", "lastName": "Organizer", "email": "organizer@test.com", "phone": "+919876543210", "password": "Test@1234"}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"id":"b0d77100-11eb-47f1-874d-f8a36f1b79d9","firstName":"Test","lastName":"Organizer"}}`

### Reseller User
```bash
curl -s -X POST http://0.0.0.0:8080/api/user/create \
  -H "Content-Type: application/json" \
  -d '{"firstName": "Test", "lastName": "Reseller", "email": "reseller@test.com", "phone": "+919876543211", "password": "Test@1234"}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"id":"78f0538e-0b41-4cf4-a9f2-f4dcf8062639","firstName":"Test","lastName":"Reseller"}}`

### Customer User
```bash
curl -s -X POST http://0.0.0.0:8080/api/user/create \
  -H "Content-Type: application/json" \
  -d '{"firstName": "Test", "lastName": "Customer", "email": "customer@test.com", "phone": "+919876543212", "password": "Test@1234"}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"id":"55f84a0c-4b91-4fdd-ba76-177f33a61648","firstName":"Test","lastName":"Customer"}}`

### Superadmin User
```bash
curl -s -X POST http://0.0.0.0:8080/api/user/create \
  -H "Content-Type: application/json" \
  -d '{"firstName": "Super", "lastName": "Admin", "email": "superadmin@test.com", "phone": "+919876543299", "password": "Test@1234"}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"id":"d75608b9-8c39-4943-b25d-13445a41f250","firstName":"Super","lastName":"Admin"}}`

**Make Superadmin:**
```bash
uv run main.py create-super-admin d75608b9-8c39-4943-b25d-13445a41f250 "Test Superadmin"
```
**Output:** `✅ Super admin created: 2cae3fdc-a525-42d6-bece-a2907b6a74a8 (Test Superadmin)`

✅ All 4 users created

---

## Step 2: Login All Users

```bash
# Organizer
curl -s -X POST http://0.0.0.0:8080/api/user/sign-in \
  -H "Content-Type: application/json" \
  -d '{"email": "organizer@test.com", "password": "Test@1234"}' > /tmp/token_organizer

# Reseller
curl -s -X POST http://0.0.0.0:8080/api/user/sign-in \
  -H "Content-Type: application/json" \
  -d '{"email": "reseller@test.com", "password": "Test@1234"}' > /tmp/token_reseller

# Customer
curl -s -X POST http://0.0.0.0:8080/api/user/sign-in \
  -H "Content-Type: application/json" \
  -d '{"email": "customer@test.com", "password": "Test@1234"}' > /tmp/token_customer

# Superadmin
curl -s -X POST http://0.0.0.0:8080/api/user/sign-in \
  -H "Content-Type: application/json" \
  -d '{"email": "superadmin@test.com", "password": "Test@1234"}' > /tmp/token_superadmin
```

✅ Tokens saved

---

## Step 3: Create Organizer Page

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
curl -s -X POST http://0.0.0.0:8080/api/organizers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"name": "Test Organizer Page", "bio": "Test bio for payment gateway testing"}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"id":"9e85f818-9325-41b1-9d64-8d6778ba8b24",...}}`

✅ Page created: `9e85f818-9325-41b1-9d64-8d6778ba8b24`

---

## Step 4: Create Event + Event Days

### Create Draft Event
```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
ORG_PAGE_ID="9e85f818-9325-41b1-9d64-8d6778ba8b24"
curl -s -X POST http://0.0.0.0:8080/api/events/drafts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"organizerPageId": "'$ORG_PAGE_ID'", "title": "Razorpay Payment Test Event", "eventAccessType": "ticketed"}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"id":"48fec5ac-2142-4b27-9f64-e87c021070e7",...}}`

### Create Day 1
```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
EVENT_ID="48fec5ac-2142-4b27-9f64-e87c021070e7"
curl -s -X POST "http://0.0.0.0:8080/api/events/${EVENT_ID}/days" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"date": "2026-06-01"}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"id":"35f2ccd7-fa30-4e29-861e-500be7ad91eb",...}}`

### Create Day 2
```bash
curl -s -X POST "http://0.0.0.0:8080/api/events/${EVENT_ID}/days" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"date": "2026-06-02"}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"id":"e2d1c37b-fe88-4319-bcb1-1aed982be98b",...}}`

✅ Event + 2 days created

---

## Step 4b: Invite Reseller to Event

### Invite Reseller
```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
RESELLER_ID="78f0538e-0b41-4cf4-a9f2-f4dcf8062639"
curl -s -X POST "http://0.0.0.0:8080/api/events/${EVENT_ID}/reseller-invites" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"userIds": ["'$RESELLER_ID'"], "permissions": ["view_sales", "issue_tickets"]}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":[{"id":"c0f18553-d3db-4e1e-abde-7978186db93e",...}]}`

### Reseller Accepts Invite
```bash
RESELLER_TOKEN=$(cat /tmp/token_reseller)
INVITE_ID="c0f18553-d3db-4e1e-abde-7978186db93e"
curl -s -X POST "http://0.0.0.0:8080/api/user/invites/${INVITE_ID}/accept" \
  -H "Authorization: Bearer $RESELLER_TOKEN"
```
**Response:** `{"status":"SUCCESS","code":200,...}`

✅ Reseller invited and accepted

---

## Step 5: Organizer Requests B2B Tickets from Superadmin

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
EVENT_ID="48fec5ac-2142-4b27-9f64-e87c021070e7"
DAY1_ID="35f2ccd7-fa30-4e29-861e-500be7ad91eb"
curl -s -X POST "http://0.0.0.0:8080/api/organizers/b2b/events/${EVENT_ID}/requests" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"eventId": "'$EVENT_ID'", "eventDayId": "'$DAY1_ID'", "quantity": 20}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"id":"7b31bc56-b5fa-47b9-9508-8f9d59ea3e91","status":"pending",...}}`

✅ B2B request created: `7b31bc56-b5fa-47b9-9508-8f9d59ea3e91`

---

## Step 6: Superadmin Approves B2B Request (FREE)

```bash
SUPERADMIN_TOKEN=$(cat /tmp/token_superadmin)
REQUEST_ID="7b31bc56-b5fa-47b9-9508-8f9d59ea3e91"
curl -s -X POST "http://0.0.0.0:8080/api/superadmin/b2b/requests/${REQUEST_ID}/approve-free" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SUPERADMIN_TOKEN" \
  -d '{}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"id":"7b31bc56-b5fa-47b9-9508-8f9d59ea3e91","status":"approved_free","allocation_id":"889bf59b-7855-475d-bece-71bdf6d23d41","order_id":"df3f23ec-2e6b-4194-b22d-b8b30a8eb816",...}}`

### DB Verification
```bash
uv run python scripts/db_query_engine.py "SELECT count(*) as ticket_count FROM tickets WHERE event_id = '48fec5ac-2142-4b27-9f64-e87c021070e7'"
```
**Response:** `ticket_count: 20`

✅ 20 B2B tickets allocated to Organizer

---

## Step 7: Verify Organizer's B2B Tickets

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
curl -s "http://0.0.0.0:8080/api/organizers/b2b/events/${EVENT_ID}/my-tickets" \
  -H "Authorization: Bearer $ORG_TOKEN"
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"eventId":"48fec5ac-2142-4b27-9f64-e87c021070e7","holderId":"df82b652-bbac-4e5f-b357-df844cce8ec4","tickets":[{"eventDayId":"35f2ccd7-fa30-4e29-861e-500be7ad91eb","count":20}],"total":20}}`

✅ Organizer has 20 tickets (Day 1)

---

## Step 8: Transfer B2B Tickets to Reseller (FREE)

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
RESELLER_ID="78f0538e-0b41-4cf4-a9f2-f4dcf8062639"
curl -s -X POST "http://0.0.0.0:8080/api/organizers/b2b/events/${EVENT_ID}/transfers/reseller" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"resellerId": "'$RESELLER_ID'", "quantity": 5, "eventDayId": "'$DAY1_ID'", "mode": "free"}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"transferId":"6439a810-9448-4369-9f3d-251da750c2b3","status":"completed","ticketCount":5,"resellerId":"78f0538e-0b41-4cf4-a9f2-f4dcf8062639","mode":"free",...}}`

### DB Verification
```bash
uv run python scripts/db_query_engine.py "SELECT owner_holder_id, count(*) as ticket_count FROM tickets WHERE event_id = '48fec5ac-2142-4b27-9f64-e87c021070e7' AND event_day_id = '35f2ccd7-fa30-4e29-861e-500be7ad91eb' GROUP BY owner_holder_id"
```
**Response:**
```
owner_holder_id                      | ticket_count
-------------------------------------+-------------
df82b652-bbac-4e5f-b357-df844cce8ec4 | 15   (Organizer)
eb5f4148-4a88-4783-810e-653db26b1dad | 5    (Reseller)
```

✅ Organizer: 15 remaining, Reseller: 5 received

---

## Step 9: Transfer B2B Tickets to Reseller (PAID - Razorpay)

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
curl -s -X POST "http://0.0.0.0:8080/api/organizers/b2b/events/${EVENT_ID}/transfers/reseller" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"resellerId": "'$RESELLER_ID'", "quantity": 10, "eventDayId": "'$DAY1_ID'", "mode": "paid", "price": 50}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"transferId":"edb797c5-cb2e-492d-86bc-455b44cde359","status":"pending_payment","ticketCount":10,"mode":"paid","paymentUrl":"https://rzp.io/rzp/XCuxJ9zi",...}}`

**Payment Link:** `https://rzp.io/rzp/XCuxJ9zi`

### Webhook Events (4 fired, 1 processed)

| Event | Action |
|-------|--------|
| `payment.authorized` | Ignored — intermediate |
| `order.paid` | Ignored — gateway_type routing |
| `payment.captured` | Ignored — intermediate |
| `payment_link.paid` | **Processed ✅** |

### DB Verification

**Order:**
```bash
uv run python scripts/db_query_engine.py "SELECT id, status, gateway_type, final_amount, gateway_payment_id FROM orders WHERE id = 'edb797c5-cb2e-492d-86bc-455b44cde359'"
```
**Response:**
```
id                                   | status | gateway_type          | final_amount | gateway_payment_id
-------------------------------------+--------+----------------------+--------------+------------------
edb797c5-cb2e-492d-86bc-455b44cde359 | paid   | RAZORPAY_PAYMENT_LINK | 50           | pay_Sm3HhkI4wSnOmq
```

**Allocation:**
```bash
uv run python scripts/db_query_engine.py "SELECT id, status, from_holder_id, to_holder_id, ticket_count FROM allocations WHERE order_id = 'edb797c5-cb2e-492d-86bc-455b44cde359'"
```
**Response:**
```
id                                   | status    | from_holder_id | to_holder_id                       | ticket_count
-------------------------------------+-----------+----------------+--------------------------------------+-------------
efcf7cf8-2516-41da-9f75-e41e669999b9 | completed | df82b652...   | eb5f4148-4a88-4783-810e-653db26b1dad | 10
```

**Final ownership:**
- Organizer: 5 tickets
- Reseller: 15 tickets (5 free + 10 paid)

✅ PAID B2B transfer to reseller working via Razorpay payment link

---

## Step 10: Transfer B2B Tickets to Customer (FREE)

> **Note:** Organizer ran out of tickets, had to request more B2B tickets from superadmin.

### Request More B2B Tickets
```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
curl -s -X POST "http://0.0.0.0:8080/api/organizers/b2b/events/${EVENT_ID}/requests" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"eventId": "'$EVENT_ID'", "eventDayId": "'$DAY1_ID'", "quantity": 10}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"id":"670db4eb-caa1-464f-8999-509fde26eb7f","status":"pending",...}}`

### Superadmin Approves
```bash
SUPERADMIN_TOKEN=$(cat /tmp/token_superadmin)
curl -s -X POST "http://0.0.0.0:8080/api/superadmin/b2b/requests/670db4eb-caa1-464f-8999-509fde26eb7f/approve-free" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SUPERADMIN_TOKEN" \
  -d '{}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"id":"670db4eb-caa1-464f-8999-509fde26eb7f","status":"approved_free",...}}`

Organizer now has 10 tickets.

### Transfer to Customer (FREE)
```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
curl -s -X POST "http://0.0.0.0:8080/api/organizers/b2b/events/${EVENT_ID}/transfers/customer" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"email": "customer@test.com", "quantity": 5, "eventDayId": "'$DAY1_ID'", "mode": "free"}'
```

**Server prints:**
```
[CUSTOMER TRANSFER] Claim URL: http://0.0.0.0:8080/api/open/claim/hyzjuiye
```

### Verify Claim API
```bash
curl -s "http://0.0.0.0:8080/api/open/claim/hyzjuiye"
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"ticketCount":5,"jwt":"eyJ...",...}}`

### DB Verification
```bash
uv run python scripts/db_query_engine.py "SELECT id, status, owner_holder_id, claim_link_id FROM tickets WHERE claim_link_id IS NOT NULL ORDER BY created_at DESC LIMIT 5"
```
**Response:** 5 tickets assigned to customer holder `0bb046cd...` with claim_link_id `9473a931...`

**Claim Link (DB):**
```bash
uv run python scripts/db_query_engine.py "SELECT id, status, jwt_jti, to_holder_id FROM claim_links WHERE id = '9473a931-4d64-4699-b5ff-0fe7cea71474'"
```
**Response:** `9473a931-4d64-4699-b5ff-0fe7cea71474 | active | 6ff21ccfeb547589 | 0bb046cd...`

✅ Customer claim link works — JWT returned with ticket indices

---

## Step 11: Transfer B2B Tickets to Customer (PAID - Razorpay)

### Request More B2B Tickets
Organizer had 0 tickets, had to request more from superadmin.
```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
curl -s -X POST "http://0.0.0.0:8080/api/organizers/b2b/events/${EVENT_ID}/requests" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"eventId": "'$EVENT_ID'", "eventDayId": "'$DAY1_ID'", "quantity": 10}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"id":"ae62f510-c125-4f80-9814-f898de4e4a2d","status":"pending",...}}`

### Superadmin Approves
```bash
SUPERADMIN_TOKEN=$(cat /tmp/token_superadmin)
curl -s -X POST "http://0.0.0.0:8080/api/superadmin/b2b/requests/ae62f510-c125-4f80-9814-f898de4e4a2d/approve-free" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SUPERADMIN_TOKEN" \
  -d '{}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"id":"ae62f510-c125-4f80-9814-f898de4e4a2d","status":"approved_free",...}}`

Organizer now has 10 tickets.

### Transfer to Customer (PAID)
```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
curl -s -X POST "http://0.0.0.0:8080/api/organizers/b2b/events/${EVENT_ID}/transfers/customer" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"email": "customer@test.com", "quantity": 5, "eventDayId": "'$DAY1_ID'", "mode": "paid", "price": 75}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"transferId":"902f0abe-d216-42f6-9e1b-fee863786a46","status":"pending_payment","ticketCount":5,"mode":"paid","paymentUrl":"https://rzp.io/rzp/qJYZg4m",...}}`

**Payment Link:** `https://rzp.io/rzp/qJYZg4m`

### Webhook Events (4 fired, 1 processed)

| Event | Action |
|-------|--------|
| `payment.authorized` | Ignored — intermediate |
| `order.paid` | Ignored — gateway_type routing |
| `payment.captured` | Ignored — intermediate |
| `payment_link.paid` | **Processed ✅** |

**Server prints:**
```
[PAID CUSTOMER TRANSFER] Payment link: https://rzp.io/rzp/qJYZg4m
[PAID CUSTOMER TRANSFER WEBHOOK] Claim URL: http://0.0.0.0:8080/api/open/claim/m5sy28a5
```

### DB Verification

**Order:**
```bash
uv run python scripts/db_query_engine.py "SELECT id, status, gateway_type, final_amount, gateway_payment_id FROM orders WHERE id = '902f0abe-d216-42f6-9e1b-fee863786a46'"
```
**Response:**
```
id                                   | status | gateway_type          | final_amount | gateway_payment_id
-------------------------------------+--------+----------------------+--------------+------------------
902f0abe-d216-42f6-9e1b-fee863786a46 | paid   | RAZORPAY_PAYMENT_LINK | 75           | pay_Sm3yRpwY0ucBKX
```

**Allocation:**
```bash
uv run python scripts/db_query_engine.py "SELECT id, status, from_holder_id, to_holder_id, ticket_count FROM allocations WHERE order_id = '902f0abe-d216-42f6-9e1b-fee863786a46'"
```
**Response:**
```
id                                   | status    | from_holder_id | to_holder_id                       | ticket_count
-------------------------------------+-----------+----------------+--------------------------------------+-------------
6860af35-0c30-4e4d-8061-c263583beab3 | completed | df82b652...   | 0bb046cd-b938-4ad5-998c-f0f453be14d9 | 5
```

### Verify Claim API
```bash
curl -s "http://0.0.0.0:8080/api/open/claim/m5sy28a5"
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"ticketCount":5,"indices":[31,32,33,34,35],...}}`

✅ PAID B2B transfer to customer working via Razorpay payment link + claim API

---

## Step 12: Reseller Transfer to Customer (FREE)

### Transfer to Customer (FREE)
```bash
RESELLER_TOKEN=$(cat /tmp/token_reseller)
curl -s -X POST "http://0.0.0.0:8080/api/resellers/b2b/events/${EVENT_ID}/transfers/customer" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RESELLER_TOKEN" \
  -d '{"email": "customer@test.com", "quantity": 5, "eventDayId": "'$DAY1_ID'", "mode": "free"}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"transferId":"a95d986f-6d5c-4222-956d-df7a11f5fd8b","status":"completed","ticketCount":5,"mode":"free",...}}`

**Server prints:**
```
[RESELLER TO CUSTOMER FREE TRANSFER] Claim URL: http://0.0.0.0:8080/api/open/claim/tqrlzarp
```

### Verify Claim API
```bash
curl -s "http://0.0.0.0:8080/api/open/claim/tqrlzarp"
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"ticketCount":5,"indices":[1,2,3,4,5],...}}`

### DB Verification
**Allocation:**
```bash
uv run python scripts/db_query_engine.py "SELECT id, status, from_holder_id, to_holder_id, ticket_count FROM allocations WHERE order_id = 'a95d986f-6d5c-4222-956d-df7a11f5fd8b'"
```
**Response:**
```
id                                   | status    | from_holder_id | to_holder_id                       | ticket_count
-------------------------------------+-----------+----------------+--------------------------------------+-------------
d79803de-ec42-473a-8e92-7b8350e558ae | completed | eb5f4148...   | 0bb046cd-b938-4ad5-998c-f0f453be14d9 | 5
```

**Ticket ownership:**
```
0bb046cd... | 25   (Customer)
eb5f4148... | 10   (Reseller)
df82b652... | 5    (Organizer)
```

> **Note:** Bug found and fixed in `claim_service.py` — claim API was returning ALL tickets owned by the customer for that event day (via fallback condition), not just tickets from this specific transfer. Fixed by removing the fallback condition.

✅ Reseller → Customer FREE transfer working correctly

---

## Step 13: Reseller Transfer to Customer (PAID - Razorpay)

### Transfer to Customer (PAID)
```bash
RESELLER_TOKEN=$(cat /tmp/token_reseller)
curl -s -X POST "http://0.0.0.0:8080/api/resellers/b2b/events/${EVENT_ID}/transfers/customer" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RESELLER_TOKEN" \
  -d '{"email": "customer@test.com", "quantity": 5, "eventDayId": "'$DAY1_ID'", "mode": "paid", "price": 100}'
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"transferId":"aec02b30-7eac-49c3-81fd-26702fe027d6","status":"pending_payment","ticketCount":5,"mode":"paid","paymentUrl":"https://rzp.io/rzp/Aou5pFiB",...}}`

**Payment Link:** `https://rzp.io/rzp/Aou5pFiB`

### Webhook Events (4 fired, 1 processed)

| Event | Action |
|-------|--------|
| `payment.authorized` | Ignored — intermediate |
| `order.paid` | Ignored — gateway_type routing |
| `payment.captured` | Ignored — intermediate |
| `payment_link.paid` | **Processed ✅** |

**Server prints:**
```
[PAID CUSTOMER TRANSFER WEBHOOK] Claim URL: http://0.0.0.0:8080/api/open/claim/e0w02wsj
```

### DB Verification

**Order:**
```bash
uv run python scripts/db_query_engine.py "SELECT id, status, gateway_type, final_amount, gateway_payment_id FROM orders WHERE id = 'aec02b30-7eac-49c3-81fd-26702fe027d6'"
```
**Response:**
```
id                                   | status | gateway_type          | final_amount | gateway_payment_id
-------------------------------------+--------+----------------------+--------------+------------------
aec02b30-7eac-49c3-81fd-26702fe027d6 | paid   | RAZORPAY_PAYMENT_LINK | 100         | pay_Sm4HOl3Ou21ebR
```

**Allocation:**
```bash
uv run python scripts/db_query_engine.py "SELECT id, status, from_holder_id, to_holder_id, ticket_count FROM allocations WHERE order_id = 'aec02b30-7eac-49c3-81fd-26702fe027d6'"
```
**Response:**
```
id                                   | status    | from_holder_id | to_holder_id                       | ticket_count
-------------------------------------+-----------+----------------+--------------------------------------+-------------
74ed24ed-9744-42f8-bd4d-06ec0ef21462 | completed | eb5f4148...   | 0bb046cd-b938-4ad5-998c-f0f453be14d9 | 5
```

**Verify Claim API:**
```bash
curl -s "http://0.0.0.0:8080/api/open/claim/e0w02wsj"
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"ticketCount":5,"indices":[6,7,8,9,10],...}}`

> **Bug found:** Claim link created but `claim_link_id` not set on tickets — `update_ticket_ownership_batch` wasn't receiving `claim_link_id` from webhook handler. Fixed in `razorpay.py`.

✅ Reseller → Customer PAID transfer working

---

### Step 13 Re-test (2 tickets @ ₹50)

```bash
curl -s -X POST "http://0.0.0.0:8080/api/resellers/b2b/events/${EVENT_ID}/transfers/customer" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RESELLER_TOKEN" \
  -d '{"email": "customer@test.com", "quantity": 2, "eventDayId": "'$DAY1_ID'", "mode": "paid", "price": 50}'
```
**Payment Link:** `https://rzp.io/rzp/pn4B6qLG`

**Server prints:**
```
[PAID CUSTOMER TRANSFER WEBHOOK] Claim URL: http://0.0.0.0:8080/api/open/claim/g1cvpvty
```

**Verify Claim API:**
```bash
curl -s "http://0.0.0.0:8080/api/open/claim/g1cvpvty"
```
**Response:** `{"status":"SUCCESS","code":200,"data":{"ticketCount":2,"indices":[11,12],...}}`

✅ Re-test passed — claim_link_id properly set on tickets

---

## Step 14: Webhook Registration

Razorpay webhook URL to register:
```
https://<ngrok-id>.ngrok-free.app/api/payment_gateway/webhooks/razorpay
```

Events to subscribe:
- `payment_link.paid`
- `payment_link.cancelled`

---

## Current Ticket Holdings (after Step 13)

| Holder | Tickets (Day 1) |
|--------|----------------|
| Organizer (`df82b652...`) | 5 |
| Reseller (`eb5f4148...`) | 3 |
| Customer (`0bb046cd...`) | 32 |

---

## Notes

- Claim URL is printed in server terminal for FREE customer transfers (no link returned in API response)
- PAID transfers print claim URL from webhook handler after payment confirmation
- `claim_links` table uses `token_hash` not plain `token` — actual token is returned by claim API in JWT
- `jwt_jti` is set on first redemption of a claim link (lazy backfill) — legacy claim links created before this fix have `NULL` jwt_jti until first redemption

## Bugs Found & Fixed

1. **Claim API returning all customer tickets** (`claim_service.py`)
   - Bug: Fallback condition in claim query returned ALL tickets owned by customer for that event day, not just tickets from specific transfer
   - Fix: Removed fallback condition — now only returns tickets with matching `claim_link_id`

2. **PAID transfer not setting claim_link_id on tickets** (`razorpay.py`)
   - Bug: `update_ticket_ownership_batch` wasn't receiving `claim_link_id` from webhook handler
   - Fix: Added `claim_link_id=claim_link.id` parameter to the call
