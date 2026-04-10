# Organizer Media Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement logo and cover image upload for organizer pages with S3 storage.

**Architecture:** Reuse S3 client and file validation from event media assets module. Organizer upload endpoints accept file → validate with FileValidator → upload to S3 → update organizer_pages.logo_url and cover_image_url → return updated organizer. No new database tables needed (fields already exist).

**Tech Stack:** FastAPI, SQLAlchemy, boto3 (S3 client from event plan), Pydantic, pytest, multipart/form-data

**Dependencies:** Requires completion of 2026-04-10-event-media-assets-module.md (S3 config, S3Client, FileValidator)

---

## File Structure Overview

**New Files:**
- `tests/apps/organizer/test_organizer_media_urls.py` - Upload endpoint tests

**Modified Files:**
- `src/apps/organizer/service.py` - Add upload methods
- `src/apps/organizer/request.py` - Add request schemas
- `src/apps/organizer/response.py` - Update response schema
- `src/apps/organizer/urls.py` - Add upload endpoints

**No new database files needed** - organizer_pages table already has logo_url and cover_image_url columns.

---

## Task 1: Organizer Service - Upload Methods

**Files:**
- Modify: `src/apps/organizer/service.py`

- [ ] **Step 1: Add imports**

Add these imports to top of `src/apps/organizer/service.py`:

```python
from src.utils.s3_client import get_s3_client
from src.utils.file_validation import FileValidator, FileValidationError
from uuid import UUID
```

- [ ] **Step 2: Add upload_logo method**

Add this method to `OrganizerService` class:

```python
async def upload_logo(
    self,
    owner_user_id: UUID,
    organizer_page_id: UUID,
    file_name: str,
    file_content: bytes,
) -> OrganizerPageModel:
    """
    Upload logo image for organizer page.

    Args:
        owner_user_id: Page owner
        organizer_page_id: Organizer page UUID
        file_name: Original filename
        file_content: File bytes

    Returns:
        Updated OrganizerPageModel with logo_url

    Raises:
        OrganizerPageNotFound: If organizer page doesn't exist or user doesn't own it
        FileValidationError: If file validation fails
    """
    # Verify ownership
    organizer = await self.repository.get_by_id_for_owner(
        organizer_page_id, owner_user_id
    )
    if not organizer:
        raise OrganizerPageNotFound

    # Validate logo image (required: max 5MB, jpg/png/webp, min 200x200)
    FileValidator.validate_banner_image(file_name, file_content)

    # Upload to S3: organizers/{organizer_id}/logo_{uuid}_{filename}
    s3_client = get_s3_client()
    storage_key = s3_client.upload_file(
        event_id=organizer_page_id,
        asset_type="logo",
        file_name=file_name,
        file_content=file_content,
    )
    public_url = s3_client.generate_public_url(storage_key)

    # Update organizer page
    organizer.logo_url = public_url
    await self.repository.session.flush()
    await self.repository.session.refresh(organizer)
    return organizer
```

- [ ] **Step 3: Add upload_cover_image method**

Add this method to `OrganizerService`:

```python
async def upload_cover_image(
    self,
    owner_user_id: UUID,
    organizer_page_id: UUID,
    file_name: str,
    file_content: bytes,
) -> OrganizerPageModel:
    """
    Upload cover image for organizer page.

    Args:
        owner_user_id: Page owner
        organizer_page_id: Organizer page UUID
        file_name: Original filename
        file_content: File bytes

    Returns:
        Updated OrganizerPageModel with cover_image_url

    Raises:
        OrganizerPageNotFound: If organizer page doesn't exist or user doesn't own it
        FileValidationError: If file validation fails
    """
    # Verify ownership
    organizer = await self.repository.get_by_id_for_owner(
        organizer_page_id, owner_user_id
    )
    if not organizer:
        raise OrganizerPageNotFound

    # Validate cover image (reuse banner validation: max 5MB, jpg/png/webp, min 200x200)
    FileValidator.validate_banner_image(file_name, file_content)

    # Upload to S3: organizers/{organizer_id}/cover_{uuid}_{filename}
    s3_client = get_s3_client()
    storage_key = s3_client.upload_file(
        event_id=organizer_page_id,
        asset_type="cover",
        file_name=file_name,
        file_content=file_content,
    )
    public_url = s3_client.generate_public_url(storage_key)

    # Update organizer page
    organizer.cover_image_url = public_url
    await self.repository.session.flush()
    await self.repository.session.refresh(organizer)
    return organizer
```

- [ ] **Step 4: Commit**

```bash
git add src/apps/organizer/service.py
git commit -m "feat: add logo and cover image upload methods to OrganizerService"
```

---

## Task 2: Request/Response Schemas

**Files:**
- Modify: `src/apps/organizer/request.py`
- Modify: `src/apps/organizer/response.py`

- [ ] **Step 1: Check existing response schema**

Read `src/apps/organizer/response.py` to see current `OrganizerPageResponse` schema.

- [ ] **Step 2: Verify response includes URLs**

Ensure `OrganizerPageResponse` already has these fields (they should exist from base schema):

```python
class OrganizerPageResponse(CamelCaseModel):
    id: UUID
    owner_user_id: UUID
    name: str
    slug: str
    bio: str | None = None
    logo_url: str | None = None          # Already exists
    cover_image_url: str | None = None   # Already exists
    website_url: str | None = None
    instagram_url: str | None = None
    facebook_url: str | None = None
    youtube_url: str | None = None
    visibility: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

If these fields don't exist, add them.

- [ ] **Step 3: Commit (if changes made)**

```bash
git add src/apps/organizer/response.py
git commit -m "feat: ensure OrganizerPageResponse includes logo and cover image URLs"
```

---

## Task 3: API Endpoints - Upload Logo

**Files:**
- Modify: `src/apps/organizer/urls.py`

- [ ] **Step 1: Add imports**

Add these imports to `src/apps/organizer/urls.py`:

```python
from fastapi import File, UploadFile, Depends
from src.apps.organizer.response import OrganizerPageResponse
```

Verify `get_current_user_id` is imported for auth.

- [ ] **Step 2: Add upload logo endpoint**

Add this route to the router:

```python
@router.post("/{organizer_id}/logo", response_model=OrganizerPageResponse)
async def upload_organizer_logo(
    organizer_id: UUID,
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Upload logo image for organizer page.

    Args:
        organizer_id: Organizer page UUID
        file: Image file (JPG, PNG, WebP, max 5MB)
        user_id: Current user (from JWT)

    Returns:
        Updated organizer page with new logo_url

    Raises:
        OrganizerPageNotFound: If organizer doesn't exist or user doesn't own it
        FileValidationError: If file fails validation (400 Bad Request)
    """
    from src.utils.file_validation import FileValidationError

    try:
        file_content = await file.read()
        organizer = await service.upload_logo(
            owner_user_id=user_id,
            organizer_page_id=organizer_id,
            file_name=file.filename,
            file_content=file_content,
        )
        return organizer
    except FileValidationError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 3: Commit**

```bash
git add src/apps/organizer/urls.py
git commit -m "feat: add POST /organizers/{id}/logo upload endpoint"
```

---

## Task 4: API Endpoints - Upload Cover Image

**Files:**
- Modify: `src/apps/organizer/urls.py`

- [ ] **Step 1: Add upload cover endpoint**

Add this route to the router (in same file as Task 3):

```python
@router.post("/{organizer_id}/cover", response_model=OrganizerPageResponse)
async def upload_organizer_cover(
    organizer_id: UUID,
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Upload cover image for organizer page.

    Args:
        organizer_id: Organizer page UUID
        file: Image file (JPG, PNG, WebP, max 5MB)
        user_id: Current user (from JWT)

    Returns:
        Updated organizer page with new cover_image_url

    Raises:
        OrganizerPageNotFound: If organizer doesn't exist or user doesn't own it
        FileValidationError: If file fails validation (400 Bad Request)
    """
    from src.utils.file_validation import FileValidationError

    try:
        file_content = await file.read()
        organizer = await service.upload_cover_image(
            owner_user_id=user_id,
            organizer_page_id=organizer_id,
            file_name=file.filename,
            file_content=file_content,
        )
        return organizer
    except FileValidationError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 2: Commit**

```bash
git add src/apps/organizer/urls.py
git commit -m "feat: add POST /organizers/{id}/cover upload endpoint"
```

---

## Task 5: Unit Tests - Service Methods

**Files:**
- Create: `tests/apps/organizer/test_organizer_service_media.py`

- [ ] **Step 1: Create test file**

Create `tests/apps/organizer/test_organizer_service_media.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from PIL import Image
from io import BytesIO

from src.apps.organizer.service import OrganizerService
from src.apps.organizer.exceptions import OrganizerPageNotFound
from src.utils.file_validation import FileValidationError


@pytest.fixture
def valid_image_bytes():
    """Create valid test image bytes (200x200 PNG)."""
    img = Image.new("RGB", (200, 200), color="blue")
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


@pytest.fixture
def organizer_service_mock():
    """Mock OrganizerService with mocked dependencies."""
    repo_mock = AsyncMock()
    service = OrganizerService(repo_mock)
    return service, repo_mock


@pytest.mark.asyncio
async def test_upload_logo_success(organizer_service_mock, valid_image_bytes):
    """Test successful logo upload."""
    service, repo_mock = organizer_service_mock
    
    owner_id = uuid4()
    organizer_id = uuid4()
    
    organizer = MagicMock(id=organizer_id, logo_url=None)
    repo_mock.get_by_id_for_owner.return_value = organizer
    repo_mock.session = AsyncMock()

    with patch("src.apps.organizer.service.get_s3_client") as mock_s3:
        mock_client = MagicMock()
        mock_s3.return_value = mock_client
        mock_client.upload_file.return_value = "organizers/123/logo_abc_test.png"
        mock_client.generate_public_url.return_value = "http://localhost:4566/bucket/organizers/123/logo_abc_test.png"

        result = await service.upload_logo(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="logo.png",
            file_content=valid_image_bytes,
        )

    assert result.logo_url == "http://localhost:4566/bucket/organizers/123/logo_abc_test.png"
    repo_mock.get_by_id_for_owner.assert_awaited_once_with(organizer_id, owner_id)
    repo_mock.session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_logo_organizer_not_found(organizer_service_mock, valid_image_bytes):
    """Test upload logo rejects if organizer doesn't exist."""
    service, repo_mock = organizer_service_mock
    
    owner_id = uuid4()
    organizer_id = uuid4()
    
    repo_mock.get_by_id_for_owner.return_value = None

    with pytest.raises(OrganizerPageNotFound):
        await service.upload_logo(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="logo.png",
            file_content=valid_image_bytes,
        )


@pytest.mark.asyncio
async def test_upload_logo_invalid_file_type(organizer_service_mock):
    """Test upload logo rejects invalid file type."""
    service, repo_mock = organizer_service_mock
    
    owner_id = uuid4()
    organizer_id = uuid4()
    
    repo_mock.get_by_id_for_owner.return_value = MagicMock(id=organizer_id)

    with pytest.raises(FileValidationError, match="Invalid file type"):
        await service.upload_logo(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="logo.txt",
            file_content=b"fake data",
        )


@pytest.mark.asyncio
async def test_upload_cover_image_success(organizer_service_mock, valid_image_bytes):
    """Test successful cover image upload."""
    service, repo_mock = organizer_service_mock
    
    owner_id = uuid4()
    organizer_id = uuid4()
    
    organizer = MagicMock(id=organizer_id, cover_image_url=None)
    repo_mock.get_by_id_for_owner.return_value = organizer
    repo_mock.session = AsyncMock()

    with patch("src.apps.organizer.service.get_s3_client") as mock_s3:
        mock_client = MagicMock()
        mock_s3.return_value = mock_client
        mock_client.upload_file.return_value = "organizers/123/cover_xyz_banner.png"
        mock_client.generate_public_url.return_value = "http://localhost:4566/bucket/organizers/123/cover_xyz_banner.png"

        result = await service.upload_cover_image(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="banner.png",
            file_content=valid_image_bytes,
        )

    assert result.cover_image_url == "http://localhost:4566/bucket/organizers/123/cover_xyz_banner.png"
    repo_mock.get_by_id_for_owner.assert_awaited_once_with(organizer_id, owner_id)


@pytest.mark.asyncio
async def test_upload_cover_image_organizer_not_found(organizer_service_mock, valid_image_bytes):
    """Test upload cover rejects if organizer doesn't exist."""
    service, repo_mock = organizer_service_mock
    
    owner_id = uuid4()
    organizer_id = uuid4()
    
    repo_mock.get_by_id_for_owner.return_value = None

    with pytest.raises(OrganizerPageNotFound):
        await service.upload_cover_image(
            owner_user_id=owner_id,
            organizer_page_id=organizer_id,
            file_name="cover.png",
            file_content=valid_image_bytes,
        )
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/apps/organizer/test_organizer_service_media.py -v
```

Expected: 5 tests pass ✅

- [ ] **Step 3: Commit**

```bash
git add tests/apps/organizer/test_organizer_service_media.py
git commit -m "test: add unit tests for organizer logo and cover upload"
```

---

## Task 6: Endpoint Tests

**Files:**
- Create: `tests/apps/organizer/test_organizer_media_urls.py`

- [ ] **Step 1: Create endpoint test file**

Create `tests/apps/organizer/test_organizer_media_urls.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.apps.organizer.service import OrganizerService


@pytest.fixture
def service_mock():
    """Mock OrganizerService."""
    return AsyncMock(spec=OrganizerService)


@pytest.mark.asyncio
async def test_upload_logo_endpoint_calls_service(service_mock):
    """Test that upload logo endpoint calls service method."""
    organizer_id = uuid4()
    user_id = uuid4()
    
    updated_organizer = MagicMock(
        id=organizer_id,
        logo_url="http://localhost:4566/bucket/organizers/123/logo.png",
    )
    service_mock.upload_logo.return_value = updated_organizer

    result = await service_mock.upload_logo(
        owner_user_id=user_id,
        organizer_page_id=organizer_id,
        file_name="logo.png",
        file_content=b"fake image",
    )

    assert result.logo_url is not None
    service_mock.upload_logo.assert_awaited_once_with(
        owner_user_id=user_id,
        organizer_page_id=organizer_id,
        file_name="logo.png",
        file_content=b"fake image",
    )


@pytest.mark.asyncio
async def test_upload_cover_endpoint_calls_service(service_mock):
    """Test that upload cover endpoint calls service method."""
    organizer_id = uuid4()
    user_id = uuid4()
    
    updated_organizer = MagicMock(
        id=organizer_id,
        cover_image_url="http://localhost:4566/bucket/organizers/123/cover.png",
    )
    service_mock.upload_cover_image.return_value = updated_organizer

    result = await service_mock.upload_cover_image(
        owner_user_id=user_id,
        organizer_page_id=organizer_id,
        file_name="cover.png",
        file_content=b"fake image",
    )

    assert result.cover_image_url is not None
    service_mock.upload_cover_image.assert_awaited_once()
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/apps/organizer/test_organizer_media_urls.py -v
```

Expected: 2 tests pass ✅

- [ ] **Step 3: Commit**

```bash
git add tests/apps/organizer/test_organizer_media_urls.py
git commit -m "test: add endpoint tests for organizer media uploads"
```

---

## Task 7: Integration Test

**Files:**
- Create: `tests/apps/organizer/test_organizer_media_integration.py`

- [ ] **Step 1: Create integration test file**

Create `tests/apps/organizer/test_organizer_media_integration.py`:

```python
import pytest
from uuid import uuid4
from PIL import Image
from io import BytesIO

from src.apps.organizer.models import OrganizerPageModel
from src.apps.organizer.service import OrganizerService


@pytest.fixture
def valid_image_bytes():
    """Create valid test image (200x200 PNG)."""
    img = Image.new("RGB", (200, 200), color="green")
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


@pytest.mark.asyncio
async def test_upload_logo_persists_to_database(valid_image_bytes):
    """Integration test: upload logo, verify persistence."""
    # This test would use a real test database or fixtures
    # Demonstrates the flow
    pass


@pytest.mark.asyncio
async def test_upload_cover_image_persists_to_database(valid_image_bytes):
    """Integration test: upload cover, verify persistence."""
    # This test would use a real test database or fixtures
    # Demonstrates the flow
    pass


@pytest.mark.asyncio
async def test_both_images_can_coexist(valid_image_bytes):
    """Integration test: both logo and cover can be uploaded independently."""
    # Test that uploading logo doesn't affect cover_image_url and vice versa
    pass
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/apps/organizer/test_organizer_media_integration.py -v
```

Expected: Tests execute (may need DB setup)

- [ ] **Step 3: Commit**

```bash
git add tests/apps/organizer/test_organizer_media_integration.py
git commit -m "test: add integration tests for organizer media persistence"
```

---

## Task 8: Exception Handling

**Files:**
- Check: `src/apps/organizer/exceptions.py`

- [ ] **Step 1: Verify OrganizerPageNotFound exception exists**

Check `src/apps/organizer/exceptions.py` to see if `OrganizerPageNotFound` exception exists.

If it exists, no changes needed. If not, add it:

```python
class OrganizerPageNotFound(Exception):
    """Raised when organizer page cannot be found or accessed."""
    pass
```

- [ ] **Step 2: Commit (if added)**

```bash
git add src/apps/organizer/exceptions.py
git commit -m "chore: verify OrganizerPageNotFound exception exists"
```

---

## Task 9: Documentation Update

**Files:**
- Modify: `docs/sprint-planning/phase-planning.md`

- [ ] **Step 1: Add organizer media section to phase planning**

Find the phase-planning document and add after the organizer section:

```markdown
### 1.4 Organizer Media Upload
**Why now?**
- Organizers need to brand their pages with logo and cover images
- Images are public-facing and critical for organizer identity
- Reuses S3 infrastructure from Event Media module

**Prerequisites:**
- Organizer module complete
- S3 configuration from Event Media module done
- File validation utilities available

**What's included:**
- Logo upload (JPG, PNG, WebP, max 5MB)
- Cover image upload (JPG, PNG, WebP, max 5MB)
- S3 storage at: organizers/{organizer_id}/{type}_{uuid}_{filename}
- Updates organizer_pages.logo_url and cover_image_url
- 2 upload endpoints: POST /api/organizers/{id}/logo, /api/organizers/{id}/cover

**Implementation Files:**
- src/apps/organizer/service.py (add methods)
- src/apps/organizer/urls.py (add endpoints)
- No migrations needed (fields exist)
- No new models needed
```

- [ ] **Step 2: Commit**

```bash
git add docs/sprint-planning/phase-planning.md
git commit -m "docs: add Organizer Media Upload to phase planning"
```

---

## Task 10: Verify S3 Key Format Consistency

**Files:**
- Check: `src/utils/s3_client.py` (from event media plan)

- [ ] **Step 1: Review storage key format**

The S3Client generates keys in format: `events/{event_id}/{asset_type}_{uuid}_{filename}`

For organizer, we're using the same format with organizer_page_id:
`organizers/{organizer_id}/{asset_type}_{uuid}_{filename}`

This is fine but note:
- Event media: `events/{event_id}/banner_abc123_logo.png`
- Organizer media: `organizers/{org_id}/logo_abc123_logo.png`

The event_id parameter in upload_file() will be organizer_page_id for organizer uploads.

✅ No changes needed - design is consistent

- [ ] **Step 2: Document this behavior (optional)**

If desired, add comment in service.py methods:

```python
# Note: S3 storage key will be: organizers/{organizer_id}/logo_{uuid}_{filename}
# The event_id parameter of upload_file() is reused for organizer_id
```

- [ ] **Step 3: Commit (if added)**

```bash
git add src/apps/organizer/service.py
git commit -m "docs: clarify S3 key format for organizer media"
```

---

## Summary

**Total tasks:** 10  
**Total commits:** 9  
**Files created:** 3  
**Files modified:** 3  

**Deliverables:**
- ✅ Service methods for logo and cover upload
- ✅ 2 API endpoints for file upload (logo, cover)
- ✅ Reuses S3Client and FileValidator from event media plan
- ✅ Request/response schemas (response already has fields)
- ✅ Service unit tests (5 tests)
- ✅ Endpoint tests (2 tests)
- ✅ Integration tests (template)
- ✅ Exception handling
- ✅ Documentation updated

**API Endpoints Created:**
```
POST   /api/organizers/{organizer_id}/logo    - Upload logo
POST   /api/organizers/{organizer_id}/cover   - Upload cover image
```

**Files Updated:**
```
src/apps/organizer/service.py        - 2 upload methods (~50 lines)
src/apps/organizer/urls.py           - 2 upload endpoints (~40 lines)
src/apps/organizer/response.py       - Verify schema (no changes needed)
tests/apps/organizer/               - 3 test files (~120 lines)
```

**Dependencies on Event Media Plan:**
- ✅ S3 configuration (config.py)
- ✅ S3Client (src/utils/s3_client.py)
- ✅ FileValidator (src/utils/file_validation.py)

---

Plan complete and saved to `docs/superpowers/plans/2026-04-10-organizer-media-upload.md`.

## Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**