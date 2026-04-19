# Graph Report - .  (2026-04-18)

## Corpus Check
- 162 files · ~168,083 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1261 nodes · 4042 edges · 64 communities detected
- Extraction: 37% EXTRACTED · 63% INFERRED · 0% AMBIGUOUS · INFERRED: 2532 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `FileValidationError` - 101 edges
2. `EventRepository` - 94 edges
3. `EventService` - 91 edges
4. `CamelCaseModel` - 78 edges
5. `EventModel` - 73 edges
6. `EventMediaAssetModel` - 72 edges
7. `EventAccessType` - 71 edges
8. `OrganizerService` - 69 edges
9. `BaseResponse` - 68 edges
10. `OrganizerPageModel` - 65 edges

## Surprising Connections (you probably didn't know these)
- `POST /api/user/invites/{invite_id}/accept     1. Calls invite_service.accept_inv` --uses--> `BaseResponse`  [INFERRED]
  tests/apps/user/test_user_invite_urls.py → src/utils/schema.py
- `POST /api/user/invites/{invite_id}/decline     Just calls invite_service.decline` --uses--> `BaseResponse`  [INFERRED]
  tests/apps/user/test_user_invite_urls.py → src/utils/schema.py
- `DELETE /api/user/invites/{invite_id}     Just calls invite_service.cancel_invite` --uses--> `BaseResponse`  [INFERRED]
  tests/apps/user/test_user_invite_urls.py → src/utils/schema.py
- `get_current_super_admin should set request.state.super_admin AND return the admi` --uses--> `SuperAdminModel`  [INFERRED]
  tests/apps/superadmin/test_superadmin_auth.py → src/apps/superadmin/models.py
- `Adding a jti should add it to the Redis set.` --uses--> `TokenBlocklist`  [INFERRED]
  tests/unit/auth/test_blocklist.py → src/auth/blocklist.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (175): _collect_models(), mount_admin(), Admin integration helper for Starlette-Admin.  This module collects the project', Return a list of model classes to register in the admin UI., Attempt to initialize and mount Starlette-Admin at `/admin`.      This function, Base, Base, A mixin class to add a primary key field in a model. (+167 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (120): AlreadyExistsError, BaseModel, B2BRequestStatus, TicketCategory, ForbiddenError, InviteAlreadyProcessed, OrganizerNotFound, OrganizerSlugAlreadyExists (+112 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (124): BaseResponse, CamelCaseModel, InviteType, AlreadyExistsError, InviteNotFound, Custom exception for representing a Conflict (HTTP 409) error indicating that th, InviteRepository, OrganizerRepository (+116 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (103): BadRequestError, Redis-based token blocklist for invalidating access tokens.  Uses a Redis SET to, Manages a Redis SET of blocked token JTIs., Add a jti to the blocklist.         Optionally set a TTL (in seconds) to auto-ex, Check if a jti is in the blocklist., Remove a jti from the blocklist (not typically needed)., TokenBlocklist, CustomException (+95 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (73): CannotDecreaseQuantity, EventNotFound, InvalidAllocation, InvalidAsset, InvalidQuantity, InvalidScanTransition, OpenEventDoesNotSupportTickets, OrganizerOwnershipError (+65 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (20): PublicEventService, PublicOrganizerService, EventRepository, _AsyncNullContext, Open event with venue and all basic info complete should be ready., Ticketed event without tickets can publish but section marked incomplete., Ticketed event without tickets should NOT fail validation., Ticketed event day without start_time should fail schedule validation. (+12 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (27): Allocation app package., accept_user_invite(), cancel_user_invite(), confirm_b2b_payment(), convert_guest(), create_b2b_request(), decline_user_invite(), delete_media_asset() (+19 more)

### Community 7 - "Community 7"
Cohesion: 0.05
Nodes (33): BaseSettings, AppEnvironment, assemble_db_url(), Enum representing different application environments.      - LOCAL: Indicates th, A settings class for the project defining all the necessary parameters within th, Settings, delete_cookies(), Delete authentication cookies from an HTTP response.      Args:         response (+25 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (16): AppGenerator, ColoredOutput, create_super_admin(), directory_created(), error(), file_created(), header(), highlight() (+8 more)

### Community 9 - "Community 9"
Cohesion: 0.1
Nodes (18): get_s3_client(), Wrapper around boto3 S3 client for event media uploads., Determine MIME type based on file extension., Get S3 client singleton., Upload file to S3 and return storage key.          Args:             resource_id, Delete file from S3.          Args:             storage_key: S3 storage key (pat, Generate public URL for file (works for LocalStack and real AWS).          Args:, S3Client (+10 more)

### Community 10 - "Community 10"
Cohesion: 0.11
Nodes (0): 

### Community 11 - "Community 11"
Cohesion: 0.15
Nodes (10): Exception raised for an unexpected HTTP response.      Attributes:         respo, Initialize the exception with the unexpected HTTP response.          Args:, UnexpectedResponse, HTTPClient, Send a PATCH request.          :param url: The URL to send the request to. Defau, Deletes a resource at the specified URL.          :param url: The URL of the res, Send a GET request.          :param url: The URL to send the request to. Default, Send a POST request.          :param url: The URL to send the request to. Defaul (+2 more)

### Community 12 - "Community 12"
Cohesion: 0.17
Nodes (1): GuestRepository

### Community 13 - "Community 13"
Cohesion: 0.17
Nodes (0): 

### Community 14 - "Community 14"
Cohesion: 0.22
Nodes (2): TestEnumService, TestToOptions

### Community 15 - "Community 15"
Cohesion: 0.22
Nodes (3): Integration tests for Guest Module - Full Flow  These tests document the complet, Integration test covering complete guest lifecycle.      This test class documen, TestGuestFullLifecycle

### Community 16 - "Community 16"
Cohesion: 0.25
Nodes (0): 

### Community 17 - "Community 17"
Cohesion: 0.25
Nodes (0): 

### Community 18 - "Community 18"
Cohesion: 0.29
Nodes (6): POST /api/user/invites/{invite_id}/decline     Just calls invite_service.decline, POST /api/user/invites/{invite_id}/accept     1. Calls invite_service.accept_inv, DELETE /api/user/invites/{invite_id}     Just calls invite_service.cancel_invite, test_accept_invite_under_user_endpoint(), test_cancel_invite_under_user_endpoint(), test_decline_invite_under_user_endpoint()

### Community 19 - "Community 19"
Cohesion: 0.29
Nodes (2): test_update_ticket_allocation_quantity_calls_service_correctly(), test_update_ticket_allocation_quantity_increases_successfully()

### Community 20 - "Community 20"
Cohesion: 0.33
Nodes (0): 

### Community 21 - "Community 21"
Cohesion: 0.5
Nodes (2): strong_password(), validate_input_fields()

### Community 22 - "Community 22"
Cohesion: 0.4
Nodes (0): 

### Community 23 - "Community 23"
Cohesion: 0.4
Nodes (0): 

### Community 24 - "Community 24"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 7c7609b23301 Revises: 760216553727 Create Date: 2026

### Community 25 - "Community 25"
Cohesion: 0.5
Nodes (1): change days_count default to -1 for zero-based day_index  Revision ID: 3bca6e2a9

### Community 26 - "Community 26"
Cohesion: 0.5
Nodes (1): add days_count to events  Revision ID: 45787abf577 Revises: 86361eeddf67 Create

### Community 27 - "Community 27"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 760216553727 Revises:  Create Date: 2026-04-15 22:30

### Community 28 - "Community 28"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 86361eeddf67 Revises: 7c7609b23301 Create Date: 2026

### Community 29 - "Community 29"
Cohesion: 0.5
Nodes (0): 

### Community 30 - "Community 30"
Cohesion: 0.5
Nodes (2): get_current_super_admin should set request.state.super_admin AND return the admi, test_get_current_super_admin_sets_request_state()

### Community 31 - "Community 31"
Cohesion: 0.5
Nodes (0): 

### Community 32 - "Community 32"
Cohesion: 0.67
Nodes (2): Simple role type - all users are regular users., RoleType

### Community 33 - "Community 33"
Cohesion: 0.67
Nodes (0): 

### Community 34 - "Community 34"
Cohesion: 0.67
Nodes (0): 

### Community 35 - "Community 35"
Cohesion: 0.67
Nodes (0): 

### Community 36 - "Community 36"
Cohesion: 0.67
Nodes (0): 

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (0): 

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (0): 

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (0): 

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (0): 

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (0): 

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Validate the required fields for the application.

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): Create a Database URL from the settings provided in the .env file.

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (1): Check if the app is running in production mode.

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (1): Check if the app is running in development mode.

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (1): Check if the app is running in local mode.

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (0): 

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (0): 

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (0): 

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (0): 

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (1): Validate banner image.          Args:             file_name: Original filename

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): Validate gallery image.

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (1): Validate gallery video.

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (1): Validate promo video URL.          Args:             url: Video URL (YouTube, Vi

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): Validate file extension against allowed types.

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): Validate image dimensions.

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (0): 

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (0): 

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (1): Step 1: Guest login creates guest record and returns tokens.          Expected:

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (1): Step 2: Guest protected endpoints require valid token.          Expected:

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (1): Step 3: Guest conversion creates User, links Guest, returns new tokens.

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (1): Step 4: Guest token refresh rotates the token pair.          Expected:         -

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (1): Step 5: Guest logout revokes the refresh token.          Expected:         - POS

## Knowledge Gaps
- **66 isolated node(s):** `Base custom exception class for raising necessary exceptions in the app.      At`, `Custom exception for representing a Bad Request (HTTP 400) error.`, `Custom exception for representing an Unauthorized (HTTP 401) error.`, `Custom exception for representing a Forbidden (HTTP 403) error.`, `Custom exception for representing a Not Found (HTTP 404) error.` (+61 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 37`** (2 nodes): `test_event_reseller_model.py`, `test_event_reseller_model_creation()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (2 nodes): `test_invite_models.py`, `test_invite_model_creation()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (2 nodes): `test_invite_enums.py`, `test_invite_status_values()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (2 nodes): `test_uuid_primary_key.py`, `test_uuid_primary_key_default_is_callable()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (2 nodes): `test_model_registry.py`, `test_model_registry_loads_organizer_table()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Validate the required fields for the application.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `Create a Database URL from the settings provided in the .env file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `Check if the app is running in production mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `Check if the app is running in development mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `Check if the app is running in local mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `regex.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `messages.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `webhook.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `scheduler.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `Validate banner image.          Args:             file_name: Original filename`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `Validate gallery image.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `Validate gallery video.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `Validate promo video URL.          Args:             url: Video URL (YouTube, Vi`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `Validate file extension against allowed types.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `Validate image dimensions.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `model_registry.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `seeder.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `Step 1: Guest login creates guest record and returns tokens.          Expected:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `Step 2: Guest protected endpoints require valid token.          Expected:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `Step 3: Guest conversion creates User, links Guest, returns new tokens.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (1 nodes): `Step 4: Guest token refresh rotates the token pair.          Expected:         -`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (1 nodes): `Step 5: Guest logout revokes the refresh token.          Expected:         - POS`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `EventService` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 5`, `Community 7`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `EventRepository` connect `Community 5` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 7`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Why does `FileValidationError` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Are the 94 inferred relationships involving `FileValidationError` (e.g. with `Check if event is ready to publish, return section-by-section validation errors.` and `Publish event. Returns 400 with validation errors if not ready.`) actually correct?**
  _`FileValidationError` has 94 INFERRED edges - model-reasoned connections that need verification._
- **Are the 65 inferred relationships involving `EventRepository` (e.g. with `Check if event is ready to publish, return section-by-section validation errors.` and `Publish event. Returns 400 with validation errors if not ready.`) actually correct?**
  _`EventRepository` has 65 INFERRED edges - model-reasoned connections that need verification._
- **Are the 63 inferred relationships involving `EventService` (e.g. with `Check if event is ready to publish, return section-by-section validation errors.` and `Publish event. Returns 400 with validation errors if not ready.`) actually correct?**
  _`EventService` has 63 INFERRED edges - model-reasoned connections that need verification._
- **Are the 72 inferred relationships involving `CamelCaseModel` (e.g. with `TokenPayload` and `TokenPair`) actually correct?**
  _`CamelCaseModel` has 72 INFERRED edges - model-reasoned connections that need verification._