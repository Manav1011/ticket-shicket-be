* Event
* TicketType
* Ticket
* Allocation (unified movement layer)
* Order (payment layer)

This is the version you can **actually build on** 🚀

---

# 🧠 FINAL ARCHITECTURE (Mental Model)

```text
Event
  ↓
TicketType (defines rules)
  ↓
Ticket (atomic ownership)

Allocation (moves tickets)
Order (handles payment, optional)
```

---

# 🏗️ 1. 🎤 Event

```text
Event
- id (PK)
- title
- description
- location
- start_time
- end_time

- distribution_mode (DIRECT / SPLIT / HYBRID)
```

---

# 🏷️ 2. TicketType (Blueprint)

```text
TicketType
- id (PK)
- event_id (FK → Event.id)

- name (VIP, Early Bird, General)
- category (ONLINE / B2B)   ✅

- price
- total_quantity

- created_at
```

---

# 🎟️ 3. Ticket (Atomic Unit)

```text
Ticket
- id (PK)
- ticket_type_id (FK → TicketType.id) ✅

- owner_user_id (FK)
- status (active / used / cancelled)

-- concurrency control
- locked_by_order_id (nullable FK → Order.id)
- lock_expires_at (timestamp)
```

---

# 🔄 4. Allocation (🔥 Core Unified Layer)

```text
Allocation
- id (PK)

- event_id (FK → Event.id)

- from_user_id (nullable → NULL means POOL/Organizer)
- to_user_id (FK)

- order_id (nullable FK → Order.id)

- source_type (POOL / USER)  -- where tickets come from

- status (pending / completed / failed)

- created_at
```

---

# 🔗 5. AllocationTicket (Mapping)

```text
AllocationTicket
- allocation_id (FK → Allocation.id)
- ticket_id (FK → Ticket.id)

PRIMARY KEY (allocation_id, ticket_id)
```

---

# 💳 6. Order (Payment Layer)

```text
Order
- id (PK)

- event_id (FK → Event.id)

- type (PURCHASE / TRANSFER)
- user_id (who is paying)

- total_amount
- status (pending / paid / failed)

- created_at
```

---

# 🧠 RELATIONSHIP OVERVIEW

```text
Event
  ├── TicketType
  │     └── Ticket
  │
  ├── Order
  │
  └── Allocation
        └── AllocationTicket → Ticket
```

---

# 🔄 HOW EVERYTHING WORKS (REAL FLOWS)

---

## 🟢 1. Online Purchase

```text
User buys 2 tickets
```

```text
Order (PURCHASE)
   ↓
Allocation (POOL → User)
   ↓
AllocationTicket → [T1, T2]
   ↓
Ticket.owner = User
```

---

## 🔵 2. B2B Distribution

```text
Organizer gives 50 tickets to A
```

```text
Allocation (POOL → A)
(no order)
```

---

## 🟣 3. Paid Transfer

```text
A → B (B pays)
```

```text
Order (TRANSFER)
   ↓
Allocation (A → B)
   ↓
Tickets moved
```

---

## 🟡 4. Offline Transfer

```text
A → B (cash outside)
```

```text
Allocation (A → B)
(no order)
```

---

# 🔐 CRITICAL RULES

---

## ✅ 1. TicketType is Mandatory

```text
Ticket.ticket_type_id → NOT NULL
```

---

## ✅ 2. Allocation Drives Ownership

👉 Ownership ONLY changes via allocation

---

## ✅ 3. Order is Optional

| Case             | Order |
| ---------------- | ----- |
| Purchase         | ✅     |
| Paid transfer    | ✅     |
| Offline transfer | ❌     |

---

## ✅ 4. Locking Before Payment

```sql
UPDATE tickets
SET locked_by_order_id = ?, lock_expires_at = now() + interval '5 min'
WHERE id IN (...);
```

---

## ✅ 5. Ownership Update (inside TX)

```sql
UPDATE tickets
SET owner_user_id = ?
WHERE id IN (...)
AND owner_user_id = ?;
```

---

# ⚡ INDEXES (IMPORTANT FOR PERFORMANCE)

---

## Ticket

```sql
INDEX (owner_user_id)
INDEX (ticket_type_id)
INDEX (locked_by_order_id)
```

---

## Allocation

```sql
INDEX (from_user_id)
INDEX (to_user_id)
INDEX (event_id)
```

---

## Order

```sql
INDEX (event_id)
INDEX (user_id)
INDEX (status)
```

---