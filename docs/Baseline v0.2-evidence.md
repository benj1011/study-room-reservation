# Baseline v0.2 — evidence

## Accepted baseline

The approval-workflow baseline was accepted by the team on 2026-09-28.

- The baseline includes Create Reservation, Check Availability, Confirm Reservation, Cancel Reservation, and Approve Reservation. Approval is separate from resource allocation.

## Core operations demonstrated

- Create Reservation persists a DRAFT without allocating a room. Reservations for approval-required rooms start with PENDING approval.
- Check Availability considers room capacity and overlapping CONFIRMED reservations.
- Approve Reservation allows the assigned approver to record APPROVED or REJECTED without allocating the room.
- Confirm Reservation allocates the room only when approval, capacity, and overlap conditions are satisfied.
- Cancel Reservation retains the record and releases any allocation.

## Executed verification examples

Run recorded on 2026-09-28 at 21:46: **55 passed, 2 warnings in 4.72s**.

Executed examples covered valid and invalid creation, interval boundaries, capacity, confirmation conflicts, cancellation, assigned-approver checks, rejection, approval expiry, concurrent operations, and preservation of existing records during migration.

```bash
python -m pytest tests/test_baseline.py tests/test_approval.py -v --tb=short
```

The run included 29 baseline tests and 26 approval tests.

Tests used isolated database schemas. Deadline tests used a controlled clock.

## Mismatch found and resolved
Impact analysis identified a gap between v0.1 and the changed requirements: confirmation had no approval guard, and the model had no approval policy, decision, or deadline.
This was resolved by adding room-level approval configuration, reservation approval metadata, an assigned-approver decision operation, and approval eligibility checks during confirmation.

No remaining mismatch was observed in the executed test cases.

## Change impact summary
Confirm requires valid approval in addition to the existing booking constraints. A new Approve Reservation operation records approval or rejection.
Availability continues to be blocked only by CONFIRMED reservations. Cancellation retains its existing lifecycle policy and supports drafts in every approval substate.

## Assumptions and open questions

Identity remains a trusted demo assertion through X-User-Id; production authentication is not implemented. All registered rooms are assumed active.

Approval expires at the earlier of 24 hours after creation and the reservation start. Rejected or expired requests require a new reservation.

## Architecture drivers carried into C03
- Trusted identity integration and per-resource authorization.
- Atomic approval, confirmation, and cancellation under concurrency.
- Authoritative time and consistent expiry evaluation.
- Notification and delivery requirements if introduced later.

## Application version

The original execution record does not include an application commit or tag.

