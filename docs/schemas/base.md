# TicketShicket Base Schema (v5)

This document captures the current core schema direction for TicketShicket.

The key change in this version is the ownership model:

- `User` is the login identity
- `Guest` is the anonymous identity
- `OrganizerPage` is the public brand/container for events
- `Event` belongs to an `OrganizerPage`, not directly to a `User`

This structure supports:

- multiple organizer pages per user
- public and private organizer pages
- draft-first event creation
- S3-backed media and content blocks for the public event page
- the existing ticketing, allocation, ordering, and scanning model

---

# 1. Identity and Organizer Layer

```text
User
 ├── OrganizerPage
 └── created / updates Events

Guest

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

## 1.3 OrganizerPage

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

    title TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,

    event_type TEXT, -- concert / conference / meetup / workshop / custom
    status TEXT NOT NULL DEFAULT 'draft', -- draft / published / archived

    location_mode TEXT NOT NULL DEFAULT 'venue', -- venue / online / recorded / hybrid

    timezone TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,

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
    category TEXT NOT NULL, -- ONLINE / B2B / PUBLIC

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

    owner_user_id UUID REFERENCES users(id),

    status TEXT NOT NULL DEFAULT 'active', -- active / cancelled / used

    locked_by_order_id UUID,
    lock_expires_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),

    UNIQUE (event_day_id, ticket_index)
);
```

---

# 4. Movement and Money

## 4.1 Allocation

```sql
CREATE TABLE allocations (
    id UUID PRIMARY KEY,

    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,

    from_user_id UUID REFERENCES users(id),
    to_user_id UUID NOT NULL REFERENCES users(id),

    order_id UUID,

    source_type TEXT NOT NULL, -- POOL / USER
    status TEXT NOT NULL, -- pending / completed / failed

    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

## 4.2 AllocationTicket

```sql
CREATE TABLE allocation_tickets (
    allocation_id UUID REFERENCES allocations(id) ON DELETE CASCADE,
    ticket_id UUID REFERENCES tickets(id) ON DELETE CASCADE,

    PRIMARY KEY (allocation_id, ticket_id)
);
```

## 4.3 Order

```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY,

    event_id UUID NOT NULL REFERENCES events(id),

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

## 4.4 Coupon

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

## 4.5 OrderCoupon

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
- `event_days` owns many `day_ticket_allocations`
- `ticket_types` are allocated across event days through `day_ticket_allocations`
- `event_days` own many `tickets`
- `tickets` belong to one `user` when assigned
- `allocations` track ticket movement between users
- `orders` record payment state, not ownership
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

- `event_days`
- `ticket_types`
- `day_ticket_allocations`
- `tickets`

The rest of the schema supports ownership movement, payment, and scanning once the core event setup flow is stable.
