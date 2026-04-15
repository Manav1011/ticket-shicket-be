# Graph Report - .  (2026-04-15)

## Corpus Check
- 162 files · ~145,389 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1191 nodes · 3399 edges · 75 communities detected
- Extraction: 42% EXTRACTED · 58% INFERRED · 0% AMBIGUOUS · INFERRED: 1973 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `FileValidationError` - 98 edges
2. `EventService` - 82 edges
3. `CamelCaseModel` - 69 edges
4. `EventModel` - 68 edges
5. `EventAccessType` - 67 edges
6. `EventMediaAssetModel` - 67 edges
7. `OrganizerPageModel` - 58 edges
8. `BaseResponse` - 55 edges
9. `UserModel` - 55 edges
10. `OrganizerService` - 53 edges

## Surprising Connections (you probably didn't know these)
- `Adding a jti should add it to the Redis set.` --uses--> `TokenBlocklist`  [INFERRED]
  tests/unit/auth/test_blocklist.py → src/auth/blocklist.py
- `Blocked jti should return True.` --uses--> `TokenBlocklist`  [INFERRED]
  tests/unit/auth/test_blocklist.py → src/auth/blocklist.py
- `Non-blocklisted jti should return False.` --uses--> `TokenBlocklist`  [INFERRED]
  tests/unit/auth/test_blocklist.py → src/auth/blocklist.py
- `Adding a jti with TTL should also set expiry on the set.` --uses--> `TokenBlocklist`  [INFERRED]
  tests/unit/auth/test_blocklist.py → src/auth/blocklist.py
- `Removing a jti should remove it from the Redis set.` --uses--> `TokenBlocklist`  [INFERRED]
  tests/unit/auth/test_blocklist.py → src/auth/blocklist.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (193): async_test_client(), auth_headers(), db_session(), guest_device_id(), invalid_file_type_bytes(), mock_s3_client(), oversized_image_bytes(), Create FastAPI app with mocked lifespan for HTTP testing. (+185 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (109): BaseResponse, CamelCaseModel, InviteType, OrganizerVisibility, ForbiddenError, InviteNotFound, Custom exception for representing a Forbidden (HTTP 403) error., InviteRepository (+101 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (106): BadRequestError, Redis-based token blocklist for invalidating access tokens.  Uses a Redis SET to, Manages a Redis SET of blocked token JTIs., Add a jti to the blocklist.         Optionally set a TTL (in seconds) to auto-ex, Check if a jti is in the blocklist., Remove a jti from the blocklist (not typically needed)., TokenBlocklist, CustomException (+98 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (78): Base, Base, A mixin class to add a primary key field in a model., Base class for defining database tables., A mixin class to add automatic timestamp fields.      Adds `created_at` and `upd, TimeStampMixin, UUIDPrimaryKeyMixin, DeclarativeBase (+70 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (41): AlreadyExistsError, BaseModel, B2BRequestStatus, OrganizerSlugAlreadyExists, Allocation app package., ApproveB2BRequestFreeBody, ApproveB2BRequestPaidBody, RejectB2BRequestBody (+33 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (19): PublicEventService, EventRepository, _AsyncNullContext, Open event with venue and all basic info complete should be ready., Ticketed event without tickets can publish but section marked incomplete., Ticketed event without tickets should NOT fail validation., Ticketed event day without start_time should fail schedule validation., Publishing event should set status, is_published, and published_at. (+11 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (32): BaseSettings, AppEnvironment, assemble_db_url(), Enum representing different application environments.      - LOCAL: Indicates th, A settings class for the project defining all the necessary parameters within th, Settings, delete_cookies(), Delete authentication cookies from an HTTP response.      Args:         response (+24 more)

### Community 7 - "Community 7"
Cohesion: 0.05
Nodes (3): PublicOrganizerService, GuestRepository, TicketingRepository

### Community 8 - "Community 8"
Cohesion: 0.14
Nodes (15): AppGenerator, ColoredOutput, create_super_admin(), directory_created(), error(), file_created(), header(), highlight() (+7 more)

### Community 9 - "Community 9"
Cohesion: 0.1
Nodes (18): get_s3_client(), Wrapper around boto3 S3 client for event media uploads., Determine MIME type based on file extension., Get S3 client singleton., Upload file to S3 and return storage key.          Args:             resource_id, Delete file from S3.          Args:             storage_key: S3 storage key (pat, Generate public URL for file (works for LocalStack and real AWS).          Args:, S3Client (+10 more)

### Community 10 - "Community 10"
Cohesion: 0.15
Nodes (10): Exception raised for an unexpected HTTP response.      Attributes:         respo, Initialize the exception with the unexpected HTTP response.          Args:, UnexpectedResponse, HTTPClient, Send a PATCH request.          :param url: The URL to send the request to. Defau, Deletes a resource at the specified URL.          :param url: The URL of the res, Send a GET request.          :param url: The URL to send the request to. Default, Send a POST request.          :param url: The URL to send the request to. Defaul (+2 more)

### Community 11 - "Community 11"
Cohesion: 0.12
Nodes (0): 

### Community 12 - "Community 12"
Cohesion: 0.15
Nodes (10): Adding a jti should add it to the Redis set., Blocked jti should return True., Non-blocklisted jti should return False., Adding a jti with TTL should also set expiry on the set., Removing a jti should remove it from the Redis set., test_add_jti_to_blocklist(), test_add_jti_with_ttl(), test_is_jti_blocklisted_false() (+2 more)

### Community 13 - "Community 13"
Cohesion: 0.17
Nodes (0): 

### Community 14 - "Community 14"
Cohesion: 0.2
Nodes (8): Test that upload endpoint calls service method., Test listing media assets returns list., Test delete endpoint calls service., Test update metadata endpoint., test_delete_media_asset_calls_service(), test_list_media_assets_returns_list(), test_update_media_asset_metadata(), test_upload_media_asset_calls_service()

### Community 15 - "Community 15"
Cohesion: 0.22
Nodes (3): Integration tests for Guest Module - Full Flow  These tests document the complet, Integration test covering complete guest lifecycle.      This test class documen, TestGuestFullLifecycle

### Community 16 - "Community 16"
Cohesion: 0.5
Nodes (7): validate_banner_image(), _validate_file_size(), _validate_file_type(), validate_gallery_image(), validate_gallery_video(), _validate_image_dimensions(), validate_promo_video_url()

### Community 17 - "Community 17"
Cohesion: 0.29
Nodes (6): Mock OrganizerService., Test that upload logo endpoint calls service method., Test that upload cover endpoint calls service method., service_mock(), test_upload_cover_endpoint_calls_service(), test_upload_logo_endpoint_calls_service()

### Community 18 - "Community 18"
Cohesion: 0.29
Nodes (2): test_update_ticket_allocation_quantity_calls_service_correctly(), test_update_ticket_allocation_quantity_increases_successfully()

### Community 19 - "Community 19"
Cohesion: 0.33
Nodes (0): 

### Community 20 - "Community 20"
Cohesion: 0.5
Nodes (2): strong_password(), validate_input_fields()

### Community 21 - "Community 21"
Cohesion: 0.4
Nodes (0): 

### Community 22 - "Community 22"
Cohesion: 0.4
Nodes (0): 

### Community 23 - "Community 23"
Cohesion: 0.4
Nodes (0): 

### Community 24 - "Community 24"
Cohesion: 0.5
Nodes (1): add guests table  Revision ID: b27c8820610c Revises: 05160b3cd708 Create Date: 2

### Community 25 - "Community 25"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 05160b3cd708 Revises:  Create Date: 2026-04-02 19:55

### Community 26 - "Community 26"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: d5ede614f47b Revises: 9bf5b22783b2 Create Date: 2026

### Community 27 - "Community 27"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: b09b4f4d48b4 Revises: e1a2b3c4d5e6 Create Date: 2026

### Community 28 - "Community 28"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 12287d5104de Revises: 479742328475 Create Date: 2026

### Community 29 - "Community 29"
Cohesion: 0.5
Nodes (1): add_tickets_pending_to_events  Revision ID: 86eca4b4e294 Revises: aa037cba12e1 C

### Community 30 - "Community 30"
Cohesion: 0.5
Nodes (1): add invite_type to invites  Revision ID: aa037cba12e1 Revises: 12287d5104de Crea

### Community 31 - "Community 31"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 479742328475 Revises: d5ede614f47b Create Date: 2026

### Community 32 - "Community 32"
Cohesion: 0.5
Nodes (1): add phase one event tables  Revision ID: 91180041173a Revises: b27c8820610c Crea

### Community 33 - "Community 33"
Cohesion: 0.5
Nodes (1): convert_string_columns_to_enum_types  Revision ID: 9bf5b22783b2 Revises: ea08286

### Community 34 - "Community 34"
Cohesion: 0.5
Nodes (1): replace_tickets_pending_with_show_tickets  Revision ID: bd5e7c3a1f2d Revises: 86

### Community 35 - "Community 35"
Cohesion: 0.5
Nodes (1): Add is_published field to events table  Revision ID: ea0828634684 Revises: cb330

### Community 36 - "Community 36"
Cohesion: 0.5
Nodes (1): Add orders table and update allocations schema  Revision ID: c1d2e3f4g5h6 Revise

### Community 37 - "Community 37"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 0a32de8db265 Revises: c1d2e3f4g5h6 Create Date: 2026

### Community 38 - "Community 38"
Cohesion: 0.5
Nodes (1): Add scan_status_history table  Revision ID: cb3302c251d1 Revises: 91180041173a C

### Community 39 - "Community 39"
Cohesion: 0.5
Nodes (1): Add event interests table and interested counter  Revision ID: e1a2b3c4d5e6 Revi

### Community 40 - "Community 40"
Cohesion: 0.5
Nodes (0): 

### Community 41 - "Community 41"
Cohesion: 0.5
Nodes (0): 

### Community 42 - "Community 42"
Cohesion: 0.5
Nodes (0): 

### Community 43 - "Community 43"
Cohesion: 0.67
Nodes (2): Simple role type - all users are regular users., RoleType

### Community 44 - "Community 44"
Cohesion: 0.67
Nodes (0): 

### Community 45 - "Community 45"
Cohesion: 0.67
Nodes (0): 

### Community 46 - "Community 46"
Cohesion: 0.67
Nodes (0): 

### Community 47 - "Community 47"
Cohesion: 0.67
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
Nodes (0): 

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (0): 

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (1): Validate the required fields for the application.

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (1): Create a Database URL from the settings provided in the .env file.

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): Check if the app is running in production mode.

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): Check if the app is running in development mode.

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (1): Check if the app is running in local mode.

### Community 58 - "Community 58"
Cohesion: 1.0
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
Nodes (1): Validate banner image.          Args:             file_name: Original filename

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (1): Validate gallery image.

### Community 64 - "Community 64"
Cohesion: 1.0
Nodes (1): Validate gallery video.

### Community 65 - "Community 65"
Cohesion: 1.0
Nodes (1): Validate promo video URL.          Args:             url: Video URL (YouTube, Vi

### Community 66 - "Community 66"
Cohesion: 1.0
Nodes (1): Validate file extension against allowed types.

### Community 67 - "Community 67"
Cohesion: 1.0
Nodes (1): Validate image dimensions.

### Community 68 - "Community 68"
Cohesion: 1.0
Nodes (0): 

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (0): 

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (1): Step 1: Guest login creates guest record and returns tokens.          Expected:

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (1): Step 2: Guest protected endpoints require valid token.          Expected:

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (1): Step 3: Guest conversion creates User, links Guest, returns new tokens.

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (1): Step 4: Guest token refresh rotates the token pair.          Expected:         -

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (1): Step 5: Guest logout revokes the refresh token.          Expected:         - POS

## Knowledge Gaps
- **77 isolated node(s):** `Base custom exception class for raising necessary exceptions in the app.      At`, `Custom exception for representing a Bad Request (HTTP 400) error.`, `Custom exception for representing an Unauthorized (HTTP 401) error.`, `Custom exception for representing a Forbidden (HTTP 403) error.`, `Custom exception for representing a Not Found (HTTP 404) error.` (+72 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 48`** (2 nodes): `test_event_reseller_model.py`, `test_event_reseller_model_creation()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (2 nodes): `test_invite_models.py`, `test_invite_model_creation()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (2 nodes): `test_invite_enums.py`, `test_invite_status_values()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (2 nodes): `test_uuid_primary_key.py`, `test_uuid_primary_key_default_is_callable()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (2 nodes): `test_model_registry.py`, `test_model_registry_loads_organizer_table()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `Validate the required fields for the application.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `Create a Database URL from the settings provided in the .env file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `Check if the app is running in production mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `Check if the app is running in development mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `Check if the app is running in local mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `regex.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `messages.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `webhook.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `scheduler.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (1 nodes): `Validate banner image.          Args:             file_name: Original filename`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (1 nodes): `Validate gallery image.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `Validate gallery video.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 65`** (1 nodes): `Validate promo video URL.          Args:             url: Video URL (YouTube, Vi`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (1 nodes): `Validate file extension against allowed types.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (1 nodes): `Validate image dimensions.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (1 nodes): `model_registry.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (1 nodes): `seeder.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (1 nodes): `Step 1: Guest login creates guest record and returns tokens.          Expected:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (1 nodes): `Step 2: Guest protected endpoints require valid token.          Expected:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (1 nodes): `Step 3: Guest conversion creates User, links Guest, returns new tokens.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `Step 4: Guest token refresh rotates the token pair.          Expected:         -`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `Step 5: Guest logout revokes the refresh token.          Expected:         - POS`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FileValidationError` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 16`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `EventService` connect `Community 0` to `Community 1`, `Community 5`, `Community 14`, `Community 7`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Why does `EventRepository` connect `Community 5` to `Community 0`, `Community 1`, `Community 3`, `Community 7`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Are the 91 inferred relationships involving `FileValidationError` (e.g. with `Check if event is ready to publish, return section-by-section validation errors.` and `Publish event. Returns 400 with validation errors if not ready.`) actually correct?**
  _`FileValidationError` has 91 INFERRED edges - model-reasoned connections that need verification._
- **Are the 54 inferred relationships involving `EventService` (e.g. with `Check if event is ready to publish, return section-by-section validation errors.` and `Publish event. Returns 400 with validation errors if not ready.`) actually correct?**
  _`EventService` has 54 INFERRED edges - model-reasoned connections that need verification._
- **Are the 63 inferred relationships involving `CamelCaseModel` (e.g. with `TokenPayload` and `TokenPair`) actually correct?**
  _`CamelCaseModel` has 63 INFERRED edges - model-reasoned connections that need verification._
- **Are the 64 inferred relationships involving `EventModel` (e.g. with `EventService` and `Recursively convert UUID objects and Pydantic models to JSON-serializable format`) actually correct?**
  _`EventModel` has 64 INFERRED edges - model-reasoned connections that need verification._