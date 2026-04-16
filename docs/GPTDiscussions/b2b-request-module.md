# B2B Request Module — Design & Implementation

**Topic:** B2B Ticket Request System for Super Admin and Organizer
**Date:** April 15-16, 2026
**Duration:** Multi-session implementation

---

## 1. Purpose

The **B2B Request module** enables organizers to request bulk tickets from the platform via a Super Admin approval workflow. It is a building block for:

- **B2B Ticket Distribution** — Organizers can request tickets in bulk (for resale, partnerships, promotions)
- **Super Admin Oversight** — Platform admins review and approve/reject B2B requests
- **Paid vs Free Transfers** — Supports both free transfers (promotional) and paid purchases

### Why It's a Building Block

The B2B system is foundational for:
1. **Reseller Networks** — Future modules will extend this to allow multi-tier reselling
2. **Promotion/Giveaway System** — Free B2B transfers power promotional campaigns
3. **Commission Tracking** — Orders and allocations track money flow for revenue sharing
4. **Ticket Provenance** — Allocation edges build the ticket ownership tree

---

## 2. Architecture Decisions

### 2.1 Removed Redundant `requesting_organizer_id`

**Problem:** `B2BRequestModel` stored `requesting_organizer_id` redundantly since the organizer can be derived via `event.organizer_page_id`.

**Solution:** Removed the column. Organizer ownership is verified by:
```
user → event.organizer_page_id → event_id → B2B request
```

**Files changed:**
- `B2BRequestModel` — removed `requesting_organizer_id` column
- Organizer endpoints now use `/events/{event_id}/b2b-requests` instead of `/{organizer_id}/b2b-requests`

### 2.2 Auto-Derive B2B Ticket Type

**Problem:** Earlier design required organizers to specify `ticket_type_id`. This was error-prone.

**Solution:** System auto-creates/gets a "B2B" ticket type per event via `get_or_create_b2b_ticket_type()`.

### 2.3 Tickets Created On-The-Fly

**Key Insight:** B2B tickets do NOT exist in the pool when the request is made. They are created:
- **Free mode:** When Super Admin approves
- **Paid mode:** When organizer confirms payment

This is different from regular allocation where tickets are pre-allocated from a pool.

---

## 3. Data Models

### 3.1 B2BRequestModel

```
B2BRequestModel {
    id: UUID (PK)
    requesting_user_id: UUID (FK → users)     -- Who requested
    event_id: UUID (FK → events)             -- Target event
    event_day_id: UUID (FK → event_days)     -- Target day
    ticket_type_id: UUID (FK → ticket_types) -- Auto-derived B2B type
    quantity: int                             -- Number of tickets
    status: B2BRequestStatus                 -- pending/approved_free/approved_paid/rejected
    reviewed_by_admin_id: UUID (FK, nullable)
    admin_notes: str (nullable)
    allocation_id: UUID (FK, nullable)
    order_id: UUID (FK, nullable)
    metadata_: dict
    created_at, updated_at: datetime
}
```

### 3.2 B2BRequestStatus Enum

```python
class B2BRequestStatus(str, Enum):
    pending = "pending"
    approved_free = "approved_free"
    approved_paid = "approved_paid"
    rejected = "rejected"
```

### 3.3 Related Models

- **OrderModel** — Tracks payment (type: transfer/purchase, status: pending/paid)
- **AllocationModel** — Links tickets to a recipient holder
- **AllocationTicketModel** — Junction linking allocation to tickets
- **TicketHolderModel** — Identity layer (separate from User)

---

## 4. API Endpoints

### 4.1 Organizer Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/organizers/events/{event_id}/b2b-requests` | Create B2B request |
| GET | `/api/organizers/events/{event_id}/b2b-requests` | List requests for event |
| POST | `/api/organizers/events/{event_id}/b2b-requests/{id}/confirm-payment` | Confirm payment (paid flow) |

### 4.2 Super Admin Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/superadmin/b2b-requests` | List all B2B requests |
| GET | `/api/superadmin/b2b-requests/pending` | List pending requests |
| GET | `/api/superadmin/b2b-requests/{id}` | Get single request |
| POST | `/api/superadmin/b2b-requests/{id}/approve-free` | Approve as free transfer |
| POST | `/api/superadmin/b2b-requests/{id}/approve-paid` | Approve as paid purchase |
| POST | `/api/superadmin/b2b-requests/{id}/reject` | Reject request |

---

## 5. Flow Diagrams

### 5.1 Free B2B Flow (Single Step)

```
Organizer                  Super Admin                  System
    |                           |                          |
    |-- Create B2B Request ---->|                          |
    |   (quantity=50)           |                          |
    |                           |-- Approve Free --------->|
    |                           |                          |-- Create $0 TRANSFER order
    |                           |                          |-- Get/create B2B ticket type
    |                           |                          |-- Create 50 tickets (indices 1-50)
    |                           |                          |-- Create allocation
    |                           |                          |-- Link tickets to holder
    |<-- Status: approved_free -|                          |
    |                           |                          |
```

### 5.2 Paid B2B Flow (Two Steps)

```
Organizer                  Super Admin                  System
    |                           |                          |
    |-- Create B2B Request ---->|                          |
    |                           |-- Approve Paid --------->|
    |                           |   (amount=5000)          |-- Create PURCHASE order (pending)
    |<-- Status: approved_paid -|                          |
    |   (order_id set)          |                          |
    |                           |                          |
    |-- Confirm Payment ------>|                          |
    |                           |                          |-- Mark order paid
    |                           |                          |-- Create 50 tickets
    |                           |                          |-- Create allocation
    |<-- Status: approved_paid -|                          |
    |   (allocation_id set)     |                          |
```

---

## 6. Key Code Paths

### 6.1 SuperAdminService.approve_b2b_request_free

```python
async def approve_b2b_request_free(self, admin_id, request_id, admin_notes):
    # 1. Validate request exists and is pending
    # 2. Resolve recipient holder (find or create TicketHolder)
    # 3. Create $0 TRANSFER order (status=paid)
    # 4. Get or create B2B ticket type for event_day
    # 5. Create tickets on-the-fly via bulk_create_tickets()
    # 6. Create allocation linking to recipient holder
    # 7. Add tickets to allocation
    # 8. Update ticket ownership
    # 9. Upsert allocation edge
    # 10. Mark allocation completed
    # 11. Update B2B request status
```

### 6.2 SuperAdminService.process_paid_b2b_allocation

```python
async def process_paid_b2b_allocation(self, request_id):
    # 1. Validate request is approved_paid
    # 2. Get existing pending order
    # 3. Mark order as paid
    # 4. Resolve recipient holder
    # 5. Create tickets on-the-fly (same as free)
    # 6. Create allocation
    # 7. Link tickets
    # 8. Update B2B request with allocation_id
```

---

## 7. Testing

### 7.1 Test Setup

**Database cleared:** All tables truncated (tickets, allocations, orders, b2b_requests, etc.)

**Entities created:**
- User: `testuser@example.com` (ID: `6e8cd6bb-3aed-4761-b766-99f5a0665b85`)
- Organizer Page: "Test Organizer" (ID: `cdfe8c34-3553-4839-ad3a-99c053eeea0b`)
- Draft Event: "Test Event" (ID: `8d3cfe58-d853-47b7-9253-4812416d9553`)
- Event Day: (ID: `1475a617-a411-4444-ae15-c2aaf68e3937`)
- Super Admin: "Admin User" (ID: `56f9b4ea-dc19-42bc-bf0b-391fecf07f3c`)

### 7.2 Test 1: Free B2B Approval

**Steps:**
```bash
# 1. Create B2B request (organizer)
curl -X POST "/api/organizers/events/{event_id}/b2b-requests" \
  -d '{"eventId": "...", "eventDayId": "...", "quantity": 50}'

# 2. Approve free (super admin)
curl -X POST "/api/superadmin/b2b-requests/{b2b_id}/approve-free" \
  -d '{"amount": 0}'
```

**Results:**
- B2B Request status: `pending` → `approved_free`
- 50 tickets created (indices 1-50)
- $0 TRANSFER order created (status=paid)
- Allocation created with 50 tickets linked
- `reviewed_by_admin_id` set

**Database verification:**
```sql
SELECT COUNT(*), ticket_type_id FROM tickets GROUP BY ticket_type_id;
-- count: 50, ticket_type_id: <b2b_type_id>
```

### 7.3 Test 2: Paid B2B Approval

**Steps:**
```bash
# 1. Create B2B request (organizer)
curl -X POST "/api/organizers/events/{event_id}/b2b-requests" \
  -d '{"eventId": "...", "eventDayId": "...", "quantity": 30}'

# 2. Approve paid (super admin)
curl -X POST "/api/superadmin/b2b-requests/{b2b_id}/approve-paid" \
  -d '{"amount": 5000}'

# 3. Confirm payment (organizer)
curl -X POST "/api/organizers/events/{event_id}/b2b-requests/{b2b_id}/confirm-payment"
```

**Results:**
- After approve-paid:
  - B2B Request status: `approved_paid`
  - Order created: type=purchase, amount=5000, status=pending
  - allocation_id: null (tickets NOT created yet)

- After confirm-payment:
  - Order status: `pending` → `paid`
  - 30 tickets created (indices 51-80)
  - Allocation created with 30 tickets linked
  - B2B Request allocation_id now set

**Database verification:**
```sql
SELECT COUNT(*), MIN(ticket_index), MAX(ticket_index) FROM tickets;
-- count: 80, min: 1, max: 80

SELECT status FROM orders WHERE id = '<order_id>';
-- status: paid
```

### 7.4 GET API Tests

All Super Admin GET endpoints verified:

| Endpoint | Result |
|----------|--------|
| GET `/api/superadmin/b2b-requests` | Returns all requests ✅ |
| GET `/api/superadmin/b2b-requests/pending` | Returns pending only ✅ |
| GET `/api/superadmin/b2b-requests/{id}` | Returns single request ✅ |

---

## 8. Future Extensions

This module is designed to support:

1. **B2B Pricing Tiers** — Different prices per organizer tier
2. **Commission Tracking** — Add `commission_amount` to order
3. **Refund Flow** — Reverse allocation and ticket ownership
4. **Multi-Event B2B** — Single request spanning multiple days
5. **B2B Analytics** — Track approval rates, average amounts

---

## 9. Files Modified

| File | Changes |
|------|---------|
| `apps/superadmin/models.py` | Removed `requesting_organizer_id` |
| `apps/superadmin/repository.py` | Removed `requesting_organizer_id` from create |
| `apps/superadmin/service.py` | Tickets created on-the-fly (not from pool) |
| `apps/superadmin/response.py` | Fixed UUID/datetime types |
| `apps/organizer/urls.py` | Changed to `/events/{event_id}/b2b-requests` |
| `apps/organizer/service.py` | Updated for event-based ownership |
| `apps/allocation/service.py` | `resolve_holder` now looks up user phone/email |
| `apps/user/service.py` | Auto-create TicketHolder on signup |
| `migrations/versions/7c7609b23301_.py` | Removes `requesting_organizer_id` column |
