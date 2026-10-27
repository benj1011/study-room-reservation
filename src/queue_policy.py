"""FIFO among directly overlapping active requests; no automatic confirmation."""
from src.models import ApprovalStatus, ReservationState


def overlaps(left, right):
    return (left.room_id == right.room_id
            and left.start_time < right.end_time
            and left.end_time > right.start_time)


def active_request(reservation, room, now):
    return (reservation.state == ReservationState.DRAFT
            and reservation.start_time > now
            and reservation.number_of_people <= room.capacity
            and reservation.effective_approval_status(now) in (
                ApprovalStatus.NOT_REQUIRED, ApprovalStatus.PENDING, ApprovalStatus.APPROVED))


def queue_details(reservation, room, candidates, now):
    if reservation.state != ReservationState.DRAFT:
        return "NONE", 0
    if (reservation.start_time <= now
            or reservation.effective_approval_status(now) == ApprovalStatus.EXPIRED):
        return "EXPIRED", 0
    if not active_request(reservation, room, now):
        return "INACTIVE", 0
    if any(other.state == ReservationState.CONFIRMED and overlaps(other, reservation)
           for other in candidates):
        return "BLOCKED", 0
    ahead = sum(1 for other in candidates
                if other.id < reservation.id and overlaps(other, reservation)
                and active_request(other, room, now))
    return ("WAITING" if ahead else "READY"), ahead
