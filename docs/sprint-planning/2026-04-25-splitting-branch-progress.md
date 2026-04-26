# feat/splitting Branch — Implementation Progress

> Track what was built on the `feat/splitting` branch, from foundations to full organizer→customer, reseller→customer, and customer→customer split transfer.

**Branch:** `feat/splitting`
**Started:** 2026-04-20
**Current Status:** ✅ Phase 1 + Phase 2 + Phase 3 + Phase 4 + Phase 5 + Phase 6 (Customer→Customer Split) complete.

---

## What Was Built

### Phase 1: Claim Link & Scan Token Infrastructure (2026-04-20 Plan)
**Goal:** Build foundational models, utilities, and repository methods before URLs and services.

| # | Task | Commit | Status |
|---|------|--------|--------|
| 1 | `ClaimLinkStatus` enum | `56a65cc` | ✅ |
| 2 | `ClaimLinkModel` | `80196b0` | ✅ |
| 3 | `RevokedScanTokenModel` | `8f216ce` | ✅ |
| 4 | `claim_link_utils.py` — 8-char alphanumeric token | `f7818af` | ✅ |
| 5 | `jwt_utils.py` — scan JWT generation/verification | `53cc6ce` | ✅ |
| 6 | `ClaimLinkRepository` | `3c34378` | ✅ |
| 7 | `RevokedScanTokenRepository` | `3f33808` | ✅ |
| 8 | `resolve_holder()` in AllocationRepository | `7e25863` | ✅ |
| 9 | `select_tickets_for_transfer()` in TicketingRepository | `d9f1c63` | ✅ |
| 10 | `update_ticket_ownership_batch()` in TicketingRepository | `9146b2e` | ✅ |
| 11 | `create_allocation_with_claim_link()` in AllocationRepository | `2e6d154` | ✅ |

**Note:** Phase 1 ended with a separate commit `4b81eb1 models created` which updated ClaimLinkModel to include `event_day_id` field.

---

### Phase 2: Organizer → Customer Transfer (2026-04-25 Plan)
**Goal:** Full end-to-end transfer from organizer to customer via phone/email, with claim link and mock notifications.

| # | Task | Commit | Status |
|---|------|--------|--------|
| 0a | Add `event_day_id` to ClaimLinkModel + migration | `c021aa9` | ✅ |
| 0b | Add `event_day_id` to `create_allocation_with_claim_link` + `ClaimLinkRepository.create` | `345df8f` | ✅ |
| 0c | `get_holder_by_phone_and_email()` in AllocationRepository | `8433b8f` | ✅ |
| 1 | Create mock notification utils (SMS/WhatsApp/Email) | `a6601eb` | ✅ |
| 2 | `CreateCustomerTransferRequest` schema | `3c973a3` | ✅ |
| 3 | `CustomerTransferResponse` schema | `8f5e4a1` | ✅ |
| 4 | `create_customer_transfer()` in OrganizerService | `e94f505` | ✅ |
| 5 | `POST /api/organizers/b2b/events/{event_id}/transfers/customer` endpoint | `874707b` | ✅ |
| 6 | `ClaimService` in `apps/event` | `432d005` | ✅ |
| 7 | `GET /api/open/claim/{token}` public redemption endpoint | `7c7a46f` | ✅ |

---

### Phase 3: Bug Fix — `lock_tickets_for_transfer` Missing `event_day_id` Filter
**Goal:** Fix critical bug where lock didn't scope to specific event_day, potentially locking tickets from wrong day.

| # | Task | Commit | Status |
|---|------|--------|--------|
| 1 | Add `event_day_id` parameter to `lock_tickets_for_transfer` in TicketingRepository | `27bbbe2` | ✅ |
| 2 | Pass `event_day_id` in `create_b2b_transfer` (organizer→reseller) call site | `27bbbe2` | ✅ |
| 3 | Pass `event_day_id` in `create_customer_transfer` (organizer→customer) call site | `27bbbe2` | ✅ |
| 4 | Clean up inline imports in `create_b2b_transfer` and `create_customer_transfer` | `27bbbe2` | ✅ |

**Bug:** `lock_tickets_for_transfer` was locking tickets from ANY event_day (ordered by `ticket_index`), not just the requested day.

**Fix:** Added `TicketModel.event_day_id == event_day_id` filter condition to the lock query.

---

### Phase 4: Reseller → Customer Transfer
**Goal:** Implement equivalent of organizer→customer transfer for resellers, following the same pattern.

| # | Task | Commit | Status |
|---|------|--------|--------|
| 1 | Add imports to `resellers/service.py` (hashlib, AllocationType, OrderModel, etc.) | `4b81eb1` | ✅ |
| 2 | Add `_allocation_repo` and `_ticketing_repo` to `ResellerService.__init__` | `4b81eb1` | ✅ |
| 3 | Implement `create_reseller_customer_transfer()` method | `4b81eb1` | ✅ |
| 4 | Add `POST /api/resellers/b2b/events/{event_id}/transfers/customer` endpoint | `4b81eb1` | ✅ |
| 5 | Write 8 unit tests for reseller customer transfer | `4b81eb1` | ✅ |

---

### Phase 5: Auto-Create B2B Ticket Type on Event Creation (2026-04-26)
**Goal:** Every new event automatically gets a B2B ticket type so B2B transfers work out of the box.

| # | Task | Commit | Status |
|---|------|--------|--------|
| 1 | Add `get_or_create_b2b_ticket_type_for_event(event_id, ...)` to TicketingRepository | `881ecc3` | ✅ |
| 2 | Inject `TicketingRepository` into `EventService` (optional, backward compat) | `881ecc3` | ✅ |
| 3 | Call auto-create at end of `create_draft_event` | `881ecc3` | ✅ |
| 4 | Update `get_event_service` in URLs to pass `TicketingRepository` | `881ecc3` | ✅ |

---

### Phase 6: Customer → Customer (Split) (2026-04-26)
**Goal:** Allow Customer A to split tickets to Customer B via their claim link. Customer A's JWT is revoked and reissued, old claim link stays active, Customer B gets a new claim link.

| # | Task | Commit | Status |
|---|------|--------|--------|
| 1 | Add `jwt_jti` column to ClaimLinkModel + migration | `da83e95` | ✅ |
| 2 | `ClaimRedemptionResponse` schema (ticket_count instead of indexes) | `da83e95` | ✅ |
| 3 | Add `SplitClaimRequest` schema | `78e123b` | ✅ |
| 4 | Add `SplitClaimResponse` schema | `78e123b` | ✅ |
| 5 | `revoke_claim_link()` method in ClaimLinkRepository | `78e123b` | ✅ |
| 6 | `add_revoked_jti()` method in RevokedScanTokenRepository | `78e123b` | ✅ |
| 7 | Implement `split_claim()` in ClaimService | `78e123b` | ✅ |
| 8 | Add `POST /api/open/claim/{token}/split` endpoint | `78e123b` | ✅ |

**Key Design:**
- `POST /api/open/claim/{token}/split` — public endpoint (no auth)
- Customer A identified by claim link token
- Customer A's claim link stays ACTIVE forever — only `jwt_jti` updated
- Customer B's JTI generated at split time, stored in B's claim link
- Customer B's claim link pre-populated with JTI at creation

**Bug Fixes:**
- `112bad5` — Don't revoke claim link on split, just update JTI
- `78e123b` — Populate JTI for Customer B at split time (not at claim time)

---

## Key Design Decisions (Locked In)

| Decision | Value |
|----------|-------|
| Claim link URL format | `/claim/{8-char alphanumeric}` — e.g., `/claim/l1xhq5a6` |
| Token storage | SHA-256 hash (64-char hex) stored in DB, raw token in URL |
| JWT payload | `{jti, holder_id, event_day_id, indexes[], iat}` — no expiry |
| JWT `indexes` source | Live DB query of `tickets.owner_holder_id`, NOT from allocation metadata |
| Claim link scope | Per `event_day_id` — redemption returns tickets only for that specific day |
| Holder resolution | If both phone+email → try AND lookup first, then single-field fallbacks |
| Allocation type | `transfer` (not `b2b`) for customer transfers |
| Free transfer | Allocation status = `completed` immediately |
| Paid transfer | Returns stub with `status="not_implemented"` — **not yet implemented** |
| Notifications | Mock SMS/WhatsApp/Email — no-op, real integration replaces later |
| B2B ticket type | Auto-created on event creation — no manual creation needed for B2B transfers |
| Self-transfer | Allowed — no guard needed, cascading holder resolution handles it naturally |
| Split claim link behavior | Customer A's claim link stays ACTIVE forever, only `jwt_jti` updated |
| Split JTI generation | Customer B's JTI generated at split time, stored in claim link |
| Claim redemption response | Returns `ticket_count` (not indexes) + JWT |

---

## Files Changed

```
src/apps/allocation/
├── enums.py              ✅ added ClaimLinkStatus
├── models.py             ✅ added ClaimLinkModel (with event_day_id, jwt_jti), RevokedScanTokenModel
├── repository.py         ✅ added ClaimLinkRepository, RevokedScanTokenRepository,
│                           get_holder_by_phone_and_email, create_allocation_with_claim_link,
│                           resolve_holder, revoke_claim_link, add_revoked_jti

src/apps/ticketing/
├── repository.py         ✅ added select_tickets_for_transfer, update_ticket_ownership_batch,
│                           lock_tickets_for_transfer (with event_day_id filter),
│                           get_or_create_b2b_ticket_type_for_event

src/apps/organizer/
├── request.py            ✅ added CreateCustomerTransferRequest
├── response.py           ✅ added CustomerTransferResponse
├── service.py            ✅ added create_b2b_transfer (organizer→reseller),
│                           create_customer_transfer (organizer→customer),
│                           inline imports cleaned up, event_day_id passed to lock
├── urls.py               ✅ added POST /transfers/reseller, POST /transfers/customer

src/apps/resellers/
├── service.py            ✅ added create_reseller_customer_transfer (reseller→customer)
├── urls.py               ✅ added POST /b2b/events/{event_id}/transfers/customer

src/apps/event/
├── claim_service.py      ✅ created ClaimService, split_claim() method
├── public_urls.py        ✅ added GET /open/claim/{token}, POST /open/claim/{token}/split
├── request.py            ✅ added SplitClaimRequest
├── response.py           ✅ added ClaimRedemptionResponse, SplitClaimResponse

src/utils/
├── claim_link_utils.py   ✅ 8-char alphanumeric token generation
├── jwt_utils.py          ✅ scan JWT generation/verification
├── notifications/
    ├── __init__.py       ✅
    ├── sms.py             ✅ mock_send_sms
    ├── whatsapp.py        ✅ mock_send_whatsapp
    ├── email.py           ✅ mock_send_email

tests/apps/allocation/
├── test_get_holder_by_phone_and_email.py   ✅

tests/apps/event/
├── test_claim_service.py                   ✅ (updated for new behavior)
├── test_claim_link_endpoint.py             ✅

tests/apps/organizer/
├── test_notification_utils.py              ✅
├── test_create_customer_transfer_request.py ✅
├── test_customer_transfer_response.py      ✅
├── test_customer_transfer.py              ✅
├── test_customer_transfer_endpoint.py     ✅

tests/apps/resellers/
├── test_reseller_customer_transfer.py     ✅ 8 tests

src/migrations/versions/
├── d01b57798e73_.py   ✅ event_day_id migration
└── xxxxxxxxx_add_jwt_jti_to_claim_links.py  ✅ jwt_jti migration
```

---

## Testing Summary

### Unit Tests

| Test Suite | Result |
|------------|--------|
| `tests/apps/organizer/test_notification_utils.py` | ✅ 3 passed |
| `tests/apps/organizer/test_create_customer_transfer_request.py` | ✅ 6 passed |
| `tests/apps/organizer/test_customer_transfer_response.py` | ✅ 3 passed |
| `tests/apps/event/test_claim_service.py` | ✅ 4 passed |
| `tests/apps/event/test_claim_link_endpoint.py` | ✅ 2 passed |
| `tests/apps/allocation/test_get_holder_by_phone_and_email.py` | ✅ 2 passed |
| `tests/apps/resellers/test_reseller_customer_transfer.py` | ✅ 8 passed |

**Total:** 28 tests passing.

**Pre-existing failures** (unrelated to this feature):
- `tests/apps/event/test_app_bootstrap.py::test_phase_one_routes_are_registered` — 1 failure (route doesn't exist)
- `tests/apps/organizer/test_b2b_requests.py` — 3 failures (were failing before this branch)

### Manual API Testing (2026-04-26)

| Test | Endpoint | Result |
|------|----------|--------|
| Organizer→customer (2 tickets, free mode) | `POST /api/organizers/b2b/events/{id}/transfers/customer` | ✅ `status: "completed"`, claim link `/claim/tue0cx98` |
| Organizer→reseller (3 tickets, free mode) | `POST /api/organizers/b2b/events/{id}/transfers/reseller` | ✅ `status: "completed"` |
| Wrong event_day_id (non-existent) | organizer→customer | ✅ 404 `Event day not found` |
| Wrong event_day_id (non-existent) | organizer→reseller | ✅ 404 `Event day not found` |
| Requesting more than available (100 vs 54) | organizer→customer | ✅ 400 `Only 54 B2B tickets available` |
| Requesting more than available (100 vs 54) | organizer→reseller | ✅ 400 `Only 54 B2B tickets available` |
| Transfer to day with 0 tickets | organizer→customer | ✅ 400 `Only 0 B2B tickets available` |
| Transfer to day with 0 tickets | organizer→reseller | ✅ 400 `Only 0 B2B tickets available` |
| Reseller tickets query | `GET /api/resellers/events/{id}/tickets` | ✅ returns 13 tickets |
| Reseller allocations query | `GET /api/resellers/events/{id}/my-allocations` | ✅ returns allocations |
| Reseller→customer (2 tickets, free mode) | `POST /api/resellers/b2b/events/{id}/transfers/customer` | ✅ `status: "completed"`, claim link `/claim/atitby9m` |
| Reseller→customer (2 more tickets) | same endpoint | ✅ ticket count 13 → 11 → 9 |
| Wrong event_day_id | reseller→customer | ✅ 404 `Event day not found` |
| Requesting more than available (20 vs 9) | reseller→customer | ✅ 400 `Only 9 B2B tickets available` |
| Transfer to day with 0 tickets | reseller→customer | ✅ 400 `Only 0 B2B tickets available` |
| Claim link redemption | `GET /api/open/claim/atitby9m` | ✅ returns JWT with `holder_id`, `event_day_id`, `ticket_count` |

### Split Testing (2026-04-26)

| Test | Endpoint | Result |
|------|----------|--------|
| Create fresh transfer (3 tickets) | `POST /api/organizers/b2b/events/{id}/transfers/customer` | ✅ claim link `/claim/wktj6bds` |
| Customer claims link | `GET /api/open/claim/wktj6bds` | ✅ JWT with stored JTI |
| Split 1 ticket to Customer B | `POST /api/open/claim/wktj6bds/split` | ✅ remaining=2, new JWT for A |
| Split again on same link | same endpoint | ✅ remaining=1, claim link still ACTIVE |
| ticket_count=0 | split with count=0 | ✅ 400 "Ticket count must be positive" |
| ticket_count > available | split with count=5, only 1 left | ✅ 400 "Only 1 tickets available" |
| Create fresh transfer | `POST /api/organizers/b2b/events/{id}/transfers/customer` | ✅ claim link `/claim/ol4x8dss` |
| Customer A claims | `GET /api/open/claim/ol4x8dss` | ✅ JWT with jti=5e753f91b25c0f5c |
| Split to Customer B | `POST /api/open/claim/ol4x8dss/split` | ✅ Customer B claim link created with jwt_jti |
| Customer B claims | `GET /api/open/claim/{customer_b_token}` | ✅ JWT uses same jti from DB |

**Verified:** Customer B's claim link has `jwt_jti` pre-populated at split time, claim API uses stored JTI.

---

## What's NOT Done (Future Work)

### 1. Paid Mode (All Transfers)
All transfer methods with `mode="paid"` return a stub:
```python
return SplitClaimResponse(
    status="not_implemented",
    ...
)
```
**Status:** Not implemented — needs payment integration.

### 2. Customer → Customer Split (Partial — Split endpoint done)
`POST /api/open/claim/{token}/split` is implemented and working. The full split flow is:
- ✅ Customer A's old JTI revoked → new JTI stored
- ✅ Customer A's claim link stays active (status not changed)
- ✅ New claim link for Customer B with JTI pre-populated
- ✅ Mock email notification to Customer B
- ⚠️ WhatsApp/SMS notifications commented out (not ready)

### 3. Scan JWT Verification at Gate
`verify_scan_jwt` exists in `jwt_utils.py` but the full scan gate flow (Redis bitmap check + mark used) is not implemented.

### 4. Claim Link Expiry / Cleanup Job
Claim links don't have expiry. A background job to expire old links was mentioned but deferred.

---

## How to Continue

```bash
# See full history
git log --oneline feat/splitting ^main

# Continue from main
git checkout main
git pull
git checkout feat/splitting
git rebase main  # if needed
```

---

## Recent Commits

| Commit | Description |
|--------|-------------|
| `da83e95` | fix(claim): return ticket_count instead of indexes in claim redemption response |
| `b750f7b` | fix(claim): add missing TicketModel import in claim_service |
| `112bad5` | fix(split): don't revoke claim link, just update jwt_jti |
| `78e123b` | fix(split): populate JTI for Customer B at split time |

*Last updated: 2026-04-26*