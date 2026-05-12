# Ticket Shicket — Event Ticketing Platform

> Event ticketing platform supporting online purchases, B2B bulk ticket operations, organizer management, ticket scanning, and reseller transfers.

## What is this?

Ticket Shicket is a full-featured event ticketing backend built with FastAPI. It handles the complete lifecycle of event management — creating events, selling tickets online, managing B2B bulk allocations, transferring tickets between organizers/resellers/customers, and enforcing ticket validity via QR scan at venues.

The system supports three primary user types:
- **Organizers** create events and manage ticket inventory
- **Resellers** are invited by organizers to sell tickets on their behalf
- **Customers** purchase or receive transferred tickets and claim them

A **Super Admin** panel handles B2B request approval and platform-wide oversight.

## Tech Stack

- **Framework**: FastAPI with async SQLAlchemy (asyncmy driver)
- **Database**: PostgreSQL ( Alembic migrations)
- **Cache/Rate Limiting**: Redis with fastapi-redis-cache and async limiter
- **Auth**: JWT access + refresh tokens with DB-backed rotation blocklist
- **Payments**: Razorpay (checkout orders and payment links)
- **Storage**: S3 (LocalStack in dev) for media assets
- **Task Scheduling**: APScheduler
- **Messaging**: NATS (structured job queues)

## Project Structure

```
src/
├── server.py              # FastAPI app factory + all route registrations
├── cli.py                 # Typer CLI: runserver, makemigrations, migrate, startapp
├── config.py              # Pydantic Settings (env vars, database URL assembly)
├── lifespan.py            # App lifespan (scheduler, Redis limiter init)
├── admin.py               # Starlette-Admin mount (optional)
├── handlers.py            # Exception handlers
├── exceptions.py          # Shared exception classes
├── apps/
│   ├── user/              # User auth: sign-up, login, refresh, logout
│   ├── guest/             # Guest (anonymous) login with device ID
│   ├── event/             # Event CRUD, publish flow, scan management, reseller invites
│   ├── organizer/         # Organizer pages, B2B requests/transfers, my-tickets
│   ├── ticketing/         # Ticket types, allocations, order creation
│   ├── allocation/        # Order model, allocation graph, coupons, claim links
│   ├── payment_gateway/   # Razorpay client, webhook handler
│   ├── queues/            # NATS workers (ticket expiry, etc.)
│   ├── resellers/        # Reseller-facing endpoints
│   ├── core/              # Public-facing endpoints (claim links, public event pages)
│   └── superadmin/        # B2B request approval dashboard
├── auth/                  # JWT utilities, password hashing, middleware, permissions
├── db/
│   ├── session.py         # asyncpg engine + session factory
│   ├── redis.py           # Redis connection
│   ├── base.py            # Base model, UUIDPrimaryKeyMixin, TimeStampMixin
│   └── model_registry.py  # Used by Alembic for autogenerate
├── jobs/                  # Scheduled jobs (lock cleanup)
├── migrations/           # Alembic migration scripts
└── utils/
    ├── jwt_utils.py, password.py, encryption.py, cookies.py
    ├── notifications/    # SMS (Twilio), WhatsApp, Email mock implementations
    ├── s3_client.py       # Boto3 S3 presigned URL utilities
    └── file_validation.py # Image upload validation
```

## Wiki Navigation

- [Architecture](./architecture.md)
- [Modules & Files](./modules.md)
- [API Reference](./api-reference.md)
- [Codebase Q&A Guide](./chat-guide.md)
