# TicketShicket — Phase Planning & Build Order

This document outlines the recommended module implementation order for TicketShicket, with rationale and prerequisites for each phase. Following this plan ensures a robust, scalable, and bug-resistant foundation.

---


## 🚀 Phase 0: User & Guest Management (Non-negotiable base)

### 1. User Management Module
**Why first?**
- All other modules depend on a robust user system for authentication, authorization, and ownership.

**Prerequisites:**
- Project setup (FastAPI / Go / DB)

### 2. Guest Management Module
**Why now?**
- Enables guest flows, invitations, and non-registered user participation.

**Prerequisites:**
- User module done

---

## 🧱 Phase 1: Event & Event Day Foundation

### 3. Event Management Module
**Why now?**
- Everything depends on Event.

**Prerequisites:**
- User system (even minimal: user_id)
- Auth (basic)

### 4. Event Day Module
**Why now?**
- Multi-day affects ticket creation, scanning, validation.

**Prerequisites:**
- Event module done

---


## 🧱 Phase 2: Core Ticket System (MOST IMPORTANT)

👉 If this is wrong, everything breaks later

### 5. Ticket Type Module
**Why now?**
- Defines structure before creating tickets

**Prerequisites:**
- Event
- Event Day

### 6. Ticket Inventory Module
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


## 🔄 Phase 3: Ownership & Movement

### 7. Allocation Module (🔥 CORE LOGIC)
**Why before orders?**
- Ownership = Allocation (not Order)

**Prerequisites:**
- Ticket module stable

### 8. Allocation Mapping Module
**Why now?**
- Needed to track ticket-level movements

**Prerequisites:**
- Allocation module

---


## 💰 Phase 4: Payment Layer

### 9. Order Module
**Why after allocation?**
- Order triggers allocation, not vice versa

**Prerequisites:**
- Allocation logic clear
- Ticket locking concept understood

### 10. Ticket Locking Module
**Why now?**
- Needed before integrating payments

**Prerequisites:**
- Ticket module
- Order module

### 11. Coupon Module (Optional but clean to add here)
**Why here?**
- Extends order layer only

**Prerequisites:**
- Order module

---


## 📲 Phase 5: Basic End-to-End Flow

At this point you should support:
- User → Buy Ticket → Payment → Ownership updated

---


## ⚡ Phase 6: Scanning System (Real-time Layer)

### 12. QR & Scan Module
**Why late?**
- Depends on tickets, ownership, event days

**Prerequisites:**
- Ticket system complete
- EventDay

### 13. Real-Time Validation Module (Redis layer)
**Why now?**
- Optimization layer — not core logic

**Prerequisites:**
- Scan logic defined
- Ticket indexing stable

---


## 📊 Phase 7: Persistence & Reliability

### 14. Scan Logs Module
**Why after scanning?**
- To persist real-time decisions

**Prerequisites:**
- Scan system working

### 15. Recovery Module
**Why last?**
- Only needed after system is running

**Prerequisites:**
- Scan logs
- Redis-based validation

---

## 🧠 FINAL BUILD ORDER (Sprint Plan)


**Phase 0:**
1. User
2. Guest

**Phase 1:**
3. Event
4. EventDay

**Phase 2:**
5. TicketType
6. Ticket

**Phase 3:**
7. Allocation
8. AllocationTicket

**Phase 4:**
9. Order
10. Ticket Locking
11. Coupon

**Phase 5:**
→ End-to-end purchase flow

**Phase 6:**
12. QR Scan
13. Real-time validation (Redis)

**Phase 7:**
14. Scan Logs
15. Recovery

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
