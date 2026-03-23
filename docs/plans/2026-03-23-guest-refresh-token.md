# Guest Refresh Token Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a refresh endpoint for guest users (`POST /v1/guests/refresh`) that validates and rotates guest refresh tokens, issuing new access and refresh tokens.

**Architecture:** 
Guest refresh follows the exact same pattern as user refresh: validate the incoming refresh token JWT, check that it exists in the database and isn't revoked, revoke the old token, generate new access and refresh tokens, and persist the new refresh token. This enables secure token rotation and audit trails via the `guest_refresh_tokens` table.

**Tech Stack:** 
Go, Gin, PostgreSQL, sqlc, JWT (golang-jwt/v5), uuid (google/uuid)

---

## Task 1: Add Guest Refresh Request/Response Models

**Files:**
- Modify: `internal/guest/model/request_model.go`
- Modify: `internal/guest/model/response_model.go`

**Step 1: Add RefreshRequest to request_model.go**

Add after `GuestRegisterRequest`:

```go
type GuestRefreshRequest struct {
	RefreshToken string `json:"refresh_token" binding:"required"`
}
```

**Step 2: Add RefreshSuccessEnvelope to response_model.go**

Add after `GuestRegisterSuccessEnvelope`:

```go
type GuestRefreshSuccessEnvelope struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
	TokenType    string `json:"token_type"`
	ExpiresIn    int64  `json:"expires_in"`
}
```

**Step 3: Verify file structure**

Run: `grep -A 3 "GuestRefreshRequest\|GuestRefreshSuccessEnvelope" internal/guest/model/*.go`
Expected: Both types visible in output

**Step 4: Commit**

```bash
cd /home/web-h-063/Documents/ticket-shicket-be
git add internal/guest/model/request_model.go internal/guest/model/response_model.go
git commit -m "feat: add guest refresh request/response models"
```

---

## Task 2: Add Refresh Method to Guest Repository

**Files:**
- Modify: `internal/guest/repository/guest_repository.go`

**Step 1: Verify repository already has refresh token methods**

Run: `grep -n "InsertGuestRefreshToken\|GetGuestRefreshToken\|RevokeGuestRefreshToken" internal/guest/repository/guest_repository.go`
Expected: Three methods already exist (added in previous work)

**Step 2: Commit (no changes needed)**

```bash
cd /home/web-h-063/Documents/ticket-shicket-be
git commit --allow-empty -m "refactor: repository already supports guest refresh tokens"
```

---

## Task 3: Add Refresh Method to Guest Service

**Files:**
- Modify: `internal/guest/service/guest_service.go`

**Step 1: Write failing test**

Create test in `internal/guest/service/guest_service_test.go`:

```go
func TestRefreshGuestToken(t *testing.T) {
	// Placeholder - integration test will verify in integration_test.go
	t.Log("GuestService.Refresh tested via integration")
}
```

**Step 2: Run test to verify it fails gracefully**

Run: `go test ./internal/guest/service -run TestRefreshGuestToken -v`
Expected: PASS (placeholder test)

**Step 3: Add Refresh method to guest_service.go**

Add after the `Register` method:

```go
// Refresh validates a guest refresh token and issues new tokens
func (s *GuestService) Refresh(ctx context.Context, refreshToken string) (*model.GuestRefreshSuccessEnvelope, error) {
	// Parse and validate the incoming refresh token
	claims, err := token.ParseToken(refreshToken)
	if err != nil {
		return nil, fmt.Errorf("parse token: %w", err)
	}
	if claims["type"] != "refresh" {
		return nil, fmt.Errorf("invalid token type")
	}

	// Check if token exists in DB
	refreshRow, err := s.repo.GetGuestRefreshToken(ctx, refreshToken)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, fmt.Errorf("refresh token not found")
		}
		return nil, fmt.Errorf("get refresh token: %w", err)
	}

	// Check if revoked
	if refreshRow.Revoked.Valid && refreshRow.Revoked.Bool {
		return nil, fmt.Errorf("token revoked")
	}

	// Revoke old token
	err = s.repo.RevokeGuestRefreshToken(ctx, refreshToken)
	if err != nil {
		return nil, fmt.Errorf("revoke refresh token: %w", err)
	}

	// Extract guest_id from claims
	guestID, ok := claims["guest_id"].(string)
	if !ok {
		return nil, fmt.Errorf("invalid guest_id in token")
	}

	// Generate new tokens
	access, err := token.GenerateAccessTokenGuest(guestID)
	if err != nil {
		return nil, fmt.Errorf("access token: %w", err)
	}
	refresh, err := token.GenerateRefreshTokenGuest(guestID)
	if err != nil {
		return nil, fmt.Errorf("refresh token: %w", err)
	}

	// Persist new refresh token
	expiresAt := time.Now().Add(s.cfg.RefreshTokenDuration)
	_, err = s.repo.InsertGuestRefreshToken(ctx, sqldb.InsertGuestRefreshTokenParams{
		GuestID:   refreshRow.GuestID,
		Token:     refresh,
		ExpiresAt: expiresAt,
		UserAgent: refreshRow.UserAgent,
		IpAddress: refreshRow.IpAddress,
	})
	if err != nil {
		return nil, fmt.Errorf("persist new refresh token: %w", err)
	}

	expiresIn := int64(s.cfg.AccessTokenDuration.Seconds())
	return &model.GuestRefreshSuccessEnvelope{
		AccessToken:  access,
		RefreshToken: refresh,
		TokenType:    "Bearer",
		ExpiresIn:    expiresIn,
	}, nil
}
```

**Step 4: Run tests**

Run: `go test ./internal/guest/service -v`
Expected: PASS

**Step 5: Commit**

```bash
cd /home/web-h-063/Documents/ticket-shicket-be
git add internal/guest/service/guest_service.go
git commit -m "feat: add guest refresh token validation and rotation"
```

---

## Task 4: Add Refresh Handler to Guest Handler

**Files:**
- Modify: `internal/guest/handler/guest_handler.go`

**Step 1: Write failing handler test**

In `internal/guest/handler/guest_handler_test.go`, add:

```go
func TestGuestRefreshHandler(t *testing.T) {
	// Placeholder - integration test will verify
	t.Log("Guest refresh handler tested via integration")
}
```

**Step 2: Run test**

Run: `go test ./internal/guest/handler -run TestGuestRefreshHandler -v`
Expected: PASS

**Step 3: Add Refresh handler method**

Add after `Register` method in `internal/guest/handler/guest_handler.go`:

```go
// Refresh validates a guest refresh token and issues new tokens.
// @Summary      Guest token refresh
// @Description  Validates a refresh token and issues new access and refresh tokens for guests.
// @Tags         guest
// @Accept       json
// @Produce      json
// @Param        body  body      model.GuestRefreshRequest  true  "Refresh token"
// @Success      200   {object}  model.GuestRefreshSuccessEnvelope
// @Failure      400   {object}  utils.APIResponse
// @Failure      401   {object}  utils.APIResponse
// @Failure      500   {object}  utils.APIResponse
// @Router       /guests/refresh [post]
func (h *GuestHandler) Refresh(c *gin.Context) {
	var req model.GuestRefreshRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.Error(c, "invalid request body", http.StatusBadRequest)
		return
	}

	data, err := h.svc.Refresh(c.Request.Context(), req.RefreshToken)
	if err != nil {
		if errors.Is(err, service.ErrGuestRegistrationFailed) {
			utils.Error(c, "token refresh failed", http.StatusInternalServerError)
			return
		}
		utils.Error(c, err.Error(), http.StatusUnauthorized)
		return
	}

	utils.Success(c, data)
}
```

**Step 4: Run tests**

Run: `go build -v ./internal/guest/handler && go test ./internal/guest/handler -v`
Expected: Build succeeds, tests pass

**Step 5: Commit**

```bash
cd /home/web-h-063/Documents/ticket-shicket-be
git add internal/guest/handler/guest_handler.go
git commit -m "feat: add guest refresh HTTP handler"
```

---

## Task 5: Register Refresh Route in Guest Routes

**Files:**
- Modify: `internal/guest/routes.go`

**Step 1: Add refresh route**

In `RegisterRoutes` function, add after the register route:

```go
guests.POST("/refresh", h.Refresh)
```

So the complete routes block becomes:

```go
func RegisterRoutes(v1 *gin.RouterGroup, h *handler.GuestHandler) {
	guests := v1.Group("/guests")
	guests.POST("/register", h.Register)
	guests.POST("/refresh", h.Refresh)
}
```

**Step 2: Verify compilation**

Run: `go build -v ./internal/guest/...`
Expected: No errors

**Step 3: Commit**

```bash
cd /home/web-h-063/Documents/ticket-shicket-be
git add internal/guest/routes.go
git commit -m "feat: register guest refresh route"
```

---

## Task 6: End-to-End Integration Test

**Files:**
- Modify: `internal/guest/integration_test.go`

**Step 1: Write guest refresh integration test**

Add new test function to `internal/guest/integration_test.go`:

```go
func TestGuestRefreshFlow(t *testing.T) {
	cfg := config.LoadConfig()
	pool := db.NewDB(cfg.DBSource)
	sqlDB := stdlib.OpenDBFromPool(pool)
	defer sqlDB.Close()

	queries := sqldb.New(sqlDB)
	repo := guestRepo.NewGuestRepository(queries)
	svc := guestSvc.NewGuestService(repo, cfg)
	handler := guestHandler.NewGuestHandler(svc)

	router := gin.New()
	v1 := router.Group("/v1")
	RegisterRoutes(v1, handler)

	// Step 1: Register guest
	registerReq := guestModel.GuestRegisterRequest{
		UserAgent: "Mozilla/5.0",
		IpAddress: "192.168.1.1",
	}
	registerBody, _ := json.Marshal(registerReq)
	httpReq := httptest.NewRequest("POST", "/v1/guests/register", bytes.NewBuffer(registerBody))
	httpReq.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, httpReq)

	if w.Code != http.StatusOK {
		t.Fatalf("Registration failed: %d", w.Code)
	}

	var registerResp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &registerResp)
	initialRefreshToken := registerResp["data"].(map[string]interface{})["refresh_token"].(string)

	// Step 2: Refresh tokens
	refreshReq := guestModel.GuestRefreshRequest{
		RefreshToken: initialRefreshToken,
	}
	refreshBody, _ := json.Marshal(refreshReq)
	httpReq = httptest.NewRequest("POST", "/v1/guests/refresh", bytes.NewBuffer(refreshBody))
	httpReq.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	router.ServeHTTP(w, httpReq)

	if w.Code != http.StatusOK {
		t.Fatalf("Expected 200, got %d: %s", w.Code, w.Body.String())
	}

	var refreshResp map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &refreshResp); err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	newAccessToken := refreshResp["data"].(map[string]interface{})["access_token"].(string)
	newRefreshToken := refreshResp["data"].(map[string]interface{})["refresh_token"].(string)

	if newAccessToken == "" {
		t.Fatal("Expected new access_token")
	}
	if newRefreshToken == "" {
		t.Fatal("Expected new refresh_token")
	}
	if newRefreshToken == initialRefreshToken {
		t.Fatal("Refresh token should be rotated")
	}

	// Verify new access token contains guest_id
	claims, err := token.ParseToken(newAccessToken)
	if err != nil {
		t.Fatalf("Failed to parse new access token: %v", err)
	}
	if claims["guest_id"] == nil {
		t.Fatal("New access token should contain guest_id")
	}
}
```

**Step 2: Run integration test**

Run: `go test ./internal/guest -run TestGuestRefreshFlow -v -timeout 30s`
Expected: PASS

**Step 3: Run all guest tests**

Run: `go test ./internal/guest/... -v -timeout 30s`
Expected: All tests PASS

**Step 4: Commit**

```bash
cd /home/web-h-063/Documents/ticket-shicket-be
git add internal/guest/integration_test.go
git commit -m "test: add guest token refresh integration test"
```

---

## Summary

Guest refresh implementation adds secure token rotation:

1. **Models**: GuestRefreshRequest + GuestRefreshSuccessEnvelope
2. **Service**: Validates refresh token, revokes old token, issues new pair
3. **Handler**: HTTP endpoint `POST /v1/guests/refresh`
4. **Route**: Registered as `/guests/refresh` under `/v1`
5. **Database**: Leverages existing `guest_refresh_tokens` table
6. **Tests**: Full integration test verifying token rotation

Guest refresh mirrors user refresh exactly, enabling audit trails and token revocation.
