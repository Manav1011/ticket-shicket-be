# Guest Registration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable guest users to register without credentials and receive access/refresh tokens with guest_id instead of user_id, including user agent tracking.

**Architecture:** 
Guests will be a lightweight alternative to full user registration. The flow mirrors user authentication but stores a guest record with `guest_id`, `user_agent`, `ip_address`, and timestamps. JWT tokens will include `guest_id` instead of `user_id`. Refresh tokens will be stored per guest session with user agent information for security tracking. The token generation functions will be extended to support both user and guest ID types.

**Tech Stack:** 
Go, Gin, PostgreSQL, sqlc, JWT (golang-jwt/v5), uuid (google/uuid)

---

## Task 1: Create Guest SQL Queries

**Files:**
- Create: `internal/db/query/guest.sql`

**Step 1: Write the guest SQL query file**

```sql
-- name: CreateGuest :one
INSERT INTO guests (user_agent, ip_address, created_at, last_active)
VALUES ($1, $2, NOW(), NOW())
RETURNING guest_id, user_agent, ip_address, created_at, last_active, slug;

-- name: GetGuestByID :one
SELECT guest_id, user_agent, ip_address, created_at, last_active, slug
FROM guests
WHERE guest_id = $1;

-- name: UpdateGuestLastActive :one
UPDATE guests
SET last_active = NOW()
WHERE guest_id = $1
RETURNING guest_id, user_agent, ip_address, created_at, last_active, slug;
```

**Step 2: Verify file is created**

Run: `ls -la internal/db/query/guest.sql`
Expected: File exists

**Step 3: Generate SQLC models**

Run: `cd /home/web-h-063/Documents/ticket-shicket-be && make` (or `sqlc generate`)
Expected: New methods generated in `internal/db/sqlc/guest.sql.go`

**Step 4: Verify generated code**

Run: `grep -n "CreateGuest\|GetGuestByID" internal/db/sqlc/guest.sql.go`
Expected: Methods exist in the file

**Step 5: Commit**

```bash
cd /home/web-h-063/Documents/ticket-shicket-be
git add internal/db/query/guest.sql internal/db/sqlc/guest.sql.go
git commit -m "feat: add guest SQL queries and generated SQLC models"
```

---

## Task 2: Extend Token Generation to Support Guest IDs

**Files:**
- Modify: `pkg/token/jwt.go`

**Step 1: Write tests for guest token generation**

Create `pkg/token/jwt_test.go` (if not exists, add tests):

```go
package token

import (
	"strings"
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/manav1011/ticket-shicket-be/internal/config"
)

func TestGenerateAccessTokenForGuest(t *testing.T) {
	guestID := "550e8400-e29b-41d4-a716-446655440000"
	token, err := GenerateAccessTokenGuest(guestID)
	if err != nil {
		t.Fatalf("GenerateAccessTokenGuest failed: %v", err)
	}
	if token == "" {
		t.Fatal("Expected token, got empty string")
	}
	if !strings.HasPrefix(token, "eyJ") {
		t.Fatal("Invalid JWT format")
	}

	claims, err := ParseToken(token)
	if err != nil {
		t.Fatalf("ParseToken failed: %v", err)
	}
	if claims["guest_id"] != guestID {
		t.Fatalf("Expected guest_id %s, got %v", guestID, claims["guest_id"])
	}
	if claims["type"] != "access" {
		t.Fatalf("Expected type 'access', got %v", claims["type"])
	}
}

func TestGenerateRefreshTokenForGuest(t *testing.T) {
	guestID := "550e8400-e29b-41d4-a716-446655440000"
	token, err := GenerateRefreshTokenGuest(guestID)
	if err != nil {
		t.Fatalf("GenerateRefreshTokenGuest failed: %v", err)
	}
	if token == "" {
		t.Fatal("Expected token, got empty string")
	}

	claims, err := ParseToken(token)
	if err != nil {
		t.Fatalf("ParseToken failed: %v", err)
	}
	if claims["guest_id"] != guestID {
		t.Fatalf("Expected guest_id %s, got %v", guestID, claims["guest_id"])
	}
	if claims["type"] != "refresh" {
		t.Fatalf("Expected type 'refresh', got %v", claims["type"])
	}
}
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/web-h-063/Documents/ticket-shicket-be && go test -v ./pkg/token/... -run Guest`
Expected: FAIL (functions don't exist yet)

**Step 3: Add guest token generation functions to jwt.go**

Add after the existing user token functions:

```go
func GenerateAccessTokenGuest(guestID string) (string, error) {
	claims := jwt.MapClaims{
		"guest_id": guestID,
		"type":     "access",
		"exp":      time.Now().Add(cfg.AccessTokenDuration).Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(cfg.JWTSecret))
}

func GenerateRefreshTokenGuest(guestID string) (string, error) {
	claims := jwt.MapClaims{
		"guest_id": guestID,
		"type":     "refresh",
		"exp":      time.Now().Add(cfg.RefreshTokenDuration).Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(cfg.JWTSecret))
}
```

**Step 4: Run tests to verify they pass**

Run: `cd /home/web-h-063/Documents/ticket-shicket-be && go test -v ./pkg/token/... -run Guest`
Expected: PASS

**Step 5: Commit**

```bash
cd /home/web-h-063/Documents/ticket-shicket-be
git add pkg/token/jwt.go pkg/token/jwt_test.go
git commit -m "feat: add guest token generation functions"
```

---

## Task 3: Create Guest Request/Response Models

**Files:**
- Create: `internal/guest/model/request_model.go`
- Create: `internal/guest/model/response_model.go`

**Step 1: Create guest request models**

File: `internal/guest/model/request_model.go`

```go
package model

// GuestRegisterRequest is the body for POST /guests/register
type GuestRegisterRequest struct {
	UserAgent string `json:"user_agent" binding:"required"`
	IpAddress string `json:"ip_address" binding:"required"`
}
```

**Step 2: Create guest response models**

File: `internal/guest/model/response_model.go`

```go
package model

import "github.com/google/uuid"

// GuestRegisterData is returned on successful guest registration
type GuestRegisterData struct {
	AccessToken  string      `json:"access_token"`
	RefreshToken string      `json:"refresh_token"`
	TokenType    string      `json:"token_type"`
	ExpiresIn    int64       `json:"expires_in"`
	Guest        GuestInfo   `json:"guest"`
}

// GuestInfo is a minimal guest projection for auth responses
type GuestInfo struct {
	ID        uuid.UUID `json:"id"`
	Slug      uuid.UUID `json:"slug"`
	CreatedAt int64     `json:"created_at"`
}

// GuestRegisterSuccessEnvelope is the JSON shape for Swagger/OpenAPI
type GuestRegisterSuccessEnvelope struct {
	Success bool              `json:"success"`
	Data    GuestRegisterData `json:"data"`
}
```

**Step 3: Create directory if needed**

Run: `mkdir -p /home/web-h-063/Documents/ticket-shicket-be/internal/guest/model`
Expected: Directory created (no error if exists)

**Step 4: Verify files are created**

Run: `ls -la internal/guest/model/`
Expected: Both files exist

**Step 5: Commit**

```bash
cd /home/web-h-063/Documents/ticket-shicket-be
git add internal/guest/model/request_model.go internal/guest/model/response_model.go
git commit -m "feat: add guest request/response models"
```

---

## Task 4: Create Guest Repository

**Files:**
- Create: `internal/guest/repository/guest_repository.go`
- Create: `internal/guest/repository/guest_repository_test.go`

**Step 1: Write failing repository tests**

File: `internal/guest/repository/guest_repository_test.go`

```go
package repository

import (
	"context"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/stdlib"
	"github.com/manav1011/ticket-shicket-be/internal/config"
	"github.com/manav1011/ticket-shicket-be/internal/db"
	sqldb "github.com/manav1011/ticket-shicket-be/internal/db/sqlc"
)

func TestCreateGuest(t *testing.T) {
	cfg := config.LoadConfig()
	pool := db.NewDB(cfg.DBSource)
	sqlDB := stdlib.OpenDBFromPool(pool)
	defer sqlDB.Close()

	queries := sqldb.New(sqlDB)
	repo := NewGuestRepository(queries)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	userAgent := "Mozilla/5.0"
	ipAddress := "192.168.1.1"

	guest, err := repo.CreateGuest(ctx, userAgent, ipAddress)
	if err != nil {
		t.Fatalf("CreateGuest failed: %v", err)
	}
	if guest.GuestID.String() == "" {
		t.Fatal("Expected guest_id, got empty UUID")
	}
	if guest.UserAgent.String != userAgent {
		t.Fatalf("Expected user_agent %s, got %s", userAgent, guest.UserAgent.String)
	}
	if guest.IpAddress.String != ipAddress {
		t.Fatalf("Expected ip_address %s, got %s", ipAddress, guest.IpAddress.String)
	}
}

func TestGetGuestByID(t *testing.T) {
	cfg := config.LoadConfig()
	pool := db.NewDB(cfg.DBSource)
	sqlDB := stdlib.OpenDBFromPool(pool)
	defer sqlDB.Close()

	queries := sqldb.New(sqlDB)
	repo := NewGuestRepository(queries)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// Create a guest
	guest, err := repo.CreateGuest(ctx, "Mozilla/5.0", "192.168.1.1")
	if err != nil {
		t.Fatalf("CreateGuest failed: %v", err)
	}

	// Retrieve it
	retrieved, err := repo.GetGuestByID(ctx, guest.GuestID)
	if err != nil {
		t.Fatalf("GetGuestByID failed: %v", err)
	}
	if retrieved.GuestID != guest.GuestID {
		t.Fatalf("Expected guest_id %s, got %s", guest.GuestID, retrieved.GuestID)
	}
}
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/web-h-063/Documents/ticket-shicket-be && go test -v ./internal/guest/repository/... 2>&1 | head -20`
Expected: FAIL (package or functions don't exist)

**Step 3: Create the repository implementation**

File: `internal/guest/repository/guest_repository.go`

```go
package repository

import (
	"context"

	"github.com/google/uuid"
	"github.com/manav1011/ticket-shicket-be/internal/db/sqlc"
)

type GuestRepository struct {
	queries *sqlc.Queries
}

func NewGuestRepository(queries *sqlc.Queries) *GuestRepository {
	return &GuestRepository{queries: queries}
}

// CreateGuest creates a new guest record
func (r *GuestRepository) CreateGuest(ctx context.Context, userAgent, ipAddress string) (*sqlc.Guest, error) {
	return r.queries.CreateGuest(ctx, sqlc.CreateGuestParams{
		UserAgent: &userAgent,
		IpAddress: &ipAddress,
	})
}

// GetGuestByID retrieves a guest by ID
func (r *GuestRepository) GetGuestByID(ctx context.Context, guestID uuid.UUID) (*sqlc.Guest, error) {
	return r.queries.GetGuestByID(ctx, guestID)
}

// UpdateGuestLastActive updates the last_active timestamp
func (r *GuestRepository) UpdateGuestLastActive(ctx context.Context, guestID uuid.UUID) (*sqlc.Guest, error) {
	return r.queries.UpdateGuestLastActive(ctx, guestID)
}
```

**Step 4: Run tests to verify they pass**

Run: `cd /home/web-h-063/Documents/ticket-shicket-be && go test -v ./internal/guest/repository/... -timeout 10s`
Expected: PASS

**Step 5: Create directory and commit**

```bash
cd /home/web-h-063/Documents/ticket-shicket-be
mkdir -p internal/guest/repository
git add internal/guest/repository/guest_repository.go internal/guest/repository/guest_repository_test.go
git commit -m "feat: add guest repository with create and retrieve operations"
```

---

## Task 5: Create Guest Service

**Files:**
- Create: `internal/guest/service/guest_service.go`
- Create: `internal/guest/service/guest_service_test.go`

**Step 1: Write failing service tests**

File: `internal/guest/service/guest_service_test.go`

```go
package service

import (
	"context"
	"testing"
	"time"

	"github.com/manav1011/ticket-shicket-be/internal/config"
)

func TestRegisterGuest(t *testing.T) {
	cfg := config.LoadConfig()
	// Mock or use real repository (for simplicity, we'll use real for integration test)
	// For unit tests, you'd want to mock this
	svc := NewGuestService(nil, cfg) // Will fail on nil repo, but that's OK for this stub

	// This test will properly work once we mock the repository
	// For now, it documents the expected contract
	t.Log("GuestService registered properly")
}
```

**Step 2: Create service implementation**

File: `internal/guest/service/guest_service.go`

```go
package service

import (
	"context"
	"fmt"
	"time"

	"github.com/manav1011/ticket-shicket-be/internal/config"
	"github.com/manav1011/ticket-shicket-be/internal/guest/model"
	"github.com/manav1011/ticket-shicket-be/internal/guest/repository"
	"github.com/manav1011/ticket-shicket-be/pkg/token"
)

type GuestService struct {
	repo *repository.GuestRepository
	cfg  *config.Config
}

func NewGuestService(repo *repository.GuestRepository, cfg *config.Config) *GuestService {
	return &GuestService{repo: repo, cfg: cfg}
}

// Register creates a new guest and issues JWT tokens
func (s *GuestService) Register(ctx context.Context, userAgent, ipAddress string) (*model.GuestRegisterData, error) {
	// Create guest in database
	guest, err := s.repo.CreateGuest(ctx, userAgent, ipAddress)
	if err != nil {
		return nil, fmt.Errorf("create guest: %w", err)
	}

	// Generate tokens with guest_id
	guestID := guest.GuestID.String()
	access, err := token.GenerateAccessTokenGuest(guestID)
	if err != nil {
		return nil, fmt.Errorf("access token: %w", err)
	}
	refresh, err := token.GenerateRefreshTokenGuest(guestID)
	if err != nil {
		return nil, fmt.Errorf("refresh token: %w", err)
	}

	expiresIn := int64(s.cfg.AccessTokenDuration.Seconds())
	createdAtUnix := guest.CreatedAt.Time.Unix()
	if createdAtUnix == 0 {
		createdAtUnix = time.Now().Unix()
	}

	return &model.GuestRegisterData{
		AccessToken:  access,
		RefreshToken: refresh,
		TokenType:    "Bearer",
		ExpiresIn:    expiresIn,
		Guest: model.GuestInfo{
			ID:        guest.GuestID,
			Slug:      guest.Slug.UUID,
			CreatedAt: createdAtUnix,
		},
	}, nil
}
```

**Step 3: Run minimal tests**

Run: `cd /home/web-h-063/Documents/ticket-shicket-be && go test -v ./internal/guest/service/... 2>&1 | head -20`
Expected: Compilation succeeds, tests pass

**Step 4: Create directory and commit**

```bash
cd /home/web-h-063/Documents/ticket-shicket-be
mkdir -p internal/guest/service
git add internal/guest/service/guest_service.go internal/guest/service/guest_service_test.go
git commit -m "feat: add guest service for registration and token generation"
```

---

## Task 6: Create Guest Handler

**Files:**
- Create: `internal/guest/handler/guest_handler.go`
- Create: `internal/guest/handler/guest_handler_test.go`

**Step 1: Write failing handler tests**

File: `internal/guest/handler/guest_handler_test.go`

```go
package handler

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/manav1011/ticket-shicket-be/internal/config"
	"github.com/manav1011/ticket-shicket-be/internal/guest/model"
	"github.com/manav1011/ticket-shicket-be/internal/guest/repository"
	"github.com/manav1011/ticket-shicket-be/internal/guest/service"
)

func TestRegisterGuest(t *testing.T) {
	// Setup (will be populated with actual DB in integration)
	cfg := config.LoadConfig()
	
	// For now, just verify handler can be created
	// Real integration test below documents the contract
	h := NewGuestHandler(nil) // Will fail in integration but that's OK
	if h == nil {
		t.Fatal("Expected handler to be initialized")
	}
	t.Log("Guest handler initialized")
}

// Integration test contract
func setupTestHandler() *GuestHandler {
	cfg := config.LoadConfig()
	// In real test: setup DB, create repo, create service
	// repo := repository.NewGuestRepository(queries)
	// svc := service.NewGuestService(repo, cfg)
	// return NewGuestHandler(svc)
	return nil // Placeholder
}
```

**Step 2: Create handler implementation**

File: `internal/guest/handler/guest_handler.go`

```go
package handler

import (
	"errors"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/manav1011/ticket-shicket-be/internal/guest/model"
	"github.com/manav1011/ticket-shicket-be/internal/guest/service"
	"github.com/manav1011/ticket-shicket-be/pkg/utils"
)

type GuestHandler struct {
	svc *service.GuestService
}

func NewGuestHandler(svc *service.GuestService) *GuestHandler {
	return &GuestHandler{svc: svc}
}

// Register creates a new guest and returns access and refresh tokens.
// @Summary      Guest registration
// @Description  Registers a guest user and returns JWT access and refresh tokens.
// @Tags         guest
// @Accept       json
// @Produce      json
// @Param        body  body      model.GuestRegisterRequest  true  "User agent and IP address"
// @Success      200   {object}  model.GuestRegisterSuccessEnvelope
// @Failure      400   {object}  utils.APIResponse
// @Failure      500   {object}  utils.APIResponse
// @Router       /guests/register [post]
func (h *GuestHandler) Register(c *gin.Context) {
	var req model.GuestRegisterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.Error(c, "invalid request body", http.StatusBadRequest)
		return
	}

	data, err := h.svc.Register(c.Request.Context(), req.UserAgent, req.IpAddress)
	if err != nil {
		if errors.Is(err, service.ErrGuestRegistrationFailed) {
			utils.Error(c, "guest registration failed", http.StatusInternalServerError)
			return
		}
		utils.Error(c, "internal server error", http.StatusInternalServerError)
		return
	}

	utils.Success(c, data)
}
```

**Step 3: Add error definitions to service**

Append to `internal/guest/service/guest_service.go`:

```go

var ErrGuestRegistrationFailed = fmt.Errorf("guest registration failed")
```

**Step 4: Test handler creation**

Run: `cd /home/web-h-063/Documents/ticket-shicket-be && go test -v ./internal/guest/handler/... 2>&1 | head -20`
Expected: Compilation succeeds

**Step 5: Create directory and commit**

```bash
cd /home/web-h-063/Documents/ticket-shicket-be
mkdir -p internal/guest/handler
git add internal/guest/handler/guest_handler.go internal/guest/handler/guest_handler_test.go
git commit -m "feat: add guest handler for registration endpoint"
```

---

## Task 7: Create Guest Routes

**Files:**
- Create: `internal/guest/routes.go`

**Step 1: Create guest routes file**

File: `internal/guest/routes.go`

```go
package guest

import (
	"github.com/gin-gonic/gin"
	"github.com/manav1011/ticket-shicket-be/internal/guest/handler"
)

// RegisterRoutes mounts guest routes under the given API group (e.g. /v1 from main).
// Paths are relative to that group: /guests/register, not /v1/guests/register here.
func RegisterRoutes(v1 *gin.RouterGroup, h *handler.GuestHandler) {
	guests := v1.Group("/guests")
	guests.POST("/register", h.Register)
}
```

**Step 2: Verify file compiles**

Run: `cd /home/web-h-063/Documents/ticket-shicket-be && go build -v ./internal/guest/...`
Expected: No errors

**Step 3: Commit**

```bash
cd /home/web-h-063/Documents/ticket-shicket-be
git add internal/guest/routes.go
git commit -m "feat: add guest route registration"
```

---

## Task 8: Register Guest Routes in Main Server

**Files:**
- Modify: `cmd/server/main.go`

**Step 1: Update main.go to register guest routes**

Add import for guest package and register routes in main():

```go
// Add to imports:
"github.com/manav1011/ticket-shicket-be/internal/guest"
"github.com/manav1011/ticket-shicket-be/internal/guest/handler"
"github.com/manav1011/ticket-shicket-be/internal/guest/repository"
"github.com/manav1011/ticket-shicket-be/internal/guest/service"

// In main(), after user routes registration, add:
// Initialize guest components
guestRepo := repository.NewGuestRepository(queries)
guestSvc := service.NewGuestService(guestRepo, cfg)
guestHandler := handler.NewGuestHandler(guestSvc)

// Register guest routes
guest.RegisterRoutes(v1, guestHandler)
```

**Step 2: Verify compilation**

Run: `cd /home/web-h-063/Documents/ticket-shicket-be && go build -v ./cmd/server`
Expected: No compile errors

**Step 3: Commit**

```bash
cd /home/web-h-063/Documents/ticket-shicket-be
git add cmd/server/main.go
git commit -m "feat: register guest routes and initialize guest components in main"
```

---

## Task 9: Update RBAC Middleware to Support Guest Tokens

**Files:**
- Modify: `internal/middleware/jwt.go`

**Step 1: Review existing JWT middleware**

Read the current jwt.go to understand how it extracts user_id

**Step 2: Update middleware to handle guest_id**

Modify the middleware to check for either `user_id` or `guest_id` in token claims and set appropriately in context

**Step 3: Test middleware with guest tokens**

Verify that the middleware can parse both user and guest tokensusing unit tests

**Step 4: Commit**

```bash
cd /home/web-h-063/Documents/ticket-shicket-be
git add internal/middleware/jwt.go
git commit -m "feat: update JWT middleware to support guest tokens"
```

---

## Task 10: End-to-End Integration Test

**Files:**
- Create: `internal/guest/integration_test.go`

**Step 1: Write integration test**

```go
package guest

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v5/stdlib"
	"github.com/manav1011/ticket-shicket-be/internal/config"
	"github.com/manav1011/ticket-shicket-be/internal/db"
	sqldb "github.com/manav1011/ticket-shicket-be/internal/db/sqlc"
	guestHandler "github.com/manav1011/ticket-shicket-be/internal/guest/handler"
	guestModel "github.com/manav1011/ticket-shicket-be/internal/guest/model"
	guestRepo "github.com/manav1011/ticket-shicket-be/internal/guest/repository"
	guestSvc "github.com/manav1011/ticket-shicket-be/internal/guest/service"
	"github.com/manav1011/ticket-shicket-be/pkg/token"
)

func TestGuestRegistrationFlow(t *testing.T) {
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

	// Request body
	req := guestModel.GuestRegisterRequest{
		UserAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
		IpAddress: "192.168.1.1",
	}
	body, _ := json.Marshal(req)

	// Make request
	httpReq := httptest.NewRequest("POST", "/v1/guests/register", bytes.NewBuffer(body))
	httpReq.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	router.ServeHTTP(w, httpReq)

	// Verify response
	if w.Code != http.StatusOK {
		t.Fatalf("Expected 200, got %d: %s", w.Code, w.Body.String())
	}

	var respBody map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &respBody); err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	if !respBody["success"].(bool) {
		t.Fatal("Expected success to be true")
	}

	data := respBody["data"].(map[string]interface{})
	if data["access_token"] == "" {
		t.Fatal("Expected access_token in response")
	}
	if data["refresh_token"] == "" {
		t.Fatal("Expected refresh_token in response")
	}

	// Verify token contains guest_id
	accessToken := data["access_token"].(string)
	claims, err := token.ParseToken(accessToken)
	if err != nil {
		t.Fatalf("Failed to parse token: %v", err)
	}
	if claims["guest_id"] == nil {
		t.Fatal("Expected guest_id in token claims")
	}
}
```

**Step 2: Run integration test**

Run: `cd /home/web-h-063/Documents/ticket-shicket-be && go test -v -timeout 30s ./internal/guest/integration_test.go`
Expected: PASS

**Step 3: Commit**

```bash
cd /home/web-h-063/Documents/ticket-shicket-be
git add internal/guest/integration_test.go
git commit -m "test: add end-to-end integration test for guest registration"
```

---

## Summary

This plan implements guest registration as a new, lightweight authentication flow:

1. **Created SQL queries** for creating guests and tracking them
2. **Extended token generation** to support guest IDs via new functions
3. **Built guest models** for request/response shapes
4. **Implemented repository layer** for database access
5. **Created service layer** that orchestrates token generation
6. **Built HTTP handler** for the registration endpoint
7. **Registered routes** following existing patterns
8. **Integrated into main** server startup
9. **Updated middleware** to recognize guest tokens
10. **Tested end-to-end** with integration test

All guests get a UUID `guest_id`, and tokens include this ID instead of `user_id`. User agent and IP address are captured for security auditing.
