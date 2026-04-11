import sys
from pathlib import Path
from io import BytesIO
from uuid import uuid4
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

# Add project root and src to path:
# - project root allows 'from src.utils.s3_client' to resolve to 'src/utils/s3_client'
# - src allows 'from apps.event import ...' to resolve to 'src/apps/event/...'
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


# =============================================================================
# Image Fixtures
# =============================================================================

@pytest.fixture
def valid_image_bytes():
    """Create valid test image (200x200 PNG) that passes validation."""
    img = Image.new("RGB", (200, 200), color="green")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def valid_jpg_image_bytes():
    """Create valid test image (200x200 JPEG) that passes validation."""
    img = Image.new("RGB", (200, 200), color="blue")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def small_image_bytes():
    """Create undersized image (100x100 PNG) that fails dimension check."""
    img = Image.new("RGB", (100, 100), color="red")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def oversized_image_bytes():
    """Create oversized file (>5MB) that fails size check."""
    return b"x" * (6 * 1024 * 1024)


@pytest.fixture
def invalid_file_type_bytes():
    """Create invalid file type (text pretending to be image)."""
    return b"this is not an image, just text content" * 100


@pytest.fixture
def valid_video_bytes():
    """Create valid test video bytes (>1MB to pass size check, mp4 header)."""
    # Create a minimal MP4 file header (this is a simplified placeholder)
    # Real videos would need proper encoding, but for validation tests this suffices
    header = b"\x00\x00\x00\x1c\x66\x74\x79\x70\x69\x73\x6f\x6d"  # ftyp box
    header += b"\x00\x00\x02\x00\x69\x73\x6f\x6d\x61\x76\x63\x31"  # isomavc1
    body = b"\x00" * (1024 * 1024)  # 1MB body to pass minimum size
    return header + body


# =============================================================================
# Mock S3 Client Fixture
# =============================================================================

@pytest.fixture
def mock_s3_client():
    """Mock S3 client for testing without real S3 calls."""
    mock_client = MagicMock()
    mock_client.upload_file.return_value = "events/test-id/banner_abc12345_test.png"
    mock_client.delete_file.return_value = True
    mock_client.generate_public_url.return_value = "http://localhost:4566/test-bucket/events/test-id/banner_abc12345_test.png"
    mock_client.client = MagicMock()
    return mock_client


@pytest.fixture
def s3_client_with_mock():
    """Patch get_s3_client to return mock S3 client."""
    mock_client = MagicMock()
    mock_client.upload_file.return_value = "events/test-id/banner_abc12345_test.png"
    mock_client.delete_file.return_value = True
    mock_client.generate_public_url.return_value = "http://localhost:4566/test-bucket/events/test-id/banner_abc12345_test.png"
    mock_client.client = MagicMock()

    with patch("src.utils.s3_client.get_s3_client", return_value=mock_client):
        with patch("src.apps.event.service.get_s3_client", return_value=mock_client):
            with patch("src.apps.organizer.service.get_s3_client", return_value=mock_client):
                yield mock_client


# =============================================================================
# Test App with Minimal Lifespan for HTTP Testing
# =============================================================================

@pytest.fixture
def test_app():
    """Create FastAPI app with mocked lifespan for HTTP testing."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from starlette.testclient import TestClient

    from apps.organizer.urls import router as organizer_router
    from apps.event.urls import router as event_router
    from apps.ticketing.urls import router as ticketing_router
    from apps.user import user_router, protected_user_router
    from apps.guest import guest_router, protected_guest_router
    from utils.schema import BaseValidationResponse

    @asynccontextmanager
    async def mock_lifespan(app):
        # Skip Redis and scheduler initialization for tests
        yield

    app = FastAPI(
        title="Test App",
        version="0.0.1",
        lifespan=mock_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        return JSONResponse(status_code=200, content={"message": "SUCCESS"})

    @app.get("/healthcheck")
    async def healthcheck():
        return JSONResponse(status_code=200, content={"message": "SUCCESS"})

    base_router = FastAPI()
    base_router.include_router(user_router)
    base_router.include_router(protected_user_router)
    base_router.include_router(guest_router)
    base_router.include_router(protected_guest_router)
    base_router.include_router(organizer_router)
    base_router.include_router(event_router)
    base_router.include_router(ticketing_router)
    app.include_router(base_router, responses={422: {"model": BaseValidationResponse}})

    return app


@pytest.fixture
async def async_test_client(test_app):
    """Async HTTP client for integration tests."""
    from httpx import AsyncClient

    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client


# =============================================================================
# Database Session Fixture (for service-level tests)
# =============================================================================

@pytest.fixture
async def db_session():
    """Provide a test database session with rollback after each test."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    # Use a test database URL or SQLite for testing
    test_db_url = "sqlite+aiosqlite:///:memory:"

    engine = create_async_engine(test_db_url, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        async with session.begin():
            yield session

    await engine.dispose()


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
async def test_user(db_session):
    """Create a test user in the database."""
    from apps.user.models import UserModel

    user = UserModel.create(
        first_name="Test",
        last_name="User",
        phone="1234567890",
        email="testuser@example.com",
        password="hashed_password_placeholder",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def test_organizer(db_session, test_user):
    """Create a test organizer linked to the test user."""
    from apps.organizer.models import OrganizerPageModel
    import re

    organizer = OrganizerPageModel(
        owner_user_id=test_user.id,
        name="Test Organizer",
        slug=re.sub(r"[^a-z0-9]+", "-", "test-organizer".lower()),
        bio="Test bio",
        visibility="public",
        status="active",
    )
    db_session.add(organizer)
    await db_session.flush()
    return organizer


@pytest.fixture
async def test_event(db_session, test_organizer, test_user):
    """Create a test event linked to the test organizer."""
    from apps.event.models import EventModel
    from apps.event.enums import EventAccessType

    event = EventModel(
        organizer_page_id=test_organizer.id,
        created_by_user_id=test_user.id,
        title="Test Event",
        event_access_type=EventAccessType.ticketed,
        status="draft",
        location_mode="venue",
        timezone="Asia/Kolkata",
        venue_name="Test Venue",
        venue_address="123 Test St",
        venue_city="Test City",
        venue_country="Test Country",
    )
    db_session.add(event)
    await db_session.flush()
    return event


# =============================================================================
# Auth Token Fixtures
# =============================================================================

@pytest.fixture
async def auth_headers(test_user):
    """Return Authorization header with Bearer token for authenticated requests."""
    from src.auth.jwt import create_tokens

    tokens = await create_tokens(user_id=test_user.id, type="user")
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture
def guest_device_id():
    """Return a unique device ID for guest requests."""
    return str(uuid4())


# =============================================================================
# Event Media Asset Fixtures
# =============================================================================

@pytest.fixture
async def test_banner_asset(db_session, test_event):
    """Create a test banner asset linked to the test event."""
    from apps.event.models import EventMediaAssetModel
    from apps.event.enums import AssetType

    asset = EventMediaAssetModel(
        event_id=test_event.id,
        asset_type=AssetType.banner,
        storage_key=f"events/{test_event.id}/banner_test1234567_test.png",
        public_url="http://localhost:4566/test-bucket/events/test-id/banner_test1234567_test.png",
        title="Test Banner",
        sort_order=0,
        is_primary=False,
    )
    db_session.add(asset)
    await db_session.flush()
    return asset