# Online Ticket Purchase — Testing Log

Date: 2026-05-10 (fresh run after DB clear)
Purpose: End-to-end manual testing of online ticket purchase (Phases 1–5 + zero-amount fix)

## Test Environment

- Server: `http://0.0.0.0:8080`
- Database queries: `uv run python scripts/db_query_engine.py "<sql>"`
- Auth tokens: stored in `/tmp/token_<user>`

---

## Step 1: Create Users

### Customer User (buyer for online purchase)
```bash
curl -s -X POST http://0.0.0.0:8080/api/user/create \
  -H "Content-Type: application/json" \
  -d '{"firstName": "Test", "lastName": "Buyer", "email": "buyer@test.com", "phone": "+919876543213", "password": "Test@1234"}'
```

### Login Customer
```bash
curl -s -X POST http://0.0.0.0:8080/api/user/sign-in \
  -H "Content-Type: application/json" \
  -d '{"email": "buyer@test.com", "password": "Test@1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])" > /tmp/token_buyer
```

---

## Step 2: Create Organizer + Event

### Organizer User
```bash
curl -s -X POST http://0.0.0.0:8080/api/user/create \
  -H "Content-Type: application/json" \
  -d '{"firstName": "Test", "lastName": "Organizer", "email": "organizer@test.com", "phone": "+919876543210", "password": "Test@1234"}'
```

### Login Organizer
```bash
curl -s -X POST http://0.0.0.0:8080/api/user/sign-in \
  -H "Content-Type: application/json" \
  -d '{"email": "organizer@test.com", "password": "Test@1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])" > /tmp/token_organizer
```

### Create Organizer Page
```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
curl -s -X POST http://0.0.0.0:8080/api/organizers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"name": "Online Purchase Test Org", "bio": "Testing online ticket purchase"}'
```

---

## Step 3: Create Draft Event

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
ORG_PAGE_ID="de9d7cb1-4fde-4251-a32f-d6eda03901af"
curl -s -X POST http://0.0.0.0:8080/api/events/drafts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"organizerPageId": "'$ORG_PAGE_ID'", "title": "Online Purchase Test Event", "eventAccessType": "ticketed"}'
```

---

## Step 4: Set Basic Info (required to publish)

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
EVENT_ID="d5dc100b-9783-4457-a5c4-e1969642ca84"
curl -s -X PATCH "http://0.0.0.0:8080/api/events/${EVENT_ID}/basic-info" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"locationMode": "venue", "timezone": "Asia/Kolkata", "venueName": "The Test Arena", "venueAddress": "123 Test St", "venueCity": "Mumbai", "venueCountry": "India"}'
```

---

## Step 5: Upload Banner Image (required to publish)

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
EVENT_ID="d5dc100b-9783-4457-a5c4-e1969642ca84"
# Create test image: python3 -c "from PIL import Image; img = Image.new('RGB', (400, 300), color=(100, 150, 200)); img.save('/tmp/test-banner.png')"
curl -s -X POST "http://0.0.0.0:8080/api/events/${EVENT_ID}/media-assets" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -F "asset_type=banner" \
  -F "file=@/tmp/test-banner.png"
```

---

## Step 6: Create Event Day

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
EVENT_ID="d5dc100b-9783-4457-a5c4-e1969642ca84"
curl -s -X POST "http://0.0.0.0:8080/api/events/${EVENT_ID}/days" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"date": "2026-06-15", "startTime": "2026-06-15T18:00:00", "endTime": "2026-06-15T22:00:00"}'
```

---

## Step 7: Create Public Ticket Type

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
EVENT_ID="d5dc100b-9783-4457-a5c4-e1969642ca84"
curl -s -X POST "http://0.0.0.0:8080/api/events/${EVENT_ID}/ticket-types" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"name": "General Admission", "category": "public", "price": 499.00, "currency": "INR"}'
```

---

## Step 8: Allocate Tickets to Day (creates pool tickets)

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
EVENT_ID="d5dc100b-9783-4457-a5c4-e1969642ca84"
DAY_ID="07e7d207-e6d2-45b8-9e90-46709dd4ab6a"
TICKET_TYPE_ID="18606f8f-1ce0-46d4-92c2-6cd94e468acf"
curl -s -X POST "http://0.0.0.0:8080/api/events/${EVENT_ID}/ticket-allocations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -d '{"eventDayId": "'$DAY_ID'", "ticketTypeId": "'$TICKET_TYPE_ID'", "quantity": 10}'
```

**DB Verification (10 pool tickets created):**
```bash
uv run python scripts/db_query_engine.py "SELECT count(*) as pool_tickets FROM tickets WHERE event_id = 'd5dc100b-9783-4457-a5c4-e1969642ca84' AND owner_holder_id IS NULL"
```

---

## Step 9: Publish Event

```bash
ORG_TOKEN=$(cat /tmp/token_organizer)
EVENT_ID="d5dc100b-9783-4457-a5c4-e1969642ca84"
curl -s -X POST "http://0.0.0.0:8080/api/events/${EVENT_ID}/publish" \
  -H "Authorization: Bearer $ORG_TOKEN"
```

**DB Verification:**
```bash
uv run python scripts/db_query_engine.py "SELECT status, is_published FROM events WHERE id = 'd5dc100b-9783-4457-a5c4-e1969642ca84'"
```

---

## Step 10: Create Coupon (100% discount for zero-amount test)

```bash
uv run python scripts/db_query_engine.py "
INSERT INTO coupons (id, code, type, value, max_discount, min_order_amount, usage_limit, per_user_limit, used_count, valid_from, valid_until, is_active, created_at, updated_at)
VALUES (
  'a0000000-0000-0000-0000-000000000001',
  'FULL100',
  'PERCENTAGE',
  100.00,
  NULL,
  0,
  100,
  10,
  0,
  '2026-01-01 00:00:00',
  '2026-12-31 23:59:59',
  true,
  now(),
  now()
)
" --commit
```

---

## Test 1: Preview Order (validate price breakdown)

**Without coupon:**
```bash
BUYER_TOKEN=$(cat /tmp/token_buyer)
curl -s -X POST http://0.0.0.0:8080/api/events/purchase/preview \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BUYER_TOKEN" \
  -d '{"event_id": "d5dc100b-9783-4457-a5c4-e1969642ca84", "event_day_id": "07e7d207-e6d2-45b8-9e90-46709dd4ab6a", "ticket_type_id": "18606f8f-1ce0-46d4-92c2-6cd94e468acf", "quantity": 2}'
```

Result: `{"subtotalAmount":"998.00","discountAmount":"0.00","finalAmount":"998.00","couponApplied":null}`

**With 100% coupon:**
```bash
BUYER_TOKEN=$(cat /tmp/token_buyer)
curl -s -X POST http://0.0.0.0:8080/api/events/purchase/preview \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BUYER_TOKEN" \
  -d '{"event_id": "d5dc100b-9783-4457-a5c4-e1969642ca84", "event_day_id": "07e7d207-e6d2-45b8-9e90-46709dd4ab6a", "ticket_type_id": "18606f8f-1ce0-46d4-92c2-6cd94e468acf", "quantity": 2, "coupon_code": "FULL100"}'
```

Result: `{"subtotalAmount":"998.00","discountAmount":"998.00","finalAmount":"0.00","couponApplied":{"code":"FULL100","type":"PERCENTAGE","value":100.0,"maxDiscount":null}}`

---

## Test 2: Create Order — PAID (normal flow with real payment)

```bash
BUYER_TOKEN=$(cat /tmp/token_buyer)
curl -s -X POST http://0.0.0.0:8080/api/events/purchase/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BUYER_TOKEN" \
  -d '{"event_id": "d5dc100b-9783-4457-a5c4-e1969642ca84", "event_day_id": "07e7d207-e6d2-45b8-9e90-46709dd4ab6a", "ticket_type_id": "18606f8f-1ce0-46d4-92c2-6cd94e468acf", "quantity": 2}'
```

Result: `{"orderId":"f8147947-0fc1-44ce-a404-3215d7581123","razorpayOrderId":"order_SnOVhZ5EtyAc7J","razorpayKeyId":"rzp_test_SjfBxgIfB43kM2","amount":99800,"currency":"INR","subtotalAmount":"998.00","discountAmount":"0.00","finalAmount":"998.00","status":"pending","isFree":false,"claimToken":null}`

**Update `test-checkout.html`** with `order_id = order_SnOVhZ5EtyAc7J` and `amount = 99800`.

**DB Verification (order created, status=pending):**
```bash
uv run python scripts/db_query_engine.py "SELECT id, status, gateway_type, final_amount, gateway_order_id FROM orders WHERE id = 'f8147947-0fc1-44ce-a404-3215d7581123'"
```
Result: `status=pending, gateway_type=RAZORPAY_ORDER, final_amount=998, gateway_order_id=order_SnOVhZ5EtyAc7J`

**DB Verification (tickets locked):**
```bash
uv run python scripts/db_query_engine.py "SELECT count(*) as locked FROM tickets WHERE event_id = 'd5dc100b-9783-4457-a5c4-e1969642ca84' AND lock_reference_id = 'f8147947-0fc1-44ce-a404-3215d7581123'"
```
Result: 2 tickets locked

---

## Test 3: Poll Pending Order Status

```bash
BUYER_TOKEN=$(cat /tmp/token_buyer)
ORDER_ID="f8147947-0fc1-44ce-a404-3215d7581123"
curl -s -X GET "http://0.0.0.0:8080/api/events/purchase/orders/${ORDER_ID}/status" \
  -H "Authorization: Bearer $BUYER_TOKEN"
```

Result: `{"orderId":"f8147947-0fc1-44ce-a404-3215d7581123","status":"pending","ticketCount":0,"jwt":null,"claimToken":null,"failureReason":null}`

---

## Test 4: Complete Payment via Razorpay Checkout

1. Open `test-checkout.html` in browser (pre-filled with order details from Test 2)
2. Click "Open Razorpay Checkout"
3. Use test card: `4111 1111 1111 1111`, any future expiry, CVV `123`
4. Complete payment

**Server webhooks received:**
- `payment.authorized` → `payment.captured` → `order.paid`

Webhook log: `[PAID ONLINE PURCHASE WEBHOOK] Claim URL: http://0.0.0.0:8080/api/open/claim/l09zic0l`

---

## Test 5: Poll PAID Order Status

```bash
BUYER_TOKEN=$(cat /tmp/token_buyer)
ORDER_ID="f8147947-0fc1-44ce-a404-3215d7581123"
curl -s -X GET "http://0.0.0.0:8080/api/events/purchase/orders/${ORDER_ID}/status" \
  -H "Authorization: Bearer $BUYER_TOKEN"
```

Result: `{"orderId":"f8147947-0fc1-44ce-a404-3215d7581123","status":"paid","ticketCount":2,"jwt":"...","claimToken":"l09zic0l","failureReason":null}`

**Verify claim URL:**
```bash
curl -s "http://0.0.0.0:8080/api/open/claim/l09zic0l"
```
Result: `{"ticketCount":2,"jwt":"..."}`

---

## Test 6: Create Order — FREE (zero-amount with 100% coupon)

**Prerequisite:** 6 pool tickets remaining after Test 2 (2 used by paid order, 8 used by free order = 4 remaining).

```bash
BUYER_TOKEN=$(cat /tmp/token_buyer)
curl -s -X POST http://0.0.0.0:8080/api/events/purchase/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BUYER_TOKEN" \
  -d '{"event_id": "d5dc100b-9783-4457-a5c4-e1969642ca84", "event_day_id": "07e7d207-e6d2-45b8-9e90-46709dd4ab6a", "ticket_type_id": "18606f8f-1ce0-46d4-92c2-6cd94e468acf", "quantity": 2, "coupon_code": "FULL100"}'
```

Result: `{"orderId":"191fdbc4-ac53-45a4-a71e-f02139e64e36","razorpayOrderId":null,"razorpayKeyId":null,"amount":0,"currency":"INR","subtotalAmount":"998.00","discountAmount":"998.00","finalAmount":"0.00","status":"paid","isFree":true,"claimToken":"z40bb9fs"}`

**Poll status immediately:**
```bash
BUYER_TOKEN=$(cat /tmp/token_buyer)
curl -s -X GET "http://0.0.0.0:8080/api/events/purchase/orders/191fdbc4-ac53-45a4-a71e-f02139e64e36/status" \
  -H "Authorization: Bearer $BUYER_TOKEN"
```
Result: `{"orderId":"191fdbc4-ac53-45a4-a71e-f02139e64e36","status":"paid","ticketCount":2,"jwt":"...","claimToken":"z40bb9fs","failureReason":null}`

**Verify claim:**
```bash
curl -s "http://0.0.0.0:8080/api/open/claim/z40bb9fs"
```
Result: `{"ticketCount":2,"jwt":"..."}`

---

## Test 7: Create Order — Insufficient Tickets

```bash
BUYER_TOKEN=$(cat /tmp/token_buyer)
curl -s -X POST http://0.0.0.0:8080/api/events/purchase/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BUYER_TOKEN" \
  -d '{"event_id": "d5dc100b-9783-4457-a5c4-e1969642ca84", "event_day_id": "07e7d207-e6d2-45b8-9e90-46709dd4ab6a", "ticket_type_id": "18606f8f-1ce0-46d4-92c2-6cd94e468acf", "quantity": 100}'
```

Result: `{"status":"Error","code":400,"message":"Only 6 tickets available, requested 100"}`

---

## Test 8: Create Order — Invalid Coupon

```bash
BUYER_TOKEN=$(cat /tmp/token_buyer)
curl -s -X POST http://0.0.0.0:8080/api/events/purchase/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BUYER_TOKEN" \
  -d '{"event_id": "d5dc100b-9783-4457-a5c4-e1969642ca84", "event_day_id": "07e7d207-e6d2-45b8-9e90-46709dd4ab6a", "ticket_type_id": "18606f8f-1ce0-46d4-92c2-6cd94e468acf", "quantity": 1, "coupon_code": "INVALID"}'
```

Result: `{"status":"Error","code":400,"message":"Invalid coupon code"}`

---

## Summary: Entity IDs Reference

| Entity | ID |
|--------|-----|
| Organizer User | `d2f65b6e-db39-4d51-95bf-af831072d274` |
| Organizer Page | `de9d7cb1-4fde-4251-a32f-d6eda03901af` |
| Event | `d5dc100b-9783-4457-a5c4-e1969642ca84` |
| Event Day | `07e7d207-e6d2-45b8-9e90-46709dd4ab6a` |
| Ticket Type | `18606f8f-1ce0-46d4-92c2-6cd94e468acf` (General Admission, ₹499) |
| Customer User | `02f9d8f7-d6b2-42cf-a084-65a6b71a1473` |
| Coupon (FULL100) | `a0000000-0000-0000-0000-000000000001` |
| Order (paid test) | `f8147947-0fc1-44ce-a404-3215d7581123` |
| Order (free test) | `191fdbc4-ac53-45a4-a71e-f02139e64e36` |
| Claim Token (paid) | `l09zic0l` |
| Claim Token (free) | `z40bb9fs` |

---

## DB Cleanup (before starting fresh)

```bash
# Clear orders, allocations, claim_links, ticket locks before re-testing
# NOTE: gateway_type enum value is RAZORPAY_ORDER (uppercase), NOT 'razorpay_order'
uv run python scripts/db_query_engine.py "DELETE FROM allocations WHERE order_id IN (SELECT id FROM orders WHERE gateway_type = 'RAZORPAY_ORDER')" --commit
uv run python scripts/db_query_engine.py "DELETE FROM orders WHERE gateway_type = 'RAZORPAY_ORDER'" --commit
uv run python scripts/db_query_engine.py "DELETE FROM claim_links WHERE event_id = 'd5dc100b-9783-4457-a5c4-e1969642ca84'" --commit
uv run python scripts/db_query_engine.py "UPDATE tickets SET owner_holder_id = NULL, claim_link_id = NULL, lock_reference_type = NULL, lock_reference_id = NULL WHERE event_id = 'd5dc100b-9783-4457-a5c4-e1969642ca84'" --commit
```