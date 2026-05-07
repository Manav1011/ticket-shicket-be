import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from apps.allocation.enums import CouponType
from apps.allocation.models import CouponModel

@pytest.fixture
async def coupon_repo(db_session):
    from apps.allocation.repository import CouponRepository
    return CouponRepository(db_session)

@pytest.fixture
async def sample_coupon(db_session):
    coupon = CouponModel(
        id=uuid4(),
        code="SAVE20",
        type=CouponType.PERCENTAGE,
        value=20,
        max_discount=500,
        min_order_amount=100,
        usage_limit=100,
        per_user_limit=5,
        used_count=0,
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        is_active=True,
    )
    db_session.add(coupon)
    await db_session.flush()
    return coupon

@pytest.mark.asyncio
async def test_get_by_code_found(coupon_repo, sample_coupon):
    result = await coupon_repo.get_by_code("SAVE20")
    assert result is not None
    assert result.code == "SAVE20"

@pytest.mark.asyncio
async def test_get_by_code_not_found(coupon_repo):
    result = await coupon_repo.get_by_code("INVALID")
    assert result is None

@pytest.mark.asyncio
async def test_increment_used_count(coupon_repo, sample_coupon):
    original_count = sample_coupon.used_count
    await coupon_repo.increment_used_count(sample_coupon.id)
    coupon_repo.session.expire(sample_coupon)
    await coupon_repo.session.refresh(sample_coupon)
    assert sample_coupon.used_count == original_count + 1
