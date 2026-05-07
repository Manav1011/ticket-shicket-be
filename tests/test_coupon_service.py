import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from apps.allocation.enums import CouponType
from apps.allocation.models import CouponModel
from apps.event.service import PurchaseService

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
        valid_from=datetime.utcnow() - timedelta(days=1),
        valid_until=datetime.utcnow() + timedelta(days=30),
        is_active=True,
    )
    db_session.add(coupon)
    await db_session.flush()
    return coupon

@pytest.fixture
def flat_coupon():
    return CouponModel(
        id=uuid4(), code="FLAT100", type=CouponType.FLAT, value=100,
        max_discount=None, min_order_amount=0, usage_limit=100,
        per_user_limit=10, used_count=0,
        valid_from=datetime.utcnow() - timedelta(days=1),
        valid_until=datetime.utcnow() + timedelta(days=30),
        is_active=True,
    )

@pytest.fixture
def percentage_coupon():
    return CouponModel(
        id=uuid4(), code="SAVE20", type=CouponType.PERCENTAGE, value=20,
        max_discount=500, min_order_amount=0, usage_limit=100,
        per_user_limit=10, used_count=0,
        valid_from=datetime.utcnow() - timedelta(days=1),
        valid_until=datetime.utcnow() + timedelta(days=30),
        is_active=True,
    )

def test_calculate_discount_flat(flat_coupon):
    result = PurchaseService.calculate_discount(flat_coupon, subtotal=500.0)
    assert result == 100.0

def test_calculate_discount_percentage(percentage_coupon):
    result = PurchaseService.calculate_discount(percentage_coupon, subtotal=1000.0)
    assert result == 200.0

def test_calculate_discount_caps_at_max_discount(percentage_coupon):
    # 20% of 5000 = 1000, but max_discount = 500
    result = PurchaseService.calculate_discount(percentage_coupon, subtotal=5000.0)
    assert result == 500.0

def test_calculate_discount_returns_zero_for_inactive():
    coupon = CouponModel(
        id=uuid4(), code="INACTIVE", type=CouponType.FLAT, value=100,
        is_active=False,
        valid_from=datetime.utcnow() - timedelta(days=1),
        valid_until=datetime.utcnow() + timedelta(days=30),
        min_order_amount=0, usage_limit=100, per_user_limit=10, used_count=0,
    )
    result = PurchaseService.calculate_discount(coupon, subtotal=500.0)
    assert result == 0.0

def test_calculate_discount_returns_zero_for_expired():
    coupon = CouponModel(
        id=uuid4(), code="EXPIRED", type=CouponType.FLAT, value=100,
        is_active=True,
        valid_from=datetime.utcnow() - timedelta(days=30),
        valid_until=datetime.utcnow() - timedelta(days=1),
        min_order_amount=0, usage_limit=100, per_user_limit=10, used_count=0,
    )
    result = PurchaseService.calculate_discount(coupon, subtotal=500.0)
    assert result == 0.0

def test_calculate_discount_returns_zero_for_usage_exceeded():
    coupon = CouponModel(
        id=uuid4(), code="LIMITED", type=CouponType.FLAT, value=100,
        is_active=True,
        valid_from=datetime.utcnow() - timedelta(days=1),
        valid_until=datetime.utcnow() + timedelta(days=30),
        usage_limit=10, used_count=10,
        min_order_amount=0, per_user_limit=10,
    )
    result = PurchaseService.calculate_discount(coupon, subtotal=500.0)
    assert result == 0.0

def test_calculate_discount_returns_zero_below_min_order():
    coupon = CouponModel(
        id=uuid4(), code="MINORDER", type=CouponType.FLAT, value=100,
        is_active=True,
        valid_from=datetime.utcnow() - timedelta(days=1),
        valid_until=datetime.utcnow() + timedelta(days=30),
        min_order_amount=1000, usage_limit=100, per_user_limit=10, used_count=0,
    )
    result = PurchaseService.calculate_discount(coupon, subtotal=500.0)
    assert result == 0.0

def test_calculate_discount_caps_at_subtotal():
    coupon = CouponModel(
        id=uuid4(), code="BIGFLAT", type=CouponType.FLAT, value=1000,
        is_active=True,
        valid_from=datetime.utcnow() - timedelta(days=1),
        valid_until=datetime.utcnow() + timedelta(days=30),
        min_order_amount=0, usage_limit=100, per_user_limit=10, used_count=0,
    )
    result = PurchaseService.calculate_discount(coupon, subtotal=500.0)
    assert result == 500.0  # capped at subtotal

@pytest.mark.asyncio
async def test_validate_coupon_raises_for_invalid_code(coupon_repo):
    from exceptions import BadRequestError
    service = PurchaseService(coupon_repo)
    with pytest.raises(BadRequestError) as exc_info:
        await service.validate_coupon("DOES_NOT_EXIST", subtotal=1000.0)
    assert "Invalid coupon code" in str(exc_info.value)

@pytest.mark.asyncio
async def test_validate_coupon_raises_for_usage_exceeded(coupon_repo, sample_coupon, db_session):
    from exceptions import BadRequestError
    sample_coupon.usage_limit = 5
    sample_coupon.used_count = 5
    await db_session.flush()

    service = PurchaseService(coupon_repo)
    with pytest.raises(BadRequestError) as exc_info:
        await service.validate_coupon(sample_coupon.code, subtotal=1000.0)
    assert "usage limit" in str(exc_info.value)
