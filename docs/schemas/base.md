Perfect — now we’ll lock this as your **final production schema (v4)** including:

* ✅ Multi-day events
* ✅ Allocation system
* ✅ Redis bitmap + DB persistence
* ✅ Scan logs
* ✅ Optional bitmap snapshots

This is something you can **directly implement with SQLC + pgx** 🚀

---

# 🧠 FINAL ARCHITECTURE (v4)

```text
Event
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

---

# 🏗️ 1. 🎤 Event

```sql
CREATE TABLE events (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    location TEXT,

    start_date DATE NOT NULL,
    end_date DATE NOT NULL,

    distribution_mode TEXT NOT NULL, -- DIRECT / SPLIT / HYBRID

    created_at TIMESTAMP DEFAULT now()
);
```

---

# 📅 2. EventDay

```sql
CREATE TABLE event_days (
    id UUID PRIMARY KEY,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,

    day_index INT NOT NULL,
    date DATE NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,

    created_at TIMESTAMP DEFAULT now(),

    UNIQUE (event_id, day_index)
);
```

---

# 🏷️ 3. TicketType

```sql
CREATE TABLE ticket_types (
    id UUID PRIMARY KEY,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,

    name TEXT NOT NULL,
    category TEXT NOT NULL, -- ONLINE / B2B

    price NUMERIC NOT NULL,

    created_at TIMESTAMP DEFAULT now()
);
```

---

# 🔗 4. DayTicketAllocation

```sql
CREATE TABLE day_ticket_allocations (
    id UUID PRIMARY KEY,

    event_day_id UUID NOT NULL REFERENCES event_days(id) ON DELETE CASCADE,
    ticket_type_id UUID NOT NULL REFERENCES ticket_types(id) ON DELETE CASCADE,

    quantity INT NOT NULL CHECK (quantity > 0),

    created_at TIMESTAMP DEFAULT now(),

    UNIQUE (event_day_id, ticket_type_id)
);
```

---

# 🎟️ 5. Ticket

```sql
CREATE TABLE tickets (
    id UUID PRIMARY KEY,

    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    event_day_id UUID NOT NULL REFERENCES event_days(id) ON DELETE CASCADE,
    ticket_type_id UUID NOT NULL REFERENCES ticket_types(id),

    ticket_index INT NOT NULL,

    owner_user_id UUID,

    status TEXT NOT NULL DEFAULT 'active', -- active / cancelled

    locked_by_order_id UUID,
    lock_expires_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT now(),

    UNIQUE (event_day_id, ticket_index)
);
```

---

# 🔄 6. Allocation

```sql
CREATE TABLE allocations (
    id UUID PRIMARY KEY,

    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,

    from_user_id UUID,
    to_user_id UUID NOT NULL,

    order_id UUID,

    source_type TEXT NOT NULL, -- POOL / USER
    status TEXT NOT NULL,      -- pending / completed / failed

    created_at TIMESTAMP DEFAULT now()
);
```

---

# 🔗 7. AllocationTicket

```sql
CREATE TABLE allocation_tickets (
    allocation_id UUID REFERENCES allocations(id) ON DELETE CASCADE,
    ticket_id UUID REFERENCES tickets(id) ON DELETE CASCADE,

    PRIMARY KEY (allocation_id, ticket_id)
);
```

---

# 💳 8. Order

```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY,

    event_id UUID NOT NULL REFERENCES events(id),

    type TEXT NOT NULL, -- PURCHASE / TRANSFER
    user_id UUID NOT NULL,

    total_amount NUMERIC NOT NULL,
    status TEXT NOT NULL, -- pending / paid / failed

    created_at TIMESTAMP DEFAULT now()
);
```

---

# 📊 9. ScanLog (🔥 CRITICAL)

```sql
CREATE TABLE scan_logs (
    id BIGSERIAL PRIMARY KEY,

    event_day_id UUID NOT NULL REFERENCES event_days(id) ON DELETE CASCADE,
    ticket_index INT NOT NULL,

    scanned_at TIMESTAMP DEFAULT now(),

    UNIQUE (event_day_id, ticket_index)
);
```

---

👉 Guarantees:

* No duplicate successful scans
* Perfect bitmap reconstruction

---

# 💾 10. Bitmap Snapshot (Optional but Included)

```sql
CREATE TABLE event_day_bitmap_snapshots (
    event_day_id UUID PRIMARY KEY REFERENCES event_days(id) ON DELETE CASCADE,

    bitmap_data BYTEA NOT NULL,
    updated_at TIMESTAMP DEFAULT now()
);
```

---

👉 Used for:

* Faster recovery
* Not updated per scan

---

# ⚡ INDEXES (IMPORTANT)

---

## Tickets

```sql
CREATE INDEX idx_tickets_owner ON tickets(owner_user_id);
CREATE INDEX idx_tickets_event ON tickets(event_id);
CREATE INDEX idx_tickets_event_day ON tickets(event_day_id);
CREATE INDEX idx_tickets_type ON tickets(ticket_type_id);
```

---

## Scan Logs

```sql
CREATE INDEX idx_scan_logs_event_day ON scan_logs(event_day_id);
```

---

## Allocations

```sql
CREATE INDEX idx_allocations_from_user ON allocations(from_user_id);
CREATE INDEX idx_allocations_to_user ON allocations(to_user_id);
CREATE INDEX idx_allocations_event ON allocations(event_id);
```

---

## Orders

```sql
CREATE INDEX idx_orders_event ON orders(event_id);
CREATE INDEX idx_orders_user ON orders(user_id);
```

---

# 🔥 REDIS STRUCTURE (FINAL)

```text
event_day:{event_day_id}:bitmap
```

---

# ⚡ FINAL FLOW SUMMARY

---

## 🎟 Ticket Creation

```text
DayTicketAllocation → generate tickets
```

---

## 🎯 Scan

```text
QR → decode
   ↓
Redis bitmap (SETBIT)
   ↓
Publish event
   ↓
Worker → insert scan_logs
```

---

## 🔁 Recovery

```text
scan_logs → rebuild bitmap
```

---

## ⚡ Optional Fast Recovery

```text
snapshot → replay recent logs
```

---

# 🧠 FINAL MENTAL MODEL

```text
DB → ownership + history
Redis → real-time state
NATS → async bridge
```

---

Just tell me 👍
