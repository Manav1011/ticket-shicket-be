# Fix: Store JTI in ClaimLinkModel

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `jwt_jti` field to ClaimLinkModel so we can revoke the correct JWT when Customer A initiates a split.

**Architecture:** The JTI generated when Customer A claims their link will be stored in the claim_links table. Later, when Customer A splits tickets, we use this stored JTI to add it to the revoked_scan_tokens table.

**Tech Stack:** SQLAlchemy, async PostgreSQL, Pydantic

---

## Problem Statement

When Organizer/Reseller transfers to Customer, a ClaimLink is created with `token_hash` but no JTI. When Customer A later calls `GET /api/open/claim/{token}`, we generate a JWT with a JTI but don't store it anywhere.

Later when Customer A wants to split tickets to Customer B:
- We need to revoke Customer A's old JWT (add old JTI to revoked list)
- But we don't know which JTI to revoke because we never stored it

**Fix:** Add `jwt_jti` column to `claim_links` table. Populate it when Customer A claims. Use it during split for revocation.

---

## File Structure

| File | Change |
|------|--------|
| `src/apps/allocation/models.py` | Add `jwt_jti` column to ClaimLinkModel |
| `src/apps/allocation/repository.py` | Add migration note + method to update `jwt_jti` |
| `src/apps/event/claim_service.py` | Store JTI when generating JWT for customer |
| `src/apps/allocation/enums.py` | (no change needed) |
| `src/apps/event/response.py` | (no change needed) |
| New migration | Add `jwt_jti` column to `claim_links` table |

---

## Tasks

### Task 1: Add `jwt_jti` Column to ClaimLinkModel

**Files:**
- Modify: `src/apps/allocation/models.py`

- [ ] **Step 1: Check current ClaimLinkModel**

Read `src/apps/allocation/models.py` and find the ClaimLinkModel definition. Note the existing fields and where `jwt_jti` should be added.

- [ ] **Step 2: Add `jwt_jti` field to ClaimLinkModel**

```python
# In ClaimLinkModel, after status field:
jwt_jti: Mapped[str | None] = mapped_column(String(32), nullable=True)
```

**Note:** JTI is a 16-char hex string (from `secrets.token_hex(8)`), so `String(32)` is safe.

- [ ] **Step 3: Run import check**

Run: `uv run python -c "from apps.allocation.models import ClaimLinkModel; print('OK')"`
Expected: No errors

---

### Task 2: Create Migration for `jwt_jti` Column

**Files:**
- Create: `src/migrations/versions/xxxxxxxx_add_jwt_jti_to_claim_links.py`

- [ ] **Step 1: Create migration**

Run: `uv run main.py makemigrations --name add_jwt_jti_to_claim_links`

Expected output: Migration file created with:
```python
def upgrade():
    op.add_column('claim_links', sa.Column('jwt_jti', sa.String(32), nullable=True))
```

- [ ] **Step 2: Apply migration**

Run: `uv run main.py migrate`

- [ ] **Step 3: Commit migration**

```bash
git add src/migrations/versions/xxxxxxxx_add_jwt_jti_to_claim_links.py
git commit -m "migrate: add jwt_jti column to claim_links"
```

---

### Task 3: Store JTI in ClaimService When Generating JWT

**Files:**
- Modify: `src/apps/event/claim_service.py:84`

- [ ] **Step 1: Read current claim_service.py**

Note the `get_claim_redemption` method. After generating the JWT (line ~84), we need to update the claim_link with the JTI.

- [ ] **Step 2: Update claim_link with JTI after JWT generation**

Add after generating the JWT (before return):

```python
# Store JTI in claim link for future revocation (e.g., during split)
claim_link.jwt_jti = jti
await self._session.flush()
```

Full updated section (from `jti = secrets.token_hex(8)` to return):

```python
# 5. Generate unique JTI for this JWT
jti = secrets.token_hex(8)  # 16-char hex string

# 6. Generate JWT
jwt = generate_scan_jwt(
    jti=jti,
    holder_id=claim_link.to_holder_id,
    event_day_id=claim_link.event_day_id,
    indexes=indexes,
)

# 7. Store JTI in claim link for future revocation
claim_link.jwt_jti = jti
await self._session.flush()

# 8. Return response with ticket count, not indexes
return ClaimRedemptionResponse(
    holder_id=claim_link.to_holder_id,
    event_day_id=claim_link.event_day_id,
    ticket_count=len(indexes),
    jwt=jwt,
)
```

- [ ] **Step 3: Run import check**

Run: `uv run python -c "from apps.event.claim_service import ClaimService; print('OK')"`
Expected: No errors

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/apps/event/test_claim_service.py -v --tb=short`
Expected: All pass

---

### Task 4: Add ClaimLinkRepository Method to Update JTI (Optional)

If we need a dedicated repository method later, we can add it. For now, direct attribute assignment works (Step 3 above). No action needed here — just noting for future.

---

## Verification

1. **Import check:**
   ```
   uv run python -c "from apps.allocation.models import ClaimLinkModel; print('OK')"
   ```

2. **Migration applied:**
   ```
   uv run main.py showmigrations | grep jwt_jti
   ```

3. **Tests pass:**
   ```
   uv run pytest tests/apps/event/test_claim_service.py -v --tb=short
   ```

---

## Files Modified

| File | Change |
|------|--------|
| `src/apps/allocation/models.py` | Added `jwt_jti: Mapped[str | None]` column |
| `src/migrations/versions/xxxxxxxx_add_jwt_jti_to_claim_links.py` | New migration |
| `src/apps/event/claim_service.py` | Store JTI in claim_link after generating JWT |

---

## After This Fix

When Customer A calls `GET /api/open/claim/{token}`:
1. JWT generated with JTI (e.g., `"abc12345def67890"`)
2. JTI stored in `claim_links.jwt_jti` column
3. Later split operation can read `claim_link.jwt_jti` to revoke the correct JWT

---

## Execution Options

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks

**2. Inline Execution** — Execute tasks in this session using executing-plans

**Which approach?**