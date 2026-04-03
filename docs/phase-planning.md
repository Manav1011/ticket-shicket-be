# TicketShicket — Phase Planning & Build Order

This document outlines the recommended module implementation order for TicketShicket, with rationale and prerequisites for each phase. Following this plan ensures a robust, scalable, and bug-resistant foundation.

---

## 🚀 Phase 0: Foundation (Non-negotiable base)

### 1. Event Management Module
**Why first?**
- Everything depends on Event.

**Prerequisites:**
- Basic user system (even minimal: user_id)
- Project setup (FastAPI / Go / DB)
- Auth (basic)

### 2. Event Day Module
**Why early?**
- Multi-day affects ticket creation, scanning, validation.

**Prerequisites:**
- Event module done

---

## 🧱 Phase 1: Core Ticket System (MOST IMPORTANT)

👉 If this is wrong, everything breaks later

### 3. Ticket Type Module
**Why now?**
- Defines structure before creating tickets

**Prerequisites:**
- Event
- Event Day

### 4. Ticket Inventory Module
**Why critical?**
- This is your core asset layer

**What to ensure here:**
- Ticket creation
- Ownership
- Status
- Indexing logic (very important)

**Prerequisites:**
- TicketType
- EventDay

---

## 🔄 Phase 2: Ownership & Movement

### 5. Allocation Module (🔥 CORE LOGIC)
**Why before orders?**
- Ownership = Allocation (not Order)

**Prerequisites:**
- Ticket module stable

### 6. Allocation Mapping Module
**Why now?**
- Needed to track ticket-level movements

**Prerequisites:**
- Allocation module

---

## 💰 Phase 3: Payment Layer

### 7. Order Module
**Why after allocation?**
- Order triggers allocation, not vice versa

**Prerequisites:**
- Allocation logic clear
- Ticket locking concept understood

### 8. Ticket Locking Module
**Why now?**
- Needed before integrating payments

**Prerequisites:**
- Ticket module
- Order module

### 9. Coupon Module (Optional but clean to add here)
**Why here?**
- Extends order layer only

**Prerequisites:**
- Order module

---

## 📲 Phase 4: Basic End-to-End Flow

At this point you should support:
- User → Buy Ticket → Payment → Ownership updated

---

## ⚡ Phase 5: Scanning System (Real-time Layer)

### 10. QR & Scan Module
**Why late?**
- Depends on tickets, ownership, event days

**Prerequisites:**
- Ticket system complete
- EventDay

### 11. Real-Time Validation Module (Redis layer)
**Why now?**
- Optimization layer — not core logic

**Prerequisites:**
- Scan logic defined
- Ticket indexing stable

---

## 📊 Phase 6: Persistence & Reliability

### 12. Scan Logs Module
**Why after scanning?**
- To persist real-time decisions

**Prerequisites:**
- Scan system working

### 13. Recovery Module
**Why last?**
- Only needed after system is running

**Prerequisites:**
- Scan logs
- Redis-based validation

---

## 🧠 FINAL BUILD ORDER (Sprint Plan)

**Phase 0:**
1. Event
2. EventDay

**Phase 1:**
3. TicketType
4. Ticket

**Phase 2:**
5. Allocation
6. AllocationTicket

**Phase 3:**
7. Order
8. Ticket Locking
9. Coupon

**Phase 4:**
→ End-to-end purchase flow

**Phase 5:**
10. QR Scan
11. Real-time validation (Redis)

**Phase 6:**
12. Scan Logs
13. Recovery

---

## 🔥 Key Strategic Insight

⚠️ **DO NOT START WITH:**
- ❌ Redis
- ❌ Scanning
- ❌ Payment gateway

✅ **ALWAYS START WITH:**
- Ticket ownership + allocation correctness

**Because:**
- Bugs here = money loss
- Everything else depends on it

---

## 🧠 How to Think While Building

At every step ask:
> Can I correctly answer: "Who owns this ticket right now?"

- If yes → move forward
- If no → fix before continuing
