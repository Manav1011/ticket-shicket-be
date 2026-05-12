# Modules & Files

## Apps

### `apps/user/` — User Authentication

| File | Role |
|------|------|
| `models.py` | `UserModel` with email/phone/password + tokens relationship |
| `repository.py` | `UserRepository` — find by email/phone/id, refresh token CRUD |
| `service.py` | `UserService` — login, signup, refresh, logout, token blocklist |
| `request.py` | `SignInRequest`, `SignUpRequest`, `GetUserByIdRequest` |
| `response.py` | `BaseUserResponse`, `UserLookupResponse` |
| `urls.py` | `/api/user` — sign-in, sign-up, refresh, logout, /self |
| `invite/` | Reseller invite system — `InviteService`, `InviteRepository` |

### `apps/guest/` — Anonymous Guests

| File | Role |
|------|------|
| `models.py` | `GuestModel` — device_id based, can be converted to User |
| `service.py` | `GuestService` — login, refresh, logout, convert-to-user |
| `urls.py` | `/api/guest` — device login, refresh, convert, logout |

Guests authenticate via `X-Device-ID` header. On login they get a UUID `device_id` from the client, which maps to a `GuestModel` record.

### `apps/event/` — Event Management

| File | Role |
|------|------|
| `models.py` | `EventModel`, `EventDayModel`, `EventMediaAssetModel`, `EventResellerModel`, `ScanStatusHistoryModel` |
| `repository.py` | `EventRepository` — event CRUD, day management, scan status, media |
| `service.py` | `EventService`, `PurchaseService` — publish flow, readiness, purchase |
| `urls.py` | `/api/events` — draft creation, day management, scan control, purchase |
| `public_urls.py` | Public-facing endpoints including `claim_router` |
| `request.py` | `CreateDraftEventRequest`, `CreateEventDayRequest`, `CreateOrderRequest` |
| `response.py` | `EventResponse`, `EventDayResponse`, `ResellerResponse`, purchase responses |

Publish readiness checks `setup_status` dict for: basic_info, ticket_types, allocations, media_assets.

Scan status transitions: `not_started → scanning → paused → ended` (each transition recorded in `ScanStatusHistoryModel`).

### `apps/organizer/` — Organizer Pages & B2B Operations

| File | Role |
|------|------|
| `models.py` | `OrganizerPageModel` |
| `repository.py` | `OrganizerRepository` — organizer CRUD |
| `service.py` | `OrganizerService` — B2B requests, transfers to reseller/customer, my-tickets |
| `urls.py` | `/api/organizers` — list/create/update organizers, B2B flows |
| `enums.py` | `OrganizerStatus`, `OrganizerVisibility` |

B2B flows:
- `create_b2b_request()` — organizer submits bulk ticket request
- `confirm_b2b_payment()` — organizer pays via Razorpay payment link
- `create_b2b_transfer()` — transfer tickets to reseller (free or paid)
- `create_customer_transfer()` — transfer to customer via phone/email with claim link
- `get_my_b2b_tickets()` — owned tickets grouped by event day

### `apps/ticketing/` — Ticket Inventory

| File | Role |
|------|------|
| `models.py` | `TicketTypeModel`, `DayTicketAllocationModel`, `TicketModel` |
| `repository.py` | `TicketingRepository` — ticket type/allocation CRUD, ticket locking |
| `service.py` | `TicketingService` — allocate ticket type to day, update quantities |
| `urls.py` | `/api/events/ticket-types`, `/api/events/ticket-allocations` |

`TicketModel` Individual ticket with seat metadata, `owner_holder_id`, and lock fields (`lock_reference_type`, `lock_reference_id`, `lock_expires_at`).

### `apps/allocation/` — Order & Transfer Graph

| File | Role |
|------|------|
| `models.py` | `OrderModel`, `TicketHolderModel`, `AllocationModel`, `AllocationEdgeModel`, `ClaimLinkModel`, `CouponModel` |
| `repository.py` | `AllocationRepository` — allocation CRUD, edges, claim links |
| `enums.py` | `OrderStatus`, `OrderType`, `AllocationStatus`, `AllocationType`, `GatewayType`, `ClaimLinkStatus` |

Key concept: every ticket allocation (purchase or transfer) creates an `OrderModel` (even $0 free transfers). `AllocationEdgeModel` tracks the ownership graph per event.

### `apps/payment_gateway/` — Razorpay Integration

| File | Role |
|------|------|
| `client.py` | Razorpay Python SDK wrapper |
| `models.py` | `PaymentGatewayEventModel` — webhook event log |
| `handlers/razorpay.py` | `RazorpayWebhookHandler` — idempotent webhook processor |
| `services/razorpay.py` | `RazorpayService` — create order, create payment link, cancel |
| `webhooks.py` | `/webhooks/razorpay` route |
| `repositories/order.py` | Order repo used by handler |

Two Razorpay modes:
- `RAZORPAY_ORDER` — online checkout (customer pays at checkout)
- `RAZORPAY_PAYMENT_LINK` — B2B payment link (organizer shares link)

### `apps/superadmin/` — B2B Approval Dashboard

| File | Role |
|------|------|
| `models.py` | `SuperAdminModel`, `B2BRequestModel` |
| `service.py` | `SuperAdminService` — approve/reject B2B requests, process allocations |
| `urls.py` | `/api/superadmin` — list/detail/approve-free/approve-paid/reject |

B2B request lifecycle: `pending → approved_free | approved_paid → payment_done → allocated | expired | rejected`

### `apps/core/` — Public Endpoints

Contains public event browsing and claim link redemption endpoints. The `claim_router` handles ticket claim flow at `/api/open/claim/{token}`.

### `apps/queues/` — NATS Workers

| File | Role |
|------|------|
| `clients/` | NATS client connections |
| `workers/` | Worker implementations (e.g., ticket expiry processing) |
| `urls.py` | Queue management routes |

### `apps/resellers/` — Reseller Endpoints

Reseller-specific endpoints for viewing allocated tickets and managing their inventory.

---

## Auth

| File | Role |
|------|------|
| `dependencies.py` | `get_current_user`, `get_current_guest`, `get_current_super_admin` |
| `jwt.py` | `access` and `refresh` JWT helpers (encode/decode) |
| `password.py` | `hash_password`, `verify_password` using bcrypt |
| `blocklist.py` | `TokenBlocklist` — Redis-backed revoked token JTIs |
| `permissions.py` | Role-based permission checks |
| `schemas.py` | Pydantic schemas for token payloads |

---

## DB

| File | Role |
|------|------|
| `session.py` | `engine`, `async_session`, `db_session` generator (commits on success, rolls back on exception) |
| `redis.py` | `redis` — async Redis connection |
| `base.py` | `Base`, `UUIDPrimaryKeyMixin`, `TimeStampMixin` |

---

## Utils

| File | Role |
|------|------|
| `s3_client.py` | Boto3 S3 client, presigned URL generation, file upload |
| `jwt_utils.py` | Additional JWT utilities |
| `notifications/sms.py` | Twilio SMS (mock in dev) |
| `notifications/whatsapp.py` | WhatsApp notifications (mock in dev) |
| `notifications/email.py` | Email notifications (mock in dev) |
| `claim_link_utils.py` | `generate_claim_link_token()` — random token generation |
| `file_validation.py` | Image type/size validation for uploads |
| `cookies.py` | `set_auth_cookies()` — set HTTP-only cookies on response |
| `scheduler.py` | APScheduler singleton instance |

---

## Jobs

| File | Role |
|------|------|
| `lock_cleanup.py` | Scheduled job — clear expired ticket locks |
| `__init__.py` | Registers `lock_cleanup` with the scheduler |

---

## Migrations

`src/migrations/` — Alembic migration scripts in `src/migrations/versions/`.

---

## Superadmin UI

`superadmin-ui/` — A standalone super admin dashboard (separate frontend).
