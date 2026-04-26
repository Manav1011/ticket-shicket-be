# Fix: Populate JTI for Customer B at Split Time

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** JTI should be generated and stored in Customer B's claim link at split time, not at claim time. At claim time, we use the stored JTI to generate JWT.

**Architecture:** JTI (16-char hex string) is generated at split time and stored in the claim link. At claim time, we read the stored JTI from DB and use it for JWT generation.

---

## File Structure

| File | Change |
|------|--------|
| `src/apps/event/claim_service.py` | Two changes: split_claim() and get_claim_redemption() |

---

## Tasks

### Task 1: Update `split_claim()` — Generate and store JTI for Customer B

**File:** `src/apps/event/claim_service.py:219-227` (Customer B claim link creation)

**Current code (around line 219):**
```python
customer_b_raw_token = generate_claim_link_token()
customer_b_token_hash = hashlib.sha256(customer_b_raw_token.encode()).hexdigest()

new_claim_link = ClaimLinkModel(
    allocation_id=allocation.id,
    token_hash=customer_b_token_hash,
    event_id=event_id,
    event_day_id=event_day_id,
    from_holder_id=customer_a_id,
    to_holder_id=customer_b.id,
    status=ClaimLinkStatus.active,
    created_by_holder_id=customer_a_id,
)
```

**Change to:**
```python
customer_b_raw_token = generate_claim_link_token()
customer_b_token_hash = hashlib.sha256(customer_b_raw_token.encode()).hexdigest()
customer_b_jti = secrets.token_hex(8)  # Generate JTI for Customer B at split time

new_claim_link = ClaimLinkModel(
    allocation_id=allocation.id,
    token_hash=customer_b_token_hash,
    event_id=event_id,
    event_day_id=event_day_id,
    from_holder_id=customer_a_id,
    to_holder_id=customer_b.id,
    status=ClaimLinkStatus.active,
    created_by_holder_id=customer_a_id,
    jwt_jti=customer_b_jti,  # Store JTI at creation time
)
```

---

### Task 2: Update `get_claim_redemption()` — Use stored JTI, generate only if NULL

**File:** `src/apps/event/claim_service.py:33-88` (`get_claim_redemption` method)

**Current code (around lines 73-84):**
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
```

**Change to:**
```python
# 5. Use existing JTI from claim link if available (set at split time)
# For legacy claim links without JTI, generate a new one
jti = claim_link.jwt_jti if claim_link.jwt_jti else secrets.token_hex(8)

# 6. If this is a legacy claim link (jwt_jti was NULL), store the new JTI
if not claim_link.jwt_jti:
    claim_link.jwt_jti = jti
    await self._session.flush()

# 7. Generate JWT using the JTI
jwt = generate_scan_jwt(
    jti=jti,
    holder_id=claim_link.to_holder_id,
    event_day_id=claim_link.event_day_id,
    indexes=indexes,
)
```

---

## Verification

1. **Import check:**
   ```
   uv run python -c "from apps.event.claim_service import ClaimService; print('OK')"
   ```

2. **Run event tests:**
   ```
   uv run pytest tests/apps/event/test_claim_service.py -v --tb=short
   ```

3. **Manual API test:**
   ```
   # Create fresh organizer→customer transfer (gives fresh claim link)
   # Split 1 ticket to Customer B
   # Check DB: Customer B's claim link should have jwt_jti populated
   # Customer B calls GET /api/open/claim/{token}
   # JWT should use the same JTI that was stored at split time
   ```

---

## Logic Summary

| Stage | JTI Behavior |
|-------|--------------|
| Split (Customer A → B) | Customer A's JTI revoked → new JTI stored in A's claim link. Customer B's JTI generated and stored in B's claim link. |
| Claim (GET /api/open/claim/{token}) | Use stored JTI from claim link. If claim link has no jwt_jti (legacy), generate new and store. |

---

## Files Modified

| File | Change |
|------|--------|
| `src/apps/event/claim_service.py` | split_claim(): add `jwt_jti=customer_b_jti` to new claim link. get_claim_redemption(): use `claim_link.jwt_jti` if exists, else generate new. |