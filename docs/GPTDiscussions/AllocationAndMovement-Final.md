# TicketShicket — Allocation & Movement Architecture

**Version:** 1.0
**Status:** Final Design
**Last Updated:** 2026-04-12

---

## 1. Core Philosophy

```
Ticket       → ownership (static asset)
Allocation   → movement  (event log / trigger)
Order        → money    (optional layer on top)
```

> **Golden Rule:** A ticket can move many times, but can only belong to one holder at any moment.

### Key Principles

1. **Tickets never move directly** — ownership changes ONLY through Allocation
2. **Allocation is an event log** — append-only history, never mutated after creation
3. **from_holder_id determines source** — NULL = pool, NOT NULL = user-to-user transfer
4. **Tree/Graf is derived, not stored** — build it at query time from allocations
5. **Atomic transactions** — ownership change and allocation creation MUST happen in same DB transaction

---

## 2. Data Models

### 2.1 TicketHolder (Identity Layer)

```sql
CREATE TABLE ticket_holders (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Auth linkage (nullable — holder may not have an account)
    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Identity contact (one or the other — NOT both at v1)
    phone       TEXT UNIQUE,
    email       TEXT UNIQUE,

    -- Status
    status      TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'deleted')),

    created_at  TIMESTAMP NOT NULL DEFAULT now(),
    updated_at  TIMESTAMP NOT NULL DEFAULT now(),

    CONSTRAINT chk_phone_or_email CHECK (
        (phone IS NOT NULL AND email IS NULL) OR
        (phone IS NULL AND email IS NOT NULL)
    )
);

CREATE INDEX idx_ticket_holders_user_id ON ticket_holders(user_id);
CREATE INDEX idx_ticket_holders_phone ON ticket_holders(phone) WHERE phone IS NOT NULL;
CREATE INDEX idx_ticket_holders_email ON ticket_holders(email) WHERE email IS NOT NULL;
```

**Design Decisions:**
- `user_id` is nullable — a holder may exist without a registered account
- Phone OR email (not both) at v1 — simplifies identity matching
- `status = deleted` (hard delete v1) — no `merged_into_holder_id` complexity

---

### 2.2 Allocation

```sql
CREATE TABLE allocations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    event_id        UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,

    -- Movement endpoints
    from_holder_id  UUID REFERENCES ticket_holders(id) ON DELETE SET NULL,
    to_holder_id    UUID NOT NULL REFERENCES ticket_holders(id),

    -- Optional order association (for purchase flows)
    order_id        UUID REFERENCES orders(id) ON DELETE SET NULL,

    -- Status machine: pending → processing → completed / failed
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'processing', 'completed', 'failed')),

    -- Failure tracking
    failure_reason  TEXT,

    created_at      TIMESTAMP NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_allocations_event_id ON allocations(event_id);
CREATE INDEX idx_allocations_from_holder ON allocations(from_holder_id);
CREATE INDEX idx_allocations_to_holder ON allocations(to_holder_id);
CREATE INDEX idx_allocations_status ON allocations(status);
CREATE INDEX idx_allocations_created_at ON allocations(created_at);
```

**Design Decisions:**
- `source_type` removed — derived from `from_holder_id`:
  - `from_holder_id IS NULL` → POOL (organizer's initial allocation)
  - `from_holder_id IS NOT NULL` → TRANSFER (user-to-user)
- Status machine enables retry logic and debugging
- `failure_reason` stores error details for failed allocations

---

### 2.3 AllocationTicket (Junction)

```sql
CREATE TABLE allocation_tickets (
    allocation_id   UUID NOT NULL REFERENCES allocations(id) ON DELETE CASCADE,
    ticket_id       UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,

    PRIMARY KEY (allocation_id, ticket_id)
);

CREATE INDEX idx_alloc_tickets_ticket_id ON allocation_tickets(ticket_id);
```

---

### 2.4 AllocationEdges (Pre-aggregated for Tree Queries)

```sql
CREATE TABLE allocation_edges (
    event_id        UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    from_holder_id  UUID REFERENCES ticket_holders(id) ON DELETE CASCADE,
    to_holder_id    UUID NOT NULL REFERENCES ticket_holders(id),

    ticket_count    INT NOT NULL DEFAULT 0,

    updated_at      TIMESTAMP NOT NULL DEFAULT now(),

    PRIMARY KEY (event_id, from_holder_id, to_holder_id)
);

CREATE INDEX idx_allocation_edges_to_holder ON allocation_edges(to_holder_id);
```

**Design Decisions:**
- Stores aggregated counts per (event, from_holder, to_holder) tuple
- Updated incrementally inside the same transaction as allocation creation
- `ON CONFLICT ... DO UPDATE` ensures atomic upsert
- Tree query becomes O(1) instead of O(n) — no GROUP BY + JOIN needed

---

### 2.5 Tickets (Updated)

```sql
CREATE TABLE tickets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    event_id        UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    event_day_id    UUID NOT NULL REFERENCES event_days(id) ON DELETE CASCADE,
    ticket_type_id  UUID NOT NULL REFERENCES ticket_types(id),

    ticket_index    INT NOT NULL,

    -- Ownership
    owner_holder_id UUID REFERENCES ticket_holders(id) ON DELETE SET NULL,

    -- Seat info (optional)
    seat_label      TEXT,
    seat_metadata   JSONB,

    -- Ticket status
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'cancelled', 'used')),

    -- Generic locking (works for both order-based and transfer-based locks)
    lock_reference_type TEXT,  -- 'order' or 'allocation'
    lock_reference_id   UUID,
    lock_expires_at     TIMESTAMP,

    created_at      TIMESTAMP NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP NOT NULL DEFAULT now(),

    UNIQUE (event_day_id, ticket_index)
);

CREATE INDEX idx_tickets_owner_holder ON tickets(owner_holder_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_lock_expires ON tickets(lock_expires_at)
    WHERE lock_expires_at IS NOT NULL;
```

**Design Decisions:**
- `owner_user_id` replaced with `owner_holder_id` — links to identity layer, not auth
- Generic locking: `lock_reference_type + lock_reference_id` works for both orders and direct transfers
- `lock_expires_at` allows automatic lock release (prevents orphaned locks)

---

## 3. All Allocation Flows

### 3.1 Flow Classification

| Flow | Order? | Allocation Timing | Status |
|------|--------|-------------------|--------|
| Online Purchase | Yes | After payment | pending → processing → completed |
| B2B Offline Sale | Optional | Instant | processing → completed |
| Organizer → Reseller | No | Instant | processing → completed |
| Organizer → Customer (Direct) | No | Instant | processing → completed |
| Reseller → Customer | Optional | Instant | processing → completed |
| Customer → Friend (Gift) | No | Instant | processing → completed |
| Refund / Cancellation | Yes | After refund | pending → processing → completed |

---

### 3.2 Online Purchase Flow

```
User selects tickets
       ↓
Order created (status: pending)
       ↓
Payment initiated
       ↓
Tickets LOCKED (lock_reference_type='order', lock_reference_id=order_id)
       ↓
Payment SUCCESS
       ↓
Allocation created (status: pending)
       ↓
allocation_tickets inserted
       ↓
Ticket owner_holder_id updated
       ↓
allocation_edges updated (ticket_count += N)
       ↓
Allocation status → completed
       ↓
Order status → paid
```

**Code Flow (Critical Transaction):**
```python
async with db.transaction():
    # 1. Lock tickets
    locked = await db.execute("""
        UPDATE tickets
        SET lock_reference_type = 'order',
            lock_reference_id = :order_id,
            lock_expires_at = :expires
        WHERE id IN (SELECT id FROM tickets WHERE ...)
        AND owner_holder_id IS NULL
        AND lock_reference_id IS NULL
        RETURNING id
    """, {...})

    # 2. Create allocation
    allocation = await db.execute("""
        INSERT INTO allocations (...)
        VALUES (...) RETURNING id
    """)

    # 3. Insert junction
    await db.execute("""
        INSERT INTO allocation_tickets (allocation_id, ticket_id)
        SELECT :allocation_id, id FROM tickets WHERE id IN (...)
    """)

    # 4. Update ownership
    await db.execute("""
        UPDATE tickets
        SET owner_holder_id = :to_holder_id,
            lock_reference_type = NULL,
            lock_reference_id = NULL,
            lock_expires_at = NULL
        WHERE id IN (...)
    """)

    # 5. Update edges
    await db.execute("""
        INSERT INTO allocation_edges (event_id, from_holder_id, to_holder_id, ticket_count)
        VALUES (:event_id, NULL, :to_holder_id, :count)
        ON CONFLICT (event_id, from_holder_id, to_holder_id)
        DO UPDATE SET ticket_count = allocation_edges.ticket_count + EXCLUDED.ticket_count
    """)

    # 6. Mark completed
    await db.execute("UPDATE allocations SET status = 'completed' WHERE id = :id")
```

---

### 3.3 B2B / Offline Allocation Flow

```
Organizer selects ticket type + quantity
       ↓
Organizer selects recipient (phone OR email)
       ↓
ticket_holder fetched/created (get_or_create)
       ↓
Allocation created (status: processing)
       ↓
[Same transaction as above — steps 2-5]
       ↓
Allocation status → completed
```

**Key Difference from Purchase:**
- No `order_id`
- No pending (since no payment async)
- `lock_reference_type` may be 'allocation' instead of 'order'
- Goes directly to `processing` status

---

### 3.4 User-to-User Transfer Flow

```
Sender selects tickets to transfer
       ↓
System validates sender owns the tickets
       ↓
Recipient identified (phone OR email)
       ↓
ticket_holder fetched/created
       ↓
Allocation created (status: processing)
       ↓
[Same atomic transaction]
       ↓
Allocation status → completed
```

**Validation Rules:**
```python
# Before allocation, verify ownership
tickets = await db.fetch_all("""
    SELECT id FROM tickets
    WHERE id IN (...)
    AND owner_holder_id = :sender_holder_id
    AND status = 'active'
    AND lock_reference_id IS NULL
""")
# If count != requested count → reject (tickets unavailable)
```

---

### 3.5 Refund / Cancellation Flow

```
Refund initiated
       ↓
Order marked for refund
       ↓
New Allocation created (from: current_owner, to: NULL/Pool)
       ↓
Status: pending → processing → completed
       ↓
Ticket returns to pool (owner_holder_id = NULL)
       ↓
allocation_edges updated (ticket_count decreases for original edge)
```

**Edge Cases:**
- If ticket was already transferred out of system → refund may not be possible
- Track via allocation history to determine original pool source

---

## 4. TicketHolder Resolution

### 4.1 Get or Create Logic

```python
async def resolve_holder(
    db,
    phone: str | None = None,
    email: str | None = None,
    user_id: uuid.UUID | None = None
) -> TicketHolder:
    """
    Resolve a ticket holder by contact info.
    Creates if not exists. Links user_id if provided.
    """
    assert phone or email or user_id, "At least one identifier required"

    # 1. Try find by user_id (highest priority — most specific)
    if user_id:
        holder = await db.fetch_one(
            "SELECT * FROM ticket_holders WHERE user_id = :user_id",
            {"user_id": user_id}
        )
        if holder:
            return holder

    # 2. Try find by phone
    if phone:
        holder = await db.fetch_one(
            "SELECT * FROM ticket_holders WHERE phone = :phone",
            {"phone": phone}
        )
        if holder:
            # If user_id also provided but not linked → link it
            if user_id and holder.user_id is None:
                await db.execute(
                    "UPDATE ticket_holders SET user_id = :uid WHERE id = :hid",
                    {"uid": user_id, "hid": holder.id}
                )
            return holder

    # 3. Try find by email
    if email:
        holder = await db.fetch_one(
            "SELECT * FROM ticket_holders WHERE email = :email",
            {"email": email}
        )
        if holder:
            if user_id and holder.user_id is None:
                await db.execute(
                    "UPDATE ticket_holders SET user_id = :uid WHERE id = :hid",
                    {"uid": user_id, "hid": holder.id}
                )
            return holder

    # 4. Create new holder
    holder_id = await db.execute("""
        INSERT INTO ticket_holders (user_id, phone, email, status)
        VALUES (:user_id, :phone, :email, 'active')
        RETURNING id
    """, {
        "user_id": user_id,
        "phone": phone,
        "email": email
    })

    return await db.fetch_one(
        "SELECT * FROM ticket_holders WHERE id = :id",
        {"id": holder_id}
    )
```

### 4.2 Concurrency Handling

```sql
-- Use DB constraint for safety
UNIQUE (phone)
UNIQUE (email)

-- Application logic:
BEGIN;
try:
    INSERT INTO ticket_holders ...;
EXCEPT UNIQUE_VIOLATION:
    -- Another request created it first
    ROLLBACK;
    -- Re-fetch existing
    SELECT * FROM ticket_holders WHERE phone = :phone;
COMMIT;
```

---

### 4.3 Signup + Holder Merge

When a user registers with both phone AND email:

```python
async def merge_holders_on_signup(
    db,
    user_id: uuid.UUID,
    phone: str | None,
    email: str | None
):
    """
    Called during user registration.
    Finds all holders matching phone/email and merges into one.
    """
    # 1. Find all matching holders
    holders = await db.fetch_all("""
        SELECT * FROM ticket_holders
        WHERE (phone = :phone OR email = :email)
        AND user_id IS NULL
    """, {"phone": phone, "email": email})

    if len(holders) == 0:
        # Create new holder linked to user
        return await resolve_holder(db, phone=phone, email=email, user_id=user_id)

    # 2. Pick primary (first found)
    primary = holders[0]
    others = holders[1:]

    # 3. Move all tickets to primary
    for h in others:
        await db.execute("""
            UPDATE tickets
            SET owner_holder_id = :primary_id
            WHERE owner_holder_id = :old_id
        """, {"primary_id": primary.id, "old_id": h.id})

    # 4. Delete (hard delete v1) old holders
    for h in others:
        await db.execute(
            "DELETE FROM ticket_holders WHERE id = :id",
            {"id": h.id}
        )

    # 5. Update primary with user_id and both contacts
    await db.execute("""
        UPDATE ticket_holders
        SET user_id = :user_id,
            phone = COALESCE(:phone, phone),
            email = COALESCE(:email, email)
        WHERE id = :id
    """, {
        "user_id": user_id,
        "phone": phone,
        "email": email,
        "id": primary.id
    })

    return primary
```

---

## 5. Ticket Travel History (Query)

### 5.1 Get Full Journey of One Ticket

```python
async def get_ticket_journey(db, ticket_id: uuid.UUID) -> list[dict]:
    """
    Returns ordered list of movements for a ticket.
    """
    rows = await db.fetch_all("""
        SELECT
            a.id                 AS allocation_id,
            a.from_holder_id,
            fh.phone             AS from_phone,
            fh.email             AS from_email,
            a.to_holder_id,
            th.phone             AS to_phone,
            th.email             AS to_email,
            a.status,
            a.created_at
        FROM allocation_tickets at
        JOIN allocations a ON at.allocation_id = a.id
        LEFT JOIN ticket_holders fh ON a.from_holder_id = fh.id
        JOIN ticket_holders th ON a.to_holder_id = th.id
        WHERE at.ticket_id = :ticket_id
        ORDER BY a.created_at ASC
    """, {"ticket_id": ticket_id})

    journey = []
    for i, row in enumerate(rows):
        journey.append({
            "step": i + 1,
            "from": {
                "holder_id": row["from_holder_id"],
                "phone": row["from_phone"],
                "email": row["from_email"],
                "label": "POOL" if row["from_holder_id"] is None else (
                    row["from_phone"] or row["from_email"]
                )
            },
            "to": {
                "holder_id": row["to_holder_id"],
                "phone": row["to_phone"],
                "email": row["to_email"],
                "label": row["to_phone"] or row["to_email"]
            },
            "status": row["status"],
            "timestamp": row["created_at"]
        })

    return journey
```

### 5.2 Get Distribution Tree (Organizer Dashboard)

```python
async def get_allocation_tree(
    db,
    event_id: uuid.UUID
) -> dict:
    """
    Builds the full distribution tree from allocation_edges.
    Fast — O(edges) no JOINs needed.
    """
    # 1. Get all edges (pre-aggregated)
    edges = await db.fetch_all("""
        SELECT
            ae.from_holder_id,
            ae.to_holder_id,
            ae.ticket_count,
            th.phone,
            th.email,
            th.user_id
        FROM allocation_edges ae
        JOIN ticket_holders th ON ae.to_holder_id = th.id
        WHERE ae.event_id = :event_id
    """, {"event_id": event_id})

    # 2. Build adjacency map
    children = {}  # holder_id -> list of {holder, count, children}
    all_holders = {}

    # First pass: collect all holder info
    for edge in edges:
        for hid in [edge["from_holder_id"], edge["to_holder_id"]]:
            if hid and hid not in all_holders:
                holder_info = await db.fetch_one(
                    "SELECT * FROM ticket_holders WHERE id = :id",
                    {"id": hid}
                )
                all_holders[hid] = {
                    "id": hid,
                    "phone": holder_info["phone"],
                    "email": holder_info["email"],
                    "user_id": holder_info["user_id"],
                    "label": holder_info["phone"] or holder_info["email"] or "Unknown"
                }

        # Build edge
        if edge["from_holder_id"] not in children:
            children[edge["from_holder_id"]] = []
        children[edge["from_holder_id"]].append({
            "to_holder": all_holders[edge["to_holder_id"]],
            "ticket_count": edge["ticket_count"],
            "children": []  # populated in next pass
        })

    # 3. Recursive tree builder
    def build_tree(holder_id, depth=0):
        node = {
            "holder": all_holders.get(holder_id, {
                "id": None,
                "label": "POOL",
                "phone": None,
                "email": None,
                "user_id": None
            }),
            "ticket_count": None,  # root has no count
            "children": []
        }

        for child in children.get(holder_id, []):
            child_node = build_tree(child["to_holder"]["id"], depth + 1)
            child_node["ticket_count"] = child["ticket_count"]
            node["children"].append(child_node)

        return node

    # 4. Return tree starting from POOL (from_holder_id = NULL)
    return build_tree(None)
```

### 5.3 Example Response

```json
{
  "holder": {
    "id": null,
    "label": "POOL",
    "phone": null,
    "email": null
  },
  "ticket_count": null,
  "children": [
    {
      "holder": {
        "id": "uuid-seller1",
        "label": "9876543210",
        "phone": "9876543210",
        "email": null
      },
      "ticket_count": 500,
      "children": [
        {
          "holder": {
            "id": "uuid-customer-a",
            "label": "9123456789",
            "phone": "9123456789",
            "email": null
          },
          "ticket_count": 200,
          "children": []
        },
        {
          "holder": {
            "id": "uuid-customer-b",
            "label": "customer@b.com",
            "phone": null,
            "email": "customer@b.com"
          },
          "ticket_count": 300,
          "children": []
        }
      ]
    },
    {
      "holder": {
        "id": "uuid-seller2",
        "label": "9988776655",
        "phone": "9988776655",
        "email": null
      },
      "ticket_count": 300,
      "children": []
    },
    {
      "holder": {
        "id": "uuid-customer-x",
        "label": "walkin@event.com",
        "phone": null,
        "email": "walkin@event.com"
      },
      "ticket_count": 200,
      "children": []
    }
  ]
}
```

---

## 6. Locking & Concurrency

### 6.1 Lock Acquisition

```python
async def acquire_ticket_locks(
    db,
    ticket_ids: list[uuid.UUID],
    lock_ref_type: str,  # 'order' or 'allocation'
    lock_ref_id: uuid.UUID,
    holder_id: uuid.UUID,
    lock_ttl_seconds: int = 300  # 5 minutes
) -> tuple[bool, list[uuid.UUID]]:
    """
    Attempts to lock tickets for allocation/purchase.
    Returns (success, locked_ticket_ids).
    """
    expires = datetime.utcnow() + timedelta(seconds=lock_ttl_seconds)

    # First: clean expired locks
    await db.execute("""
        UPDATE tickets
        SET lock_reference_type = NULL,
            lock_reference_id = NULL,
            lock_expires_at = NULL
        WHERE lock_expires_at < :now
        AND lock_reference_id IS NOT NULL
    """, {"now": datetime.utcnow()})

    # Attempt lock
    result = await db.execute("""
        UPDATE tickets
        SET lock_reference_type = :ref_type,
            lock_reference_id = :ref_id,
            lock_expires_at = :expires
        WHERE id IN :ticket_ids
        AND owner_holder_id = :holder_id
        AND lock_reference_id IS NULL
        AND status = 'active'
        RETURNING id
    """, {
        "ticket_ids": tuple(ticket_ids),
        "ref_type": lock_ref_type,
        "ref_id": lock_ref_id,
        "expires": expires,
        "holder_id": holder_id
    })

    locked_ids = [row["id"] for row in result]

    if len(locked_ids) != len(ticket_ids):
        # Partial lock — rollback what we got
        await db.execute("""
            UPDATE tickets
            SET lock_reference_type = NULL,
                lock_reference_id = NULL,
                lock_expires_at = NULL
            WHERE id IN :ids
        """, {"ids": tuple(locked_ids)})
        return False, []

    return True, locked_ids
```

### 6.2 Lock Release

```python
async def release_ticket_locks(
    db,
    ticket_ids: list[uuid.UUID],
    lock_ref_id: uuid.UUID
):
    """
    Releases locks on tickets.
    Called on payment failure, timeout, or cancellation.
    """
    await db.execute("""
        UPDATE tickets
        SET lock_reference_type = NULL,
            lock_reference_id = NULL,
            lock_expires_at = NULL
        WHERE id IN :ticket_ids
        AND lock_reference_id = :ref_id
    """, {
        "ticket_ids": tuple(ticket_ids),
        "ref_id": lock_ref_id
    })
```

---

## 7. Allocation Status Machine

```
┌──────────┐
│ pending  │  ← Initial state for async flows (payment required)
└────┬─────┘
     │ processing initiated
     ↓
┌────────────┐
│ processing │  ← Tickets locked, allocation in progress
└────┬───────┘
     │
     ├─── success ──→ ┌───────────┐
     │                │ completed │
     │                └───────────┘
     │
     └─── failure ──→ ┌────────┐
                      │ failed │
                      └────────┘
```

### 7.1 Status Transition Rules

| From | To | Trigger |
|------|----|---------|
| pending | processing | Lock acquired, transaction starts |
| processing | completed | All steps succeeded, committed |
| processing | failed | Any step failed, rolled back |
| pending | failed | Payment declined / cancelled before processing |

### 7.2 Idempotency

```python
async def process_allocation(
    db,
    allocation_id: uuid.UUID,
    ticket_ids: list[uuid.UUID],
    from_holder_id: uuid.UUID | None,
    to_holder_id: uuid.UUID,
    event_id: uuid.UUID
):
    """
    Idempotent allocation processor.
    Checks current status before acting.
    """
    # Get current state
    alloc = await db.fetch_one(
        "SELECT status FROM allocations WHERE id = :id",
        {"id": allocation_id}
    )

    if alloc["status"] == "completed":
        return  # Already done, skip

    if alloc["status"] == "processing":
        raise Exception(f"Allocation {allocation_id} already being processed")

    # Transition to processing
    await db.execute("""
        UPDATE allocations
        SET status = 'processing'
        WHERE id = :id
        AND status = 'pending'
    """, {"id": allocation_id})

    try:
        async with db.transaction():
            # ... do the allocation work ...

            await db.execute("""
                UPDATE allocations
                SET status = 'completed'
                WHERE id = :id
            """, {"id": allocation_id})

    except Exception as e:
        await db.execute("""
            UPDATE allocations
            SET status = 'failed',
                failure_reason = :reason
            WHERE id = :id
        """, {"id": allocation_id, "reason": str(e)})
        raise
```

---

## 8. Edge Cases & Error Handling

### 8.1 Over-allocation Prevention

```python
async def validate_allocation_quantity(
    db,
    event_id: uuid.UUID,
    ticket_type_id: uuid.UUID,
    event_day_id: uuid.UUID,
    requested_quantity: int
) -> tuple[bool, int]:
    """
    Check if enough unallocated tickets exist.
    Returns (can_allocate, available_count).
    """
    # Count total tickets for this type + day
    total = await db.fetch_val("""
        SELECT COUNT(*) FROM tickets
        WHERE event_id = :event_id
        AND ticket_type_id = :ticket_type_id
        AND event_day_id = :event_day_id
        AND status = 'active'
    """, {"event_id": event_id, "ticket_type_id": ticket_type_id, "event_day_id": event_day_id})

    # Count already allocated (has owner)
    allocated = await db.fetch_val("""
        SELECT COUNT(*) FROM tickets
        WHERE event_id = :event_id
        AND ticket_type_id = :ticket_type_id
        AND event_day_id = :event_day_id
        AND status = 'active'
        AND owner_holder_id IS NOT NULL
    """, {...})

    available = total - allocated

    return requested_quantity <= available, available
```

### 8.2 Concurrent Allocation Race Condition

```
Scenario:
- Seller has 100 tickets
- Request A: allocate 80
- Request B: allocate 30 (concurrent)

Problem: Both see 100 available, both allocate → 110 tickets allocated

Solution: Use ticket-level locking
```

```sql
-- Every allocation picks specific ticket IDs
UPDATE tickets
SET lock_reference_id = :alloc_id
WHERE id IN (
    SELECT id FROM tickets
    WHERE event_id = :event_id
    AND ticket_type_id = :ticket_type_id
    AND owner_holder_id = :from_holder_id
    AND lock_reference_id IS NULL
    AND status = 'active'
    ORDER BY ticket_index  -- deterministic ordering
    LIMIT :quantity
)
RETURNING id
```

> **Key:** The `LIMIT :quantity` with deterministic `ORDER BY ticket_index` ensures atomic allocation without overselling.

### 8.3 Lock Expiry Mid-Transaction

```python
async def with_lock_expiry_guard(db, ticket_ids, operation):
    """
    Ensures locks don't expire while allocation is in progress.
    """
    try:
        # Extend lock for duration of transaction
        await db.execute("""
            UPDATE tickets
            SET lock_expires_at = :new_expires
            WHERE id IN :ids
        """, {"ids": ticket_ids, "new_expires": datetime.utcnow() + timedelta(hours=1)})

        result = await operation()

        # Release lock after commit
        await release_ticket_locks(db, ticket_ids, ...)

    except Exception:
        await release_ticket_locks(db, ticket_ids, ...)
        raise
```

### 8.4 Failed Allocation Edge Cleanup

When allocation fails after `allocation_edges` was updated:

```python
async def rollback_edge_update(
    db,
    event_id: uuid.UUID,
    from_holder_id: uuid.UUID | None,
    to_holder_id: uuid.UUID,
    ticket_count: int
):
    """
    Decrements edge count on failed allocation.
    """
    await db.execute("""
        UPDATE allocation_edges
        SET ticket_count = GREATEST(0, ticket_count - :count),
            updated_at = now()
        WHERE event_id = :event_id
        AND from_holder_id <=> :from_holder_id  -- NULL-safe compare
        AND to_holder_id = :to_holder_id
    """, {
        "event_id": event_id,
        "from_holder_id": from_holder_id,
        "to_holder_id": to_holder_id,
        "count": ticket_count
    })
```

### 8.5 Allocation to Deleted Holder

```python
async def validate_recipient(
    db,
    to_holder_id: uuid.UUID
) -> bool:
    """
    Validates recipient holder is active before allocation.
    """
    holder = await db.fetch_one(
        "SELECT status FROM ticket_holders WHERE id = :id",
        {"id": to_holder_id}
    )
    return holder and holder["status"] == "active"
```

---

## 9. API Contracts

### 9.1 Allocate Tickets (B2B / Organizer)

```
POST /api/internal/events/{event_id}/allocations

Request:
{
    "from_holder_id": "uuid-or-null",   // null = from pool
    "recipient": {
        "phone": "9876543210",          // phone OR email (not both)
        "email": null
    },
    "ticket_type_id": "uuid",
    "event_day_id": "uuid",
    "quantity": 50,
    "order_id": "uuid-or-null"          // if payment involved
}

Response (201):
{
    "allocation_id": "uuid",
    "status": "completed",              // or "pending" if async
    "tickets_allocated": 50,
    "to_holder_id": "uuid"
}
```

### 9.2 Transfer Tickets (User → User)

```
POST /api/internal/holders/{from_holder_id}/transfers

Request:
{
    "to": {
        "phone": "9876543210"
    },
    "ticket_ids": ["uuid1", "uuid2", ...]
}

Response (201):
{
    "allocation_id": "uuid",
    "status": "completed",
    "tickets_transferred": 3
}
```

### 9.3 Get Ticket Journey

```
GET /api/internal/tickets/{ticket_id}/journey

Response (200):
{
    "ticket_id": "uuid",
    "journey": [
        {
            "step": 1,
            "from": { "label": "POOL" },
            "to": { "label": "9876543210", "holder_id": "uuid" },
            "status": "completed",
            "timestamp": "2026-04-10T12:00:00Z"
        },
        ...
    ]
}
```

### 9.4 Get Distribution Tree

```
GET /api/internal/events/{event_id}/distribution-tree

Response (200):
{
    "event_id": "uuid",
    "tree": { ... }  // See 5.3 example
}
```

### 9.5 Get Holder's Tickets

```
GET /api/internal/holders/{holder_id}/tickets

Query params:
    event_id: uuid (optional)
    status: active | cancelled | used (optional)

Response (200):
{
    "holder_id": "uuid",
    "tickets": [
        {
            "ticket_id": "uuid",
            "event_id": "uuid",
            "event_title": "...",
            "ticket_type": "VIP",
            "ticket_index": 42,
            "status": "active",
            "allocation_history": [...]
        }
    ]
}
```

---

## 10. Rollback & Recovery Procedures

### 10.1 Expired Lock Recovery (Background Job)

```python
async def cleanup_expired_locks(db):
    """
    Periodic job (every 5 min) to release expired locks.
    """
    result = await db.execute("""
        UPDATE tickets
        SET lock_reference_type = NULL,
            lock_reference_id = NULL,
            lock_expires_at = NULL
        WHERE lock_expires_at < :now
        AND lock_reference_id IS NOT NULL
        RETURNING id, lock_reference_type, lock_reference_id
    """, {"now": datetime.utcnow()})

    for row in result:
        # Log for debugging
        print(f"Cleaned expired lock on ticket {row['id']}, "
              f"ref={row['lock_reference_type']}/{row['lock_reference_id']}")
```

### 10.2 Orphaned Allocation Cleanup

```python
async def cleanup_stale_pending_allocations(db, stale_threshold_minutes=30):
    """
    Mark pending allocations as failed if they're stuck too long.
    Run as scheduled job.
    """
    await db.execute("""
        UPDATE allocations
        SET status = 'failed',
            failure_reason = 'Timeout: allocation stuck in pending state'
        WHERE status = 'pending'
        AND created_at < :threshold
    """, {"threshold": datetime.utcnow() - timedelta(minutes=stale_threshold_minutes)})
```

### 10.3 Failed Edge Decrement

```python
async def reconcile_allocation_edges(db, event_id: uuid.UUID):
    """
    Reconciles allocation_edges counts with actual allocation_tickets.
    Run as periodic health check.
    """
    # Recalculate from scratch
    correct_counts = await db.fetch_all("""
        SELECT
            a.event_id,
            a.from_holder_id,
            a.to_holder_id,
            COUNT(*) as ticket_count
        FROM allocations a
        JOIN allocation_tickets at ON at.allocation_id = a.id
        WHERE a.event_id = :event_id
        AND a.status = 'completed'
        GROUP BY a.event_id, a.from_holder_id, a.to_holder_id
    """, {"event_id": event_id})

    # Upsert correct values
    for row in correct_counts:
        await db.execute("""
            INSERT INTO allocation_edges (event_id, from_holder_id, to_holder_id, ticket_count)
            VALUES (:event_id, :from, :to, :count)
            ON CONFLICT (event_id, from_holder_id, to_holder_id)
            DO UPDATE SET ticket_count = :count, updated_at = now()
        """, row)
```

---

## 11. Performance Considerations

### 11.1 Indexes Summary

```sql
-- ticket_holders
CREATE INDEX idx_th_user_id ON ticket_holders(user_id);
CREATE INDEX idx_th_phone ON ticket_holders(phone) WHERE phone IS NOT NULL;
CREATE INDEX idx_th_email ON ticket_holders(email) WHERE email IS NOT NULL;

-- allocations
CREATE INDEX idx_alloc_event ON allocations(event_id);
CREATE INDEX idx_alloc_from ON allocations(from_holder_id);
CREATE INDEX idx_alloc_to ON allocations(to_holder_id);
CREATE INDEX idx_alloc_status ON allocations(status);
CREATE INDEX idx_alloc_created ON allocations(created_at);

-- allocation_tickets
CREATE INDEX idx_at_ticket ON allocation_tickets(ticket_id);

-- allocation_edges
CREATE INDEX idx_ae_to ON allocation_edges(to_holder_id);

-- tickets
CREATE INDEX idx_tickets_owner ON tickets(owner_holder_id);
CREATE INDEX idx_tickets_lock_expires ON tickets(lock_expires_at) WHERE lock_expires_at IS NOT NULL;
```

### 11.2 Tree Query Complexity

| Approach | 1000 tickets | 50k tickets | 500k tickets |
|----------|-------------|-------------|--------------|
| GROUP BY + JOIN | ~50ms | ~800ms | ~8s |
| allocation_edges (pre-agg) | ~5ms | ~5ms | ~5ms |

---

## 12. Decisions Summary

| Decision | Final Choice |
|----------|-------------|
| Identity layer | `ticket_holders` (separate from users) |
| Contact per holder | Phone OR email (not both at v1) |
| `source_type` field | Removed — derived from `from_holder_id` |
| Allocation status | `pending → processing → completed / failed` |
| Transaction | Single atomic transaction for all allocation steps |
| Tree storage | Not stored — derived from `allocation_edges` |
| Edge pre-aggregation | `allocation_edges` updated on every allocation |
| Holder merge | On user signup — hard delete old holders |
| Lock mechanism | Generic: `lock_reference_type + lock_reference_id` |
| Failed allocation | Mark `failed`, edge decrement via reconciliation job |
| Soft delete | Not at v1 — hard delete for simplicity |

---

## 13. Open Questions / Future Considerations

1. **Partial allocation on failure** — if 5 tickets succeed and 3 fail mid-transaction, rollback all or partial commit?
2. **Gift/transfer with no payment** — should this require OTP verification from recipient?
3. **Batch allocation API** — for large B2B deals (500+ tickets), async processing?
4. **Waitlist / reservation** — if tickets are scarce, hold a "reservation" before allocation?
5. **Multi-event transfer** — can a ticket holder transfer tickets across events?
6. **Analytics / reseller performance** — add per-holder stats (tickets received, transferred, unsold)?

---

*End of Document*
