# Baseline v0.2

## Accepted baseline: 

- Approval workflow. The specification and implementation are prepared for review.Accepted by Team on 28/9

- The baseline includes Create Reservation, Check Availability, Confirm Reservation, Cancel Reservation, and Approve Reservation. Approval is separate from resource allocation.

## Core operations demonstrated:

- Create Reservation persists a DRAFT without allocating a room. Reservations for approval-required rooms start with PENDING approval.
- Check Availability considers room capacity and overlapping CONFIRMED reservations.
- Approve Reservation allows the assigned approver to record APPROVED or REJECTED without allocating the room.
- Confirm Reservation allocates the room only when approval, capacity, and overlap conditions are satisfied.
- Cancel Reservation retains the record and releases any allocation.

## Verification examples actually executed:

28/9/2026 21:46 : 55 passed, 2 warnings in 4.72s

Executed examples covered valid and invalid creation, interval boundaries, capacity, confirmation conflicts, cancellation, assigned-approver checks, rejection, approval expiry, concurrent operations, and preservation of existing records during migration.

```bash
Command: python -m pytest tests/test_baseline.py tests/test_approval.py -v --tb=short
```

"baseline 29 items, approvall, 26 items"
Tests used isolated database schemas. Deadline tests used a controlled clock.

## Mismatch found and resolved:
Impact analysis identified a gap between v0.1 and the changed requirements:  Confirmation had no approval guard, and the model had no approval policy, decision, or deadline.
This was resolved by adding room-level approval configuration, reservation approval metadata, an assigned-approver decision operation, and approval eligibility checks during confirmation.

No remaining mismatch was observed in the executed test cases.

## NChange impact summary:
Confirm requires valid approval in addition to the existing booking constraints. A new Approve Reservation operation records approval or rejection.
Availability continues to be blocked only by CONFIRMED reservations. Cancellation retains its existing lifecycle policy and supports drafts in every approval substate.

## Remaining assumption / unknown:

Identity remains a trusted demo assertion through X-User-Id; production authentication is not implemented. All registered rooms are assumed active.

Approval expires at the earlier of 24 hours after creation and the reservation start. Rejected or expired requests require a new reservation.

## Architecture driver(s) carried into C03:
- Trusted identity integration and per-resource authorization.
- Atomic approval, confirmation, and cancellation under concurrency.
- Authoritative time and consistent expiry evaluation.
- Notification and delivery requirements if introduced later.
## Application commit/tag:


