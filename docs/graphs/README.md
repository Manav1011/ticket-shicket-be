# Code Graphs Index
_Last updated: 2026-03-25_

Quick navigation to all codebase architecture graphs. Each graph shows different levels of detail for the Ticket Shicket backend.

## Available Graphs

| Graph | Description | Entry Point(s) | Depth | File |
|-------|-------------|-----------------|-------|------|
| [Overview](./overview.md) | Full backend architecture with all layers | cmd/server/main.go | 4 | [overview.md](./overview.md) |
| [User Feature](./user-feature.md) | User authentication flow (login, signup, refresh) | internal/user/handler | 3 | [user-feature.md](./user-feature.md) |
| [Guest Feature](./guest-feature.md) | Guest authentication flow (register, refresh) | internal/guest/handler | 3 | [guest-feature.md](./guest-feature.md) |

## Architecture Highlights

### Layered Design
- **Handler Layer**: HTTP request processing, validation, and response serialization
- **Service Layer**: Business logic, token generation, data transformation
- **Repository Layer**: Database access abstraction using sqlc
- **Middleware Layer**: CORS, authentication, RBAC

### Key Modules
- `internal/config/` — Configuration management
- `internal/db/` — Database connection and query generation
- `internal/user/` — User authentication and management
- `internal/guest/` — Guest (anonymous) user handling
- `internal/middleware/` — HTTP middleware (CORS, Auth, RBAC)
- `pkg/token/` — JWT token utilities
- `pkg/utils/` — Common response and utility functions

### Database Tables
- `users` — User credentials and metadata
- `guests` — Anonymous guest records (identified by UA + IP signature)
- `refresh_tokens` — User refresh tokens
- `guest_refresh_tokens` — Guest refresh tokens
- `roles` — User roles (from migrations)
- `permissions` — Permission definitions (from migrations)
- `user_roles` — User-Role many-to-many (from migrations)
- `role_permissions` — Role-Permission many-to-many (from migrations)

### Entry Points
1. **HTTP Server**: `cmd/server/main.go` — Gin web server on port 8080
2. **User Routes**: `POST /v1/users/login`, `POST /v1/users/signup`, `POST /v1/users/refresh`
3. **Guest Routes**: `POST /v1/guests/register`, `POST /v1/guests/refresh`
4. **Health**: `GET /v1/health`
5. **Swagger**: `GET /swagger/index.html`

## Legend

- 🚀 **Entry Point** — Application or feature entry
- 👤 **User Feature** — User-specific functionality
- 🧑 **Guest Feature** — Guest-specific functionality
- ⚙️ **Service Layer** — Business logic
- 💾 **Repository Layer** — Data access
- 📋 **Handler Layer** — HTTP handlers
- 💿 **Database** — Data persistence
- 📦 **Utilities** — Shared functions and helpers

## How to Use These Graphs

1. **Start with [Overview](./overview.md)** to understand the overall architecture
2. **Dive into [User Feature](./user-feature.md)** to understand authentication flow for registered users
3. **Explore [Guest Feature](./guest-feature.md)** to understand anonymous user handling
4. Use the cross-file call indicators (bold edges) to trace dependencies between modules
