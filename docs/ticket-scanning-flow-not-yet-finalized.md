---

# 🧠 🔥 Core Idea (Your System)

```text
ticket_index → maps to Redis bitmap
```

👉 This is the **heart of your scan system**

* DB → stores tickets + ownership
* Redis → real-time validation
* ScanLog → persistence + recovery

---

# 🏗️ 1. Pre-Event Setup (Before Scanning Starts)

---

## Step 1: Tickets already exist

From your system:

* `tickets.ticket_index` (unique per event_day)
* `next_ticket_index` defines total tickets

---

## Step 2: Organizer clicks **“Start Scanning”**

This triggers:

```text
event_day.scan_status = active
```

---

## Step 3: Initialize Redis bitmap

```text
key:
event_day:{event_day_id}:bitmap

size:
= next_ticket_index
```

---

## Step 4 (optional but important): Recovery replay

```text
scan_logs → rebuild bitmap
```

👉 Ensures consistency after restart

---

# ⚡ 2. QR Code Structure

Each ticket QR contains:

```json
{
  "event_day_id": "...",
  "ticket_index": 123
}
```

👉 That’s all you need for scan

---

# 🚀 3. REAL-TIME SCAN FLOW

---

## 🔹 Step 1: Scan QR

```text
→ extract event_day_id, ticket_index
```

---

## 🔹 Step 2: Validate scanning state

```text
event_day.scan_status == active ?
```

❌ If not → reject

---

## 🔹 Step 3: Check Redis bitmap (FAST PATH)

```text
GETBIT event_day:{id}:bitmap ticket_index
```

---

### Case 1: bit = 1

```text
→ Already scanned ❌
```

---

### Case 2: bit = 0

Proceed 👇

---

## 🔹 Step 4: Validate ticket (light check)

From cache or DB:

```text
- ticket exists
- status != cancelled
- belongs to this event_day
```

❌ If invalid → reject

---

## 🔹 Step 5: Atomic mark as used (CRITICAL)

```text
SETBIT event_day:{id}:bitmap ticket_index 1
```

👉 Ideally via Lua:

```text
if bit == 0:
   set → success
else:
   fail
```

---

## 🔹 Step 6: Async persistence

```text
Publish → NATS / queue
```

Worker:

```sql
INSERT INTO scan_logs (event_day_id, ticket_index)
```

---

# 🔁 4. Full Flow Summary

```text
Scan QR
  ↓
Check scan_status
  ↓
GETBIT
  ↓
(if 0)
  ↓
Validate ticket
  ↓
SETBIT (atomic)
  ↓
Async → scan_logs
```

---

# 🔒 Guarantees

---

## ✅ 1. No duplicate entry

```text
bitmap ensures:
only first scan succeeds
```

---

## ✅ 2. Ultra fast

```text
no DB hit in hot path
```

---

## ✅ 3. Safe concurrency

```text
atomic bit operation
```

---

# 🧠 5. Late Ticket Handling (Your advanced feature)

If tickets added after scan start:

---

## Two paths:

```text
IF index < bitmap_limit:
   → bitmap

ELSE:
   → Redis SET (late tickets)
```

---

## Keys:

```text
event_day:{id}:late_valid_tickets
event_day:{id}:late_used_tickets
```

---

# ⚠️ 6. Cancellation Handling

If:

```text
ticket.status = cancelled
```

Then:

```text
reject scan
```

👉 Even if bitmap says unused

---

# 🔁 7. Recovery Flow

If Redis crashes:

```text
scan_logs → rebuild bitmap
```

---

## Optional optimization:

```text
bitmap snapshot + replay delta logs
```

---

# 🔴 8. Pause / Resume

---

## Pause:

```text
scan_status = paused
```

👉 Reject all scans

---

## Resume:

```text
scan_status = active
```

👉 Continue using same bitmap

---

# 🧠 Final Mental Model

```text
ticket_index → position in bitmap

bitmap → real-time used state

scan_logs → permanent record

DB → ownership & validity
```

---

# 🚀 Final Answer

👉 Your scanning system works as:

* Redis bitmap for **real-time validation**
* DB for **truth + recovery**
* atomic operations for **no double entry**

---

# 🧠 One-line intuition

> Scan = flip a bit, and never flip it back.

---