# Session Conversation — April 13, 2026

**Topic:** Allocation & Movement Architecture Design
**Duration:** Single session
**Outcome:** Finalized v1.2 of Allocation & Movement Architecture

---

## Chronological Walkthrough

### 1. Starting Point — Base Schema Review

We had an existing schema in `base.md` and a phase planning document that outlined:
- Allocation model
- AllocationTicket junction
- Movement of tickets between users

The architecture already had the core idea:
> Ticket → ownership, Allocation → movement, Order → money

---

### 2. Reading the Previous Discussion (GPTDiscussions/AllocationAndMovement.md)

Before this session, there was a prior AI conversation that established:
- TicketHolder as identity layer (separate from User)
- Allocation = unified movement engine (not separate purchase/transfer/reseller systems)
- from_holder_id defines source (NULL = pool, NOT NULL = transfer)
- Tree is derived, not stored
- Locking mechanism with `locked_by_order_id`

---

### 3. Quick Graph Review

We looked at the project's graph report to understand the current state:
- 1060 nodes, 2854 edges, 72 communities
- God nodes: FileValidationError, EventService, EventModel
- The allocation/ticketing module was in Community 4 (PublicEventService, EventRepository)

---

### 4. Discussing the Prior Discussion

The user asked if we agreed with the prior discussion or had optimizations.

**First round of concerns I raised:**

1. **`source_type` naming confusion** — POOL/USER was misleading. Suggested removing it entirely and deriving from `from_holder_id`.

2. **Pending state for offline/B2B** — User clarified that B2B can also have payment, so pending state makes sense.

3. **Failed allocation reversal undefined** — What if `owner_user_id` is updated but allocation insert fails? Need rollback strategy.

4. **Tree query at scale** — GROUP BY + JOIN on 50k+ tickets would be slow. Suggested pre-aggregated `allocation_edges` table.

5. **Phone + email conflict** — User said only one contact allowed at v1 (simpler).

6. **`merged_into_holder_id` complexity** — Suggested hard delete for v1 instead.

---

### 5. User's Counter-Feedback

User responded with refinements:

- **Remove `source_type`** — Agreed. Derive from `from_holder_id`.
- **Single DB transaction** — All allocation steps in one transaction with rollback.
- **`allocation_edges` pre-aggregation** — ON CONFLICT DO UPDATE for atomic upsert.
- **Hard delete for v1** — Agreed.
- **Status flow** — `pending → processing → failed` with better state machine.

---

### 6. Created First Draft — AllocationAndMovement-Final.md

I wrote the first comprehensive document covering:
- Core philosophy
- All data models
- All allocation flows (purchase, B2B, user-to-user, refund)
- TicketHolder resolution
- Ticket travel history queries
- Locking & concurrency
- Status machine
- Edge cases
- API contracts
- Rollback procedures
- Performance considerations

---

### 7. First Review Feedback (from User)

User found 5 issues:

1. **Constraint vs merge conflict** — The CHECK constraint `(phone IS NOT NULL AND email IS NULL)` would be violated after merge when holder has both phone AND email.

2. **Edge rollback unsafe** — A separate `rollback_edge_update()` call after commit is dangerous (if transaction already rolled back, decrement causes inconsistency).

3. **N+1 tree query** — `get_allocation_tree` was fetching holder info inside a loop → 100 holders = 100 queries.

4. **Locking syntax** — `WHERE id IN :ticket_ids` is invalid in pgx/asyncpg.

5. **Missing index** — `idx_allocation_edges_event_id` needed for filtering.

**Improvements proposed:**
- `ticket_count INT` in allocations (denormalized)
- `metadata JSONB` for audit
- FIFO ticket selection strategy explicitly defined

---

### 8. Document Updated to v1.1

Applied all fixes:
- Removed DB CHECK constraint on phone/email
- Edge update only inside transaction (no separate rollback)
- Batch fetch all holders upfront (2 queries total)
- `= ANY(:array)` syntax for PostgreSQL
- Added `ticket_count` column
- Added `metadata` JSONB column
- Added `idx_allocation_edges_event_id`
- FIFO strategy documented
- Merge logic: `COALESCE(:phone, phone)` to preserve existing

---

### 9. Second Review Feedback (3 Final Improvements)

User proposed 3 more improvements:

1. **Missing ownership check during UPDATE** — If race condition occurs between lock and update, wrong owner could be overwritten.
   - Fix: `owner_holder_id IS NOT DISTINCT FROM :from_holder_id`

2. **Edge decrement on refund breaks append-only** — Manual decrement breaks the consistency model.
   - Fix: Treat refund as new reverse allocation `(current_owner → NULL)`, never decrement.

3. **Status transition race** — No check if `UPDATE ... WHERE status = 'pending'` actually affected a row.
   - Fix: Use `RETURNING id` and check `rows_affected > 0`.

---

### 10. Document Updated to v1.2 (Final)

Applied all 3 final fixes:
- Ownership check on both lock and update queries
- Refund = new reverse allocation edge, no manual decrement
- Status transition checks `rows_affected` via `RETURNING id`

---

## Final Architecture Summary

### Core Principle
> A ticket can move many times, but can only belong to one holder at any moment.

### Key Design Decisions

| Decision | Choice |
|----------|--------|
| Identity layer | `ticket_holders` (separate from User) |
| Contact | Phone OR email (not both at v1) |
| Movement source | Derived from `from_holder_id` (NULL = pool) |
| Allocations | Single atomic transaction |
| Tree | Derived from `allocation_edges` (pre-aggregated) |
| Ticket selection | FIFO (ORDER BY ticket_index ASC) |
| Ownership safety | `IS NOT DISTINCT FROM` on all updates |
| Refunds | New reverse allocation (not decrement) |

### Data Model (5 Tables)

1. **`ticket_holders`** — Identity layer (phone/email, optional user_id)
2. **`allocations`** — Movement events (from/to, status, ticket_count, metadata)
3. **`allocation_tickets`** — Junction (allocation_id, ticket_id)
4. **`allocation_edges`** — Pre-aggregated counts for fast tree queries
5. **`tickets`** — Updated with `owner_holder_id` and generic locking

### Status Machine

```
pending → processing → completed / failed
```

### Safety Measures

- Ownership check on every UPDATE
- `RETURNING id` + `rows_affected` check on status transitions
- All changes inside single DB transaction
- FIFO deterministic ticket selection (no overselling)
- Pre-aggregated edges updated atomically inside transaction

---

## Link to Final Document

**Final Architecture Document:**
[AllocationAndMovement-Final.md](./AllocationAndMovement-Final.md)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-04-12 | Initial design from prior discussion |
| v1.1 | 2026-04-13 | Post-review fixes (constraint, N+1, syntax, indexes, ticket_count, metadata) |
| v1.2 | 2026-04-13 | Final fixes (ownership check, refund=reverse allocation, status transition race) |

---

*End of session summary*
