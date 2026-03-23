# Refresh Token Uniqueness (User + Guest) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ensure refresh token rotation always produces a new token string for both user and guest flows, then verify both refresh endpoints succeed without DB unique-token collisions.

**Architecture:** Both user and guest refresh endpoints rely on shared JWT generators in `pkg/token/jwt.go`. The safest fix is to add a per-token unique claim (`jti`) to both access and refresh tokens so token strings differ even when generated in the same second with identical subject and expiry. We then validate this behavior at token-unit level and endpoint-integration level for user and guest.

**Tech Stack:** Go, Gin, PostgreSQL, sqlc, golang-jwt/v5, google/uuid

---

### Task 1: Add Failing Uniqueness Tests for User and Guest Tokens

**Files:**
- Modify: `pkg/token/jwt_test.go`

**Step 1: Write the failing tests**

Add tests that currently fail (or are flaky) without uniqueness claim:

```go
func TestGenerateRefreshTokenIsUniqueForSameUser(t *testing.T) {
	userID := "63bdcfa3-5b91-4fd9-a870-8d4a86528ee3"
	t1, err := GenerateRefreshToken(userID)
	if err != nil {
		t.Fatalf("first token error: %v", err)
	}
	t2, err := GenerateRefreshToken(userID)
	if err != nil {
		t.Fatalf("second token error: %v", err)
	}
	if t1 == t2 {
		t.Fatal("expected different refresh tokens for same user")
	}
}

func TestGenerateRefreshTokenIsUniqueForSameGuest(t *testing.T) {
	guestID := "550e8400-e29b-41d4-a716-446655440000"
	t1, err := GenerateRefreshTokenGuest(guestID)
	if err != nil {
		t.Fatalf("first token error: %v", err)
	}
	t2, err := GenerateRefreshTokenGuest(guestID)
	if err != nil {
		t.Fatalf("second token error: %v", err)
	}
	if t1 == t2 {
		t.Fatal("expected different refresh tokens for same guest")
	}
}
```

**Step 2: Run tests to verify failure**

Run:

```bash
go test ./pkg/token -run "TestGenerateRefreshTokenIsUniqueForSameUser|TestGenerateRefreshTokenIsUniqueForSameGuest" -v
```

Expected: FAIL at least one uniqueness assertion (or flaky behavior proves collision risk)

**Step 3: Commit**

```bash
git add pkg/token/jwt_test.go
git commit -m "test: add failing refresh-token uniqueness tests for user and guest"
```

---

### Task 2: Add `jti` Claim to Shared JWT Generators

**Files:**
- Modify: `pkg/token/jwt.go`

**Step 1: Implement minimal code change**

Add `github.com/google/uuid` import and include `jti: uuid.NewString()` in all generated token claims (user/guest access+refresh).

```go
claims := jwt.MapClaims{
	"user_id": userID,
	"type":    "refresh",
	"jti":     uuid.NewString(),
	"exp":     time.Now().Add(cfg.RefreshTokenDuration).Unix(),
}
```

and

```go
claims := jwt.MapClaims{
	"guest_id": guestID,
	"type":     "refresh",
	"jti":      uuid.NewString(),
	"exp":      time.Now().Add(cfg.RefreshTokenDuration).Unix(),
}
```

(Repeat for access token generators too for consistency.)

**Step 2: Run token tests to verify pass**

Run:

```bash
go test ./pkg/token -v
```

Expected: PASS including new uniqueness tests

**Step 3: Commit**

```bash
git add pkg/token/jwt.go pkg/token/jwt_test.go
git commit -m "fix: add jti claim to user and guest JWT generation"
```

---

### Task 3: Add/Update Guest Refresh Endpoint Integration Test

**Files:**
- Modify: `internal/guest/integration_test.go`

**Step 1: Write or keep test for refresh rotation**

Ensure `TestGuestRefreshFlow` verifies:
- register guest
- call `/v1/guests/refresh` with initial refresh token
- response is 200
- new refresh token differs from old refresh token
- new access token contains `guest_id`

**Step 2: Run test**

Run:

```bash
go test ./internal/guest -run TestGuestRefreshFlow -v -timeout 30s
```

Expected: PASS

**Step 3: Commit**

```bash
git add internal/guest/integration_test.go
git commit -m "test: verify guest refresh endpoint rotates tokens"
```

---

### Task 4: Add User Refresh Endpoint Integration Test

**Files:**
- Create: `internal/user/integration_test.go`

**Step 1: Write failing integration test for `/v1/users/refresh`**

Test flow:
- create DB + app router
- create a known user row with hashed password
- call `/v1/users/login` to get initial refresh token
- call `/v1/users/refresh` with initial token
- assert 200 response
- assert new refresh token differs from old token
- parse new access token and assert `user_id` exists

Skeleton:

```go
func TestUserRefreshFlow(t *testing.T) {
	// setup cfg/db/queries/repo/service/handler/router
	// create user directly using repo.Create with hashed password
	// POST /v1/users/login
	// POST /v1/users/refresh
	// assert rotated refresh token and user_id in claims
}
```

**Step 2: Run test to verify it fails before final adjustments**

Run:

```bash
go test ./internal/user -run TestUserRefreshFlow -v -timeout 30s
```

Expected: FAIL initially if setup incomplete

**Step 3: Implement minimal missing setup to pass**

Add any minimal fixture setup needed (user creation + cleanup) while keeping YAGNI.

**Step 4: Re-run test to verify pass**

Run:

```bash
go test ./internal/user -run TestUserRefreshFlow -v -timeout 30s
```

Expected: PASS

**Step 5: Commit**

```bash
git add internal/user/integration_test.go
git commit -m "test: verify user refresh endpoint rotates tokens"
```

---

### Task 5: Full Regression Pass for User + Guest Auth Paths

**Files:**
- Modify (if needed): `internal/guest/service/guest_service.go`
- Modify (if needed): `internal/user/service/user_service.go`

**Step 1: Run guest suite**

```bash
go test ./internal/guest/... -v -timeout 30s
```

Expected: PASS

**Step 2: Run user suite**

```bash
go test ./internal/user/... -v -timeout 30s
```

Expected: PASS

**Step 3: Run token suite**

```bash
go test ./pkg/token -v
```

Expected: PASS

**Step 4: Run combined smoke target**

```bash
go test ./... -run "Refresh|Token|Guest|User" -v -timeout 60s
```

Expected: PASS for relevant tests

**Step 5: Commit final cleanups (if any)**

```bash
git add internal/guest/service/guest_service.go internal/user/service/user_service.go
git commit -m "chore: finalize refresh-token rotation reliability across user and guest"
```

---

### Task 6: Swagger/Contract Validation for New/Existing Refresh Endpoints

**Files:**
- Modify (if needed): `internal/guest/handler/guest_handler.go`
- Modify (if needed): `internal/user/handler/user_handler.go`

**Step 1: Validate annotations are correct**

Ensure route docs match actual endpoints:
- `POST /guests/refresh`
- `POST /users/refresh`

Ensure request/response models are accurate.

**Step 2: Regenerate docs**

```bash
swag init -g cmd/server/main.go -o docs
```

Expected: docs refreshed with no errors

**Step 3: Build server**

```bash
go build ./cmd/server
```

Expected: PASS

**Step 4: Commit**

```bash
git add docs internal/guest/handler/guest_handler.go internal/user/handler/user_handler.go
git commit -m "docs: verify refresh endpoint contracts for user and guest"
```

---

## Summary

This plan fixes refresh token collision risk and verifies both API layers:

1. Add failing uniqueness tests for user/guest refresh tokens.
2. Add `jti` claim in shared JWT generators to guarantee unique token strings.
3. Verify guest refresh endpoint rotates tokens correctly.
4. Add/verify user refresh endpoint integration test with token rotation checks.
5. Run regression tests across guest, user, and token packages.
6. Validate API contract/docs for refresh endpoints.

Result: both `POST /v1/users/refresh` and `POST /v1/guests/refresh` reliably rotate refresh tokens without unique-token DB collisions.
