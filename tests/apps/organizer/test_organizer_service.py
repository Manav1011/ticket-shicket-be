from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.organizer.service import OrganizerService


@pytest.mark.asyncio
async def test_create_b2b_transfer_paid_mode_creates_pending_order():
    """Paid mode creates a pending order, generates payment link, returns payment_url."""
    from apps.organizer.service import OrganizerService
    from apps.ticketing.enums import OrderStatus
    from apps.allocation.enums import TransferMode

    mock_repo = AsyncMock()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_repo.session = mock_session

    service = OrganizerService(mock_repo)
    service._ticketing_repo = AsyncMock()
    service._allocation_repo = AsyncMock()
    service._allocation_service = AsyncMock()

    # Mock allocation_repo methods
    org_holder = MagicMock(id=uuid4())
    reseller_holder = MagicMock(id=uuid4())
    reseller_user = MagicMock(id=uuid4(), name="Reseller Co", email="reseller@co.in", phone="+919999999999")

    service._allocation_repo.get_holder_by_user_id = AsyncMock(
        side_effect=[org_holder, reseller_holder]
    )
    service._allocation_repo.list_b2b_tickets_by_holder = AsyncMock(return_value=[
        {"event_day_id": uuid4(), "count": 5}
    ])
    service._allocation_repo.get_holder_by_email = AsyncMock(return_value=None)
    service._allocation_repo.get_holder_by_phone = AsyncMock(return_value=None)

    service._ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=MagicMock(id=uuid4())
    )
    service._ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4(), uuid4()])

    # Mock gateway
    with patch("apps.organizer.service.get_gateway") as mock_get_gateway:
        mock_gateway = MagicMock()
        mock_gateway.create_payment_link = AsyncMock(
            return_value=MagicMock(
                gateway_order_id="plink_test123",
                short_url="https://razorpay.in/test",
                gateway_response={"id": "plink_test123"},
            )
        )
        mock_get_gateway.return_value = mock_gateway

        with patch("apps.organizer.service.OrderModel") as mock_order_model:
            order_instance = MagicMock()
            order_instance.id = uuid4()
            mock_order_model.return_value = order_instance

            with patch("apps.organizer.service.UserRepository") as mock_user_repo_cls:
                mock_user_repo = MagicMock()
                mock_user_repo.find_by_id = AsyncMock(return_value=reseller_user)
                mock_user_repo_cls.return_value = mock_user_repo

                with patch("apps.organizer.service.EventRepository") as mock_event_repo_cls:
                    mock_event_repo = MagicMock()
                    mock_event_repo.get_reseller_for_event = AsyncMock(return_value=MagicMock(accepted_at=uuid4()))
                    mock_event_repo.get_by_id_for_owner = AsyncMock(return_value=MagicMock(name="Test Event"))
                    
                    target_event_id = uuid4()
                    mock_event_repo.get_event_day_by_id = AsyncMock(return_value=MagicMock(event_id=target_event_id))
                    mock_event_repo_cls.return_value = mock_event_repo

                    result = await service.create_b2b_transfer(
                        user_id=uuid4(),
                        event_id=target_event_id,
                        reseller_id=uuid4(),
                        quantity=2,
                        event_day_id=uuid4(),
                        mode=TransferMode.PAID,
                    )

    assert result.status == "pending_payment"
    assert result.mode == TransferMode.PAID
    assert result.payment_url == "https://razorpay.in/test"
    assert result.ticket_count == 2
    mock_gateway.create_payment_link.assert_called_once()


@pytest.mark.asyncio
async def test_create_customer_transfer_paid_mode_creates_pending_order():
    """Paid mode creates a pending order, generates payment link, returns payment_url."""
    from apps.organizer.service import OrganizerService
    from apps.ticketing.enums import OrderStatus
    from apps.allocation.enums import TransferMode

    mock_repo = AsyncMock()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_repo.session = mock_session

    service = OrganizerService(mock_repo)
    service._ticketing_repo = AsyncMock()
    service._allocation_repo = AsyncMock()
    service._allocation_service = AsyncMock()

    customer_holder = MagicMock(id=uuid4())
    org_holder = MagicMock(id=uuid4())

    service._allocation_repo.get_holder_by_user_id = AsyncMock(return_value=org_holder)
    service._allocation_repo.get_holder_by_phone_and_email = AsyncMock(return_value=None)
    service._allocation_repo.get_holder_by_phone = AsyncMock(return_value=None)
    service._allocation_repo.get_holder_by_email = AsyncMock(return_value=None)
    service._allocation_repo.create_holder = AsyncMock(return_value=customer_holder)
    service._allocation_repo.list_b2b_tickets_by_holder = AsyncMock(return_value=[{"count": 5}])
    service._ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=MagicMock(id=uuid4())
    )
    service._ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4()])

    with patch("apps.organizer.service.get_gateway") as mock_get_gateway:
        mock_gateway = MagicMock()
        mock_gateway.create_payment_link = AsyncMock(
            return_value=MagicMock(
                gateway_order_id="plink_cust123",
                short_url="https://razorpay.in/cust",
                gateway_response={"id": "plink_cust123"},
            )
        )
        mock_get_gateway.return_value = mock_gateway

        with patch("apps.organizer.service.OrderModel") as mock_order_model:
            order_instance = MagicMock()
            order_instance.id = uuid4()
            mock_order_model.return_value = order_instance

            with patch("apps.organizer.service.EventRepository") as mock_event_repo_cls:
                mock_event_repo = MagicMock()
                target_event_id = uuid4()
                mock_event_repo.get_by_id_for_owner = AsyncMock(return_value=MagicMock(name="Test Event"))
                mock_event_repo.get_event_day_by_id = AsyncMock(return_value=MagicMock(event_id=target_event_id))
                mock_event_repo_cls.return_value = mock_event_repo

                result = await service.create_customer_transfer(
                    user_id=uuid4(),
                    event_id=target_event_id,
                    phone="+919999999999",
                    email=None,
                    quantity=1,
                    event_day_id=uuid4(),
                    mode=TransferMode.PAID,
                )

    assert result.status == "pending_payment"
    assert result.mode == TransferMode.PAID
    assert result.payment_url == "https://razorpay.in/cust"
    assert result.ticket_count == 1
    mock_gateway.create_payment_link.assert_called_once()



@pytest.mark.asyncio
async def test_create_organizer_normalizes_slug_and_uses_owner_scope():
    repo = AsyncMock()
    repo.get_by_slug.return_value = None
    repo.add = MagicMock()
    service = OrganizerService(repo)

    organizer = await service.create_organizer(
        owner_user_id=uuid4(),
        name="Ahmedabad Talks",
        bio="Meetups",
        logo_url="https://cdn/logo.png",
        cover_image_url="https://cdn/cover.png",
        website_url="https://example.com",
        instagram_url="https://instagram.com/ahmedabadtalks",
        facebook_url=None,
        youtube_url=None,
        visibility="public",
    )

    assert organizer.slug == "ahmedabad-talks"
    assert organizer.logo_url == "https://cdn/logo.png"
    repo.add.assert_called_once()


@pytest.mark.asyncio
async def test_list_organizers_only_returns_owner_rows():
    owner_id = uuid4()
    repo = AsyncMock()
    repo.list_by_owner.return_value = [SimpleNamespace(owner_user_id=owner_id)]
    service = OrganizerService(repo)

    organizers = await service.list_organizers(owner_id)

    assert len(organizers) == 1
    repo.list_by_owner.assert_awaited_once_with(owner_id)


@pytest.mark.asyncio
async def test_list_organizer_events_filters_by_owner_and_status():
    owner_id = uuid4()
    organizer_id = uuid4()
    repo = AsyncMock()
    repo.list_events_for_owner.return_value = [
        SimpleNamespace(id=uuid4(), organizer_page_id=organizer_id, status="draft")
    ]
    service = OrganizerService(repo)

    events = await service.list_organizer_events(owner_id, organizer_id, "draft")

    assert len(events) == 1
    repo.list_events_for_owner.assert_awaited_once_with(owner_id, organizer_id, "draft")


@pytest.mark.asyncio
async def test_update_organizer_only_changes_provided_fields():
    owner_id = uuid4()
    organizer_id = uuid4()
    organizer = SimpleNamespace(
        id=organizer_id,
        owner_user_id=owner_id,
        name="Ahmedabad Talks",
        slug="ahmedabad-talks",
        bio="Meetups",
        logo_url="https://cdn/logo.png",
        cover_image_url=None,
        website_url=None,
        instagram_url=None,
        facebook_url=None,
        youtube_url=None,
        visibility="public",
    )
    repo = AsyncMock()
    repo.get_by_id_for_owner.return_value = organizer
    repo.get_by_slug.return_value = None
    repo.session = AsyncMock()
    service = OrganizerService(repo)

    updated = await service.update_organizer(
        owner_user_id=owner_id,
        organizer_id=organizer_id,
        bio="New bio",
    )

    assert updated.bio == "New bio"
    assert updated.name == "Ahmedabad Talks"
    assert updated.logo_url == "https://cdn/logo.png"


@pytest.mark.asyncio
async def test_list_public_organizers_returns_only_active():
    from apps.organizer.repository import OrganizerRepository
    
    session = AsyncMock()
    repo = OrganizerRepository(session)

    organizers_data = [
        SimpleNamespace(id=uuid4(), name="Org 1", status="active"),
        SimpleNamespace(id=uuid4(), name="Org 2", status="active"),
    ]
    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=organizers_data)
    session.scalars = AsyncMock(return_value=mock_result)

    organizers = await repo.list_public_organizers()

    assert len(organizers) == 2
    session.scalars.assert_called_once()


@pytest.mark.asyncio
async def test_get_organizer_by_id_returns_organizer():
    from apps.organizer.repository import OrganizerRepository
    
    org_id = uuid4()
    session = AsyncMock()
    repo = OrganizerRepository(session)

    session.scalar.return_value = SimpleNamespace(id=org_id, name="Test Org")

    result = await repo.get_by_id(org_id)

    assert result is not None
    assert result.id == org_id


@pytest.mark.asyncio
async def test_list_events_by_organizer_public_returns_published_events():
    from apps.organizer.repository import OrganizerRepository
    
    org_id = uuid4()
    session = AsyncMock()
    repo = OrganizerRepository(session)

    events_data = [
        SimpleNamespace(id=uuid4(), title="Event 1", is_published=True),
    ]
    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=events_data)
    session.scalars = AsyncMock(return_value=mock_result)

    events = await repo.list_events_by_organizer_public(org_id)

    assert len(events) == 1
    session.scalars.assert_called_once()


@pytest.mark.asyncio
async def test_list_public_organizers_service():
    from apps.organizer.public_service import PublicOrganizerService
    
    repo = AsyncMock()
    repo.list_public_organizers.return_value = [
        SimpleNamespace(id=uuid4(), name="Org 1"),
        SimpleNamespace(id=uuid4(), name="Org 2"),
    ]
    service = PublicOrganizerService(repo)

    result = await service.list_organizers()

    assert len(result) == 2
    repo.list_public_organizers.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_organizer_returns_organizer():
    from apps.organizer.public_service import PublicOrganizerService
    
    org_id = uuid4()
    repo = AsyncMock()
    repo.get_by_id.return_value = SimpleNamespace(id=org_id, name="Test Org")
    service = PublicOrganizerService(repo)

    result = await service.get_organizer(org_id)

    assert result is not None
    assert result.id == org_id


@pytest.mark.asyncio
async def test_get_organizer_raises_not_found():
    from apps.organizer.public_service import PublicOrganizerService
    from exceptions import NotFoundError
    
    org_id = uuid4()
    repo = AsyncMock()
    repo.get_by_id.return_value = None
    service = PublicOrganizerService(repo)

    with pytest.raises(NotFoundError):
        await service.get_organizer(org_id)


@pytest.mark.asyncio
async def test_list_events_by_organizer_returns_only_published():
    from apps.organizer.public_service import PublicOrganizerService
    
    org_id = uuid4()
    repo = AsyncMock()
    repo.list_events_by_organizer_public.return_value = [
        SimpleNamespace(id=uuid4(), title="Event 1", is_published=True),
    ]
    service = PublicOrganizerService(repo)

    result = await service.list_events_by_organizer(org_id)

    assert len(result) == 1

@pytest.mark.asyncio
async def test_create_b2b_transfer_paid_mode_uses_price_for_amount():
    """Paid mode uses price as final_amount and passes price*100 (paise) to gateway."""
    from apps.organizer.service import OrganizerService
    from apps.allocation.enums import TransferMode
    from uuid import uuid4
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_repo = AsyncMock()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_repo.session = mock_session

    service = OrganizerService(mock_repo)
    service._ticketing_repo = AsyncMock()
    service._allocation_repo = AsyncMock()
    service._allocation_service = AsyncMock()

    org_holder = MagicMock(id=uuid4())
    reseller_holder = MagicMock(id=uuid4())
    reseller_user = MagicMock(id=uuid4(), name="Reseller Co", email="reseller@co.in", phone="+919999999999")

    service._allocation_repo.get_holder_by_user_id = AsyncMock(
        side_effect=[org_holder, reseller_holder]
    )
    service._allocation_repo.list_b2b_tickets_by_holder = AsyncMock(return_value=[{"event_day_id": uuid4(), "count": 5}])
    service._allocation_repo.get_holder_by_email = AsyncMock(return_value=None)
    service._allocation_repo.get_holder_by_phone = AsyncMock(return_value=None)
    service._ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=MagicMock(id=uuid4())
    )
    service._ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4(), uuid4()])

    with patch("apps.organizer.service.get_gateway") as mock_get_gateway:
        mock_gateway = MagicMock()
        mock_gateway.create_payment_link = AsyncMock(
            return_value=MagicMock(
                gateway_order_id="plink_test123",
                short_url="https://razorpay.in/test",
                gateway_response={"id": "plink_test123"},
            )
        )
        mock_get_gateway.return_value = mock_gateway

        with patch("apps.organizer.service.OrderModel") as mock_order_model:
            order_instance = MagicMock()
            order_instance.id = uuid4()
            mock_order_model.return_value = order_instance

            with patch("apps.organizer.service.UserRepository") as mock_user_repo_cls:
                mock_user_repo = MagicMock()
                mock_user_repo.find_by_id = AsyncMock(return_value=reseller_user)
                mock_user_repo_cls.return_value = mock_user_repo

                with patch("apps.organizer.service.EventRepository") as mock_event_repo_cls:
                    mock_event_repo = MagicMock()
                    mock_event_repo.get_by_id_for_owner = AsyncMock(return_value=MagicMock(title="Test Event"))
                    mock_event_repo.get_reseller_for_event = AsyncMock(return_value=MagicMock(status="accepted"))
                    mock_event_id = uuid4()
                    mock_event_repo.get_event_day_by_id = AsyncMock(return_value=MagicMock(event_id=mock_event_id))
                    mock_event_repo_cls.return_value = mock_event_repo

                    result = await service.create_b2b_transfer(
                        user_id=uuid4(),
                        event_id=mock_event_id,
                        reseller_id=uuid4(),
                        quantity=2,
                        event_day_id=uuid4(),
                        mode=TransferMode.PAID,
                        price=250.0,
                    )

    assert result.status == "pending_payment"
    # Verify amount passed to gateway was price*100 in paise
    mock_gateway.create_payment_link.assert_called_once()
    call_kwargs = mock_gateway.create_payment_link.call_args.kwargs
    assert call_kwargs["amount"] == int(250.0 * 100)  # 25000 paise = ₹250


@pytest.mark.asyncio
async def test_create_customer_transfer_paid_mode_uses_price_for_amount():
    """Paid mode uses price as final_amount and passes price*100 (paise) to gateway."""
    from apps.organizer.service import OrganizerService
    from apps.allocation.enums import TransferMode
    from uuid import uuid4
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_repo = AsyncMock()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_repo.session = mock_session

    service = OrganizerService(mock_repo)
    service._ticketing_repo = AsyncMock()
    service._allocation_repo = AsyncMock()
    service._allocation_service = AsyncMock()

    customer_holder = MagicMock(id=uuid4())
    org_holder = MagicMock(id=uuid4())

    service._allocation_repo.get_holder_by_user_id = AsyncMock(return_value=org_holder)
    service._allocation_repo.get_holder_by_phone_and_email = AsyncMock(return_value=None)
    service._allocation_repo.get_holder_by_phone = AsyncMock(return_value=None)
    service._allocation_repo.get_holder_by_email = AsyncMock(return_value=None)
    service._allocation_repo.create_holder = AsyncMock(return_value=customer_holder)
    service._allocation_repo.list_b2b_tickets_by_holder = AsyncMock(return_value=[{"count": 5}])
    service._ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=MagicMock(id=uuid4())
    )
    service._ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4()])

    with patch("apps.organizer.service.get_gateway") as mock_get_gateway:
        mock_gateway = MagicMock()
        mock_gateway.create_payment_link = AsyncMock(
            return_value=MagicMock(
                gateway_order_id="plink_cust123",
                short_url="https://razorpay.in/cust",
                gateway_response={"id": "plink_cust123"},
            )
        )
        mock_get_gateway.return_value = mock_gateway

        with patch("apps.organizer.service.OrderModel") as mock_order_model:
            order_instance = MagicMock()
            order_instance.id = uuid4()
            mock_order_model.return_value = order_instance

            with patch("apps.organizer.service.EventRepository") as mock_event_repo_cls:
                mock_event_repo = MagicMock()
                target_event_id = uuid4()
                mock_event_repo.get_by_id_for_owner = AsyncMock(return_value=MagicMock(title="Test Event"))
                mock_event_repo.get_event_day_by_id = AsyncMock(return_value=MagicMock(event_id=target_event_id))
                mock_event_repo_cls.return_value = mock_event_repo

                result = await service.create_customer_transfer(
                    user_id=uuid4(),
                    event_id=target_event_id,
                    phone="+919999999999",
                    email=None,
                    quantity=3,
                    event_day_id=uuid4(),
                    mode=TransferMode.PAID,
                    price=100.0,
                )

    assert result.status == "pending_payment"
    mock_gateway.create_payment_link.assert_called_once()
    call_kwargs = mock_gateway.create_payment_link.call_args.kwargs
    assert call_kwargs["amount"] == int(100.0 * 100)  # 10000 paise = ₹100
