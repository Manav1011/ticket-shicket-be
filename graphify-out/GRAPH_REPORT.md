# Graph Report - .  (2026-04-26)

## Corpus Check
- 203 files · ~213,092 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1528 nodes · 5094 edges · 87 communities detected
- Extraction: 35% EXTRACTED · 65% INFERRED · 0% AMBIGUOUS · INFERRED: 3306 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `FileValidationError` - 107 edges
2. `EventRepository` - 107 edges
3. `EventService` - 93 edges
4. `OrganizerService` - 87 edges
5. `CamelCaseModel` - 86 edges
6. `EventModel` - 81 edges
7. `BaseResponse` - 80 edges
8. `NotFoundError` - 78 edges
9. `TicketingRepository` - 78 edges
10. `OrganizerPageModel` - 76 edges

## Surprising Connections (you probably didn't know these)
- `Test that upload endpoint calls service method.` --uses--> `EventService`  [INFERRED]
  tests/apps/event/test_event_media_urls.py → src/apps/event/service.py
- `Test listing media assets returns list.` --uses--> `EventService`  [INFERRED]
  tests/apps/event/test_event_media_urls.py → src/apps/event/service.py
- `Test delete endpoint calls service.` --uses--> `EventService`  [INFERRED]
  tests/apps/event/test_event_media_urls.py → src/apps/event/service.py
- `Test update metadata endpoint.` --uses--> `EventService`  [INFERRED]
  tests/apps/event/test_event_media_urls.py → src/apps/event/service.py
- `get_current_super_admin should set request.state.super_admin AND return the admi` --uses--> `SuperAdminModel`  [INFERRED]
  tests/apps/superadmin/test_superadmin_auth.py → src/apps/superadmin/models.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (144): AlreadyExistsError, BadRequestError, Redis-based token blocklist for invalidating access tokens.  Uses a Redis SET to, Manages a Redis SET of blocked token JTIs., Add a jti to the blocklist.         Optionally set a TTL (in seconds) to auto-ex, Check if a jti is in the blocklist., Remove a jti from the blocklist (not typically needed)., TokenBlocklist (+136 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (113): BaseResponse, CamelCaseModel, OrganizerVisibility, InviteNotFound, [PUBLIC — No Auth Required]      Redeem a claim link token and receive a scan JW, InviteRepository, OrganizerRepository, UserRepository (+105 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (135): _collect_models(), mount_admin(), Admin integration helper for Starlette-Admin.  This module collects the project', Return a list of model classes to register in the admin UI., Attempt to initialize and mount Starlette-Admin at `/admin`.      This function, Base, Base, A mixin class to add a primary key field in a model. (+127 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (138): AssetType, EventAccessType, InviteType, LocationMode, ScanStatus, AlreadyExistsError, CannotPublishEvent, EventNotFound (+130 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (82): AppEnvironment, Enum representing different application environments.      - LOCAL: Indicates th, Enum, AllocationSourceType, AllocationStatus, AllocationType, B2BRequestStatus, CouponType (+74 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (66): BaseModel, Jobs package — imports trigger @scheduler.scheduled_job registration., ResellerRepository, ApproveB2BRequestFreeBody, ApproveB2BRequestPaidBody, RejectB2BRequestBody, ResellerAllocationItem, ResellerAllocationsResponse (+58 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (60): OrganizerService, mock_s3_client(), organizer_repo(), Integration tests for Organizer Media Asset workflow.  Tests the complete lifecy, Test that uploading a new logo replaces the existing one., Test that a valid 200x200+ image passes validation., Test that uploading a cover image updates the organizer's cover_image_url., Test that uploading a new cover replaces the existing one. (+52 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (19): PublicEventService, EventRepository, _AsyncNullContext, Open event with venue and all basic info complete should be ready., Ticketed event without tickets can publish but section marked incomplete., Ticketed event without tickets should NOT fail validation., Ticketed event day without start_time should fail schedule validation., Publishing event should set status, is_published, and published_at. (+11 more)

### Community 8 - "Community 8"
Cohesion: 0.05
Nodes (32): BaseSettings, AppGenerator, ColoredOutput, create_super_admin(), directory_created(), error(), file_created(), header() (+24 more)

### Community 9 - "Community 9"
Cohesion: 0.07
Nodes (9): ClaimService, PublicOrganizerService, redeem_claim_link(), Invalid token raises NotFoundError., Inactive claim link raises BadRequestError., Valid active claim link returns JWT string., test_get_jwt_for_claim_token_inactive(), test_get_jwt_for_claim_token_not_found() (+1 more)

### Community 10 - "Community 10"
Cohesion: 0.1
Nodes (18): get_s3_client(), Wrapper around boto3 S3 client for event media uploads., Determine MIME type based on file extension., Get S3 client singleton., Upload file to S3 and return storage key.          Args:             resource_id, Delete file from S3.          Args:             storage_key: S3 storage key (pat, Generate public URL for file (works for LocalStack and real AWS).          Args:, S3Client (+10 more)

### Community 11 - "Community 11"
Cohesion: 0.11
Nodes (0): 

### Community 12 - "Community 12"
Cohesion: 0.15
Nodes (10): Exception raised for an unexpected HTTP response.      Attributes:         respo, Initialize the exception with the unexpected HTTP response.          Args:, UnexpectedResponse, HTTPClient, Send a PATCH request.          :param url: The URL to send the request to. Defau, Deletes a resource at the specified URL.          :param url: The URL of the res, Send a GET request.          :param url: The URL to send the request to. Default, Send a POST request.          :param url: The URL to send the request to. Defaul (+2 more)

### Community 13 - "Community 13"
Cohesion: 0.17
Nodes (0): 

### Community 14 - "Community 14"
Cohesion: 0.2
Nodes (8): Test that upload endpoint calls service method., Test listing media assets returns list., Test delete endpoint calls service., Test update metadata endpoint., test_delete_media_asset_calls_service(), test_list_media_assets_returns_list(), test_update_media_asset_metadata(), test_upload_media_asset_calls_service()

### Community 15 - "Community 15"
Cohesion: 0.2
Nodes (4): Rejects when neither phone nor email provided., Rejects when event_day_id is not provided., test_rejects_empty(), test_rejects_missing_event_day_id()

### Community 16 - "Community 16"
Cohesion: 0.22
Nodes (3): Integration tests for Guest Module - Full Flow  These tests document the complet, Integration test covering complete guest lifecycle.      This test class documen, TestGuestFullLifecycle

### Community 17 - "Community 17"
Cohesion: 0.25
Nodes (0): 

### Community 18 - "Community 18"
Cohesion: 0.25
Nodes (0): 

### Community 19 - "Community 19"
Cohesion: 0.29
Nodes (2): test_update_ticket_allocation_quantity_calls_service_correctly(), test_update_ticket_allocation_quantity_increases_successfully()

### Community 20 - "Community 20"
Cohesion: 0.29
Nodes (6): Job runs without error when no locks are expired., Job processes large number of locks in batches of 1000., Job finds tickets with expired lock_expires_at and clears lock fields., test_cleanup_job_batches_large_lock_sets(), test_cleanup_job_clears_expired_locks(), test_cleanup_job_handles_no_expired_locks()

### Community 21 - "Community 21"
Cohesion: 0.4
Nodes (3): normalize_slug(), strong_password(), validate_input_fields()

### Community 22 - "Community 22"
Cohesion: 0.33
Nodes (0): 

### Community 23 - "Community 23"
Cohesion: 0.33
Nodes (0): 

### Community 24 - "Community 24"
Cohesion: 0.33
Nodes (0): 

### Community 25 - "Community 25"
Cohesion: 0.4
Nodes (4): Invalid token returns 404., GET /open/claim/{token} returns a plain JWT string., test_claim_link_invalid_token_returns_404(), test_claim_link_returns_jwt_string()

### Community 26 - "Community 26"
Cohesion: 0.4
Nodes (0): 

### Community 27 - "Community 27"
Cohesion: 0.4
Nodes (4): Paid mode returns not_implemented stub without creating any records., Free mode transfer creates allocation, claim link, updates ownership., test_create_customer_transfer_free_mode(), test_create_customer_transfer_paid_mode_returns_stub()

### Community 28 - "Community 28"
Cohesion: 0.4
Nodes (4): Endpoint rejects request with neither phone nor email., Endpoint returns completed transfer with claim link., test_create_customer_transfer_free_mode_success(), test_create_customer_transfer_validates_phone_or_email()

### Community 29 - "Community 29"
Cohesion: 0.4
Nodes (0): 

### Community 30 - "Community 30"
Cohesion: 0.4
Nodes (2): When holder exists by phone, should return it without checking email., test_resolve_holder_prefers_phone_over_email()

### Community 31 - "Community 31"
Cohesion: 0.4
Nodes (4): Returns None when no holder matches both., Returns holder when phone and email both match., test_get_holder_by_phone_and_email_returns_holder(), test_get_holder_by_phone_and_email_returns_none()

### Community 32 - "Community 32"
Cohesion: 0.5
Nodes (3): mock_send_email(), Mock Email notification utility. No-op implementation — real email provider (e.g, Send email.      Args:         to_email: Destination email address         subje

### Community 33 - "Community 33"
Cohesion: 0.5
Nodes (3): mock_send_whatsapp(), Mock WhatsApp notification utility. No-op implementation — real WhatsApp Busines, Send WhatsApp message to a phone number.      Args:         to_phone: Destinatio

### Community 34 - "Community 34"
Cohesion: 0.5
Nodes (3): mock_send_sms(), Mock SMS notification utility. No-op implementation — real SMS integration (e.g., Send SMS to a phone number.      Args:         to_phone: Destination phone numbe

### Community 35 - "Community 35"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 7c7609b23301 Revises: 760216553727 Create Date: 2026

### Community 36 - "Community 36"
Cohesion: 0.5
Nodes (1): change days_count default to -1 for zero-based day_index  Revision ID: 3bca6e2a9

### Community 37 - "Community 37"
Cohesion: 0.5
Nodes (1): add days_count to events  Revision ID: 45787abf577 Revises: 86361eeddf67 Create

### Community 38 - "Community 38"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 760216553727 Revises:  Create Date: 2026-04-15 22:30

### Community 39 - "Community 39"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 86361eeddf67 Revises: 7c7609b23301 Create Date: 2026

### Community 40 - "Community 40"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: d01b57798e73 Revises: 3bca6e2a9b45 Create Date: 2026

### Community 41 - "Community 41"
Cohesion: 0.5
Nodes (0): 

### Community 42 - "Community 42"
Cohesion: 0.5
Nodes (2): get_current_super_admin should set request.state.super_admin AND return the admi, test_get_current_super_admin_sets_request_state()

### Community 43 - "Community 43"
Cohesion: 0.5
Nodes (0): 

### Community 44 - "Community 44"
Cohesion: 0.5
Nodes (0): 

### Community 45 - "Community 45"
Cohesion: 0.5
Nodes (0): 

### Community 46 - "Community 46"
Cohesion: 0.5
Nodes (0): 

### Community 47 - "Community 47"
Cohesion: 0.5
Nodes (0): 

### Community 48 - "Community 48"
Cohesion: 0.67
Nodes (2): Simple role type - all users are regular users., RoleType

### Community 49 - "Community 49"
Cohesion: 0.67
Nodes (2): generate_claim_link_token(), Generate a cryptographically random 8-char alphanumeric token.     Uses ASCII le

### Community 50 - "Community 50"
Cohesion: 0.67
Nodes (0): 

### Community 51 - "Community 51"
Cohesion: 0.67
Nodes (0): 

### Community 52 - "Community 52"
Cohesion: 0.67
Nodes (0): 

### Community 53 - "Community 53"
Cohesion: 0.67
Nodes (0): 

### Community 54 - "Community 54"
Cohesion: 0.67
Nodes (0): 

### Community 55 - "Community 55"
Cohesion: 0.67
Nodes (0): 

### Community 56 - "Community 56"
Cohesion: 0.67
Nodes (0): 

### Community 57 - "Community 57"
Cohesion: 0.67
Nodes (0): 

### Community 58 - "Community 58"
Cohesion: 0.67
Nodes (0): 

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (0): 

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (0): 

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (0): 

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (0): 

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (0): 

### Community 64 - "Community 64"
Cohesion: 1.0
Nodes (0): 

### Community 65 - "Community 65"
Cohesion: 1.0
Nodes (1): Validate the required fields for the application.

### Community 66 - "Community 66"
Cohesion: 1.0
Nodes (1): Create a Database URL from the settings provided in the .env file.

### Community 67 - "Community 67"
Cohesion: 1.0
Nodes (1): Check if the app is running in production mode.

### Community 68 - "Community 68"
Cohesion: 1.0
Nodes (1): Check if the app is running in development mode.

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (1): Check if the app is running in local mode.

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (0): 

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (0): 

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (0): 

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (0): 

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (1): Validate banner image.          Args:             file_name: Original filename

### Community 75 - "Community 75"
Cohesion: 1.0
Nodes (1): Validate gallery image.

### Community 76 - "Community 76"
Cohesion: 1.0
Nodes (1): Validate gallery video.

### Community 77 - "Community 77"
Cohesion: 1.0
Nodes (1): Validate promo video URL.          Args:             url: Video URL (YouTube, Vi

### Community 78 - "Community 78"
Cohesion: 1.0
Nodes (1): Validate file extension against allowed types.

### Community 79 - "Community 79"
Cohesion: 1.0
Nodes (1): Validate image dimensions.

### Community 80 - "Community 80"
Cohesion: 1.0
Nodes (0): 

### Community 81 - "Community 81"
Cohesion: 1.0
Nodes (0): 

### Community 82 - "Community 82"
Cohesion: 1.0
Nodes (1): Step 1: Guest login creates guest record and returns tokens.          Expected:

### Community 83 - "Community 83"
Cohesion: 1.0
Nodes (1): Step 2: Guest protected endpoints require valid token.          Expected:

### Community 84 - "Community 84"
Cohesion: 1.0
Nodes (1): Step 3: Guest conversion creates User, links Guest, returns new tokens.

### Community 85 - "Community 85"
Cohesion: 1.0
Nodes (1): Step 4: Guest token refresh rotates the token pair.          Expected:         -

### Community 86 - "Community 86"
Cohesion: 1.0
Nodes (1): Step 5: Guest logout revokes the refresh token.          Expected:         - POS

## Knowledge Gaps
- **83 isolated node(s):** `Base custom exception class for raising necessary exceptions in the app.      At`, `Custom exception for representing a Bad Request (HTTP 400) error.`, `Custom exception for representing an Unauthorized (HTTP 401) error.`, `Custom exception for representing a Forbidden (HTTP 403) error.`, `Custom exception for representing a Not Found (HTTP 404) error.` (+78 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 59`** (2 nodes): `test_event_reseller_model.py`, `test_event_reseller_model_creation()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (2 nodes): `test_invite_models.py`, `test_invite_model_creation()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (2 nodes): `test_invite_enums.py`, `test_invite_status_values()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (2 nodes): `test_create_allocation_with_claim_link.py`, `test_create_allocation_with_claim_link_returns_both()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (2 nodes): `test_uuid_primary_key.py`, `test_uuid_primary_key_default_is_callable()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (2 nodes): `test_model_registry.py`, `test_model_registry_loads_organizer_table()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 65`** (1 nodes): `Validate the required fields for the application.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (1 nodes): `Create a Database URL from the settings provided in the .env file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (1 nodes): `Check if the app is running in production mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (1 nodes): `Check if the app is running in development mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (1 nodes): `Check if the app is running in local mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (1 nodes): `regex.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (1 nodes): `messages.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (1 nodes): `webhook.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `scheduler.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `Validate banner image.          Args:             file_name: Original filename`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `Validate gallery image.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `Validate gallery video.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (1 nodes): `Validate promo video URL.          Args:             url: Video URL (YouTube, Vi`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (1 nodes): `Validate file extension against allowed types.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 79`** (1 nodes): `Validate image dimensions.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 80`** (1 nodes): `model_registry.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 81`** (1 nodes): `seeder.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 82`** (1 nodes): `Step 1: Guest login creates guest record and returns tokens.          Expected:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 83`** (1 nodes): `Step 2: Guest protected endpoints require valid token.          Expected:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 84`** (1 nodes): `Step 3: Guest conversion creates User, links Guest, returns new tokens.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 85`** (1 nodes): `Step 4: Guest token refresh rotates the token pair.          Expected:         -`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 86`** (1 nodes): `Step 5: Guest logout revokes the refresh token.          Expected:         - POS`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `OrganizerService` connect `Community 6` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 7`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Why does `EventService` connect `Community 3` to `Community 1`, `Community 2`, `Community 4`, `Community 7`, `Community 14`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Why does `EventRepository` connect `Community 7` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 100 inferred relationships involving `FileValidationError` (e.g. with `Check if event is ready to publish, return section-by-section validation errors.` and `Publish event. Returns 400 with validation errors if not ready.`) actually correct?**
  _`FileValidationError` has 100 INFERRED edges - model-reasoned connections that need verification._
- **Are the 77 inferred relationships involving `EventRepository` (e.g. with `Check if event is ready to publish, return section-by-section validation errors.` and `Publish event. Returns 400 with validation errors if not ready.`) actually correct?**
  _`EventRepository` has 77 INFERRED edges - model-reasoned connections that need verification._
- **Are the 65 inferred relationships involving `EventService` (e.g. with `Check if event is ready to publish, return section-by-section validation errors.` and `Publish event. Returns 400 with validation errors if not ready.`) actually correct?**
  _`EventService` has 65 INFERRED edges - model-reasoned connections that need verification._
- **Are the 71 inferred relationships involving `OrganizerService` (e.g. with `[Organizer] List all events across all organizer pages owned by the current user` and `Upload logo image for organizer page.`) actually correct?**
  _`OrganizerService` has 71 INFERRED edges - model-reasoned connections that need verification._