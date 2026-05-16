import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_reseller_customer_transfer_free_mode_happy_path():
    """
    Reseller transfers 2 B2B tickets to customer via phone+email.
    Customer is new (no existing holder). Transfer completes immediately.
    """
    from apps.resellers.service import ResellerService
    from apps.organizer.response import CustomerTransferResponse

    repo = AsyncMock()
    allocation_repo = AsyncMock()
    ticketing_repo = AsyncMock()

    service = ResellerService.__new__(ResellerService)
    service._repo = repo
    service._allocation_repo = allocation_repo
    service._ticketing_repo = ticketing_repo

    user_id = uuid4()
    event_id = uuid4()
    event_day_id = uuid4()
    phone = "+1234567890"
    email = "customer@example.com"
    quantity = 2

    # Mock reseller is accepted for event
    repo.is_accepted_reseller = AsyncMock(return_value=True)

    # Mock get_my_holder_for_event returns reseller holder
    reseller_holder_id = uuid4()
    repo.get_my_holder_for_event = AsyncMock(return_value=MagicMock(id=reseller_holder_id))

    # Mock get_b2b_ticket_type_for_event
    b2b_type_id = uuid4()
    ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=MagicMock(id=b2b_type_id)
    )

    # Mock list_b2b_tickets_by_holder returns 5 available
    allocation_repo.list_b2b_tickets_by_holder = AsyncMock(
        return_value=[{"event_day_id": event_day_id, "count": 5}]
    )

    # Mock get_holder_by_phone_and_email returns None (new customer)
    allocation_repo.get_holder_by_phone_and_email = AsyncMock(return_value=None)
    allocation_repo.get_holder_by_phone = AsyncMock(return_value=None)
    allocation_repo.get_holder_by_email = AsyncMock(return_value=None)

    # Mock create_holder returns new customer holder
    customer_holder_id = uuid4()
    allocation_repo.create_holder = AsyncMock(
        return_value=MagicMock(id=customer_holder_id)
    )

    # Mock order creation
    order_id = uuid4()
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock(side_effect=lambda o: setattr(o, 'id', order_id))
    session.execute = AsyncMock()

    # Patch session access on repo
    repo._session = session

    # Mock lock_tickets_for_transfer
    locked_ids = [uuid4(), uuid4()]
    ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=locked_ids)

    # Mock allocation creation
    allocation_id = uuid4()
    mock_allocation = MagicMock(id=allocation_id)
    claim_link_id = uuid4()
    allocation_repo.create_allocation_with_claim_link = AsyncMock(
        return_value=(mock_allocation, MagicMock(id=claim_link_id))
    )
    allocation_repo.add_tickets_to_allocation = AsyncMock()
    allocation_repo.upsert_edge = AsyncMock()
    allocation_repo.transition_allocation_status = AsyncMock()

    # Mock event_repo to return valid event_day
    mock_event_day = MagicMock()
    mock_event_day.event_id = event_id
    mock_event_repo = MagicMock()
    mock_event_repo.get_event_day_by_id = AsyncMock(return_value=mock_event_day)
    mock_event_repo.get_by_id = AsyncMock(return_value=MagicMock(title="Test Event"))

    with patch('apps.event.repository.EventRepository', return_value=mock_event_repo):
        result = await service.create_reseller_customer_transfer(
            user_id=user_id,
            event_id=event_id,
            phone=phone,
            email=email,
            quantity=quantity,
            event_day_id=event_day_id,
            mode="free",
        )

    assert isinstance(result, CustomerTransferResponse)
    assert result.status == "completed"
    assert result.ticket_count == 2
    assert result.mode == "free"
    assert "claim_link" not in result.model_dump()
    ticketing_repo.update_ticket_ownership_batch.assert_awaited_once_with(
        ticket_ids=locked_ids,
        new_owner_holder_id=customer_holder_id,
        claim_link_id=claim_link_id,
    )


@pytest.mark.asyncio
async def test_create_reseller_customer_transfer_paid_mode():
    """Paid mode creates pending order, generates payment link, returns payment_url."""
    from apps.resellers.service import ResellerService
    from apps.organizer.response import CustomerTransferResponse
    from apps.allocation.enums import TransferMode

    mock_repo = AsyncMock()
    mock_session = AsyncMock()
    mock_repo._session = mock_session
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()

    service = ResellerService(mock_repo)
    service._allocation_repo = AsyncMock()
    service._ticketing_repo = AsyncMock()

    customer_holder = MagicMock(id=uuid4())
    reseller_holder = MagicMock(id=uuid4())

    mock_repo.is_accepted_reseller = AsyncMock(return_value=True)
    mock_repo.get_my_holder_for_event = AsyncMock(return_value=reseller_holder)
    service._allocation_repo.get_holder_by_phone = AsyncMock(return_value=None)
    service._allocation_repo.get_holder_by_email = AsyncMock(return_value=None)
    service._allocation_repo.create_holder = AsyncMock(return_value=customer_holder)
    service._allocation_repo.list_b2b_tickets_by_holder = AsyncMock(return_value=[{"event_day_id": uuid4(), "count": 5}])
    service._ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=MagicMock(id=uuid4())
    )
    service._ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4(), uuid4()])

    with patch("apps.resellers.service.get_gateway") as mock_get_gateway:
        mock_gateway = MagicMock()
        mock_gateway.create_payment_link = AsyncMock(
            return_value=MagicMock(
                gateway_order_id="plink_reseller123",
                short_url="https://razorpay.in/reseller",
                gateway_response={"id": "plink_reseller123"},
            )
        )
        mock_get_gateway.return_value = mock_gateway

        with patch("apps.resellers.service.OrderModel") as mock_order_model:
            order_instance = MagicMock()
            order_instance.id = uuid4()
            mock_order_model.return_value = order_instance

            # Mock event_repo to return valid event_day
            event_id = uuid4()
            event_day_id = uuid4()
            mock_event_day = MagicMock()
            mock_event_day.event_id = event_id
            mock_event_repo = MagicMock()
            mock_event_repo.get_event_day_by_id = AsyncMock(return_value=mock_event_day)
            mock_event_repo.get_by_id = AsyncMock(return_value=MagicMock(title="Test Event"))
            
            with patch('apps.event.repository.EventRepository', return_value=mock_event_repo):
                result = await service.create_reseller_customer_transfer(
                    user_id=uuid4(),
                    event_id=event_id,
                    phone="+919999999999",
                    email=None,
                    quantity=2,
                    event_day_id=event_day_id,
                    mode=TransferMode.PAID,
                )

    assert result.status == "pending_payment"
    assert result.mode == TransferMode.PAID
    assert result.payment_url == "https://razorpay.in/reseller"
    assert result.ticket_count == 2
    mock_gateway.create_payment_link.assert_called_once()


@pytest.mark.asyncio
async def test_reseller_customer_transfer_no_phone_or_email_raises():
    """
    Transfer without phone or email raises BadRequestError.
    """
    from apps.resellers.service import ResellerService
    from exceptions import BadRequestError

    service = ResellerService.__new__(ResellerService)
    service._repo = AsyncMock()

    with pytest.raises(BadRequestError):
        await service.create_reseller_customer_transfer(
            user_id=uuid4(),
            event_id=uuid4(),
            phone=None,
            email=None,
            quantity=2,
            event_day_id=uuid4(),
            mode="free",
        )


@pytest.mark.asyncio
async def test_reseller_customer_transfer_not_reseller_forbidden():
    """
    Non-reseller trying to transfer returns ForbiddenError.
    """
    from apps.resellers.service import ResellerService
    from exceptions import ForbiddenError

    repo = AsyncMock()

    service = ResellerService.__new__(ResellerService)
    service._repo = repo

    repo.is_accepted_reseller = AsyncMock(return_value=False)

    with pytest.raises(ForbiddenError):
        await service.create_reseller_customer_transfer(
            user_id=uuid4(),
            event_id=uuid4(),
            phone="+1234567890",
            email=None,
            quantity=2,
            event_day_id=uuid4(),
            mode="free",
        )


@pytest.mark.asyncio
async def test_reseller_customer_transfer_insufficient_tickets():
    """
    Reseller requests 5 tickets but only 2 available — raises BadRequestError.
    """
    from apps.resellers.service import ResellerService
    from exceptions import BadRequestError

    repo = AsyncMock()
    allocation_repo = AsyncMock()
    ticketing_repo = AsyncMock()

    service = ResellerService.__new__(ResellerService)
    service._repo = repo
    service._allocation_repo = allocation_repo
    service._ticketing_repo = ticketing_repo

    repo.is_accepted_reseller = AsyncMock(return_value=True)
    repo.get_my_holder_for_event = AsyncMock(return_value=MagicMock(id=uuid4()))

    b2b_type_id = uuid4()
    ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=MagicMock(id=b2b_type_id)
    )

    # Only 2 available, requesting 5
    allocation_repo.list_b2b_tickets_by_holder = AsyncMock(
        return_value=[{"event_day_id": uuid4(), "count": 2}]
    )

    # Mock event_repo to return valid event_day
    event_id = uuid4()
    event_day_id = uuid4()
    mock_event_day = MagicMock()
    mock_event_day.event_id = event_id
    mock_event_repo = MagicMock()
    mock_event_repo.get_event_day_by_id = AsyncMock(return_value=mock_event_day)
    mock_event_repo.get_by_id = AsyncMock(return_value=MagicMock(title="Test Event"))

    with patch('apps.event.repository.EventRepository', return_value=mock_event_repo):
        with pytest.raises(BadRequestError) as exc:
            await service.create_reseller_customer_transfer(
                user_id=uuid4(),
                event_id=event_id,
                phone="+1234567890",
                email=None,
                quantity=5,
                event_day_id=event_day_id,
                mode="free",
            )

    assert "Only 2 B2B tickets available" in str(exc.value)


@pytest.mark.asyncio
async def test_reseller_customer_transfer_existing_holder_by_phone():
    """
    Customer already exists with phone only. Reseller transfers — uses existing holder.
    """
    from apps.resellers.service import ResellerService

    repo = AsyncMock()
    allocation_repo = AsyncMock()
    ticketing_repo = AsyncMock()

    service = ResellerService.__new__(ResellerService)
    service._repo = repo
    service._allocation_repo = allocation_repo
    service._ticketing_repo = ticketing_repo

    existing_holder_id = uuid4()
    event_id = uuid4()
    event_day_id = uuid4()

    repo.is_accepted_reseller = AsyncMock(return_value=True)
    repo.get_my_holder_for_event = AsyncMock(return_value=MagicMock(id=uuid4()))

    b2b_type_id = uuid4()
    ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=MagicMock(id=b2b_type_id)
    )
    allocation_repo.list_b2b_tickets_by_holder = AsyncMock(
        return_value=[{"event_day_id": event_day_id, "count": 5}]
    )

    # AND lookup fails, phone lookup succeeds
    allocation_repo.get_holder_by_phone_and_email = AsyncMock(return_value=None)
    allocation_repo.get_holder_by_phone = AsyncMock(
        return_value=MagicMock(id=existing_holder_id)
    )

    # Mock session
    order_id = uuid4()
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock(side_effect=lambda o: setattr(o, 'id', order_id))
    session.execute = AsyncMock()
    repo._session = session

    ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4(), uuid4()])
    allocation_repo.create_allocation_with_claim_link = AsyncMock(
        return_value=(MagicMock(id=uuid4()), MagicMock(id=uuid4()))
    )
    allocation_repo.add_tickets_to_allocation = AsyncMock()
    allocation_repo.upsert_edge = AsyncMock()
    allocation_repo.transition_allocation_status = AsyncMock()

    # Mock event_repo to return valid event_day
    mock_event_day = MagicMock()
    mock_event_day.event_id = event_id
    mock_event_repo = MagicMock()
    mock_event_repo.get_event_day_by_id = AsyncMock(return_value=mock_event_day)
    mock_event_repo.get_by_id = AsyncMock(return_value=MagicMock(title="Test Event"))

    with patch('apps.event.repository.EventRepository', return_value=mock_event_repo):
        result = await service.create_reseller_customer_transfer(
            user_id=uuid4(),
            event_id=event_id,
            phone="+1234567890",
            email="new@example.com",
            quantity=1,
            event_day_id=event_day_id,
            mode="free",
        )

    # create_holder should NOT have been called — used existing holder by phone
    allocation_repo.create_holder.assert_not_called()
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_reseller_customer_transfer_self_transfer_allowed():
    """
    Reseller transfers tickets to their own phone — resolves to their own holder.
    Transfer completes normally. No self-transfer guard needed.
    """
    from apps.resellers.service import ResellerService

    repo = AsyncMock()
    allocation_repo = AsyncMock()
    ticketing_repo = AsyncMock()

    service = ResellerService.__new__(ResellerService)
    service._repo = repo
    service._allocation_repo = allocation_repo
    service._ticketing_repo = ticketing_repo

    reseller_holder_id = uuid4()
    event_id = uuid4()
    event_day_id = uuid4()

    repo.is_accepted_reseller = AsyncMock(return_value=True)
    repo.get_my_holder_for_event = AsyncMock(return_value=MagicMock(id=reseller_holder_id))

    b2b_type_id = uuid4()
    ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=MagicMock(id=b2b_type_id)
    )
    allocation_repo.list_b2b_tickets_by_holder = AsyncMock(
        return_value=[{"event_day_id": event_day_id, "count": 5}]
    )

    # AND lookup succeeds — finds reseller's own holder (same as from get_my_holder_for_event)
    allocation_repo.get_holder_by_phone_and_email = AsyncMock(
        return_value=MagicMock(id=reseller_holder_id)
    )

    # Mock session
    order_id = uuid4()
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock(side_effect=lambda o: setattr(o, 'id', order_id))
    session.execute = AsyncMock()
    repo._session = session

    ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4(), uuid4()])
    allocation_repo.create_allocation_with_claim_link = AsyncMock(
        return_value=(MagicMock(id=uuid4()), MagicMock(id=uuid4()))
    )
    allocation_repo.add_tickets_to_allocation = AsyncMock()
    allocation_repo.upsert_edge = AsyncMock()
    allocation_repo.transition_allocation_status = AsyncMock()

    # Mock event_repo to return valid event_day
    mock_event_day = MagicMock()
    mock_event_day.event_id = event_id
    mock_event_repo = MagicMock()
    mock_event_repo.get_event_day_by_id = AsyncMock(return_value=mock_event_day)
    mock_event_repo.get_by_id = AsyncMock(return_value=MagicMock(title="Test Event"))

    with patch('apps.event.repository.EventRepository', return_value=mock_event_repo):
        result = await service.create_reseller_customer_transfer(
            user_id=uuid4(),
            event_id=event_id,
            phone="+1234567890",
            email="reseller@example.com",
            quantity=1,
            event_day_id=event_day_id,
            mode="free",
        )

    # Transfer completes — no error raised for self-transfer
    assert result.status == "completed"
    # create_holder was NOT called — existing holder was used
    allocation_repo.create_holder.assert_not_called()


@pytest.mark.asyncio
async def test_reseller_customer_transfer_event_day_not_found():
    """
    Provided event_day_id does not belong to the event — raises NotFoundError.
    """
    from apps.resellers.service import ResellerService
    from exceptions import NotFoundError

    repo = AsyncMock()
    service = ResellerService.__new__(ResellerService)
    service._repo = repo

    repo.is_accepted_reseller = AsyncMock(return_value=True)

    # Mock event_day lookup returning None (not found / wrong event)
    mock_event_repo = MagicMock()
    mock_event_repo.get_event_day_by_id = AsyncMock(return_value=None)

    with patch('apps.event.repository.EventRepository', return_value=mock_event_repo):
        with pytest.raises(NotFoundError):
            await service.create_reseller_customer_transfer(
                user_id=uuid4(),
                event_id=uuid4(),
                phone="+1234567890",
                email=None,
                quantity=2,
                event_day_id=uuid4(),
                mode="free",
            )

@pytest.mark.asyncio
async def test_create_reseller_customer_transfer_paid_mode_uses_price_for_amount():
    """Paid mode uses price as final_amount and passes price*100 (paise) to gateway."""
    from apps.resellers.service import ResellerService
    from apps.allocation.enums import TransferMode
    from uuid import uuid4
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_repo = AsyncMock()
    mock_session = AsyncMock()
    mock_repo._session = mock_session
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()

    service = ResellerService(mock_repo)
    service._allocation_repo = AsyncMock()
    service._ticketing_repo = AsyncMock()

    customer_holder = MagicMock(id=uuid4())
    reseller_holder = MagicMock(id=uuid4())

    service._repo.is_accepted_reseller = AsyncMock(return_value=True)
    service._repo.get_my_holder_for_event = AsyncMock(return_value=reseller_holder)
    service._allocation_repo.get_holder_by_phone = AsyncMock(return_value=None)
    service._allocation_repo.get_holder_by_email = AsyncMock(return_value=None)
    service._allocation_repo.create_holder = AsyncMock(return_value=customer_holder)
    service._allocation_repo.list_b2b_tickets_by_holder = AsyncMock(return_value=[{"count": 5}])
    service._ticketing_repo.get_b2b_ticket_type_for_event = AsyncMock(
        return_value=MagicMock(id=uuid4())
    )
    service._ticketing_repo.lock_tickets_for_transfer = AsyncMock(return_value=[uuid4(), uuid4()])

    with patch("apps.resellers.service.get_gateway") as mock_get_gateway:
        mock_gateway = MagicMock()
        mock_gateway.create_payment_link = AsyncMock(
            return_value=MagicMock(
                gateway_order_id="plink_reseller123",
                short_url="https://razorpay.in/reseller",
                gateway_response={"id": "plink_reseller123"},
            )
        )
        mock_get_gateway.return_value = mock_gateway

        with patch("apps.resellers.service.OrderModel") as mock_order_model:
            order_instance = MagicMock()
            order_instance.id = uuid4()
            mock_order_model.return_value = order_instance

            with patch("apps.event.repository.EventRepository") as mock_event_repo_cls:
                mock_event_repo = MagicMock()
                mock_event_id = uuid4()
                mock_event_repo.get_by_id = AsyncMock(return_value=MagicMock(title="Test Event"))
                mock_event_repo.get_event_day_by_id = AsyncMock(return_value=MagicMock(event_id=mock_event_id))
                mock_event_repo_cls.return_value = mock_event_repo

                result = await service.create_reseller_customer_transfer(
                    user_id=uuid4(),
                    event_id=mock_event_id,
                    phone="+919999999999",
                    email=None,
                    quantity=2,
                    event_day_id=uuid4(),
                    mode=TransferMode.PAID,
                    price=175.0,
                )

    assert result.status == "pending_payment"
    mock_gateway.create_payment_link.assert_called_once()
    call_kwargs = mock_gateway.create_payment_link.call_args.kwargs
    assert call_kwargs["amount"] == int(175.0 * 100)  # 17500 paise = ₹175
