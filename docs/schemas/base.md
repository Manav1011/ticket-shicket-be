# TicketShicket Base Schema (v7)

This document captures the current core schema direction for TicketShicket.

## Key Changes in v7

### Ownership Model
- `User` is the login identity
- `Guest` is the anonymous identity
- `TicketHolder` is the ticket identity layer (separate from User)
  - A holder can have a `user_id` link (if they have an account)
  - A holder can have phone and/or email (contact-based identity)
  - A holder may exist without a user account (B2B recipients)
- `OrganizerPage` is the public brand/container for events

### Unified Order Model
**Every ticket movement creates an order.** Free transfers (B2B, U2U gift) create a `$0 TRANSFER` order. This keeps the flow consistent:

| Flow | Order Type | Amount | Status |
|------|------------|--------|--------|
| Online purchase | `PURCHASE` | actual price | `pending` → `paid` |
| B2B (free allocation) | `TRANSFER` | 0 | instant `paid` |
| U2U (gift/transfer) | `TRANSFER` | 0 | instant `paid` |

### Locking
All locks use `lock_reference_type='order'` and `lock_reference_id=order_id`. No separate `allocation` lock type exists — every allocation is created via an order.

---

# 1. Identity and Organizer Layer

```text
User
 ├── OrganizerPage
 └── created / updates Events

Guest

TicketHolder (identity layer for tickets)
 ├── linked to User (optional)
 └── identified by phone and/or email

OrganizerPage
 └── Event
```

## 1.1 User

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,

    status TEXT NOT NULL DEFAULT 'active', -- active / disabled / deleted

    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

## 1.2 Guest

```sql
CREATE TABLE guests (
    id UUID PRIMARY KEY,
    signature TEXT NOT NULL UNIQUE,
    user_agent TEXT,
    ip_address TEXT,

    status TEXT NOT NULL DEFAULT 'active',

    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

## 1.3 TicketHolder

Identity layer for ticket ownership. Separated from `User` to support:
- B2B recipients without user accounts (phone/email only)
- Gift transfers to non-users
- Future: holder with both phone + email

```sql
CREATE TABLE ticket_holders (
    id UUID PRIMARY KEY,

    user_id UUID REFERENCES users(id) ON DELETE SET NULL,  -- nullable: holder may not have account

    phone TEXT UNIQUE,   -- phone OR email at v1 (not both)
    email TEXT UNIQUE,

    status TEXT NOT NULL DEFAULT 'active', -- active / deleted

    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

## 1.4 OrganizerPage

```sql
CREATE TABLE organizer_pages (
    id UUID PRIMARY KEY,
    owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    bio TEXT,

    logo_url TEXT,
    cover_image_url TEXT,
    website_url TEXT,
    instagram_url TEXT,
    facebook_url TEXT,
    youtube_url TEXT,

    visibility TEXT NOT NULL DEFAULT 'private', -- public / private
    status TEXT NOT NULL DEFAULT 'active', -- active / archived

    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

---

# 2. Event Layer

```text
Event
 ├── EventMediaAsset
 ├── EventFAQ
 ├── EventDay
 │     ├── DayTicketAllocation
 │     ├── ScanLog
 │     └── BitmapSnapshot (optional)
 │
 ├── TicketType
 │     └── Ticket
 │
 ├── Allocation
 │     └── AllocationTicket
 │
 └── Order
```

## 2.1 Event

```sql
CREATE TABLE events (
    id UUID PRIMARY KEY,

    organizer_page_id UUID NOT NULL REFERENCES organizer_pages(id) ON DELETE CASCADE,
    created_by_user_id UUID NOT NULL REFERENCES users(id),

    title TEXT,
    slug TEXT UNIQUE,
    description TEXT,

    event_type TEXT, -- concert / conference / meetup / workshop / custom
    status TEXT NOT NULL DEFAULT 'draft', -- draft / published / archived
    event_access_type TEXT NOT NULL DEFAULT 'ticketed', -- open / ticketed
    setup_status JSONB NOT NULL DEFAULT '{}'::jsonb, -- section completion flags for guided setup

    location_mode TEXT, -- venue / online / recorded / hybrid

    timezone TEXT,
    start_date DATE,
    end_date DATE,

    venue_name TEXT,
    venue_address TEXT,
    venue_city TEXT,
    venue_state TEXT,
    venue_country TEXT,
    venue_latitude NUMERIC,
    venue_longitude NUMERIC,
    venue_google_place_id TEXT,

    online_event_url TEXT,
    recorded_event_url TEXT,

    published_at TIMESTAMP,
    is_published BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

## 2.2 EventMediaAsset

S3 stores the file, but the database stores the event-facing metadata.

```sql
CREATE TABLE event_media_assets (
    id UUID PRIMARY KEY,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,

    asset_type TEXT NOT NULL, -- banner / gallery_image / gallery_video / promo_video
    storage_key TEXT NOT NULL,
    public_url TEXT,

    title TEXT,
    caption TEXT,
    alt_text TEXT,
    sort_order INT NOT NULL DEFAULT 0,
    is_primary BOOLEAN NOT NULL DEFAULT false,

    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

## 2.3 EventFAQ

```sql
CREATE TABLE event_faqs (
    id UUID PRIMARY KEY,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,

    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    is_published BOOLEAN NOT NULL DEFAULT true,

    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

---

# 3. Scheduling and Ticket Definition

## 3.1 EventDay

```sql
CREATE TABLE event_days (
    id UUID PRIMARY KEY,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,

    day_index INT NOT NULL,
    date DATE NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,

    scan_status TEXT NOT NULL DEFAULT 'not_started', -- not_started / active / paused / ended
    scan_started_at TIMESTAMP,
    scan_paused_at TIMESTAMP,
    scan_ended_at TIMESTAMP,

    next_ticket_index INT NOT NULL DEFAULT 1,

    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),

    UNIQUE (event_id, day_index)
);
```

## 3.2 TicketType

```sql
CREATE TABLE ticket_types (
    id UUID PRIMARY KEY,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,

    name TEXT NOT NULL,
    category TEXT NOT NULL, -- ONLINE / B2B / PUBLIC / VIP

    price NUMERIC NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',

    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

## 3.3 DayTicketAllocation

```sql
CREATE TABLE day_ticket_allocations (
    id UUID PRIMARY KEY,

    event_day_id UUID NOT NULL REFERENCES event_days(id) ON DELETE CASCADE,
    ticket_type_id UUID NOT NULL REFERENCES ticket_types(id) ON DELETE CASCADE,

    quantity INT NOT NULL CHECK (quantity > 0),

    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),

    UNIQUE (event_day_id, ticket_type_id)
);
```

## 3.4 Ticket

```sql
CREATE TABLE tickets (
    id UUID PRIMARY KEY,

    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    event_day_id UUID NOT NULL REFERENCES event_days(id) ON DELETE CASCADE,
    ticket_type_id UUID NOT NULL REFERENCES ticket_types(id),

    ticket_index INT NOT NULL,
    seat_label TEXT,
    seat_metadata JSONB,

    -- Ownership: NULL = pool (unallocated), NOT NULL = held by ticket_holder
    owner_holder_id UUID REFERENCES ticket_holders(id) ON DELETE SET NULL,

    status TEXT NOT NULL DEFAULT 'active', -- active / cancelled / used

    -- Generic lock: always uses lock_reference_type='order' and lock_reference_id=order_id
    -- (every allocation is created via an order, even free transfers create $0 orders)
    lock_reference_type TEXT,
    lock_reference_id UUID,
    lock_expires_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),

    UNIQUE (event_day_id, ticket_index)
);
```

---

# 4. Movement and Money

## Design Principle

> A ticket can move many times, but can only belong to one holder at any moment.

**Allocation is the only mechanism for changing ticket ownership.**

```
Ticket       → ownership (static asset)
Allocation   → movement  (event log / trigger)
Order        → money    (always created, even for $0 transfers)
```

### Unified Flow

All allocation flows follow the same pattern:

```
1. Order created (type=PURCHASE or TRANSFER, final_amount=$0 for free transfers)
2. Tickets LOCKED (lock_reference_type='order', lock_reference_id=order_id)
3. [For paid flows: payment happens here]
4. Allocation created (status: pending → processing → completed)
5. Ticket owner_holder_id updated
6. allocation_edges updated (pre-aggregated counts)
7. Allocation status → completed
8. Lock cleared
```

---

## 4.1 Allocation

Tracks ticket movement between holders. Append-only event log.

```sql
CREATE TABLE allocations (
    id UUID PRIMARY KEY,

    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,

    -- Movement endpoints: from_holder_id=NULL means pool
    from_holder_id UUID REFERENCES ticket_holders(id) ON DELETE SET NULL,  -- NULL = pool
    to_holder_id   UUID NOT NULL REFERENCES ticket_holders(id),

    -- Every allocation is created via an order
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE RESTRICT,

    -- Status machine: pending → processing → completed / failed
    status TEXT NOT NULL DEFAULT 'pending', -- pending / processing / completed / failed
    failure_reason TEXT,

    ticket_count INT NOT NULL DEFAULT 0,  -- denormalized: avoids COUNT join
    metadata JSONB NOT NULL DEFAULT '{}', -- audit trail, source info

    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

**Design Notes:**
- `source_type` field removed — source is derived from `from_holder_id`:
  - `from_holder_id IS NULL` → POOL (organizer's initial distribution)
  - `from_holder_id IS NOT NULL` → TRANSFER (user-to-user)
- `order_id` is non-nullable — every allocation is created via an order
- `status` uses `processing` state for async flows (payment required)
- `ticket_count` denormalized to avoid COUNT(*) joins on every query
- `metadata` JSONB for audit trail (source app, notes, etc.)

---

## 4.2 AllocationTicket

Junction table linking allocations to tickets.

```sql
CREATE TABLE allocation_tickets (
    allocation_id UUID NOT NULL REFERENCES allocations(id) ON DELETE CASCADE,
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,

    PRIMARY KEY (allocation_id, ticket_id)
);
```

---

## 4.3 AllocationEdges

Pre-aggregated counts for fast distribution tree queries. Updated atomically inside the same transaction as allocation creation.

```sql
CREATE TABLE allocation_edges (
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    from_holder_id UUID REFERENCES ticket_holders(id) ON DELETE CASCADE,  -- NULL for pool edges
    to_holder_id UUID NOT NULL REFERENCES ticket_holders(id),

    ticket_count INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT now(),

    PRIMARY KEY (event_id, from_holder_id, to_holder_id)
);
```

**Why pre-aggregated?**
- Querying distribution tree without this requires `GROUP BY` + `JOIN` on potentially 50k+ tickets
- With edges: O(1) lookup per edge, 2 queries total (edges + batch-fetch holders)
- Updated inside transaction via `ON CONFLICT DO UPDATE` — atomic upsert

---

## 4.4 Order

```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY,

    event_id UUID NOT NULL REFERENCES events(id),

    -- Every ticket movement creates an order
    type TEXT NOT NULL, -- PURCHASE / TRANSFER
    user_id UUID NOT NULL REFERENCES users(id),

    subtotal_amount NUMERIC NOT NULL,
    discount_amount NUMERIC NOT NULL DEFAULT 0,
    final_amount NUMERIC NOT NULL,

    status TEXT NOT NULL, -- pending / paid / failed / expired

    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

**Order Types:**
- `PURCHASE` — paid ticket buy (online)
- `TRANSFER` — free allocation (B2B, U2U gift). `final_amount = 0`, `status = paid` instantly.

---

## 4.5 Coupon

```sql
CREATE TABLE coupons (
    id UUID PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,

    type TEXT NOT NULL, -- FLAT / PERCENTAGE
    value NUMERIC NOT NULL,
    max_discount NUMERIC,

    min_order_amount NUMERIC NOT NULL DEFAULT 0,

    usage_limit INT NOT NULL,
    per_user_limit INT NOT NULL DEFAULT 1,
    used_count INT NOT NULL DEFAULT 0,

    valid_from TIMESTAMP NOT NULL,
    valid_until TIMESTAMP NOT NULL,

    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

## 4.6 OrderCoupon

```sql
CREATE TABLE order_coupons (
    order_id UUID PRIMARY KEY REFERENCES orders(id) ON DELETE CASCADE,
    coupon_id UUID NOT NULL REFERENCES coupons(id),
    discount_applied NUMERIC NOT NULL DEFAULT 0
);
```

---

# 5. Scanning and Recovery

## 5.1 ScanLog

```sql
CREATE TABLE scan_logs (
    id BIGSERIAL PRIMARY KEY,

    event_day_id UUID NOT NULL REFERENCES event_days(id) ON DELETE CASCADE,
    ticket_index INT NOT NULL,

    scanned_at TIMESTAMP DEFAULT now(),

    UNIQUE (event_day_id, ticket_index)
);
```

## 5.2 EventDayBitmapSnapshot

```sql
CREATE TABLE event_day_bitmap_snapshots (
    event_day_id UUID PRIMARY KEY REFERENCES event_days(id) ON DELETE CASCADE,

    bitmap_data BYTEA NOT NULL,
    updated_at TIMESTAMP DEFAULT now()
);
```

---

# 6. Key Relationships

- `users` owns many `organizer_pages`
- `organizer_pages` owns many `events`
- `events` owns many `event_days`
- `events` owns many `ticket_types`
- `events` owns many `event_media_assets`
- `events` owns many `event_faqs`
- `events` can be either `open` or `ticketed`
- `event_days` owns many `day_ticket_allocations`
- `ticket_types` are allocated across event days through `day_ticket_allocations`
- `event_days` own many `tickets`
- `ticket_holders` are separate from `users` — holders may exist without accounts
- `tickets` belong to one `ticket_holder` when allocated (or NULL = pool)
- `allocations` track movement between holders — append-only event log
- `allocation_edges` pre-aggregate counts for fast tree queries
- `orders` are created for every allocation (PURCHASE or TRANSFER type)
- `scan_logs` and `event_day_bitmap_snapshots` support real-time validation and recovery

---

# 7. Notes for Phase 0 and 1

For the draft-first event creation flow, the important phase 0 entities are:

- `users`
- `guests`
- `organizer_pages`
- `events`
- `event_media_assets`
- `event_faqs`

For phase 1, the important ticketing entities are:

- `ticket_holders`
- `event_days`
- `ticket_types`
- `day_ticket_allocations`
- `tickets`
- `allocations`
- `allocation_tickets`
- `allocation_edges`
- `orders`

Suggested backend rules for this version:

- draft creation only needs an organizer page
- draft events may keep core publish fields empty until the organizer fills them
- `open` events do not create ticket rows or allocations
- `ticketed` events use the full ticket flow
- scanning is controlled manually per `event_day`
- publish-time validation should be stricter than draft-time validation
- every allocation creates an order (even $0 transfers)
- all locks use `lock_reference_type='order'` and `lock_reference_id=order_id`
