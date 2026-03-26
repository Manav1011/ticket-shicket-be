Perfect — now let’s **merge everything you’ve designed so far** (multi-day + bitmap + allocation system) into one **clean, final production-ready data model**.

You already had a strong base. We’ll **extend it properly**, not break it.

---

# 🧠 FINAL EVOLVED ARCHITECTURE (v2 🚀)

```text
Event
 └── EventDay
      └── DayTicketAllocation

TicketType
 └── Ticket

Allocation
AllocationTicket

Order
```

👉 This keeps your original design intact + adds **multi-day support cleanly**

---

# 🏗️ 1. 🎤 Event

```text
Event
- id (PK)
- title
- description
- location

- start_date
- end_date

- distribution_mode (DIRECT / SPLIT / HYBRID)

- created_at
```

---

# 📅 2. EventDay (NEW 🔥)

```text
EventDay
- id (PK)
- event_id (FK → Event.id)

- day_index (INT)   ✅ (1,2,3…)
- date
- start_time
- end_time

- created_at
```

---

👉 This is the foundation of your **multi-day UX**

---

# 🏷️ 3. TicketType (Global Blueprint)

```text
TicketType
- id (PK)
- event_id (FK → Event.id)

- name (VIP, General, Early Bird)
- category (ONLINE / B2B)

- price

- created_at
```

---

👉 No more `total_quantity` here ❗
👉 Quantity now lives per **day allocation**

---

# 🔗 4. DayTicketAllocation (🔥 CRITICAL NEW LAYER)

```text
DayTicketAllocation
- id (PK)

- event_day_id (FK → EventDay.id)
- ticket_type_id (FK → TicketType.id)

- quantity

UNIQUE (event_day_id, ticket_type_id)
```

---

👉 This connects:

```text
Day ↔ TicketType ↔ Quantity
```

---

# 🎟️ 5. Ticket (Atomic Unit, Updated)

```text
Ticket
- id (PK)

- ticket_type_id (FK → TicketType.id)
- event_day_id (FK → EventDay.id)   ✅ NEW

- ticket_index (INT)                ✅ REQUIRED (for bitmap)

- owner_user_id (FK)

- status (active / used / cancelled)

-- locking
- locked_by_order_id (nullable FK → Order.id)
- lock_expires_at
```

---

👉 KEY CHANGE:

```text
Ticket is now DAY-SPECIFIC
```

---

# 🔄 6. Allocation (Same Core Idea)

```text
Allocation
- id (PK)

- event_id (FK → Event.id)

- from_user_id (nullable)
- to_user_id (FK)

- order_id (nullable FK → Order.id)

- source_type (POOL / USER)

- status (pending / completed / failed)

- created_at
```

---

# 🔗 7. AllocationTicket (Same)

```text
AllocationTicket
- allocation_id (FK)
- ticket_id (FK)

PRIMARY KEY (allocation_id, ticket_id)
```

---

# 💳 8. Order (Same)

```text
Order
- id (PK)

- event_id (FK)

- type (PURCHASE / TRANSFER)

- user_id

- total_amount
- status (pending / paid / failed)

- created_at
```

---

# 🧠 RELATIONSHIP (UPDATED)

```text
Event
 ├── EventDay
 │     └── DayTicketAllocation
 │
 ├── TicketType
 │     └── Ticket (linked to EventDay)
 │
 ├── Order
 │
 └── Allocation
       └── AllocationTicket → Ticket
```

---

# ⚡ HOW SYSTEM WORKS NOW

---

## 🟢 Ticket Creation

```text
DayTicketAllocation (Day 1, VIP, 100)
   ↓
Generate 100 Tickets:
   → ticket_index: 0 → 99
   → event_day_id = Day 1
```

---

## 🔵 Scan Flow (SUPER SIMPLE NOW)

```text
QR → decode
   ↓
event_id + event_day_id + ticket_index
   ↓
Redis:
event:{event_id}:day:{day_index}:bitmap
   ↓
SETBIT check
   ↓
Allow / Reject
```

---

👉 ❌ No need for:

* days_mask
* DB validation

---

## 🟣 Allocation Flow (UNCHANGED)

```text
Allocation → moves tickets
```

---

# 🔥 REDIS STRUCTURE (FINAL)

```text
event:{event_id}:day:{day_index}:bitmap
```

---

👉 Each ticket already belongs to a day
👉 So no ambiguity

---

# 🧠 WHY THIS MODEL IS STRONG

---

## ✅ 1. Clean separation

| Layer      | Purpose   |
| ---------- | --------- |
| EventDay   | time      |
| TicketType | category  |
| Allocation | ownership |
| Ticket     | atomic    |

---

## ✅ 2. Perfect for scanning

* No joins
* No DB calls
* Pure Redis

---

## ✅ 3. Flexible for business

* Different quantities per day
* B2B + online unified
* Transfer system intact

---

## ✅ 4. Scales easily

* Multi-day
* Multi-event
* High concurrency

---

# ⚠️ ONE IMPORTANT INDEX

---

## Ticket

```sql
UNIQUE (event_day_id, ticket_index)
```

👉 Required for bitmap correctness

---

# 🧠 FINAL MENTAL MODEL

```text
Event → multiple days
Day → has ticket allocations
Allocation → creates tickets
Ticket → belongs to one day
Scan → checks bitmap per day
```

---

# 🚀 FINAL ANSWER

> “What is our final data model?”

👉 Your original system + these upgrades:

* ✅ Add **EventDay**
* ✅ Add **DayTicketAllocation**
* ✅ Make **Ticket day-specific**
* ❌ Remove TicketTypeDays
* ❌ Remove global quantity from TicketType

---
