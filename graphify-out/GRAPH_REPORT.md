# Graph Report - .  (2026-04-18)

## Corpus Check
- 158 files · ~161,969 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1206 nodes · 3781 edges · 57 communities detected
- Extraction: 38% EXTRACTED · 62% INFERRED · 0% AMBIGUOUS · INFERRED: 2326 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `FileValidationError` - 101 edges
2. `EventService` - 84 edges
3. `EventRepository` - 84 edges
4. `CamelCaseModel` - 74 edges
5. `EventModel` - 72 edges
6. `EventMediaAssetModel` - 71 edges
7. `EventAccessType` - 70 edges
8. `OrganizerService` - 69 edges
9. `OrganizerPageModel` - 64 edges
10. `BaseResponse` - 60 edges

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
Nodes (113): BadRequestError, Redis-based token blocklist for invalidating access tokens.  Uses a Redis SET to, Manages a Redis SET of blocked token JTIs., Add a jti to the blocklist.         Optionally set a TTL (in seconds) to auto-ex, Check if a jti is in the blocklist., Remove a jti from the blocklist (not typically needed)., TokenBlocklist, CustomException (+105 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (131): AlreadyExistsError, AlreadyExistsError, EventNotFound, ForbiddenError, InvalidAsset, InvalidScanTransition, InviteAlreadyProcessed, NotInviteRecipient (+123 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (135): _collect_models(), mount_admin(), Admin integration helper for Starlette-Admin.  This module collects the project', Return a list of model classes to register in the admin UI., Attempt to initialize and mount Starlette-Admin at `/admin`.      This function, Base, Base, A mixin class to add a primary key field in a model. (+127 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (93): BaseResponse, CamelCaseModel, InviteType, InviteNotFound, GuestRepository, InviteRepository, AllocateTicketTypeRequest, CreateDraftEventRequest (+85 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (75): BaseModel, B2BRequestStatus, OrganizerVisibility, TicketCategory, Allocation app package., TicketingRepository, ApproveB2BRequestFreeBody, ApproveB2BRequestPaidBody (+67 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (29): PublicEventService, EventRepository, EventService, _serialize_for_json(), Test that upload endpoint calls service method., Test listing media assets returns list., Test delete endpoint calls service., Test update metadata endpoint. (+21 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (55): AppEnvironment, Enum representing different application environments.      - LOCAL: Indicates th, Enum, AllocationSourceType, AllocationStatus, AllocationType, CouponType, EventType (+47 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (42): BaseSettings, AppGenerator, ColoredOutput, create_super_admin(), directory_created(), error(), file_created(), header() (+34 more)

### Community 8 - "Community 8"
Cohesion: 0.1
Nodes (18): get_s3_client(), Wrapper around boto3 S3 client for event media uploads., Determine MIME type based on file extension., Get S3 client singleton., Upload file to S3 and return storage key.          Args:             resource_id, Delete file from S3.          Args:             storage_key: S3 storage key (pat, Generate public URL for file (works for LocalStack and real AWS).          Args:, S3Client (+10 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (1): PublicOrganizerService

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (0): 

### Community 11 - "Community 11"
Cohesion: 0.15
Nodes (10): Adding a jti should add it to the Redis set., Blocked jti should return True., Non-blocklisted jti should return False., Adding a jti with TTL should also set expiry on the set., Removing a jti should remove it from the Redis set., test_add_jti_to_blocklist(), test_add_jti_with_ttl(), test_is_jti_blocklisted_false() (+2 more)

### Community 12 - "Community 12"
Cohesion: 0.17
Nodes (0): 

### Community 13 - "Community 13"
Cohesion: 0.22
Nodes (3): Integration tests for Guest Module - Full Flow  These tests document the complet, Integration test covering complete guest lifecycle.      This test class documen, TestGuestFullLifecycle

### Community 14 - "Community 14"
Cohesion: 0.33
Nodes (0): 

### Community 15 - "Community 15"
Cohesion: 0.5
Nodes (2): strong_password(), validate_input_fields()

### Community 16 - "Community 16"
Cohesion: 0.4
Nodes (0): 

### Community 17 - "Community 17"
Cohesion: 0.4
Nodes (0): 

### Community 18 - "Community 18"
Cohesion: 0.4
Nodes (0): 

### Community 19 - "Community 19"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 7c7609b23301 Revises: 760216553727 Create Date: 2026

### Community 20 - "Community 20"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 760216553727 Revises:  Create Date: 2026-04-15 22:30

### Community 21 - "Community 21"
Cohesion: 0.5
Nodes (1): empty message  Revision ID: 86361eeddf67 Revises: 7c7609b23301 Create Date: 2026

### Community 22 - "Community 22"
Cohesion: 0.5
Nodes (0): 

### Community 23 - "Community 23"
Cohesion: 0.5
Nodes (0): 

### Community 24 - "Community 24"
Cohesion: 0.5
Nodes (0): 

### Community 25 - "Community 25"
Cohesion: 0.67
Nodes (2): Simple role type - all users are regular users., RoleType

### Community 26 - "Community 26"
Cohesion: 0.67
Nodes (0): 

### Community 27 - "Community 27"
Cohesion: 0.67
Nodes (0): 

### Community 28 - "Community 28"
Cohesion: 0.67
Nodes (0): 

### Community 29 - "Community 29"
Cohesion: 0.67
Nodes (0): 

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (0): 

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (0): 

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (0): 

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (0): 

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (0): 

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Validate the required fields for the application.

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Create a Database URL from the settings provided in the .env file.

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): Check if the app is running in production mode.

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): Check if the app is running in development mode.

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): Check if the app is running in local mode.

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (0): 

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (0): 

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (0): 

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (0): 

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (1): Validate banner image.          Args:             file_name: Original filename

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (1): Validate gallery image.

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (1): Validate gallery video.

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): Validate promo video URL.          Args:             url: Video URL (YouTube, Vi

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): Validate file extension against allowed types.

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): Validate image dimensions.

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (0): 

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (0): 

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): Step 1: Guest login creates guest record and returns tokens.          Expected:

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (1): Step 2: Guest protected endpoints require valid token.          Expected:

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (1): Step 3: Guest conversion creates User, links Guest, returns new tokens.

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): Step 4: Guest token refresh rotates the token pair.          Expected:         -

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): Step 5: Guest logout revokes the refresh token.          Expected:         - POS

## Knowledge Gaps
- **64 isolated node(s):** `Base custom exception class for raising necessary exceptions in the app.      At`, `Custom exception for representing a Bad Request (HTTP 400) error.`, `Custom exception for representing an Unauthorized (HTTP 401) error.`, `Custom exception for representing a Forbidden (HTTP 403) error.`, `Custom exception for representing a Not Found (HTTP 404) error.` (+59 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 30`** (2 nodes): `test_event_reseller_model.py`, `test_event_reseller_model_creation()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (2 nodes): `test_invite_models.py`, `test_invite_model_creation()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (2 nodes): `test_invite_enums.py`, `test_invite_status_values()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (2 nodes): `test_uuid_primary_key.py`, `test_uuid_primary_key_default_is_callable()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (2 nodes): `test_model_registry.py`, `test_model_registry_loads_organizer_table()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Validate the required fields for the application.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Create a Database URL from the settings provided in the .env file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Check if the app is running in production mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `Check if the app is running in development mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `Check if the app is running in local mode.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `regex.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `messages.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `webhook.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `scheduler.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `Validate banner image.          Args:             file_name: Original filename`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `Validate gallery image.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `Validate gallery video.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `Validate promo video URL.          Args:             url: Video URL (YouTube, Vi`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `Validate file extension against allowed types.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `Validate image dimensions.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `model_registry.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `seeder.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `Step 1: Guest login creates guest record and returns tokens.          Expected:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `Step 2: Guest protected endpoints require valid token.          Expected:`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `Step 3: Guest conversion creates User, links Guest, returns new tokens.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `Step 4: Guest token refresh rotates the token pair.          Expected:         -`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `Step 5: Guest logout revokes the refresh token.          Expected:         - POS`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `EventService` connect `Community 5` to `Community 1`, `Community 2`, `Community 3`, `Community 6`?**
  _High betweenness centrality (0.082) - this node is a cross-community bridge._
- **Why does `FileValidationError` connect `Community 1` to `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Why does `EventRepository` connect `Community 5` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 6`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Are the 94 inferred relationships involving `FileValidationError` (e.g. with `Check if event is ready to publish, return section-by-section validation errors.` and `Publish event. Returns 400 with validation errors if not ready.`) actually correct?**
  _`FileValidationError` has 94 INFERRED edges - model-reasoned connections that need verification._
- **Are the 56 inferred relationships involving `EventService` (e.g. with `Check if event is ready to publish, return section-by-section validation errors.` and `Publish event. Returns 400 with validation errors if not ready.`) actually correct?**
  _`EventService` has 56 INFERRED edges - model-reasoned connections that need verification._
- **Are the 56 inferred relationships involving `EventRepository` (e.g. with `Check if event is ready to publish, return section-by-section validation errors.` and `Publish event. Returns 400 with validation errors if not ready.`) actually correct?**
  _`EventRepository` has 56 INFERRED edges - model-reasoned connections that need verification._
- **Are the 68 inferred relationships involving `CamelCaseModel` (e.g. with `TokenPayload` and `TokenPair`) actually correct?**
  _`CamelCaseModel` has 68 INFERRED edges - model-reasoned connections that need verification._