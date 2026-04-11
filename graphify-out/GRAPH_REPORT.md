# Graph Report - .  (2026-04-11)

## Corpus Check
- 116 files · ~101,200 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 908 nodes · 2484 edges · 60 communities detected
- Extraction: 43% EXTRACTED · 57% INFERRED · 0% AMBIGUOUS · INFERRED: 1427 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `FileValidationError` - 93 edges
2. `EventService` - 76 edges
3. `EventModel` - 69 edges
4. `EventMediaAssetModel` - 68 edges
5. `EventAccessType` - 65 edges
6. `OrganizerPageModel` - 54 edges
7. `CamelCaseModel` - 53 edges
8. `UserModel` - 52 edges
9. `UnauthorizedError` - 48 edges
10. `AssetType` - 47 edges

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
Cohesion: 0.04
Nodes (92): BaseModel, CamelCaseModel, Ticketing app package.  Keep package imports side-effect free so model imports r, OrganizerRepository, AllocateTicketTypeRequest, CreateDraftEventRequest, CreateEventDayRequest, CreateOrganizerPageRequest (+84 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (92): AlreadyExistsError, BadRequestError, Redis-based token blocklist for invalidating access tokens.  Uses a Redis SET to, Manages a Redis SET of blocked token JTIs., Add a jti to the blocklist.         Optionally set a TTL (in seconds) to auto-ex, Check if a jti is in the blocklist., Remove a jti from the blocklist (not typically needed)., TokenBlocklist (+84 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (90): async_test_client(), auth_headers(), db_session(), guest_device_id(), invalid_file_type_bytes(), mock_s3_client(), oversized_image_bytes(), Create FastAPI app with mocked lifespan for HTTP testing. (+82 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (39): Base, Base, A mixin class to add a primary key field in a model., Base class for defining database tables., A mixin class to add automatic timestamp fields.      Adds `created_at` and `upd, TimeStampMixin, UUIDPrimaryKeyMixin, DeclarativeBase (+31 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (73): OrganizerNotFound, FileValidationError, Raised when file validation fails., validate_banner_image(), _validate_file_size(), _validate_file_type(), validate_gallery_image(), validate_gallery_video() (+65 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (49): EventNotFound, ForbiddenError, InvalidAsset, InvalidScanTransition, OrganizerOwnershipError, Custom exception for representing a Forbidden (HTTP 403) error., ValidationError, FileValidator (+41 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (34): BaseSettings, AppEnvironment, assemble_db_url(), Enum representing different application environments.      - LOCAL: Indicates th, A settings class for the project defining all the necessary parameters within th, Settings, delete_cookies(), Delete authentication cookies from an HTTP response.      Args:         response (+26 more)

### Community 7 - "Community 7"
Cohesion: 0.1
Nodes (18): get_s3_client(), Wrapper around boto3 S3 client for event media uploads., Determine MIME type based on file extension., Get S3 client singleton., Upload file to S3 and return storage key.          Args:             resource_id, Delete file from S3.          Args:             storage_key: S3 storage key (pat, Generate public URL for file (works for LocalStack and real AWS).          Args:, S3Client (+10 more)

### Community 8 - "Community 8"
Cohesion: 0.15
Nodes (13): AppGenerator, ColoredOutput, directory_created(), error(), file_created(), header(), highlight(), info() (+5 more)

### Community 9 - "Community 9"
Cohesion: 0.14
Nodes (11): Exception, Exception raised for an unexpected HTTP response.      Attributes:         respo, Initialize the exception with the unexpected HTTP response.          Args:, UnexpectedResponse, HTTPClient, Send a PATCH request.          :param url: The URL to send the request to. Defau, Deletes a resource at the specified URL.          :param url: The URL of the res, Send a GET request.          :param url: The URL to send the request to. Default (+3 more)

### Community 10 - "Community 10"
Cohesion: 0.11
Nodes (8): Open event with venue and all basic info complete should be ready., Ticketed event without ticket types should fail validation., Ticketed event day without start_time should fail schedule validation., Publishing event should set status, is_published, and published_at., test_publish_event_sets_published_fields(), test_validate_for_publish_open_venue_complete(), test_validate_for_publish_ticketed_missing_tickets(), test_validate_for_publish_ticketed_no_start_time()

### Community 11 - "Community 11"
Cohesion: 0.15
Nodes (0): 

### Community 12 - "Community 12"
Cohesion: 0.15
Nodes (10): Adding a jti should add it to the Redis set., Blocked jti should return True., Non-blocklisted jti should return False., Adding a jti with TTL should also set expiry on the set., Removing a jti should remove it from the Redis set., test_add_jti_to_blocklist(), test_add_jti_with_ttl(), test_is_jti_blocklisted_false() (+2 more)

### Community 13 - "Community 13"
Cohesion: 0.17
Nodes (1): GuestRepository

### Community 14 - "Community 14"
Cohesion: 0.2
Nodes (8): Test that upload endpoint calls service method., Test listing media assets returns list., Test delete endpoint calls service., Test update metadata endpoint., test_delete_media_asset_calls_service(), test_list_media_assets_returns_list(), test_update_media_asset_metadata(), test_upload_media_asset_calls_service()

### Community 15 - "Community 15"
Cohesion: 0.22
Nodes (3): Integration tests for Guest Module - Full Flow  These tests document the complet, Integration test covering complete guest lifecycle.      This test class documen, TestGuestFullLifecycle

### Community 16 - "Community 16"
Cohesion: 0.29
Nodes (2): test_update_ticket_allocation_quantity_calls_service_correctly(), test_update_ticket_allocation_quantity_increases_successfully()

### Community 17 - "Community 17"
Cohesion: 0.4
Nodes (4): create_password(), decrypt(), Create a random password.      :return: A randomly generated password., Decrypts the given encrypted data.      :param rsa_key: The RSA private key.

### Community 18 - "Community 18"
Cohesion: 0.5
Nodes (2): strong_password(), validate_input_fields()

### Community 19 - "Community 19"
Cohesion: 0.4
Nodes (0): 

### Community 20 - "Community 20"
Cohesion: 0.4
Nodes (0): 

### Community 21 - "Community 21"
Cohesion: 0.4
Nodes (0): 

### Community 22 - "Community 22"
Cohesion: 0.5
Nodes (1): add guests table  Revision ID: b27c8820610c Revises: 05160b3cd708 Create Date: 2

### Community 23 - "Community 23"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 05160b3cd708 Revises:  Create Date: 2026-04-02 19:55

### Community 24 - "Community 24"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: d5ede614f47b Revises: 9bf5b22783b2 Create Date: 2026

### Community 25 - "Community 25"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 479742328475 Revises: d5ede614f47b Create Date: 2026

### Community 26 - "Community 26"
Cohesion: 0.5
Nodes (1): add phase one event tables  Revision ID: 91180041173a Revises: b27c8820610c Crea

### Community 27 - "Community 27"
Cohesion: 0.5
Nodes (1): convert_string_columns_to_enum_types  Revision ID: 9bf5b22783b2 Revises: ea08286

### Community 28 - "Community 28"
Cohesion: 0.5
Nodes (1): Add is_published field to events table  Revision ID: ea0828634684 Revises: cb330

### Community 29 - "Community 29"
Cohesion: 0.5
Nodes (1): Add scan_status_history table  Revision ID: cb3302c251d1 Revises: 91180041173a C

### Community 30 - "Community 30"
Cohesion: 0.5
Nodes (0): 

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
Cohesion: 1.0
Nodes (0): 

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (0): 

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): Validate the required fields for the application.

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): Create a Database URL from the settings provided in the .env file.

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): Check if the app is running in production mode.

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): Check if the app is running in development mode.

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Check if the app is running in local mode.

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (0): 

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (0): 

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (0): 

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (0): 

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): Validate banner image.          Args:             file_name: Original filename

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): Validate gallery image.

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): Validate gallery video.

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (1): Validate promo video URL.          Args:             url: Video URL (YouTube, Vi

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (1): Validate file extension against allowed types.

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): Validate image dimensions.

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (0): 

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (0): 

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): Step 1: Guest login creates guest record and returns tokens.          Expected:

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): Step 2: Guest protected endpoints require valid token.          Expected:

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (1): Step 3: Guest conversion creates User, links Guest, returns new tokens.

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (1): Step 4: Guest token refresh rotates the token pair.          Expected:         -

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (1): Step 5: Guest logout revokes the refresh token.          Expected:         - POS

## Knowledge Gaps
- **66 isolated node(s):** `Base custom exception class for raising necessary exceptions in the app.      At`, `Custom exception for representing a Bad Request (HTTP 400) error.`, `Custom exception for representing an Unauthorized (HTTP 401) error.`, `Custom exception for representing a Forbidden (HTTP 403) error.`, `Custom exception for representing a Not Found (HTTP 404) error.` (+61 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 36`** (2 nodes): `test_uuid_primary_key.py`, `test_uuid_primary_key_default_is_callable()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (2 nodes): `test_model_registry.py`, `test_model_registry_loads_organizer_table()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `Validate the required fields for the application.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `Create a Database URL from the settings provided in the .env file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `Check if the app is running in production mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `Check if the app is running in development mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Check if the app is running in local mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `regex.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `messages.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `webhook.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `scheduler.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `Validate banner image.          Args:             file_name: Original filename`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `Validate gallery image.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `Validate gallery video.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `Validate promo video URL.          Args:             url: Video URL (YouTube, Vi`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `Validate file extension against allowed types.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `Validate image dimensions.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `model_registry.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `seeder.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `Step 1: Guest login creates guest record and returns tokens.          Expected:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `Step 2: Guest protected endpoints require valid token.          Expected:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `Step 3: Guest conversion creates User, links Guest, returns new tokens.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `Step 4: Guest token refresh rotates the token pair.          Expected:         -`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `Step 5: Guest logout revokes the refresh token.          Expected:         - POS`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FileValidationError` connect `Community 4` to `Community 0`, `Community 9`, `Community 2`, `Community 5`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Why does `EventService` connect `Community 2` to `Community 0`, `Community 1`, `Community 4`, `Community 5`, `Community 10`, `Community 14`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Why does `Convert guest to user at checkout.     Requires valid guest token.     Creates U` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 13`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Are the 86 inferred relationships involving `FileValidationError` (e.g. with `Check if event is ready to publish, return section-by-section validation errors.` and `Convert guest to user at checkout.     Requires valid guest token.     Creates U`) actually correct?**
  _`FileValidationError` has 86 INFERRED edges - model-reasoned connections that need verification._
- **Are the 50 inferred relationships involving `EventService` (e.g. with `Check if event is ready to publish, return section-by-section validation errors.` and `Convert guest to user at checkout.     Requires valid guest token.     Creates U`) actually correct?**
  _`EventService` has 50 INFERRED edges - model-reasoned connections that need verification._
- **Are the 65 inferred relationships involving `EventModel` (e.g. with `EventService` and `Recursively convert UUID objects and Pydantic models to JSON-serializable format`) actually correct?**
  _`EventModel` has 65 INFERRED edges - model-reasoned connections that need verification._
- **Are the 64 inferred relationships involving `EventMediaAssetModel` (e.g. with `EventService` and `Recursively convert UUID objects and Pydantic models to JSON-serializable format`) actually correct?**
  _`EventMediaAssetModel` has 64 INFERRED edges - model-reasoned connections that need verification._