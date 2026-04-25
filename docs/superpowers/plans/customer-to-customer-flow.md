# Customer → Customer Transfer Flow

## End-to-End Flow with Validations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CUSTOMER A INITIATES SPLIT                           │
│                     POST /api/customers/split-tickets                       │
│                     { to_phone, to_email, ticket_indexes[], event_id }     │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  VALIDATION 1: Customer A must exist and own these tickets                 │
│  → Verify holder exists                                                    │
│  → Verify tickets belong to Customer A (owner_holder_id match)            │
│  → Verify tickets are active (not locked, not used)                       │
│  → Verify all requested indexes exist for this event_day                   │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ FAIL → 400 "Tickets not found or not owned"
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  VALIDATION 2: Customer B (recipient) is different from Customer A         │
│  → Cannot split to yourself                                                │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ FAIL → 400 "Cannot transfer to yourself"
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  VALIDATION 3: Resolve Customer B (recipient)                               │
│  → Try AND lookup (phone + email)                                          │
│  → If not found, try phone-only                                            │
│  → If not found, try email-only                                            │
│  → If not found, create new TicketHolder                                   │
│  → This is cascading resolution (same as organizer/reseller flow)          │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  VALIDATION 4: Event_day_id validation                                      │
│  → Get event_day_id from the tickets                                       │
│  → Verify event_day exists                                                 │
│  → Verify Customer A still has tickets for this event_day                  │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ FAIL → 400 "Invalid event_day"
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: Lock tickets for transfer                                          │
│  → lock_tickets_for_transfer(                                              │
│      owner_holder_id = Customer A,                                         │
│      event_id, ticket_type_id, event_day_id,                               │
│      quantity = len(ticket_indexes),                                      │
│      order_id = UUID                                                       │
│  )                                                                          │
│  → Sets lock_reference_type='transfer', lock_reference_id=order_id        │
│  → Uses FOR UPDATE to prevent concurrent lock                              │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ FAIL → 400 "Not enough tickets available"
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: Create OrderModel                                                  │
│  → OrderModel(                                                             │
│      id = order_id,                                                        │
│      from_holder_id = Customer A,                                          │
│      to_holder_id = Customer B,                                            │
│      ticket_count = len(ticket_indexes),                                   │
│      type = 'transfer',                                                    │
│      status = 'completed',                                                 │
│      amount = 0                                                            │
│  )                                                                          │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: Create AllocationModel (NEW allocation for this transfer)         │
│  → AllocationModel(                                                         │
│      from_holder_id = Customer A,                                          │
│      to_holder_id = Customer B,                                            │
│      ticket_count = len(ticket_indexes),                                   │
│      status = 'completed',                                                 │
│      event_day_id                                                          │
│  )                                                                          │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: Update ticket ownership (transfer tickets to Customer B)           │
│  → update_ticket_ownership_batch(                                          │
│      ticket_ids = selected ticket IDs,                                     │
│      new_owner_holder_id = Customer B                                     │
│  )                                                                          │
│  → Also clears lock_reference_type, lock_reference_id, lock_expires_at     │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: Create ClaimLink for Customer B                                    │
│  → ClaimLinkModel(                                                         │
│      allocation_id = new allocation.id,                                   │
│      token_hash = SHA-256(8-char alphanumeric token),                     │
│      event_id,                                                             │
│      from_holder_id = Customer A,                                          │
│      to_holder_id = Customer B,                                            │
│      status = 'active',                                                    │
│      created_by_holder_id = Customer A                                    │
│  )                                                                          │
│  → Token generated: 8-char alphanumeric via claim_link_utils              │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 6: REVOKE Customer A's old JWT                                        │
│  → Add old JTI to RevokedScanTokenModel(                                    │
│      event_day_id,                                                         │
│      jti = Customer A's current jti,                                       │
│      reason = 'split'                                                      │
│  )                                                                          │
│  → This marks old JWT as invalid going forward                             │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 7: Generate NEW JWT for Customer A (remaining tickets only)           │
│  → generate_scan_jwt(                                                      │
│      holder_id = Customer A,                                               │
│      event_day_id = same day,                                              │
│      indexes = Customer A's REMAINING ticket indexes (from DB query)        │
│  )                                                                          │
│  → New jti generated, indexes = only tickets Customer A still owns          │
│  → Note: indexes come from LIVE DB query, not from memory                   │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 8: Send claim link to Customer B                                     │
│  → mock_send_sms / mock_send_whatsapp / mock_send_email                    │
│  → Message contains: "/claim/{8-char-token}"                               │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   RETURN RESPONSE   │
                    └─────────────────────┘
                    {                      │
                      transfer_id,          │
                      status: "completed", │
                      ticket_count,         │
                      new_jwt,              │
                      claim_link_url,       │
                      mode: "free"          │
                    }                       │

```

---

## Customer B Claims Tickets

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  CUSTOMER B OPENS CLAIM LINK                                │
│                         GET /claim/{token}                                  │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LOOKUP: Find claim link by token                                           │
│  → token_hash = SHA-256(requested_token)                                    │
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
│  → status remains 'active' (not changed to inactive)                        │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  LOOKUP: Get Customer B's current tickets (from DB)                         │
│  → select tickets where owner_holder_id = Customer B                        │
│  → Returns indexes that Customer B now owns                                 │
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
                    ┌─────────────────────┐
                    │   RETURN RESPONSE   │
                    └─────────────────────┘
                    {                      │
                      holder_id,           │
                      event_day_id,        │
                      indexes,             │
                      jwt                  │
                    }                      │

```

---

## Key Differences Summary

| Aspect | Organizer→Customer | Reseller→Customer | Customer→Customer |
|--------|-------------------|-------------------|-------------------|
| Sender keeps same JWT? | ✅ Yes | ✅ Yes | ❌ No - revoked and reissued |
| New allocation created? | ✅ Yes | ✅ Yes | ✅ Yes |
| Claim link generated for | Recipient | Recipient | Recipient |
| Old link revoked? | N/A | N/A | ✅ Old link becomes 'inactive' |
| JTI added to revoked list? | N/A | N/A | ✅ Old JTI revoked |

---

## Scan Validation Flow (at gate)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SCAN GATE VERIFICATION                              │
│                    POST /api/open/scan { jwt_token }                        │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: Decode and verify JWT signature                                   │
│  → verify_scan_jwt(token)                                                   │
│  → If fails → 401 "Invalid token"                                          │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: Extract jti from JWT                                               │
│  → get_jti_from_jwt(token)                                                  │
│  → jti = "abc12345"                                                        │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: Check if JTI is revoked                                           │
│  → RevokedScanTokenRepository.is_revoked(event_day_id, jti)                 │
│  → If revoked → 401 "Token has been revoked"                               │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ FAIL → 401 "Token revoked"
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: Check Redis bitmap for each index                                  │
│  → For each index in JWT.indexes[]:                                         │
│  → Check Redis: GETBIT event_day:{id}:bitmap {index}                       │
│  → If any bit == 1 → 400 "Ticket already scanned"                          │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ FAIL → 400 "Already scanned"
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: Mark tickets as scanned in Redis                                   │
│  → For each index in JWT.indexes[]:                                         │
│  → SETBIT event_day:{id}:bitmap {index} 1                                  │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   RETURN SUCCESS    │
                    └─────────────────────┘
                    {                      │
                      status: "valid",      │
                      holder_id,           │
                      indexes_scanned      │
                    }                      │
```