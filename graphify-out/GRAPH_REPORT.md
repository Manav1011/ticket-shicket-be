# Graph Report - .  (2026-04-18)

## Corpus Check
- 151 files · ~156,176 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1167 nodes · 3582 edges · 61 communities detected
- Extraction: 39% EXTRACTED · 61% INFERRED · 0% AMBIGUOUS · INFERRED: 2170 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `FileValidationError` - 98 edges
2. `EventService` - 82 edges
3. `EventModel` - 72 edges
4. `EventMediaAssetModel` - 71 edges
5. `CamelCaseModel` - 69 edges
6. `EventAccessType` - 67 edges
7. `EventRepository` - 64 edges
8. `OrganizerService` - 63 edges
9. `OrganizerPageModel` - 62 edges
10. `UserModel` - 58 edges

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
Cohesion: 0.03
Nodes (88): Redis-based token blocklist for invalidating access tokens.  Uses a Redis SET to, Manages a Redis SET of blocked token JTIs., Add a jti to the blocklist.         Optionally set a TTL (in seconds) to auto-ex, Check if a jti is in the blocklist., Remove a jti from the blocklist (not typically needed)., TokenBlocklist, CustomException, ActorContext (+80 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (106): AppEnvironment, Enum representing different application environments.      - LOCAL: Indicates th, async_test_client(), auth_headers(), db_session(), guest_device_id(), invalid_file_type_bytes(), mock_s3_client() (+98 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (117): AlreadyExistsError, BadRequestError, create_password(), decrypt(), Create a random password.      :return: A randomly generated password., Decrypts the given encrypted data.      :param rsa_key: The RSA private key., AllocationLockError, AllocationOwnershipError (+109 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (89): BaseResponse, CamelCaseModel, InviteType, OrganizerVisibility, InviteNotFound, InviteRepository, OrganizerRepository, AllocateTicketTypeRequest (+81 more)

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (72): _collect_models(), mount_admin(), Admin integration helper for Starlette-Admin.  This module collects the project', Return a list of model classes to register in the admin UI., Attempt to initialize and mount Starlette-Admin at `/admin`.      This function, Base, Base, A mixin class to add a primary key field in a model. (+64 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (60): OrganizerService, mock_s3_client(), organizer_repo(), Integration tests for Organizer Media Asset workflow.  Tests the complete lifecy, Test that uploading a new logo replaces the existing one., Test that a valid 200x200+ image passes validation., Test that uploading a cover image updates the organizer's cover_image_url., Test that uploading a new cover replaces the existing one. (+52 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (22): Allocation app package., approve_b2b_request_free(), approve_b2b_request_paid(), convert_guest(), delete_media_asset(), generate_device_id(), get_b2b_request(), get_guest_self() (+14 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (19): PublicEventService, EventRepository, _AsyncNullContext, Open event with venue and all basic info complete should be ready., Ticketed event without tickets can publish but section marked incomplete., Ticketed event without tickets should NOT fail validation., Ticketed event day without start_time should fail schedule validation., Publishing event should set status, is_published, and published_at. (+11 more)

### Community 8 - "Community 8"
Cohesion: 0.05
Nodes (32): BaseSettings, AppGenerator, ColoredOutput, create_super_admin(), directory_created(), error(), file_created(), header() (+24 more)

### Community 9 - "Community 9"
Cohesion: 0.1
Nodes (32): BaseModel, B2BRequestStatus, TicketCategory, TicketingRepository, ApproveB2BRequestFreeBody, ApproveB2BRequestPaidBody, CreateB2BRequestBody, RejectB2BRequestBody (+24 more)

### Community 10 - "Community 10"
Cohesion: 0.1
Nodes (18): get_s3_client(), Wrapper around boto3 S3 client for event media uploads., Determine MIME type based on file extension., Get S3 client singleton., Upload file to S3 and return storage key.          Args:             resource_id, Delete file from S3.          Args:             storage_key: S3 storage key (pat, Generate public URL for file (works for LocalStack and real AWS).          Args:, S3Client (+10 more)

### Community 11 - "Community 11"
Cohesion: 0.15
Nodes (10): Exception raised for an unexpected HTTP response.      Attributes:         respo, Initialize the exception with the unexpected HTTP response.          Args:, UnexpectedResponse, HTTPClient, Send a PATCH request.          :param url: The URL to send the request to. Defau, Deletes a resource at the specified URL.          :param url: The URL of the res, Send a GET request.          :param url: The URL to send the request to. Default, Send a POST request.          :param url: The URL to send the request to. Defaul (+2 more)

### Community 12 - "Community 12"
Cohesion: 0.12
Nodes (1): PublicOrganizerService

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (0): 

### Community 14 - "Community 14"
Cohesion: 0.17
Nodes (0): 

### Community 15 - "Community 15"
Cohesion: 0.2
Nodes (8): Test that upload endpoint calls service method., Test listing media assets returns list., Test delete endpoint calls service., Test update metadata endpoint., test_delete_media_asset_calls_service(), test_list_media_assets_returns_list(), test_update_media_asset_metadata(), test_upload_media_asset_calls_service()

### Community 16 - "Community 16"
Cohesion: 0.22
Nodes (3): Integration tests for Guest Module - Full Flow  These tests document the complet, Integration test covering complete guest lifecycle.      This test class documen, TestGuestFullLifecycle

### Community 17 - "Community 17"
Cohesion: 0.5
Nodes (7): validate_banner_image(), _validate_file_size(), _validate_file_type(), validate_gallery_image(), validate_gallery_video(), _validate_image_dimensions(), validate_promo_video_url()

### Community 18 - "Community 18"
Cohesion: 0.33
Nodes (0): 

### Community 19 - "Community 19"
Cohesion: 0.5
Nodes (2): strong_password(), validate_input_fields()

### Community 20 - "Community 20"
Cohesion: 0.4
Nodes (0): 

### Community 21 - "Community 21"
Cohesion: 0.4
Nodes (0): 

### Community 22 - "Community 22"
Cohesion: 0.4
Nodes (0): 

### Community 23 - "Community 23"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 7c7609b23301 Revises: 760216553727 Create Date: 2026

### Community 24 - "Community 24"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 760216553727 Revises:  Create Date: 2026-04-15 22:30

### Community 25 - "Community 25"
Cohesion: 0.5
Nodes (0): 

### Community 26 - "Community 26"
Cohesion: 0.5
Nodes (2): get_current_super_admin should set request.state.super_admin AND return the admi, test_get_current_super_admin_sets_request_state()

### Community 27 - "Community 27"
Cohesion: 0.5
Nodes (0): 

### Community 28 - "Community 28"
Cohesion: 0.5
Nodes (0): 

### Community 29 - "Community 29"
Cohesion: 0.67
Nodes (2): Simple role type - all users are regular users., RoleType

### Community 30 - "Community 30"
Cohesion: 0.67
Nodes (0): 

### Community 31 - "Community 31"
Cohesion: 0.67
Nodes (0): 

### Community 32 - "Community 32"
Cohesion: 0.67
Nodes (0): 

### Community 33 - "Community 33"
Cohesion: 0.67
Nodes (0): 

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (0): 

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (0): 

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (0): 

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (0): 

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (0): 

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): Validate the required fields for the application.

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): Create a Database URL from the settings provided in the .env file.

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): Check if the app is running in production mode.

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Check if the app is running in development mode.

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): Check if the app is running in local mode.

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
Nodes (0): 

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): Validate banner image.          Args:             file_name: Original filename

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): Validate gallery image.

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (1): Validate gallery video.

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (1): Validate promo video URL.          Args:             url: Video URL (YouTube, Vi

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): Validate file extension against allowed types.

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (1): Validate image dimensions.

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (0): 

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (0): 

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): Step 1: Guest login creates guest record and returns tokens.          Expected:

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (1): Step 2: Guest protected endpoints require valid token.          Expected:

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (1): Step 3: Guest conversion creates User, links Guest, returns new tokens.

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (1): Step 4: Guest token refresh rotates the token pair.          Expected:         -

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (1): Step 5: Guest logout revokes the refresh token.          Expected:         - POS

## Knowledge Gaps
- **63 isolated node(s):** `Base custom exception class for raising necessary exceptions in the app.      At`, `Custom exception for representing a Bad Request (HTTP 400) error.`, `Custom exception for representing an Unauthorized (HTTP 401) error.`, `Custom exception for representing a Forbidden (HTTP 403) error.`, `Custom exception for representing a Not Found (HTTP 404) error.` (+58 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 34`** (2 nodes): `test_event_reseller_model.py`, `test_event_reseller_model_creation()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (2 nodes): `test_invite_models.py`, `test_invite_model_creation()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (2 nodes): `test_invite_enums.py`, `test_invite_status_values()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (2 nodes): `test_uuid_primary_key.py`, `test_uuid_primary_key_default_is_callable()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (2 nodes): `test_model_registry.py`, `test_model_registry_loads_organizer_table()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `Validate the required fields for the application.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `Create a Database URL from the settings provided in the .env file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `Check if the app is running in production mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Check if the app is running in development mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `Check if the app is running in local mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `regex.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `messages.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `webhook.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `scheduler.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `Validate banner image.          Args:             file_name: Original filename`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `Validate gallery image.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `Validate gallery video.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `Validate promo video URL.          Args:             url: Video URL (YouTube, Vi`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `Validate file extension against allowed types.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `Validate image dimensions.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `model_registry.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `seeder.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `Step 1: Guest login creates guest record and returns tokens.          Expected:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `Step 2: Guest protected endpoints require valid token.          Expected:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `Step 3: Guest conversion creates User, links Guest, returns new tokens.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `Step 4: Guest token refresh rotates the token pair.          Expected:         -`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `Step 5: Guest logout revokes the refresh token.          Expected:         - POS`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FileValidationError` connect `Community 1` to `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 17`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `EventService` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 7`, `Community 15`?**
  _High betweenness centrality (0.082) - this node is a cross-community bridge._
- **Why does `EventRepository` connect `Community 7` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 9`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Are the 91 inferred relationships involving `FileValidationError` (e.g. with `Check if event is ready to publish, return section-by-section validation errors.` and `Publish event. Returns 400 with validation errors if not ready.`) actually correct?**
  _`FileValidationError` has 91 INFERRED edges - model-reasoned connections that need verification._
- **Are the 54 inferred relationships involving `EventService` (e.g. with `Check if event is ready to publish, return section-by-section validation errors.` and `Publish event. Returns 400 with validation errors if not ready.`) actually correct?**
  _`EventService` has 54 INFERRED edges - model-reasoned connections that need verification._
- **Are the 68 inferred relationships involving `EventModel` (e.g. with `Admin integration helper for Starlette-Admin.  This module collects the project'` and `Return a list of model classes to register in the admin UI.`) actually correct?**
  _`EventModel` has 68 INFERRED edges - model-reasoned connections that need verification._
- **Are the 67 inferred relationships involving `EventMediaAssetModel` (e.g. with `Admin integration helper for Starlette-Admin.  This module collects the project'` and `Return a list of model classes to register in the admin UI.`) actually correct?**
  _`EventMediaAssetModel` has 67 INFERRED edges - model-reasoned connections that need verification._