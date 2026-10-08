# C02 change card — approval workflow (Part B.12)

Impact analysis performed on 2026-09-28 **before application edits**.
Baseline: v0.1; requested change: some Resources require an authorized person's
approval before CONFIRMED. Approval may be delayed, rejected or expire.
This impact analysis covers B.12–14.

## Observed starting point

`src/main.py` exposes Create, Availability, Confirm and Cancel. Confirmation
checks DRAFT, capacity and overlap while holding the Room row lock; cancellation
uses the same lock. Models have no approval fields. Demo identity and the
assumption that all registered rooms are active are explicit v0.1 decisions.
The v0.1 acceptance suite uses isolated real PostgreSQL schemas.

## Impact analysis

| Area | Impact before implementation |
| --- | --- |
| Create / OP-01 / REQ-01 | Preserve DRAFT/no allocation; capture whether approval is required and a server-owned deadline. Protected resources need a future start so there is a useful decision window. Ordinary rooms keep v0.1 behavior. |
| Availability / OP-02 / REQ-02 | Blocking semantics unchanged: pending/approved/rejected/expired drafts do not allocate. Expose room approval policy so availability is not mistaken for permission to confirm. |
| Confirm / OP-03 / REQ-03 | Add approval eligibility guard evaluated at transition time; APPROVED alone never allocates. Capacity and overlap must still be checked because approval can be delayed. |
| Concurrent Confirm / REQ-04 | Existing exclusivity requirement unchanged; new decision/deadline must be evaluated consistently with concurrent Approve/Cancel. |
| Approve / new OP-05 | New assigned-approver actor. Record approve/reject decision and actor/time; enforce per-room permission within the trusted demo identity boundary. Reject is an outcome of this operation, not a sixth core goal. |
| Cancel / OP-04 / REQ-05 | Preserve DRAFT/CONFIRMED policy and retained records; any approval substate of DRAFT can be cancelled. No later approval may revive it. |
| Statechart | Use two dimensions: reservation lifecycle plus approval status. Pending, approved, rejected and expired are not allocations. Cancellation/confirmation ends the approval window. |
| Use-case view | Add assigned Approver and Approve Reservation; no invented notification actor. |
| Verification | Keep ordinary-room v0.1 regressions; add pending rejection, authorization, approve/reject, deadline boundaries, delayed overlap, and competing operations. |
| Persistence/setup | Add room policy, reservation approval metadata and decision enum. Existing databases need an explicit additive migration; create_all alone cannot upgrade them. |
| Interface | API/Swagger is the complete v0.2 interface; the existing UI remains a v0.1 demo. No UI rewrite is required by this assignment. |

## Proposed policy and alternatives

Retain DRAFT/CONFIRMED/CANCELLED and track approval separately. This avoids
pretending APPROVED means allocated. Ordinary reservations use NOT_REQUIRED;
protected ones start PENDING. Approve accepts either APPROVED or REJECTED.
Only a pending, unexpired draft can receive one decision. No resubmission or
renewal in v0.2; a new reservation is needed after rejection/expiry.

Proposed deadline: earlier of Create + 24 hours and reservation start. At the
exact deadline, a pending or approved draft is EXPIRED. A committed CONFIRMED
reservation is never automatically cancelled by that deadline. Expiry is an
observable derived status, not a background job or mutation on GET.

Alternatives considered: allocate on approval (rejected: conflates decisions
and allocation); block availability while waiting (rejected: introduces holds);
introduce a queue/worker now (deferred: unnecessary to show correct expiry at
read/transition time). The selected policy is recorded in the v0.2 specification.

## Architecture drivers carried to C03, not solved here

- Trusted identity integration and per-resource authorization beyond the demo.
- Atomic state/decision checks under concurrent requests and retries.
- Authoritative clock, boundary semantics and multi-instance clock consistency.
- Durable decision attribution and future audit/history requirements.
- Schema evolution that preserves existing reservations.
- Potential notification/retry/scheduling needs if stakeholders later require
  proactive expiry messages; no delivery guarantees are invented now.

The subsequent implementation results and acceptance record are in
[Baseline v0.2 evidence](Baseline%20v0.2-evidence.md).
