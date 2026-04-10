# Media Upload Testing Session

**Date:** 2026-04-10
**Focus:** Organizer & Event Media Upload API Testing, Bug Fixes, S3 Path Fixes
**Status:** ✅ Complete

---

## Executive Summary

Tested both organizer and event media upload APIs end-to-end. Fixed S3 path prefix issue, AssetType enum migration, and multiple `current_user` reference bugs in event URLs. All media APIs now fully functional.

---

## What Was Tested

### 1. Organizer Media Uploads

**Endpoints:**
- `POST /api/organizers/{organizer_id}/logo`
- `POST /api/organizers/{organizer_id}/cover`

**Tests Run:**
| Test | Result |
|------|--------|
| Valid logo upload (PNG 400x400) | ✅ 200 - logoUrl populated |
| Valid cover upload (PNG 800x400) | ✅ 200 - coverImageUrl populated |
| JPEG upload | ✅ 200 - Accepted |
| Invalid file type (TXT) | ✅ 400 - "Invalid file type: txt" |
| Too small dimensions (100x100) | ✅ 400 - "Image dimensions below minimum" |
| Non-existent organizer | ✅ 404 - "Organizer page not found" |

**Organizer ID:** `5840652a-828d-41e2-9011-c52eb7b012a2`

---

### 2. Event Media Uploads

**Endpoint:** `POST /api/events/{event_id}/media-assets`

**Tests Run:**
| Test | Result |
|------|--------|
| Banner upload | ✅ 200 |
| Gallery image upload | ✅ 200 |
| Gallery video upload | ✅ 200 |
| Invalid file type | ✅ 400 |
| Too small dimensions | ✅ 400 |
| Non-existent event | ✅ 404 |
| List media assets | ✅ 200 |
| Update metadata | ✅ 200 |
| Delete media asset | ✅ 200 |

**Event ID:** `a093d9d4-4933-4272-9a1c-9e80f3ccc816`

**Asset Types Verified:**
| Type | Status |
|------|--------|
| banner | ✅ Uploaded |
| gallery_image | ✅ Uploaded |
| gallery_video | ✅ Uploaded |
| promo_video | ⚠️ Not via file upload (YouTube URL only) |

---

## Bugs Fixed

### Bug #1: S3 Path Prefix (Organizer Uploads)

**Problem:** Organizer uploads were saving to `events/{id}/...` path instead of `organizers/{id}/...`

**Root Cause:** `S3Client.upload_file()` hardcoded `events/` prefix

**Fix:** Added `path_prefix` parameter with default `"events"`
```python
# s3_client.py
def upload_file(self, resource_id, asset_type, file_name, file_content, path_prefix="events"):
    storage_key = f"{path_prefix}/{resource_id}/{asset_type}_{unique_id}_{file_name}"
```

**Result:** Organizer uploads now use `organizers/{id}/` path

---

### Bug #2: AssetType Enum Not Used in Model

**Problem:** `EventMediaAssetModel.asset_type` used `String(50)` instead of `Enum(AssetType)`

**Fix:**
```python
# models.py - Changed from:
asset_type: Mapped[str] = mapped_column(String(50), nullable=False)

# To:
asset_type: Mapped[str] = mapped_column(Enum(AssetType), nullable=False)
```

---

### Bug #3: Migration Failed - Enum Type Not Created

**Error:** `UndefinedObjectError: type "assettype" does not exist`

**Fix:** Updated migration to create enum type first:
```python
op.execute("DO $$ BEGIN CREATE TYPE assettype AS ENUM ('banner', 'gallery_image', 'gallery_video', 'promo_video'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
```

---

### Bug #4: Migration Failed - Data Type Mismatch

**Error:** `DatatypeMismatchError: column "asset_type" cannot be cast automatically to type assettype`

**Fix:** Added `postgresql_using` clause:
```python
op.alter_column('event_media_assets', 'asset_type',
    existing_type=sa.VARCHAR(length=50),
    type_=sa.Enum(...),
    postgresql_using='asset_type::assettype')
```

---

### Bug #5: `current_user` Not Defined in Event URLs

**Error:** `NameError: name 'current_user' is not defined`

**Location:** Lines 244, 260, 277 in `src/apps/event/urls.py`

**Fix:** Changed `current_user.id` to `request.state.user.id`
```python
# Before (BROKEN):
owner_user_id=current_user.id,

# After (FIXED):
owner_user_id=request.state.user.id,
```

**Affected Endpoints:**
- `GET /events/{id}/media-assets` (line 244)
- `DELETE /events/{id}/media-assets/{id}` (line 260)
- `PATCH /events/{id}/media-assets/{id}` (line 277)

---

## S3 Storage Structure

**One bucket:** `ticket-shicket-media`

```
ticket-shicket-media/
├── organizers/{organizer_id}/
│   ├── logo_xxx.png
│   └── cover_xxx.png
└── events/{event_id}/
    ├── banner_xxx.png
    ├── gallery_image_xxx.png
    └── gallery_video_xxx.mp4
```

---

## Event Setup Status

The `setupStatus` tracks 4 progressive sections:

| Section | Requirement |
|---------|-------------|
| basic_info | title, event_access_type, location_mode, timezone |
| schedule | 1+ event days |
| tickets | for ticketed: 1+ ticket types AND allocations |
| assets | 1+ banner uploaded |

**All sections now show `true`** after media upload tests.

---

## Files Modified

```
src/utils/s3_client.py                        # Added path_prefix parameter
src/apps/organizer/service.py               # Uses path_prefix="organizers"
src/apps/event/models.py                     # Added AssetType enum
src/migrations/versions/479742328475_.py     # Fixed enum migration
src/apps/event/urls.py                       # Fixed current_user references
```

---

## Commands Run

### Sign In
```bash
curl -X POST http://localhost:8080/api/user/sign-in \
  -H "Content-Type: application/json" \
  -d '{"email":"maya.patel@example.com", "password":"Manav@1011"}'
```

### Create S3 Bucket
```bash
AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test \
  aws --endpoint-url=http://localhost:4566 s3 mb s3://ticket-shicket-media --region us-east-1
```

### Upload Organizer Logo
```bash
curl -X POST http://localhost:8080/api/organizers/{id}/logo \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/media_test/logo_valid.png"
```

### Upload Event Banner
```bash
curl -X POST http://localhost:8080/api/events/{id}/media-assets \
  -H "Authorization: Bearer $TOKEN" \
  -F "asset_type=banner" \
  -F "file=@/tmp/media_test/logo_valid.png"
```

### List Event Assets
```bash
curl -X GET http://localhost:8080/api/events/{id}/media-assets \
  -H "Authorization: Bearer $TOKEN"
```

---

## Test Images Created

```
/tmp/media_test/
├── logo_valid.png       (400x400 - valid logo)
├── cover_valid.png     (800x400 - valid cover)
├── logo_valid.jpg      (400x400 JPEG)
├── logo_too_small.png  (100x100 - invalid dimensions)
└── invalid.txt        (text file - invalid type)
```

---

**Status:** All media APIs tested and working. Event is ready for publishing.
