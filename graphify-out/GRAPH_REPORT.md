# Graph Report - .  (2026-04-27)

## Corpus Check
- 205 files · ~234,595 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1552 nodes · 5200 edges · 93 communities detected
- Extraction: 35% EXTRACTED · 65% INFERRED · 0% AMBIGUOUS · INFERRED: 3385 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `FileValidationError` - 108 edges
2. `EventRepository` - 108 edges
3. `EventService` - 94 edges
4. `CamelCaseModel` - 89 edges
5. `OrganizerService` - 86 edges
6. `TicketingRepository` - 85 edges
7. `BaseResponse` - 83 edges
8. `EventModel` - 81 edges
9. `NotFoundError` - 80 edges
10. `OrganizerPageModel` - 76 edges

## Surprising Connections (you probably didn't know these)
- `POST /api/user/invites/{invite_id}/accept     1. Calls invite_service.accept_inv` --uses--> `BaseResponse`  [INFERRED]
  tests/apps/user/test_user_invite_urls.py → src/utils/schema.py
- `POST /api/user/invites/{invite_id}/decline     Just calls invite_service.decline` --uses--> `BaseResponse`  [INFERRED]
  tests/apps/user/test_user_invite_urls.py → src/utils/schema.py
- `DELETE /api/user/invites/{invite_id}     Just calls invite_service.cancel_invite` --uses--> `BaseResponse`  [INFERRED]
  tests/apps/user/test_user_invite_urls.py → src/utils/schema.py
- `Test that upload endpoint calls service method.` --uses--> `EventService`  [INFERRED]
  tests/apps/event/test_event_media_urls.py → src/apps/event/service.py
- `Test listing media assets returns list.` --uses--> `EventService`  [INFERRED]
  tests/apps/event/test_event_media_urls.py → src/apps/event/service.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (146): BaseResponse, CamelCaseModel, InviteType, OrganizerVisibility, AlreadyExistsError, EventNotFound, InviteNotFound, Custom exception for representing a Conflict (HTTP 409) error indicating that th (+138 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (152): async_test_client(), auth_headers(), db_session(), guest_device_id(), invalid_file_type_bytes(), mock_s3_client(), oversized_image_bytes(), Create FastAPI app with mocked lifespan for HTTP testing. (+144 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (129): _collect_models(), mount_admin(), Admin integration helper for Starlette-Admin.  This module collects the project', Return a list of model classes to register in the admin UI., Attempt to initialize and mount Starlette-Admin at `/admin`.      This function, Base, Base, A mixin class to add a primary key field in a model. (+121 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (127): AlreadyExistsError, BadRequestError, Redis-based token blocklist for invalidating access tokens.  Uses a Redis SET to, Manages a Redis SET of blocked token JTIs., Add a jti to the blocklist.         Optionally set a TTL (in seconds) to auto-ex, Check if a jti is in the blocklist., Remove a jti from the blocklist (not typically needed)., TokenBlocklist (+119 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (89): BaseModel, B2BRequestStatus, OrderStatus, OrderType, TicketCategory, ForbiddenError, OrganizerNotFound, OrganizerSlugAlreadyExists (+81 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (34): Jobs package — imports trigger @scheduler.scheduled_job registration., accept_user_invite(), approve_b2b_request_free(), approve_b2b_request_paid(), cancel_user_invite(), confirm_b2b_payment(), create_b2b_request(), create_b2b_transfer_endpoint() (+26 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (60): OrganizerService, mock_s3_client(), organizer_repo(), Integration tests for Organizer Media Asset workflow.  Tests the complete lifecy, Test that uploading a new logo replaces the existing one., Test that a valid 200x200+ image passes validation., Test that uploading a cover image updates the organizer's cover_image_url., Test that uploading a new cover replaces the existing one. (+52 more)

### Community 7 - "Community 7"
Cohesion: 0.05
Nodes (34): BaseSettings, AppEnvironment, assemble_db_url(), Enum representing different application environments.      - LOCAL: Indicates th, A settings class for the project defining all the necessary parameters within th, Settings, delete_cookies(), Delete authentication cookies from an HTTP response.      Args:         response (+26 more)

### Community 8 - "Community 8"
Cohesion: 0.05
Nodes (6): PublicOrganizerService, redeem_claim_link(), split_claim(), GuestRepository, test_update_ticket_allocation_quantity_calls_service_correctly(), test_update_ticket_allocation_quantity_increases_successfully()

### Community 9 - "Community 9"
Cohesion: 0.09
Nodes (16): AppGenerator, ColoredOutput, create_super_admin(), directory_created(), error(), file_created(), header(), highlight() (+8 more)

### Community 10 - "Community 10"
Cohesion: 0.08
Nodes (1): EventRepository

### Community 11 - "Community 11"
Cohesion: 0.1
Nodes (18): get_s3_client(), Wrapper around boto3 S3 client for event media uploads., Determine MIME type based on file extension., Get S3 client singleton., Upload file to S3 and return storage key.          Args:             resource_id, Delete file from S3.          Args:             storage_key: S3 storage key (pat, Generate public URL for file (works for LocalStack and real AWS).          Args:, S3Client (+10 more)

### Community 12 - "Community 12"
Cohesion: 0.09
Nodes (10): _AsyncNullContext, test_interest_event_creates_row_and_increments_counter_for_user(), test_interest_event_is_idempotent_for_same_guest_event_pair(), test_publish_event_sets_published_fields(), test_setup_status_tickets_false_when_show_tickets_disabled(), test_ticketed_event_can_be_published_without_tickets_and_then_tickets_added(), test_validate_for_publish_open_venue_complete(), test_validate_for_publish_ticketed_missing_tickets() (+2 more)

### Community 13 - "Community 13"
Cohesion: 0.11
Nodes (0): 

### Community 14 - "Community 14"
Cohesion: 0.15
Nodes (10): Exception raised for an unexpected HTTP response.      Attributes:         respo, Initialize the exception with the unexpected HTTP response.          Args:, UnexpectedResponse, HTTPClient, Send a PATCH request.          :param url: The URL to send the request to. Defau, Deletes a resource at the specified URL.          :param url: The URL of the res, Send a GET request.          :param url: The URL to send the request to. Default, Send a POST request.          :param url: The URL to send the request to. Defaul (+2 more)

### Community 15 - "Community 15"
Cohesion: 0.14
Nodes (1): UserRepository

### Community 16 - "Community 16"
Cohesion: 0.17
Nodes (0): 

### Community 17 - "Community 17"
Cohesion: 0.2
Nodes (8): Test that upload endpoint calls service method., Test listing media assets returns list., Test delete endpoint calls service., Test update metadata endpoint., test_delete_media_asset_calls_service(), test_list_media_assets_returns_list(), test_update_media_asset_metadata(), test_upload_media_asset_calls_service()

### Community 18 - "Community 18"
Cohesion: 0.2
Nodes (4): Rejects when neither phone nor email provided., Rejects when event_day_id is not provided., test_rejects_empty(), test_rejects_missing_event_day_id()

### Community 19 - "Community 19"
Cohesion: 0.22
Nodes (3): Integration tests for Guest Module - Full Flow  These tests document the complet, Integration test covering complete guest lifecycle.      This test class documen, TestGuestFullLifecycle

### Community 20 - "Community 20"
Cohesion: 0.25
Nodes (0): 

### Community 21 - "Community 21"
Cohesion: 0.25
Nodes (0): 

### Community 22 - "Community 22"
Cohesion: 0.29
Nodes (6): POST /api/user/invites/{invite_id}/decline     Just calls invite_service.decline, POST /api/user/invites/{invite_id}/accept     1. Calls invite_service.accept_inv, DELETE /api/user/invites/{invite_id}     Just calls invite_service.cancel_invite, test_accept_invite_under_user_endpoint(), test_cancel_invite_under_user_endpoint(), test_decline_invite_under_user_endpoint()

### Community 23 - "Community 23"
Cohesion: 0.29
Nodes (6): Job runs without error when no locks are expired., Job processes large number of locks in batches of 1000., Job finds tickets with expired lock_expires_at and clears lock fields., test_cleanup_job_batches_large_lock_sets(), test_cleanup_job_clears_expired_locks(), test_cleanup_job_handles_no_expired_locks()

### Community 24 - "Community 24"
Cohesion: 0.4
Nodes (3): normalize_slug(), strong_password(), validate_input_fields()

### Community 25 - "Community 25"
Cohesion: 0.33
Nodes (0): 

### Community 26 - "Community 26"
Cohesion: 0.33
Nodes (0): 

### Community 27 - "Community 27"
Cohesion: 0.33
Nodes (0): 

### Community 28 - "Community 28"
Cohesion: 0.33
Nodes (0): 

### Community 29 - "Community 29"
Cohesion: 0.4
Nodes (4): Invalid token returns 404., GET /open/claim/{token} returns a plain JWT string., test_claim_link_invalid_token_returns_404(), test_claim_link_returns_jwt_string()

### Community 30 - "Community 30"
Cohesion: 0.4
Nodes (0): 

### Community 31 - "Community 31"
Cohesion: 0.4
Nodes (4): Paid mode returns not_implemented stub without creating any records., Free mode transfer creates allocation, claim link, updates ownership., test_create_customer_transfer_free_mode(), test_create_customer_transfer_paid_mode_returns_stub()

### Community 32 - "Community 32"
Cohesion: 0.4
Nodes (4): Endpoint rejects request with neither phone nor email., Endpoint returns completed transfer with claim link., test_create_customer_transfer_free_mode_success(), test_create_customer_transfer_validates_phone_or_email()

### Community 33 - "Community 33"
Cohesion: 0.4
Nodes (0): 

### Community 34 - "Community 34"
Cohesion: 0.4
Nodes (2): When holder exists by phone, should return it without checking email., test_resolve_holder_prefers_phone_over_email()

### Community 35 - "Community 35"
Cohesion: 0.4
Nodes (4): Returns None when no holder matches both., Returns holder when phone and email both match., test_get_holder_by_phone_and_email_returns_holder(), test_get_holder_by_phone_and_email_returns_none()

### Community 36 - "Community 36"
Cohesion: 0.5
Nodes (3): mock_send_email(), Mock Email notification utility. No-op implementation — real email provider (e.g, Send email.      Args:         to_email: Destination email address         subje

### Community 37 - "Community 37"
Cohesion: 0.5
Nodes (3): mock_send_whatsapp(), Mock WhatsApp notification utility. No-op implementation — real WhatsApp Busines, Send WhatsApp message to a phone number.      Args:         to_phone: Destinatio

### Community 38 - "Community 38"
Cohesion: 0.5
Nodes (3): mock_send_sms(), Mock SMS notification utility. No-op implementation — real SMS integration (e.g., Send SMS to a phone number.      Args:         to_phone: Destination phone numbe

### Community 39 - "Community 39"
Cohesion: 0.5
Nodes (1): add_jwt_jti_to_claim_links  Revision ID: e3f1d0b2f77a Revises: d01b57798e73 Crea

### Community 40 - "Community 40"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 7c7609b23301 Revises: 760216553727 Create Date: 2026

### Community 41 - "Community 41"
Cohesion: 0.5
Nodes (1): change days_count default to -1 for zero-based day_index  Revision ID: 3bca6e2a9

### Community 42 - "Community 42"
Cohesion: 0.5
Nodes (1): add days_count to events  Revision ID: 45787abf577 Revises: 86361eeddf67 Create

### Community 43 - "Community 43"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 760216553727 Revises:  Create Date: 2026-04-15 22:30

### Community 44 - "Community 44"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 86361eeddf67 Revises: 7c7609b23301 Create Date: 2026

### Community 45 - "Community 45"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: d01b57798e73 Revises: 3bca6e2a9b45 Create Date: 2026

### Community 46 - "Community 46"
Cohesion: 0.5
Nodes (1): add claim_link_id to tickets  Revision ID: 3e3562fc8e6d Revises: e3f1d0b2f77a Cr

### Community 47 - "Community 47"
Cohesion: 0.5
Nodes (0): 

### Community 48 - "Community 48"
Cohesion: 0.5
Nodes (2): get_current_super_admin should set request.state.super_admin AND return the admi, test_get_current_super_admin_sets_request_state()

### Community 49 - "Community 49"
Cohesion: 0.5
Nodes (0): 

### Community 50 - "Community 50"
Cohesion: 0.5
Nodes (0): 

### Community 51 - "Community 51"
Cohesion: 0.5
Nodes (0): 

### Community 52 - "Community 52"
Cohesion: 0.5
Nodes (0): 

### Community 53 - "Community 53"
Cohesion: 0.5
Nodes (2): claim_link_id should be included when provided., test_update_ownership_batch_sets_claim_link_id()

### Community 54 - "Community 54"
Cohesion: 0.5
Nodes (0): 

### Community 55 - "Community 55"
Cohesion: 0.67
Nodes (2): Simple role type - all users are regular users., RoleType

### Community 56 - "Community 56"
Cohesion: 0.67
Nodes (2): generate_claim_link_token(), Generate a cryptographically random 8-char alphanumeric token.     Uses ASCII le

### Community 57 - "Community 57"
Cohesion: 0.67
Nodes (0): 

### Community 58 - "Community 58"
Cohesion: 0.67
Nodes (0): 

### Community 59 - "Community 59"
Cohesion: 0.67
Nodes (0): 

### Community 60 - "Community 60"
Cohesion: 0.67
Nodes (0): 

### Community 61 - "Community 61"
Cohesion: 0.67
Nodes (0): 

### Community 62 - "Community 62"
Cohesion: 0.67
Nodes (0): 

### Community 63 - "Community 63"
Cohesion: 0.67
Nodes (0): 

### Community 64 - "Community 64"
Cohesion: 0.67
Nodes (0): 

### Community 65 - "Community 65"
Cohesion: 1.0
Nodes (0): 

### Community 66 - "Community 66"
Cohesion: 1.0
Nodes (0): 

### Community 67 - "Community 67"
Cohesion: 1.0
Nodes (0): 

### Community 68 - "Community 68"
Cohesion: 1.0
Nodes (0): 

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (0): 

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (0): 

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (1): Validate the required fields for the application.

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (1): Create a Database URL from the settings provided in the .env file.

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (1): Check if the app is running in production mode.

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (1): Check if the app is running in development mode.

### Community 75 - "Community 75"
Cohesion: 1.0
Nodes (1): Check if the app is running in local mode.

### Community 76 - "Community 76"
Cohesion: 1.0
Nodes (0): 

### Community 77 - "Community 77"
Cohesion: 1.0
Nodes (0): 

### Community 78 - "Community 78"
Cohesion: 1.0
Nodes (0): 

### Community 79 - "Community 79"
Cohesion: 1.0
Nodes (0): 

### Community 80 - "Community 80"
Cohesion: 1.0
Nodes (1): Validate banner image.          Args:             file_name: Original filename

### Community 81 - "Community 81"
Cohesion: 1.0
Nodes (1): Validate gallery image.

### Community 82 - "Community 82"
Cohesion: 1.0
Nodes (1): Validate gallery video.

### Community 83 - "Community 83"
Cohesion: 1.0
Nodes (1): Validate promo video URL.          Args:             url: Video URL (YouTube, Vi

### Community 84 - "Community 84"
Cohesion: 1.0
Nodes (1): Validate file extension against allowed types.

### Community 85 - "Community 85"
Cohesion: 1.0
Nodes (1): Validate image dimensions.

### Community 86 - "Community 86"
Cohesion: 1.0
Nodes (0): 

### Community 87 - "Community 87"
Cohesion: 1.0
Nodes (0): 

### Community 88 - "Community 88"
Cohesion: 1.0
Nodes (1): Step 1: Guest login creates guest record and returns tokens.          Expected:

### Community 89 - "Community 89"
Cohesion: 1.0
Nodes (1): Step 2: Guest protected endpoints require valid token.          Expected:

### Community 90 - "Community 90"
Cohesion: 1.0
Nodes (1): Step 3: Guest conversion creates User, links Guest, returns new tokens.

### Community 91 - "Community 91"
Cohesion: 1.0
Nodes (1): Step 4: Guest token refresh rotates the token pair.          Expected:         -

### Community 92 - "Community 92"
Cohesion: 1.0
Nodes (1): Step 5: Guest logout revokes the refresh token.          Expected:         - POS

## Knowledge Gaps
- **85 isolated node(s):** `Base custom exception class for raising necessary exceptions in the app.      At`, `Custom exception for representing a Bad Request (HTTP 400) error.`, `Custom exception for representing an Unauthorized (HTTP 401) error.`, `Custom exception for representing a Forbidden (HTTP 403) error.`, `Custom exception for representing a Not Found (HTTP 404) error.` (+80 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 65`** (2 nodes): `test_event_reseller_model.py`, `test_event_reseller_model_creation()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (2 nodes): `test_invite_models.py`, `test_invite_model_creation()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (2 nodes): `test_invite_enums.py`, `test_invite_status_values()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (2 nodes): `test_create_allocation_with_claim_link.py`, `test_create_allocation_with_claim_link_returns_both()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (2 nodes): `test_uuid_primary_key.py`, `test_uuid_primary_key_default_is_callable()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (2 nodes): `test_model_registry.py`, `test_model_registry_loads_organizer_table()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (1 nodes): `Validate the required fields for the application.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (1 nodes): `Create a Database URL from the settings provided in the .env file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `Check if the app is running in production mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `Check if the app is running in development mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `Check if the app is running in local mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `regex.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (1 nodes): `messages.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (1 nodes): `webhook.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 79`** (1 nodes): `scheduler.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 80`** (1 nodes): `Validate banner image.          Args:             file_name: Original filename`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 81`** (1 nodes): `Validate gallery image.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 82`** (1 nodes): `Validate gallery video.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 83`** (1 nodes): `Validate promo video URL.          Args:             url: Video URL (YouTube, Vi`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 84`** (1 nodes): `Validate file extension against allowed types.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 85`** (1 nodes): `Validate image dimensions.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 86`** (1 nodes): `model_registry.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 87`** (1 nodes): `seeder.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 88`** (1 nodes): `Step 1: Guest login creates guest record and returns tokens.          Expected:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 89`** (1 nodes): `Step 2: Guest protected endpoints require valid token.          Expected:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 90`** (1 nodes): `Step 3: Guest conversion creates User, links Guest, returns new tokens.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 91`** (1 nodes): `Step 4: Guest token refresh rotates the token pair.          Expected:         -`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 92`** (1 nodes): `Step 5: Guest logout revokes the refresh token.          Expected:         - POS`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `OrganizerService` connect `Community 6` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 10`, `Community 15`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `EventService` connect `Community 1` to `Community 0`, `Community 3`, `Community 4`, `Community 10`, `Community 12`, `Community 17`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Why does `EventRepository` connect `Community 10` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 6`, `Community 8`, `Community 12`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 101 inferred relationships involving `FileValidationError` (e.g. with `Check if event is ready to publish, return section-by-section validation errors.` and `Publish event. Returns 400 with validation errors if not ready.`) actually correct?**
  _`FileValidationError` has 101 INFERRED edges - model-reasoned connections that need verification._
- **Are the 78 inferred relationships involving `EventRepository` (e.g. with `Check if event is ready to publish, return section-by-section validation errors.` and `Publish event. Returns 400 with validation errors if not ready.`) actually correct?**
  _`EventRepository` has 78 INFERRED edges - model-reasoned connections that need verification._
- **Are the 66 inferred relationships involving `EventService` (e.g. with `Check if event is ready to publish, return section-by-section validation errors.` and `Publish event. Returns 400 with validation errors if not ready.`) actually correct?**
  _`EventService` has 66 INFERRED edges - model-reasoned connections that need verification._
- **Are the 83 inferred relationships involving `CamelCaseModel` (e.g. with `TokenPayload` and `TokenPair`) actually correct?**
  _`CamelCaseModel` has 83 INFERRED edges - model-reasoned connections that need verification._