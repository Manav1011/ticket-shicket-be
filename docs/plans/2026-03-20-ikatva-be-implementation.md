# Ticket Shicket Backend Modular Structure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Scaffolding a modular Go backend using `gin`, `sqlc`, `pgx`, and `golang-migrate` with separate `user` and `auth` modules.

**Architecture:** A layered architecture (`handler` -> `service` -> `repository`) with centralized `sqlc` models in `internal/db/gen` and shared utilities in `pkg/`.

**Tech Stack:** Go 1.24+, Gin, PGX, SQLC, Golang-Migrate, Golang-JWT.

---

### Task 1: Scaffolding Directory Structure
**Files:**
- Create: `cmd/server/main.go`
- Create: `internal/db/db.go`
- Create: `internal/db/store.go`
- Create: `internal/user/handler/user_handler.go`
- Create: `internal/user/service/user_service.go`
- Create: `internal/user/repository/user_repository.go`
- Create: `internal/user/routes.go`
- Create: `internal/auth/handler/auth_handler.go`
- Create: `internal/auth/service/auth_service.go`
- Create: `internal/auth/routes.go`
- Create: `internal/middleware/auth.go`
- Create: `pkg/token/jwt.go`
- Create: `pkg/utils/hash.go`
- Create: `pkg/utils/response.go`
- Create: `migrations/000001_initial_schema.up.sql`
- Create: `sqlc.yaml`

**Step 1: Create all core directories**
Run: `mkdir -p cmd/server internal/db/gen internal/user/handler internal/user/service internal/user/repository internal/auth/handler internal/auth/service internal/middleware pkg/token pkg/utils migrations`

**Step 2: Commit scaffolding**
Run: `git add . && git commit -m "chore: scaffold modular project structure"`

### Task 2: Environment and Dependencies
**Files:**
- Modify: `go.mod`
- Create: `.env.example`

**Step 1: Install required dependencies**
Run: `go get github.com/gin-gonic/gin github.com/jackc/pgx/v5 github.com/jackc/pgx/v5/pgxpool github.com/golang-jwt/jwt/v5 golang.org/x/crypto/bcrypt github.com/joho/godotenv`

**Step 2: Create .env.example**
```env
DB_URL=postgres://user:password@localhost:5432/ticket_shicket_db?sslmode=disable
JWT_SECRET=super-secret-key
SERVER_PORT=8080
```

**Step 3: Commit dependencies**
Run: `git add go.mod go.sum .env.example && git commit -m "chore: add dependencies and env example"`

### Task 3: SQLC Configuration
**Files:**
- Create: `sqlc.yaml`

**Step 1: Define central SQLC config**
```yaml
version: "2"
sql:
  - schema: "migrations/"
    queries: "internal/"
    engine: "postgresql"
    gen:
      go:
        package: "db"
        out: "internal/db/gen"
        emit_json_tags: true
        emit_prepared_queries: false
        emit_interface: true
        emit_exact_table_names: false
```

**Step 2: Commit SQLC config**
Run: `git add sqlc.yaml && git commit -m "feat: add sqlc configuration"`

### Task 4: Server Entry Point
**Files:**
- Create: `cmd/server/main.go`

**Step 1: Basic Gin server scaffolding**
```go
package main

import (
	"log"
	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

func main() {
	if err := godotenv.Load(); err != nil {
		log.Println("No .env file found, using defaults")
	}

	r := gin.Default()
	
	// Add health check
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "ok"})
	})

	log.Println("Starting server on :8080")
	if err := r.Run(":8080"); err != nil {
		log.Fatal(err)
	}
}
```

**Step 2: Commit main.go**
Run: `git add cmd/server/main.go && git commit -m "feat: add server entry point with health check"`
