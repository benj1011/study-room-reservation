"""C05 DD-03/DD-08: deadline evaluation is pure and occurs after serialization."""
from datetime import datetime, timedelta, timezone

import pytest

from src.models import ApprovalStatus, Reservation, ReservationState


@pytest.mark.parametrize("decision", [ApprovalStatus.PENDING, ApprovalStatus.APPROVED])
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_effective_expiry_is_a_pure_boundary_query(decision, offset):
    deadline = datetime(2030, 10, 1, 10, tzinfo=timezone.utc)
    reservation = Reservation(
        state=ReservationState.DRAFT,
        approval_decision=decision,
        approval_deadline=deadline,
        decided_by=7 if decision == ApprovalStatus.APPROVED else None,
        decided_at=deadline - timedelta(hours=1) if decision == ApprovalStatus.APPROVED else None,
    )
    before = (reservation.state, reservation.approval_decision,
              reservation.approval_deadline, reservation.decided_by, reservation.decided_at)
    now = deadline + timedelta(microseconds=offset)
    expected = decision if offset < 0 else ApprovalStatus.EXPIRED
    assert reservation.effective_approval_status(now) == expected
    # Equivalent instants in another timezone obey the same boundary.
    assert reservation.effective_approval_status(now.astimezone(timezone(timedelta(hours=2)))) == expected
    assert (reservation.state, reservation.approval_decision,
            reservation.approval_deadline, reservation.decided_by, reservation.decided_at) == before


@pytest.mark.parametrize("state", [ReservationState.CONFIRMED, ReservationState.CANCELLED])
def test_expiry_does_not_rewrite_terminal_lifecycle(state):
    deadline = datetime(2030, 10, 1, 10, tzinfo=timezone.utc)
    reservation = Reservation(state=state, approval_decision=ApprovalStatus.APPROVED,
                              approval_deadline=deadline)
    assert reservation.effective_approval_status(deadline + timedelta(days=1)) == ApprovalStatus.APPROVED
    assert reservation.state == state


@pytest.mark.parametrize("decision", [ApprovalStatus.NOT_REQUIRED, ApprovalStatus.REJECTED])
def test_non_expiring_decisions_are_preserved(decision):
    deadline = datetime(2030, 10, 1, 10, tzinfo=timezone.utc)
    reservation = Reservation(state=ReservationState.DRAFT, approval_decision=decision,
                              approval_deadline=None if decision == ApprovalStatus.NOT_REQUIRED else deadline)
    assert reservation.effective_approval_status(deadline + timedelta(days=1)) == decision
    assert reservation.approval_decision == decision
