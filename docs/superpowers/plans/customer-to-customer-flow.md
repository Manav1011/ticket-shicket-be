# Customer → Customer Transfer (Split) Flow

## API Design

### Endpoint
```
POST /api/open/claim/{token}/split
```
- This is a **public/open endpoint** — no authentication required
- Customer A identifies themselves via the claim token (same token used in `/api/open/claim/{token}`)
- The token maps to Customer A's claim link, which gives us `to_holder_id` = Customer A's identity

### Request
```json
{
  "to_email": "customer_b@example.com",
  "ticket_count": 5
}
```
- `to_email`: Customer B's email (phone param accepted but ignored for now)
- `ticket_count`: Number of tickets Customer A wants to transfer to Customer B

### Response
```json
{
  "status": "completed",
  "tickets_transferred": 5,
  "remaining_ticket_count": 5,
  "new_jwt": "eyJhbGc...",
  "message": "Your previous QR code is no longer valid. Please use the new QR code for entry."
}
```

---

## End-to-End Flow with Validations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   CUSTOMER A INITIATES SPLIT                               │
│          POST /api/open/claim/{token}/split                                │
│          { to_email, ticket_count }                                        │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  VALIDATION 1: token must be a valid claim link token                       │
│  → Hash token → SHA256(raw_token)                                          │
│  → Look up ClaimLink by token_hash                                         │
│  → If not found → 404 "Link not found"                                    │
│  → If status == 'inactive' → 400 "Link has been revoked"                   │
│  → If claimed_at is not None → 400 "Link already used"                     │
│  → Customer A = claim_link.to_holder_id (the recipient of the original)    │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ FAIL → respective error
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  VALIDATION 2: ticket_count must be valid                                    │
│  → Must be > 0                                                             │
│  → Must be <= Customer A's total tickets for this event_day                 │
│  → If 0 → 400 "Ticket count must be positive"                              │
│  → If > available → 400 "Only {N} tickets available"                        │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ FAIL → 400 "Not enough tickets"
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  VALIDATION 3: to_email must be provided                                    │
│  → Phone param is accepted but ignored for now                              │
│  → If not provided → 400 "Email is required"                                │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ FAIL → 400 "Email is required"
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: Resolve Customer B by email                                        │
│  → Try find TicketHolder by email                                          │
│  → If not found, create new TicketHolder                                   │
│  → This is cascading resolution: email-only lookup (no AND/phone fallback) │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  VALIDATION 4: Customer B cannot be Customer A                              │
│  → If resolved Customer B == Customer A → 400 "Cannot transfer to yourself" │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ FAIL → 400 "Cannot transfer to yourself"
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: Get Customer A's tickets for this event_day                         │
│  → select tickets where owner_holder_id = Customer A                       │
│    AND event_day_id = claim_link.event_day_id                              │
│  → Returns list of tickets sorted by ticket_index                          │
│  → Customer A has e.g., 10 tickets: indexes [0,1,2,3,4,5,6,7,8,9]          │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: Lock tickets being transferred                                      │
│  → lock_tickets_for_transfer(                                              │
│      owner_holder_id = Customer A,                                         │
│      event_id = from claim_link,                                           │
│      ticket_type_id = from B2B ticket type,                                │
│      event_day_id = from claim_link,                                       │
│      quantity = ticket_count (e.g., 5),                                   │
│      order_id = UUID                                                       │
│  )                                                                          │
│  → Locks first N tickets by ticket_index (FIFO)                            │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ FAIL → 400 "Not enough tickets available"
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: Create OrderModel                                                  │
│  → OrderModel(                                                             │
│      id = order_id,                                                        │
│      from_holder_id = Customer A,                                          │
│      to_holder_id = Customer B,                                            │
│      ticket_count = ticket_count,                                          │
│      type = 'transfer',                                                    │
│      status = 'completed',                                                 │
│      amount = 0                                                            │
│  )                                                                          │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: Create NEW AllocationModel (A → B)                                │
│  → AllocationModel(                                                         │
│      from_holder_id = Customer A,                                          │
│      to_holder_id = Customer B,                                            │
│      ticket_count = ticket_count,                                          │
│      status = 'completed',                                                 │
│      event_day_id = from claim_link                                        │
│  )                                                                          │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 6: Update ticket ownership (transfer to Customer B)                   │
│  → update_ticket_ownership_batch(                                          │
│      ticket_ids = locked ticket IDs (first N),                            │
│      new_owner_holder_id = Customer B                                     │
│  )                                                                          │
│  → Also clears lock_reference_type, lock_reference_id, lock_expires_at     │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 7: REVOKE Customer A's old claim link                                 │
│  → ClaimLinkRepository.update_status(claim_id, 'inactive')                │
│  → This marks Customer A's old claim link as invalid                       │
│  → Customer A can no longer share their old link with others              │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 8: REVOKE Customer A's old JWT (add JTI to revoked list)             │
│  → RevokedScanTokenModel(                                                   │
│      event_day_id = from claim_link,                                       │
│      jti = Customer A's current JWT's jti,                                  │
│      reason = 'split'                                                      │
│  )                                                                          │
│  → Customer A's old JWT is now invalid at scan gate                        │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 9: Generate NEW JWT for Customer A (remaining tickets only)           │
│  → Get Customer A's remaining tickets from DB:                              │
│    SELECT ticket_index FROM tickets                                       │
│    WHERE owner_holder_id = Customer A                                    │
│    AND event_day_id = claim_link.event_day_id                              │
│    → Returns indexes of remaining tickets (e.g., [0,1,2,3,4])             │
│  → generate_scan_jwt(                                                      │
│      holder_id = Customer A,                                                │
│      event_day_id = from claim_link,                                       │
│      indexes = remaining indexes                                           │
│  )                                                                          │
│  → New JTI generated, indexes = only remaining tickets                      │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 10: Create claim link for Customer B                                   │
│  → Generate 8-char token via claim_link_utils                               │
│  → Hash with SHA256 → token_hash                                           │
│  → ClaimLinkModel(                                                         │
│      allocation_id = new allocation.id,                                    │
│      token_hash = hash,                                                    │
│      event_id = from claim_link,                                           │
│      event_day_id = from claim_link,                                       │
│      from_holder_id = Customer A,                                           │
│      to_holder_id = Customer B,                                             │
│      status = 'active',                                                    │
│      created_by_holder_id = Customer A                                    │
│  )                                                                          │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 11: Send notifications to Customer B                                  │
│  → mock_send_sms(to_phone?, "Your claim link: /claim/{token}")            │
│  → mock_send_whatsapp(to_email, "Your claim link: /claim/{token}")       │
│  → mock_send_email(to_email, "Your claim link: /claim/{token}")          │
│  → Note: phone is ignored for now, only email is used                       │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────────────┐
                    │      RETURN RESPONSE        │
                    └─────────────────────────────┘
                    {                              │
                      status: "completed",         │
                      tickets_transferred: 5,      │
                      remaining_ticket_count: 5,   │
                      new_jwt: "eyJ..." ,          │
                      message: "Your previous QR  │
                      code is no longer valid..."  │
                    }                              │

```

---

## Customer B Claims Tickets (Same as Original Flow)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  CUSTOMER B OPENS CLAIM LINK                                │
│                         GET /claim/{token}                                  │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LOOKUP: Find claim link by token                                           │
│  → token_hash = SHA256(requested_token)                                    │
│  → ClaimLinkRepository.get_by_token_hash(token_hash)                         │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ FAIL → 404 "Link not found"
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  VALIDATION: Check claim link status                                         │
│  → If status == 'inactive' → 400 "Link has been revoked"                    │
│  → If claimed_at is not None → 400 "Link already used"                      │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ FAIL → respective error
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  UPDATE: Mark claim link as claimed                                         │
│  → claimed_at = now()                                                      │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LOOKUP: Get Customer B's current tickets (from DB)                         │
│  → select tickets where owner_holder_id = Customer B                        │
│  → Returns ticket count                                                     │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  GENERATE: New JWT for Customer B                                           │
│  → generate_scan_jwt(                                                      │
│      holder_id = Customer B,                                                │
│      event_day_id = from claim_link,                                        │
│      indexes = Customer B's ticket indexes                                  │
│  )                                                                          │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────────────┐
                    │     RETURN RESPONSE         │
                    └─────────────────────────────┘
                    {                              │
                      holder_id: "uuid",           │
                      event_day_id: "uuid",        │
                      ticket_count: 5,             │
                      jwt: "eyJ..."                │
                    }                              │

```

---

## Key Differences: Split vs Regular Transfer

| Aspect | Organizer→Customer / Reseller→Customer | Customer A → Customer B (Split) |
|--------|---------------------------------------|----------------------------------|
| Endpoint | `event_id` + `to_phone/email` | `POST /api/open/claim/{token}/split` (public) |
| Sender identity | From auth token | From claim link token (maps to `to_holder_id`) |
| Claim link revoked | ❌ No | ✅ Yes (old link becomes inactive) |
| Old JWT revoked | ❌ No | ✅ Yes (JTI added to revoked list) |
| New JWT issued to sender | ❌ No | ✅ Yes (remaining tickets only) |
| Claim link created for recipient | ✅ Yes | ✅ Yes |
| Notifications sent to recipient | ✅ SMS/WhatsApp/Email | ✅ Mock WhatsApp/Email only (phone ignored) |

---

## Example: Customer A Splits 5 of 10 Tickets to Customer B

**Before split:**
- Customer A: 10 tickets (indexes 0-9), old claim link active, old JWT valid

**After split:**
- Customer A: 5 tickets (indexes 0-4), old claim link inactive, new JWT with [0-4]
- Customer B: 5 tickets (indexes 5-9), new claim link, new JWT with [5-9]
- Allocation created: Customer A → Customer B, 5 tickets
- Notifications sent to Customer B via mock WhatsApp/Email

**Original Organizer→Customer A allocation:**
- Stays intact as immutable history (10 tickets from Organizer to Customer A)
- But Customer A's current actual ownership is now only 5 remaining