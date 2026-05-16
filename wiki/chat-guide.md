# Codebase Q&A Guide

## Q: How does authentication work?

Authentication uses short-lived JWT **access tokens** (1 hour) and longer-lived **refresh tokens** (24 hours). On `/api/user/sign-in`, the service validates credentials, creates both tokens, stores the refresh token hash in the DB, and sets them as HTTP-only cookies via `set_auth_cookies()`. On `/api/user/refresh`, the refresh token is validated, rotated (old revoked, new issued).

Guests (`/api/guest/login`) use a `X-Device-ID` header (UUID generated client-side) and get a guest-specific JWT with `user_type=guest`. They can later convert to a full user account.

Token revocation uses a Redis blocklist (`TokenBlocklist`) keyed by `jti` — any token whose `jti` is in the blocklist is rejected. Refresh tokens are also stored hashed in the DB for rotation and revocation.

Source: [auth/jwt.py](src/auth/jwt.py), [auth/dependencies.py](src/auth/dependencies.py), [apps/user/urls.py](src/apps/user/urls.py)

---

## Q: How does a customer buy tickets online?

1. Customer calls `POST /api/events/purchase/preview` to validate price (applies coupon if any)
2. Customer calls `POST /api/events/purchase/create` → `PurchaseService.create_order()`:
   - Locks tickets via `TicketingRepository.lock_tickets()`
   - Creates `OrderModel` with `gateway_type=RAZORPAY_ORDER`
   - Calls Razorpay to create a checkout order
   - Returns order ID + Razorpay `gateway_order_id`
3. Customer pays via Razorpay checkout
4. Razorpay sends `order.paid` webhook to `POST /webhooks/razorpay`
5. `RazorpayWebhookHandler.handle_order_paid()`:
   - Idempotency via `PaymentGatewayEventModel` unique constraint on `gateway_payment_id`
   - Atomic `UPDATE ... WHERE status=pending` prevents double-processing
   - Creates `AllocationModel` (pool → buyer) and `ClaimLinkModel`
   - Transfers ticket `owner_holder_id` to buyer's `TicketHolderModel`
   - Sends claim link via SMS/WhatsApp/Email

Source: [apps/event/urls.py](src/apps/event/urls.py) (purchase endpoints), [apps/payment_gateway/handlers/razorpay.py](src/apps/payment_gateway/handlers/razorpay.py)

---

## Q: How do B2B requests work?

1. **Request**: Organizer calls `POST /api/organizers/b2b/events/{event_id}/requests` → creates `B2BRequestModel` with `status=pending`
2. **Review**: Super admin views pending requests at `GET /api/superadmin/b2b/requests/pending`
3. **Approval**: Super admin approves via:
   - `POST /api/superadmin/b2b/requests/{id}/approve-free` → creates `$0 TRANSFER` order + allocation immediately
   - `POST /api/superadmin/b2b/requests/{id}/approve-paid` → sets amount, creates pending `PURCHASE` order
4. **Payment** (paid mode): Organizer calls `POST /api/organizers/b2b/events/{event_id}/requests/{id}/confirm-payment` → creates Razorpay payment link
5. **Fulfillment**: `payment_link.paid` webhook triggers `SuperAdminService.process_paid_b2b_allocation()` → creates allocation

Source: [apps/organizer/urls.py](src/apps/organizer/urls.py), [apps/superadmin/urls.py](src/apps/superadmin/urls.py), [apps/superadmin/service.py](src/apps/superadmin/service.py)

---

## Q: How do B2B ticket transfers to resellers and customers work?

Organizer calls `POST /api/organizers/b2b/events/{event_id}/transfers/reseller` or `.../transfers/customer`:

- **Free mode**: Immediately locks tickets, creates `$0 TRANSFER` order, creates allocation (reseller) or allocation + claim link (customer)
- **Paid mode**: Creates `RAZORPAY_PAYMENT_LINK` order + payment link; webhook completes transfer

For reseller transfers, no claim link is created (they have an account). For customer transfers, a claim link is generated and sent via notification so they can claim ownership of the tickets.

Source: [apps/organizer/service.py](src/apps/organizer/service.py), [apps/payment_gateway/handlers/razorpay.py](src/apps/payment_gateway/handlers/razorpay.py)

---

## Q: Where is the database connection configured?

`src/db/session.py` — `create_async_engine()` is called with `DATABASE_URL` from settings, configured with:
- `pool_size=10`, `max_overflow=20`, `pool_recycle=3600`, `pool_pre_ping=True`
- `async_sessionmaker(engine, expire_on_commit=False)`
- `db_session()` generator yields the session, auto-commits on success, rolls back on exception

The `engine` is disposed gracefully on app shutdown in `lifespan.py`.

Source: [src/db/session.py](src/db/session.py), [src/lifespan.py](src/lifespan.py)

---

## Q: How do I add a new API endpoint?

1. Create/update files in the appropriate `apps/<module>/` directory:
   - `models.py` — SQLAlchemy model
   - `repository.py` — DB operations
   - `service.py` — business logic
   - `request.py` — Pydantic input schema (extend `CamelCaseModel`)
   - `response.py` — Pydantic output schema (extend `BaseResponse`)
   - `urls.py` — FastAPI router with `Depends()` injection
2. Import the router in `src/server.py` and add to `base_router`
3. Add any new enums to `apps/<module>/enums.py`

The project uses `startapp` CLI command to generate the file skeleton.

Source: [src/cli.py](src/cli.py), [src/server.py](src/server.py)

---

## Q: How does ticket scanning work?

Event days have a `ScanStatus` state machine: `not_started → scanning → paused → scanning → ended`. The state transitions are:

- `start_scan`: sets `scan_status=scanning`, `scan_started_at`
- `pause_scan`: sets `scan_status=paused`, `scan_paused_at`
- `resume_scan`: back to `scanning`
- `end_scan`: sets `scan_status=ended`, `scan_ended_at`

Each transition creates a `ScanStatusHistoryModel` record for audit. Scan endpoints are in `apps/event/urls.py` at `/api/events/days/{event_day_id}/start-scan|pause-scan|resume-scan|end-scan`.

Source: [apps/event/urls.py](src/apps/event/urls.py), [apps/event/models.py](src/apps/event/models.py)

---

## Q: How are tickets locked during a purchase?

Before payment, tickets are locked via `TicketingRepository.lock_tickets()`:
- Sets `TicketModel.lock_reference_type = 'order'` (or `'transfer'`)
- Sets `TicketModel.lock_reference_id = order.id`
- Sets `TicketModel.lock_expires_at` to ~15 minutes

If payment fails or expires, `TicketingRepository.clear_locks_for_order()` removes the lock fields. The `LockCleanup` scheduled job also periodically clears expired locks.

Source: [apps/ticketing/repository.py](src/apps/ticketing/repository.py), [src/jobs/lock_cleanup.py](src/jobs/lock_cleanup.py)

---

## Q: How do I run database migrations?

```bash
# Detect changes and create migration
uv run main.py makemigrations -m "description"

# Apply pending migrations
uv run main.py migrate

# Show migration status
uv run main.py showmigrations

# Rollback last migration
uv run main.py rollback
```

Migrations are in `src/migrations/versions/` managed by Alembic.

Source: [src/cli.py](src/cli.py), [alembic.ini](alembic.ini)

---

## Q: How does the allocation/ticket ownership graph work?

Every ticket allocation (purchase, B2B transfer, gift) creates:
1. An `OrderModel` (even $0 free transfers have a `$0 TRANSFER` order)
2. An `AllocationModel` linking `from_holder_id` → `to_holder_id`
3. An `AllocationEdgeModel` upsert (per event) tracking aggregate ticket counts between holders
4. `TicketModel.owner_holder_id` is updated to the new owner

The edge table allows querying "how many tickets does holder X have for event Y?" by summing edges.

Source: [apps/allocation/models.py](src/apps/allocation/models.py), [apps/allocation/repository.py](src/apps/allocation/repository.py)

---

## Q: How are Razorpay webhooks handled?

`POST /webhooks/razorpay` → `RazorpayWebhookHandler.handle()`:
1. Verifies signature via `gateway.verify_webhook_signature()`
2. Parses event to `WebhookEvent` schema
3. Routes by event type:
   - `order.paid` → `handle_order_paid()` (online checkout)
   - `payment_link.paid` → `handle_order_paid()` (B2B payment link)
   - `payment.failed` → `handle_payment_failed()`
   - `payment_link.expired` / `payment_link.cancelled` → handlers that clear locks
4. Idempotency: `PaymentGatewayEventModel` unique constraint on `gateway_payment_id` + atomic pending-status UPDATE

Source: [apps/payment_gateway/webhooks.py](src/apps/payment_gateway/webhooks.py), [apps/payment_gateway/handlers/razorpay.py](src/apps/payment_gateway/handlers/razorpay.py)

---

## Q: How does the claim link flow work?

1. On B2B transfer to a customer, `generate_claim_link_token(length=8)` creates a random token
2. A `ClaimLinkModel` is created with the token hash + `to_holder_id`
3. The raw token is sent to the customer via SMS/WhatsApp/Email
4. Customer opens `GET /api/open/claim/{token}` (`apps/core/urls.py` / `claim_router`)
5. The endpoint validates the token hash, finds matching tickets, and returns ticket details + QR

The claim link proves the recipient was explicitly transferred tickets and allows them to take ownership.

Source: [apps/core/urls.py](src/apps/core/urls.py), [apps/allocation/models.py](src/apps/allocation/models.py), [utils/claim_link_utils.py](src/utils/claim_link_utils.py)

---

## Q: How do I add a new scheduled job?

1. Create a module in `src/jobs/` (e.g., `my_job.py`)
2. Define an async function `run()` in that module
3. Import and register in `src/jobs/__init__.py`:
   ```python
   from .my_job import run as my_job_run
   scheduler.add_job(my_job_run, "interval", seconds=30, id="my_job")
   ```
4. The scheduler is started in `lifespan.py` on app startup and shut down on graceful shutdown.

Source: [src/jobs/__init__.py](src/jobs/__init__.py), [src/lifespan.py](src/lifespan.py)

---

## Q: How does rate limiting work?

`fastapi-limiter` is initialized in `lifespan.py` with Redis: `await FastAPILimiter.init(redis)`. Endpoints use `@limiter.limit("5/minute")` decorator from `fastapi_limiter.depends`.

Source: [src/lifespan.py](src/lifespan.py)

---

## Q: How are media assets handled?

Event media (banners, gallery images) are uploaded via `POST /api/events/{event_id}/media-assets`. The file is validated by `FileValidationError`, then uploaded to S3 via `S3Client.upload_file()`. The `EventMediaAssetModel` stores the S3 `storage_key` and a `public_url` (or presigned URL).

The `S3Client` uses boto3 with `AWS_S3_ENDPOINT_URL` (LocalStack in dev). Presigned URLs are generated for secure time-limited access.

Source: [apps/event/urls.py](src/apps/event/urls.py) (media endpoints), [src/utils/s3_client.py](src/utils/s3_client.py)
