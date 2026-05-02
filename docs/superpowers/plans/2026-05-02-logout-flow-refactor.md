# Logout Flow Refactor + Transaction Fix

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the logout API to use a shared `jti` in both access and refresh tokens, and fix the "closed transaction" error in the refresh endpoint.

**Architecture:**
1. **Logout flow**: Add `jti` to both access and refresh tokens at creation time. On logout, decode refresh token to extract `jti`, then revoke all refresh tokens sharing that `jti`. Access token is short-lived and deleted client-side.
2. **Transaction fix**: Remove redundant `commit()` calls from service/repository methods. The `db_session` dependency already provides a transaction context that auto-commits on success / rollback on exception. Services should flush (write to DB) but never commit manually.

**Tech Stack:** FastAPI, SQLAlchemy async, Redis, PyJWT

---

## Issue 1: Transaction Error in Refresh

The error "Can't operate on closed transaction inside context manager" happens because:

1. `db_session()` at [src/db/session.py:25-32](src/db/session.py#L25-L32) wraps work in `async with session.begin()` — this creates a transaction context that auto-commits on exit
2. `UserService.refresh_user()` at [src/apps/user/service.py:166](src/apps/user/service.py#L166) calls `await self.repository.session.commit()` manually — this closes the transaction
3. When `db_session` exits, it tries to commit again on the already-closed transaction → error

**Fix:** Remove `commit()` from `refresh_user` and all other service/repository methods. Let `db_session` manage the transaction boundary.

---

## Issue 2: Logout API Design

**Current problem:**
- `logout` endpoint requires `access_token_jti` in request body
- But access token is in `Authorization: Bearer` header — client can't easily extract `jti`
- More importantly: access tokens don't actually carry a `jti` claim currently

**Proposed flow:**
1. `create_tokens()` adds a `jti` (UUID) to **both** access and refresh token payloads
2. `RefreshTokenModel` gets a `jti` column to store it alongside `token_hash`
3. On logout, decode the refresh token (sent in body or cookie), extract `jti`, revoke all refresh tokens with that `jti`
4. No `access_token_jti` needed — logout uses the refresh token's jti

---

## File Map

```
src/
  auth/jwt.py                  — add jti to both token payloads in create_tokens()
  auth/dependencies.py         — store decoded access token payload in request.state.token_payload
  auth/schemas.py              — drop access_token_jti from RefreshRequestWithJti
  apps/user/models.py          — add jti column to RefreshTokenModel
  apps/user/repository.py     — add revoke_by_jti() method
  apps/user/service.py        — change logout_user to accept jti; remove manual commits
  apps/user/urls.py           — simplify logout endpoint
  db/session.py                — no changes (already correct)
```

---

## Task 1: Fix Transaction Error in Refresh Endpoint

**Files:**
- Modify: `src/apps/user/service.py:134-168`

- [ ] **Step 1: Read the current refresh_user implementation**

Verify current code at [src/apps/user/service.py:134-168](src/apps/user/service.py#L134-L168)

- [ ] **Step 2: Remove the manual commit**

Change:
```python
        await self.repository.session.commit()

        return new_tokens
```

To:
```python
        return new_tokens
```

The `db_session` dependency already commits on success / rolls back on exception.

**Run:** `uv run pytest tests/apps/user/test_service.py -v -k refresh 2>&1 | head -50`
Expected: Tests still pass

- [ ] **Step 3: Verify refresh endpoint works end-to-end**

**Run:** `curl -X POST http://localhost:8000/api/user/refresh -H "Content-Type: application/json" -d '{"refresh_token": "..."}'`
Expected: 200 OK, new tokens returned, no transaction error in terminal

---

## Task 2: Add JTI to RefreshTokenModel

**Files:**
- Modify: `src/apps/user/models.py:45-64`

- [ ] **Step 1: Add jti column to RefreshTokenModel**

In `RefreshTokenModel`, add after `user_id` column:
```python
    jti: Mapped[uuid.UUID] = mapped_column(index=True, nullable=False)
```

- [ ] **Step 2: Create migration**

**Run:** `uv run main.py makemigrations --name add_jti_to_refresh_tokens`
Expected: Migration file created in `migrations/versions/`

- [ ] **Step 3: Apply migration**

**Run:** `uv run main.py migrate`
Expected: Migration applied successfully

---

## Task 3: Add JTI to Token Payloads in create_tokens

**Files:**
- Modify: `src/auth/jwt.py:54-78`

- [ ] **Step 1: Generate jti once and add to both tokens**

Change:
```python
async def create_tokens(
    user_id: UUID = None,
    guest_id: UUID = None,
    type: Literal["user", "guest"] = "user",
) -> dict[str, str]:
    # ...
    sub = str(user_id) if type == "user" else str(guest_id)

    access_token = access.encode(
        payload={"sub": sub, "user_type": type},
        expire_period=int(settings.ACCESS_TOKEN_EXP),
    )
    refresh_token = refresh.encode(
        payload={"sub": sub, "user_type": type},
        expire_period=int(settings.REFRESH_TOKEN_EXP),
    )
    return {"access_token": access_token, "refresh_token": refresh_token}
```

To:
```python
async def create_tokens(
    user_id: UUID = None,
    guest_id: UUID = None,
    type: Literal["user", "guest"] = "user",
) -> dict[str, str]:
    # ...
    jti = str(uuid.uuid4())
    sub = str(user_id) if type == "user" else str(guest_id)

    access_token = access.encode(
        payload={"sub": sub, "user_type": type, "jti": jti},
        expire_period=int(settings.ACCESS_TOKEN_EXP),
    )
    refresh_token = refresh.encode(
        payload={"sub": sub, "user_type": type, "jti": jti},
        expire_period=int(settings.REFRESH_TOKEN_EXP),
    )
    return {"access_token": access_token, "refresh_token": refresh_token}
```

Also add `import uuid` at top of file if not present.

**Run:** `uv run pytest tests/auth/test_jwt.py -v 2>&1 | head -50`
Expected: Tests pass

---

## Task 4: Store JTI When Creating Refresh Token Record

**Files:**
- Modify: `src/apps/user/repository.py:73-84`

- [ ] **Step 1: Update create_refresh_token to accept and store jti**

Change:
```python
    async def create_refresh_token(
        self, token_hash: str, user_id: UUID, expires_at: datetime
    ) -> RefreshTokenModel:
        """Create a new refresh token record."""
        token = RefreshTokenModel(
            token_hash=token_hash,
            user_id=user_id,
            expires_at=expires_at,
        )
        self._session.add(token)
        await self._session.flush()
        return token
```

To:
```python
    async def create_refresh_token(
        self, token_hash: str, user_id: UUID, expires_at: datetime, jti: str
    ) -> RefreshTokenModel:
        """Create a new refresh token record."""
        token = RefreshTokenModel(
            token_hash=token_hash,
            user_id=user_id,
            expires_at=expires_at,
            jti=uuid.UUID(jti),
        )
        self._session.add(token)
        await self._session.flush()
        return token
```

Also update import at top of file to include `import uuid`.

- [ ] **Step 2: Update service calls to create_refresh_token**

In [src/apps/user/service.py](src/apps/user/service.py), update:
- `login_user` (line ~64): pass `jti` extracted from `create_tokens` return
- `refresh_user` (line ~161): pass `jti` from decoded refresh token

In [src/apps/user/urls.py](src/apps/user/urls.py):
- `sign_in` route (line ~152): pass `jti` from tokens returned by `login_user`

**Run:** `uv run pytest tests/apps/user/test_service.py -v 2>&1 | head -80`
Expected: Tests pass

---

## Task 5: Add revoke_by_jti to Repository

**Files:**
- Modify: `src/apps/user/repository.py`

- [ ] **Step 1: Add revoke_by_jti method**

After existing `revoke_refresh_token` (line ~95-102), add:
```python
    async def revoke_by_jti(self, jti: str) -> None:
        """Revoke all refresh tokens with a given jti."""
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.jti == uuid.UUID(jti))
            .values(revoked=True)
        )
        await self._session.flush()
```

Add `import uuid` if not present.

- [ ] **Step 2: Run tests**

**Run:** `uv run pytest tests/apps/user/test_repository.py -v 2>&1 | head -50`
Expected: Tests pass

---

## Task 6: Update logout_user Service Method

**Files:**
- Modify: `src/apps/user/service.py:120-132`

- [ ] **Step 1: Change logout_user signature and implementation**

Change:
```python
    async def logout_user(
        self,
        refresh_token: str,
        access_token_jti: str | None = None,
    ) -> None:
        """Revoke refresh token and optionally blocklist access token by jti."""
        token_hash = self._hash_token(refresh_token)
        await self.repository.revoke_refresh_token(token_hash)

        if access_token_jti:
            await self._blocklist.add(access_token_jti, ttl=int(settings.ACCESS_TOKEN_EXP))

        await self.repository.session.commit()
```

To:
```python
    async def logout_user(
        self,
        refresh_token: str,
    ) -> None:
        """Revoke all refresh tokens sharing jti with the provided refresh token."""
        from auth.jwt import refresh as refresh_jwt
        payload = refresh_jwt.decode(refresh_token)
        jti = payload.get("jti")
        if jti:
            await self.repository.revoke_by_jti(jti)
```

Note: `logout_user` no longer needs to commit manually — `db_session` handles it.

---

## Task 7: Update Logout Endpoint

**Files:**
- Modify: `src/apps/user/urls.py:202-214`
- Modify: `src/auth/schemas.py:26-29`

- [ ] **Step 1: Update RefreshRequestWithJti to just RefreshRequest**

In `src/auth/schemas.py`, change `RefreshRequestWithJti` to just use `RefreshRequest` (drop `access_token_jti`):
```python
class RefreshRequestWithJti(CamelCaseModel):
    """Request body for logout with optional access token jti."""
    refresh_token: str
```

Or rename to just `LogoutRequest` to be clear:
```python
class LogoutRequest(CamelCaseModel):
    """Request body for logout."""
    refresh_token: str
```

- [ ] **Step 2: Update logout endpoint**

Change:
```python
@protected_router.post("/logout", status_code=status.HTTP_200_OK, operation_id="logout")
async def logout(
    request: Request,
    body: RefreshRequestWithJti,
    service: Annotated[UserService, Depends(get_user_service)],
):
    """Logout endpoint. Revokes refresh token and blocklists access token."""
    user: UserModel = request.state.user  # from auth dependency
    await service.logout_user(
        refresh_token=body.refresh_token,
        access_token_jti=body.access_token_jti,
    )
    return BaseResponse(message="Logged out successfully")
```

To:
```python
@protected_router.post("/logout", status_code=status.HTTP_200_OK, operation_id="logout")
async def logout(
    request: Request,
    body: LogoutRequest,
    service: Annotated[UserService, Depends(get_user_service)],
):
    """Logout endpoint. Revokes all refresh tokens sharing the jti from the provided refresh token."""
    await service.logout_user(refresh_token=body.refresh_token)
    return BaseResponse(data={"message": "Logged out successfully"})
```

Also fix the `BaseResponse(message=...)` → `BaseResponse(data=...)` error.

---

## Task 8: Verify End-to-End Logout Flow

**Run:**
```bash
# Sign in to get tokens
curl -X POST http://localhost:8000/api/user/sign-in \
  -H "Content-Type: application/json" \
  -d '{"email": "...", "password": "..."}'

# Copy the refresh_token from response, then logout
curl -X POST http://localhost:8000/api/user/logout \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

Expected: 200 OK with `{"status": "SUCCESS", "code": 200, "data": {"message": "Logged out successfully"}}`

Then try to use the old refresh token:
```bash
curl -X POST http://localhost:8000/api/user/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<old_refresh_token>"}'
```

Expected: 401 Unauthorized (token revoked)

---

## Verification Checklist

- [ ] Refresh endpoint returns 200 with no transaction error in logs
- [ ] Sign-in creates tokens with `jti` in payload (decode to verify)
- [ ] Refresh token DB record has `jti` stored
- [ ] Logout endpoint only requires `refresh_token` in body (no `access_token_jti`)
- [ ] Logout revokes all tokens with matching jti
- [ ] Old refresh token rejected after logout (401)
- [ ] No `BaseResponse(message=...)` errors in logout response

---

## Notes

- The `TokenBlocklist` class and `is_blocklisted` check are **not wired up** in `get_current_user` — this plan doesn't fix that. The logout flow works without it because refresh tokens are revoked server-side in the DB.
- If blocklist enforcement is needed later, `get_current_user` would need to call `is_blocklisted(jti)` after decoding the access token.
- The `jti` in the access token is never used in this plan — it's only used in the refresh token for revocation tracking. Access token is short-lived and handled client-side.