# Phase 1: Coupon Infrastructure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add coupon models, migration, repository, and discount validation logic — reusable by purchase endpoints in Phase 4.

**Architecture:** Coupon models live in `allocation/models.py` alongside `OrderModel` and `AllocationModel`. `CouponRepository` lives in `allocation/repository.py`. `calculate_discount` and `validate_coupon` are stateless helpers in `event/service.py` (since purchase service also lives there). Migration creates `coupons` and `order_coupons` tables.

**Tech Stack:** SQLAlchemy (async), Alembic migrations, Pydantic, Python 3.12+

---

## File Map

| Action | File |
|--------|------|
| Create | `src/migrations/versions/xxxx_add_coupons.py` |
| Modify | `src/apps/allocation/enums.py` — add `CouponType` enum |
| Modify | `src/apps/allocation/models.py` — add `CouponModel`, `OrderCouponModel` |
| Modify | `src/apps/allocation/repository.py` — add `CouponRepository` |
| Modify | `src/apps/event/service.py` — add `PurchaseService` class with coupon methods |
| Create | `tests/test_coupon_repository.py` — unit tests for CouponRepository |
| Create | `tests/test_coupon_service.py` — unit tests for discount/validation logic |

---

## Tasks

### Task 1: Add `CouponType` Enum

**Files:**
- Modify: `src/apps/allocation/enums.py`

- [ ] **Step 1: Add CouponType enum to allocation/enums.py**

Add after `TransferMode` (around line 34):

```python
class CouponType(str, Enum):
    FLAT = "flat"
    PERCENTAGE = "percentage"
```

- [ ] **Step 2: Commit**

```bash
git add src/apps/allocation/enums.py
git commit -m "feat(coupon): add CouponType enum (FLAT, PERCENTAGE)"
```

---

### Task 2: Add Coupon Models to allocation/models

**Files:**
- Modify: `src/apps/allocation/models.py` — add at end of file (after `OrderModel`, around line 230)

- [ ] **Step 1: Add CouponModel and OrderCouponModel classes**

Add these two classes at the end of `src/apps/allocation/models.py`:

```python
class CouponModel(Base, UUIDPrimaryKeyMixin, TimeStampMixin):
    __tablename__ = "coupons"

    code: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(
        Enum(CouponType), nullable=False
    )
    value: Mapped[float] = mapped_column(
        Numeric(), nullable=False
    )
    max_discount: Mapped[float | None] = mapped_column(
        Numeric(), nullable=True
    )
    min_order_amount: Mapped[float] = mapped_column(
        Numeric(), nullable=False, server_default="0"
    )
    usage_limit: Mapped[int] = mapped_column(
        Integer(), nullable=False
    )
    per_user_limit: Mapped[int] = mapped_column(
        Integer(), nullable=False, server_default="1"
    )
    used_count: Mapped[int] = mapped_column(
        Integer(), nullable=False, server_default="0"
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False
    )
    valid_until: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default="true"
    )


class OrderCouponModel(Base, TimeStampMixin):
    __tablename__ = "order_coupons"

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True
    )
    coupon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    discount_applied: Mapped[float] = mapped_column(
        Numeric(), nullable=False
    )
```

- [ ] **Step 2: Add missing import at top of models.py**

Add `Boolean` to the `from sqlalchemy import (...)` block at the top of the file.

- [ ] **Step 3: Commit**

```bash
git add src/apps/allocation/models.py
git commit -m "feat(coupon): add CouponModel and OrderCouponModel to allocation/models"
```

---

### Task 3: Create Migration for Coupons

**Files:**
- Create: `src/migrations/versions/xxxx_add_coupons.py`

- [ ] **Step 1: Generate migration**

```bash
uv run main.py makemigrations --name add_coupons
```

- [ ] **Step 2: Review generated migration**

Open the generated file at `src/migrations/versions/` and verify it:
- Creates `coupons` table with all columns matching the spec (code, type, value, max_discount, min_order_amount, usage_limit, per_user_limit, used_count, valid_from, valid_until, is_active, created_at, updated_at)
- Creates `order_coupons` table with `order_id (PK)`, `coupon_id (FK)`, `discount_applied`
- Has proper down_revision pointing to the latest existing migration

If adjustments are needed, edit the file before committing.

- [ ] **Step 3: Run migration**

```bash
uv run main.py migrate
```

Expected: migration runs without errors.

- [ ] **Step 4: Commit**

```bash
git add src/migrations/versions/xxxx_add_coupons.py
git commit -m "feat(coupon): add coupons and order_coupons migration"
```

---

### Task 4: Add CouponRepository

**Files:**
- Modify: `src/apps/allocation/repository.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_coupon_repository.py`:

```python
import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from apps.allocation.enums import CouponType
from apps.allocation.models import CouponModel

@pytest.fixture
async def coupon_repo(session):
    from apps.allocation.repository import CouponRepository
    return CouponRepository(session)

@pytest.fixture
async def sample_coupon(session):
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
    session.add(coupon)
    await session.commit()
    return coupon

async def test_get_by_code_found(coupon_repo, sample_coupon):
    result = await coupon_repo.get_by_code("SAVE20")
    assert result is not None
    assert result.code == "SAVE20"

async def test_get_by_code_not_found(coupon_repo):
    result = await coupon_repo.get_by_code("INVALID")
    assert result is None

async def test_increment_used_count(coupon_repo, sample_coupon):
    original_count = sample_coupon.used_count
    await coupon_repo.increment_used_count(sample_coupon.id)
    await coupon_repo.session.expire(sample_coupon)
    await coupon_repo.session.refresh(sample_coupon)
    assert sample_coupon.used_count == original_count + 1
```

Run: `pytest tests/test_coupon_repository.py -v`
Expected: FAIL — `CouponRepository` not defined yet.

- [ ] **Step 2: Implement CouponRepository**

Add to `src/apps/allocation/repository.py` (at end of file):

```python
class CouponRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def get_by_code(self, code: str) -> Optional[CouponModel]:
        """Get an active coupon by its code. Returns None if not found or inactive."""
        return await self._session.scalar(
            select(CouponModel).where(
                CouponModel.code == code.upper(),
                CouponModel.is_active == True,
            )
        )

    async def increment_used_count(self, coupon_id: UUID) -> None:
        """Atomically increment the used_count for a coupon."""
        await self._session.execute(
            update(CouponModel)
            .where(CouponModel.id == coupon_id)
            .values(used_count=CouponModel.used_count + 1)
        )
        await self._session.flush()
```

- [ ] **Step 3: Add import at top of repository.py**

`update` and `Optional` are already imported. Add `CouponModel` to the import from `.models`.

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_coupon_repository.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/allocation/repository.py tests/test_coupon_repository.py
git commit -m "feat(coupon): add CouponRepository with get_by_code and increment_used_count"
```

---

### Task 5: Add `PurchaseService` class with coupon logic to event/service.py

**Files:**
- Modify: `src/apps/event/service.py` — add new `PurchaseService` class before `EventService`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_coupon_service.py`:

```python
import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from apps.allocation.enums import CouponType
from apps.allocation.models import CouponModel
from apps.event.service import PurchaseService

@pytest.fixture
def flat_coupon():
    return CouponModel(
        id=uuid4(), code="FLAT100", type=CouponType.FLAT, value=100,
        max_discount=None, min_order_amount=0, usage_limit=100,
        per_user_limit=10, used_count=0,
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        is_active=True,
    )

@pytest.fixture
def percentage_coupon():
    return CouponModel(
        id=uuid4(), code="SAVE20", type=CouponType.PERCENTAGE, value=20,
        max_discount=500, min_order_amount=0, usage_limit=100,
        per_user_limit=10, used_count=0,
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        valid_until=datetime.now(timezone.utc) + timedelta(days=30),
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
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        min_order_amount=0, usage_limit=100, per_user_limit=10, used_count=0,
    )
    result = PurchaseService.calculate_discount(coupon, subtotal=500.0)
    assert result == 0.0

def test_calculate_discount_returns_zero_for_expired():
    coupon = CouponModel(
        id=uuid4(), code="EXPIRED", type=CouponType.FLAT, value=100,
        is_active=True,
        valid_from=datetime.now(timezone.utc) - timedelta(days=30),
        valid_until=datetime.now(timezone.utc) - timedelta(days=1),
        min_order_amount=0, usage_limit=100, per_user_limit=10, used_count=0,
    )
    result = PurchaseService.calculate_discount(coupon, subtotal=500.0)
    assert result == 0.0

def test_calculate_discount_returns_zero_for_usage_exceeded():
    coupon = CouponModel(
        id=uuid4(), code="LIMITED", type=CouponType.FLAT, value=100,
        is_active=True,
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        usage_limit=10, used_count=10,
        min_order_amount=0, per_user_limit=10,
    )
    result = PurchaseService.calculate_discount(coupon, subtotal=500.0)
    assert result == 0.0

def test_calculate_discount_returns_zero_below_min_order():
    coupon = CouponModel(
        id=uuid4(), code="MINORDER", type=CouponType.FLAT, value=100,
        is_active=True,
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        min_order_amount=1000, usage_limit=100, per_user_limit=10, used_count=0,
    )
    result = PurchaseService.calculate_discount(coupon, subtotal=500.0)
    assert result == 0.0

def test_calculate_discount_caps_at_subtotal():
    coupon = CouponModel(
        id=uuid4(), code="BIGFLAT", type=CouponType.FLAT, value=1000,
        is_active=True,
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        min_order_amount=0, usage_limit=100, per_user_limit=10, used_count=0,
    )
    result = PurchaseService.calculate_discount(coupon, subtotal=500.0)
    assert result == 500.0  # capped at subtotal

@pytest.mark.asyncio
async def test_validate_coupon_raises_for_invalid_code(coupon_repo):
    from exceptions import BadRequestError
    service = PurchaseService(coupon_repo)
    with pytest.raises(BadRequestError) as exc_info:
        await service.validate_coupon("DOES_NOT_EXIST", subtotal=1000.0, user_id=uuid4())
    assert "Invalid coupon code" in str(exc_info.value)

@pytest.mark.asyncio
async def test_validate_coupon_raises_for_usage_exceeded(coupon_repo, sample_coupon):
    from exceptions import BadRequestError
    sample_coupon.usage_limit = 5
    sample_coupon.used_count = 5
    await coupon_repo.session.commit()

    service = PurchaseService(coupon_repo)
    with pytest.raises(BadRequestError) as exc_info:
        await service.validate_coupon(sample_coupon.code, subtotal=1000.0, user_id=uuid4())
    assert "usage limit" in str(exc_info.value)
```

Run: `pytest tests/test_coupon_service.py -v`
Expected: FAIL — `PurchaseService` not defined yet.

- [ ] **Step 2: Implement PurchaseService class**

Add before the `EventService` class in `src/apps/event/service.py`:

```python
class PurchaseService:
    """Service for online ticket purchase flow — includes coupon validation and discount calculation."""

    def __init__(self, coupon_repository: CouponRepository) -> None:
        self._coupon_repo = coupon_repository

    @staticmethod
    def calculate_discount(coupon: CouponModel, subtotal: float) -> float:
        """
        Apply coupon to subtotal and return discount amount.
        Returns 0 if coupon is invalid or cannot be applied.
        """
        if not coupon.is_active:
            return 0.0

        now = datetime.now(timezone.utc)
        if not (coupon.valid_from <= now <= coupon.valid_until):
            return 0.0

        if coupon.used_count >= coupon.usage_limit:
            return 0.0

        if subtotal < float(coupon.min_order_amount):
            return 0.0

        if coupon.type == CouponType.FLAT:
            discount = float(coupon.value)
        else:  # PERCENTAGE
            discount = subtotal * (float(coupon.value) / 100)
            if coupon.max_discount is not None:
                discount = min(discount, float(coupon.max_discount))

        return min(discount, subtotal)

    async def validate_coupon(
        self,
        code: str,
        subtotal: float,
        user_id: UUID,
    ) -> CouponModel:
        """
        Validate coupon code and return coupon if valid.
        Raises BadRequestError if invalid.
        """
        coupon = await self._coupon_repo.get_by_code(code)
        if not coupon:
            from exceptions import BadRequestError
            raise BadRequestError("Invalid coupon code")

        discount = self.calculate_discount(coupon, subtotal)
        if discount == 0.0:
            if coupon.used_count >= coupon.usage_limit:
                from exceptions import BadRequestError
                raise BadRequestError("Coupon usage limit reached")
            from exceptions import BadRequestError
            raise BadRequestError("Coupon cannot be applied to this order")

        return coupon
```

- [ ] **Step 3: Add imports at top of service.py**

Add:
- `from datetime import datetime, timezone, timedelta`
- `from apps.allocation.enums import CouponType`
- `from apps.allocation.models import CouponModel`
- `from apps.allocation.repository import CouponRepository`

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_coupon_service.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/event/service.py tests/test_coupon_service.py
git commit -m "feat(coupon): add PurchaseService with calculate_discount and validate_coupon"
```

---

## Verification

After all tasks complete:

1. Run `uv run main.py showmigrations` — verify `add_coupons` migration is applied
2. Run `pytest tests/test_coupon_repository.py tests/test_coupon_service.py -v` — all pass
3. Verify `CouponModel` and `OrderCouponModel` instances can be created and flushed to DB