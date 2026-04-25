# feat/splitting Branch — Implementation Progress

> Track what was built on the `feat/splitting` branch, from foundations to full organizer→customer transfer.

**Branch:** `feat/splitting`
**Started:** 2026-04-20
**Current Status:** ✅ Phase 1 (Models/Utils) + Phase 2 (Organizer→Customer Transfer) complete. Paid mode not yet implemented.

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
| 5 | `jwt_utils.py` — scan JWT generation/verification | `53cc6de` | ✅ |
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

## Key Design Decisions (Locked In)

| Decision | Value |
|----------|-------|
| Claim link URL format | `/claim/{8-char alphanumeric}` — e.g., `/claim/l1xhq5a6` |
| Token storage | SHA-256 hash (64-char hex) stored in DB, raw token in URL |
| JWT payload | `{jti, holder_id, event_day_id, indexes[], iat}` — no expiry, no allocation_id |
| JWT `indexes` source | Live DB query of `tickets.owner_holder_id`, NOT from allocation metadata |
| Claim link scope | Per `event_day_id` — redemption returns tickets only for that specific day |
| Holder resolution | If both phone+email → try AND lookup first, then single-field fallbacks |
| Allocation type | `transfer` (not `b2b`) for customer transfers |
| Free transfer | Allocation status = `completed` immediately |
| Paid transfer | Returns stub with `status="not_implemented"` — **not yet implemented** |
| Notifications | Mock SMS/WhatsApp/Email — no-op, real integration replaces later |

---

## Files Changed

```
src/apps/allocation/
├── enums.py              ✅ added ClaimLinkStatus
├── models.py             ✅ added ClaimLinkModel (with event_day_id), RevokedScanTokenModel
├── repository.py         ✅ added ClaimLinkRepository, RevokedScanTokenRepository,
│                           get_holder_by_phone_and_email, create_allocation_with_claim_link,
│                           resolve_holder

src/apps/ticketing/
├── repository.py         ✅ added select_tickets_for_transfer, update_ticket_ownership_batch

src/apps/organizer/
├── request.py            ✅ added CreateCustomerTransferRequest
├── response.py           ✅ added CustomerTransferResponse
├── service.py            ✅ added create_customer_transfer (with bug fix: token_hash = SHA256)
├── urls.py               ✅ added POST /transfers/customer endpoint

src/apps/event/
├── claim_service.py      ✅ created ClaimService
├── public_urls.py       ✅ added GET /open/claim/{token} endpoint

src/utils/
├── claim_link_utils.py   ✅ create: 8-char alphanumeric token generation
├── jwt_utils.py         ✅ create: scan JWT generation/verification
├── notifications/
    ├── __init__.py       ✅
    ├── sms.py            ✅ mock_send_sms
    ├── whatsapp.py       ✅ mock_send_whatsapp
    ├── email.py          ✅ mock_send_email

tests/apps/allocation/
├── test_get_holder_by_phone_and_email.py   ✅
├── test_claim_link_utils.py                ✅ (from Phase 1)
├── test_jwt_utils.py                       ✅ (from Phase 1)

tests/apps/event/
├── test_claim_service.py                   ✅
├── test_claim_link_endpoint.py             ✅

tests/apps/organizer/
├── test_notification_utils.py              ✅
├── test_create_customer_transfer_request.py ✅
├── test_customer_transfer_response.py      ✅
├── test_customer_transfer.py              ✅
├── test_customer_transfer_endpoint.py     ✅

src/migrations/versions/d01b57798e73_.py    ✅ event_day_id migration
```

---

## Testing Summary

| Test Suite | Result |
|------------|--------|
| `tests/apps/organizer/test_notification_utils.py` | ✅ 3 passed |
| `tests/apps/organizer/test_create_customer_transfer_request.py` | ✅ 6 passed |
| `tests/apps/organizer/test_customer_transfer_response.py` | ✅ 3 passed |
| `tests/apps/event/test_claim_service.py` | ✅ 3 passed |
| `tests/apps/event/test_claim_link_endpoint.py` | ✅ 2 passed |
| `tests/apps/allocation/test_get_holder_by_phone_and_email.py` | ✅ 2 passed |

**Total:** 18 tests passing for the customer transfer feature.

**Pre-existing failures** (unrelated to this feature):
- `tests/apps/organizer/test_b2b_requests.py` — 3 failures (were failing before this branch)

---

## What's NOT Done (Future Work)

### 1. Paid Mode (Customer Transfer)
`create_customer_transfer` with `mode="paid"` returns a stub:
```python
return CustomerTransferResponse(
    transfer_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
    status="not_implemented",
    ticket_count=0,
    mode="paid",
    message="Paid customer transfer coming soon",
)
```
**Status:** Not implemented — needs payment integration.

### 2. Customer → Customer Transfer (Split)
No endpoint or service for customer-to-customer transfer/split. This would need:
- Customer-facing endpoint to initiate split/transfer
- JWT revocation logic when Customer A splits
- New claim link generation for Customer B
- New JWT generation for Customer A (remaining tickets)

### 3. Scan JWT Verification at Gate
`verify_scan_jwt` exists in `jwt_utils.py` but the full scan gate flow (Redis bitmap check + mark used) is not implemented.

### 4. Reseller → Customer Transfer
Reseller can transfer to customer — needs `create_customer_transfer` equivalent for resellers (different `from_holder_id`).

### 5. Claim Link Expiry / Cleanup Job
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

*Last updated: 2026-04-25*