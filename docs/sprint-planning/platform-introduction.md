# TicketShicket — Platform Introduction

## Overview

TicketShicket is a scalable event ticketing and real-time entry management platform designed to handle everything from ticket sales to high-speed on-ground validation at large events. It supports both online ticket sales and offline/B2B distribution, ensuring fraud-proof, ultra-fast QR-based entry scanning at event venues.

## Problems Solved
- Slow entry during peak crowds
- Duplicate or fake ticket usage
- Poor handling of offline or reseller-based distribution
- Lack of real-time control during events

## Key Solutions
- Strong backend ownership tracking
- Real-time in-memory validation (Redis)
- Flexible ticket distribution

## Core Modules
1. **Event Management**: Create/manage events with multiple days, timings, locations, and distribution strategies (direct, reseller, hybrid).
2. **Ticket Types**: Define categories (VIP, General, Early Bird) with pricing, quantity, and distribution category (online/B2B).
3. **Ticket Ownership System**: Every ticket is an atomic unit with a tracked owner. Ownership changes only via controlled allocations.
4. **Allocation System**: Handles purchases, organizer distribution, reseller transfers, and offline movement. All ownership changes are tracked.
5. **Order & Payment System**: Manages purchases, paid transfers, payment tracking, ticket locking, and failure handling to prevent overselling.
6. **Coupon & Discount System**: Supports flat/percentage discounts, usage limits, and per-user restrictions. Coupons affect pricing only.
7. **Real-Time QR Scanning**: Uses Redis for instant validation, ensuring sub-millisecond scan response, no duplicate entry, and high concurrency.
8. **Bitmap-Based Entry Validation**: Each ticket maps to a bitmap index for atomic, ultra-fast entry checks—ideal for large crowds.
9. **Scan Logging & Recovery**: All scans are logged asynchronously. Redis state can be rebuilt from logs for fault tolerance.

## End-to-End Flow
- **Ticket Purchase**: User selects tickets → Order created → Tickets locked → Payment → Ownership transferred
- **Ticket Transfer**: User-to-user, fully tracked
- **Event Entry**: QR scanned → Checked in Redis → Marked as used → Logged in DB

## Design Philosophy
- Separation of responsibilities: DB for ownership/history, Redis for real-time, messaging for async processing
- Controlled ownership: All movements tracked via allocations
- Speed during events: No heavy DB queries during scanning
- Fault tolerance: Recoverable from crashes, no scan data loss

## What Makes TicketShicket Strong
- Ultra-fast QR validation
- No double entry or fraud
- Supports online & offline flows
- Clean, modular, scalable architecture

---

# Product Modules Overview

TicketShicket is designed to handle event ticketing, distribution, selling, and real-time entry validation in a scalable and flexible way.

At a high level, everything revolves around:

**Event → Tickets → Movement → Payment → Entry**

## Module Definitions

1. **Event Management Module**
	- Purpose: Foundation of the system — everything starts with an event.
	- Handles: Creating events (concerts, festivals, etc.), event details (title, description, location, date & time), event configuration (ticket distribution: direct/reseller/hybrid).
	- Think of this as the container for everything else.

2. **Event Day Management Module**
	- Purpose: Handles multi-day events cleanly.
	- Handles: Splitting an event into multiple days, each with different timings and ticket allocations. Enables day-specific entry validation and better control over large events.

3. **Ticket Type Module**
	- Purpose: Defines what kinds of tickets exist.
	- Handles: Ticket categories (VIP, General, Early Bird), pricing, classification (online sale, B2B/reseller allocation).
	- This is the blueprint of tickets (not actual tickets yet).

4. **Ticket Inventory Module**
	- Purpose: Manages actual tickets (real units).
	- Handles: Creating tickets for each event/day, assigning ownership, ticket states (active, used, cancelled).
	- This is the core asset layer of your system.

5. **Allocation (Ticket Movement) Module**
	- Purpose: Handles movement of tickets between users.
	- Handles: Organizer → User (purchase), Organizer → Reseller (bulk), User → User (transfer/resale).
	- Key idea: Tickets never magically change owner — they always move via allocation.

6. **Allocation Mapping Module**
	- Purpose: Links which tickets were moved in a transaction.
	- Handles: Tracks which tickets belong to which allocation. Helps in auditing, debugging, and history tracking.
	- Think of it as line items of ticket transfers.

7. **Order & Payment Module**
	- Purpose: Handles the money side of the system.
	- Handles: Ticket purchases, paid transfers, payment status (pending, paid, failed).
	- Important: Orders handle money, not ticket ownership directly.

8. **Coupon & Discount Module**
	- Purpose: Applies discount logic to orders.
	- Handles: Coupon codes (flat/% discount), usage limits, per-user restrictions, expiry dates.
	- Key idea: Coupons affect price, not tickets.

9. **Ticket Locking Module**
	- Purpose: Prevents overselling during checkout.
	- Handles: Temporarily reserving tickets, expiring locks if payment not completed, ensuring no double booking.
	- Critical for high-concurrency purchases.

10. **QR & Scan Module**
	 - Purpose: Handles entry validation at event venue.
	 - Handles: QR code generation for tickets, scanning tickets at entry, validations (is ticket valid, already used, allowed for this day?).
	 - This is the real-time entry system.

11. **Real-Time Validation Module**
	 - Purpose: Ensures fast and reliable scanning.
	 - Handles: Instant ticket validation, prevents duplicate entry, handles high load (multiple scanners).
	 - Key idea: System must respond in milliseconds during entry.

12. **Scan Logs & Audit Module**
	 - Purpose: Maintains history of all scans.
	 - Handles: Logs every successful scan, prevents duplicate entries, enables analytics, debugging, and recovery.
	 - This is your ground truth after the event.

13. **Recovery & Reliability Module**
	 - Purpose: Ensures system can recover from failures.
	 - Handles: Rebuilding scan state if system crashes, ensuring no data loss, maintaining consistency.
	 - Critical for production-grade reliability.

## Final System View (Non-Technical)

Event
 ├── Days
 ├── Ticket Types
 ├── Tickets
 │
 ├── Orders (money)
 │     └── Coupons
 │
 ├── Allocations (movement)
 │     └── Ticket mapping
 │
 └── Scanning System
		 ├── QR validation
		 ├── Real-time checks
		 └── Scan logs

---
**One-Line Understanding:**

TicketShicket is a system that manages tickets as assets, allocations as movement, orders as money, and scanning as real-time validation.
