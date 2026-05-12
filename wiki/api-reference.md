# API Reference

## Entry Points

### `main.py`
```
uv run main.py <command>
```
CLI via Typer. Commands: `run`, `makemigrations`, `migrate`, `showmigrations`, `rollback`, `startapp`, `startapps`, `create_super_admin`.

### `src/server.py` — `create_app(debug=False)`
FastAPI app factory. Registers all routers, CORS, exception handlers, and optionally mounts Starlette-Admin.

---

## Auth Dependencies

### `get_current_user(request, credentials, session) -> UserModel`
Verifies Bearer token JWT (`access` token). Sets `request.state.user` and `request.state.token_payload`. Returns the `UserModel`.

### `get_current_guest(request, credentials, session) -> GuestModel`
Verifies Bearer token JWT with `user_type=guest`. Rejects converted guests. Sets `request.state.guest`.

### `get_current_super_admin(request, credentials, session) -> SuperAdminModel`
Verifies Bearer token and checks `SuperAdminModel` table for the user. Sets `request.state.super_admin`.

### `get_current_user_or_guest(request, credentials, session) -> ActorContext`
Returns normalized `ActorContext(kind="user"|"guest", id=UUID)`. Sets both `request.state.actor` and `request.state.user` or `request.state.guest`.

---

## Core Utilities

### `db_session() -> AsyncIterator[AsyncSession]`
Async context manager. On success: commits. On exception: rolls back. Used as FastAPI `Depends()`.

### `redis` — async Redis instance
Used for rate limiting (`fastapi-limiter`) and token blocklist.

### `set_auth_cookies(response, tokens) -> JSONResponse`
Sets `access_token` and `refresh_token` as HTTP-only cookies on the response.

---

## Key Services

### `EventService(repository, organizer_repo, ticketing_repo)`
- `create_draft_event(user_id, organizer_page_id, title, event_access_type)` → `EventModel`
- `publish_event(user_id, event_id)` → `EventModel`
- `get_readiness(user_id, event_id)` → readiness dict
- `validate_for_publish(user_id, event_id)` → validation errors dict
- `create_event_day(user_id, event_id, date, start_time, end_time)` → `EventDayModel`
- `start_scan(user_id, event_day_id)` / `pause_scan` / `resume_scan` / `end_scan` → `EventDayModel`
- `upload_media_asset(owner_user_id, event_id, asset_type, file_name, file_content, ...)` → `EventMediaAssetModel`
- `create_order(user_id, event_id, event_day_id, ticket_type_id, quantity, coupon_code)` → `CreateOrderResponse`

### `PurchaseService(coupon_repository, repository)`
- `preview_order(event_id, event_day_id, ticket_type_id, quantity, coupon_code)` → price breakdown
- `create_order(...)` → creates `OrderModel`, locks tickets, creates Razorpay order
- `poll_order_status(order_id, user_id)` → current status

### `OrganizerService(repository)`
- `create_organizer(owner_user_id, ...)` → `OrganizerPageModel`
- `create_b2b_request(user_id, event_id, event_day_id, quantity)` → `B2BRequestModel`
- `confirm_b2b_payment(request_id, event_id, user_id)` → creates Razorpay payment link
- `create_b2b_transfer(user_id, event_id, reseller_id, quantity, event_day_id, mode, price)` → transfer result
- `create_customer_transfer(user_id, event_id, phone, email, quantity, event_day_id, mode, price)` → transfer result
- `get_my_b2b_tickets(event_id, user_id, event_day_id)` → grouped ticket summary
- `get_my_b2b_allocations(event_id, user_id, event_day_id, limit, offset)` → allocation history

### `TicketingService(repository, event_repo, ticketing_repo)`
- `create_ticket_type(user_id, event_id, ...)` → `TicketTypeModel`
- `allocate_ticket_type_to_day(user_id, event_id, event_day_id, ticket_type_id, quantity)` → `DayTicketAllocationModel`
- `update_allocation_quantity(user_id, event_id, allocation_id, quantity)` → updated allocation
- `list_ticket_types(user_id, event_id)` → list of `TicketTypeModel`

### `UserService(repository, blocklist)`
- `login_user(email, password)` → `{access_token, refresh_token}`
- `refresh_user(refresh_token)` → new `TokenPair`
- `logout_user(jti)` → revokes all refresh tokens sharing the jti

### `GuestService(repository, user_repo, blocklist)`
- `login_guest(device_id)` → tokens
- `convert_guest(guest_id, email, phone, password, first_name, last_name)` → user tokens

### `SuperAdminService(session)`
- `list_all_b2b_requests(status, limit, offset)` → list
- `list_pending_b2b_requests(limit, offset)` → list
- `get_b2b_request_detail(request_id)` → enriched detail
- `approve_b2b_request_free(admin_id, request_id, admin_notes)` → `B2BRequestModel`
- `approve_b2b_request_paid(admin_id, request_id, amount, admin_notes)` → `B2BRequestModel` + creates order
- `reject_b2b_request(admin_id, request_id, reason)` → `B2BRequestModel`
- `process_paid_b2b_allocation(request_id)` → creates allocation after payment

### `RazorpayWebhookHandler(session)`
- `handle(body, headers)` → routes Razorpay events (`order.paid`, `payment_link.paid`, `payment.failed`, etc.)
- `handle_order_paid(event)` → idempotent order completion with ticket allocation
- `handle_payment_failed(event)` / `handle_payment_link_expired` / `handle_payment_link_cancelled`

---

## Enums

### `apps/event/enums.py`
`EventStatus` (draft/published/archived), `EventAccessType` (open/ticketed), `ScanStatus` (not_started/scanning/paused/ended), `AssetType`, `LocationMode`

### `apps/ticketing/enums.py`
`TicketCategory` (vip/general/early_bird), `TicketStatus` (active/sold/transferred/cancelled/used), `OrderStatus` (pending/paid/failed/expired), `OrderType` (purchase/transfer)

### `apps/allocation/enums.py`
`AllocationStatus` (pending/completed/failed), `AllocationType` (purchase/b2b/free_transfer/gift), `GatewayType` (razorpay_order/razorpay_payment_link), `ClaimLinkStatus` (active/claimed/expired)

### `apps/superadmin/enums.py`
`B2BRequestStatus` (pending/approved_free/approved_paid/payment_done/allocated/expired/rejected)

---

## Database Models (Key Fields)

### `EventModel`
`id`, `organizer_page_id`, `created_by_user_id`, `title`, `slug`, `status`, `event_access_type`, `start_date`, `end_date`, `venue_*`, `published_at`, `is_published`, `show_tickets`

### `EventDayModel`
`id`, `event_id`, `day_index`, `date`, `start_time`, `end_time`, `scan_status`, `scan_started_at`, `scan_paused_at`, `scan_ended_at`, `next_ticket_index`

### `TicketModel`
`id`, `event_id`, `event_day_id`, `ticket_type_id`, `ticket_index`, `seat_label`, `owner_holder_id`, `status`, `lock_reference_type`, `lock_reference_id`, `lock_expires_at`, `claim_link_id`

### `OrderModel`
`id`, `event_id`, `user_id`, `sender_holder_id`, `receiver_holder_id`, `transfer_type`, `gateway_flow_type`, `event_day_id`, `type`, `subtotal_amount`, `discount_amount`, `final_amount`, `status`, `gateway_type`, `gateway_order_id`, `gateway_payment_id`, `captured_at`

### `AllocationModel`
`id`, `event_id`, `from_holder_id`, `to_holder_id`, `order_id`, `allocation_type`, `status`, `ticket_count`, `metadata_`

### `B2BRequestModel`
`id`, `requesting_user_id`, `event_id`, `event_day_id`, `ticket_type_id`, `quantity`, `status`, `reviewed_by_admin_id`, `admin_notes`, `allocation_id`, `order_id`, `metadata_`

---

## Request/Response Schemas

### `utils/schema.py`
- `BaseResponse` — wraps all responses: `{status, code, message?, data}`
- `BaseValidationResponse` — 422 validation error format
- `CamelCaseModel` — Pydantic model with camel-case aliasing

All API responses use `BaseResponse[data=...]` wrapping.
