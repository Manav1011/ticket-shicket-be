# Ticket Shicket Backend Design - Modular Auth & User Architecture

## Overview
A modular Go backend using `gin`, `sqlc`, `pgx`, and `golang-migrate`. The architecture separates business logic into domain-driven modules while centralizing database models and shared utilities.

## Core Architecture
- **Layered Structure**: Each module follows a `handler` -> `service` -> `repository` pattern.
- **Internal Only**: Business logic is kept in `internal/` to prevent external imports.
- **Dependency Flow**: `Auth` module depends on `User` module for user data fetching and creation.

## Modular Strategy
- **Centralized SQLC**: A single root `sqlc.yaml` generates code into `internal/db/gen`. This avoids duplicate model types and type-casting across modules.
- **Shared DB Core**: `internal/db/db.go` initializes the `pgxpool.Pool` and provides a base `*db.Queries` instance.
- **Global Middleware**: JWT and Logging middleware live in `internal/middleware` to avoid circular dependencies (User/Auth modules don't import each other's handlers).

## Data Flow & Dependencies
1. **User Module**: Handles profile data, password hashing (stored in DB), and direct user CRUD.
2. **Auth Module**: Handles login (validates credentials via User module) and token generation (via `pkg/token`).
3. **Circular Prevention**: `User` will NEVER import `Auth`. If `User` needs to check permissions, it uses the context set by the Global Middleware.

## Implementation Details
- **Database**: PostgreSQL with `pgx` driver.
- **Migrations**: `golang-migrate` files stored in `/migrations`.
- **Authentication**: JWT-based using `golang-jwt`.
- **Environment**: `.env` for variables (DB URI, JWT Secret).

## Repository Structure
```text
cmd/
  server/
    main.go
internal/
  auth/
    handler/
    service/
    routes.go
  user/
    handler/
    service/
    repository/
    routes.go
  db/
    gen/ (sqlc output)
    db.go
    store.go
  middleware/
    auth.go
    logging.go
pkg/
  token/
    jwt.go
  utils/
    hash.go
    response.go
migrations/
  000001_initial_schema.up.sql
sqlc.yaml
```
