# Baseline v0.2 — approval workflow (Part B.13)

Status: implemented. Team acceptance is recorded in
[Baseline v0.2 evidence](Baseline%20v0.2-evidence.md).
The deadline policy was selected on 2026-09-28. The
[change analysis](change-approval-impact.md) records the B.12 impact assessment.

## Changed condition and scope

Some rooms require a decision by their assigned Approver before a reservation
can be confirmed. Waiting can be delayed, a decision can be rejection, and
pending or approved drafts can expire. Approval is permission, not allocation.
The runnable interface for v0.2 is the API/Swagger; no new browser UI is required.

The v0.1 trusted demo identity and all-registered-rooms-active assumptions remain.
The new operation enforces that the asserted user is the room's assigned
approver. `X-User-Id` is a trusted demo identity assertion, not authentication:
a caller can impersonate a user if the API is exposed to untrusted clients.
Production authentication remains an open architecture requirement.
User/room provisioning is trusted setup. No public API edits room policy or
approver assignments after creation. Self-approval is allowed if that user was
explicitly assigned; separation of duties is not an unstated constraint.

## Changed and unchanged requirements

| Requirement / slice | v0.2 effect |
| --- | --- |
| REQ-01 / OP-01 Create | DRAFT retained; initialize approval metadata according to Room policy; protected-room start must be future |
| REQ-02 / OP-02 Availability | Core outcome unchanged; only CONFIRMED allocates, so approval substates do not block; room response adds policy |
| REQ-03 / OP-03 Confirm | New guard: NOT_REQUIRED or still-valid APPROVED; pending/rejected/expired is a conflict |
| REQ-04 / OP-03 concurrency | Exclusive confirmed allocation unchanged; additionally coordinate with decision and cancellation |
| REQ-05 / OP-04 Cancel | Lifecycle/time policy unchanged; all approval substates of DRAFT can be cancelled |
| REQ-06 / OP-01 validation | Existing failures unchanged; add protected-room start/deadline validation |
| REQ-07 / OP-05 Approve | New assigned actor can record one approve/reject decision before expiry, without allocation |
| REQ-08 / time semantics | New observable expiry boundary on reads and state-change validation |

Unchanged rules from [v0.1](baseline-v0.1.md): BR-01 interval semantics,
BR-02 exclusive allocation, BR-03 cancellation policy, BR-04 capacity and
BR-07 read/atomicity principles. They still apply to ordinary and protected
rooms. BR-05 is extended with approval attribution; BR-06's Confirm eligibility
is extended by BR-08 below. Three reservation lifecycle states are unchanged.
Approve is a separate operation; Confirm continues to allocate the room.

## New shared rules and state semantics

| ID | Authoritative definition |
| --- | --- |
| BR-08 — Approval eligibility | Snapshot approval requirement at Create: ordinary room → NOT_REQUIRED; protected room → PENDING. Only NOT_REQUIRED or APPROVED with an unexpired window can Confirm a DRAFT. Approve never allocates or guarantees availability. |
| BR-09 — Decision authority | Room has one existing assigned User if requires_approval=true; ordinary room has no assigned approver. Only the assigned asserted identity may decide, only once, on a PENDING unexpired DRAFT. Decision is APPROVED or REJECTED with server-owned decided_by and decided_at. Repeats, reversals and resubmissions are rejected. |
| BR-10 — Deadline | For protected reservations, deadline=min(server UTC Create time + 24h, reservation start); start must be after Create time. At now >= deadline, pending or approved DRAFT has effective EXPIRED status. At now < deadline it remains eligible for its applicable action. Clock is sampled after acquiring transition serialization; time passing after a successful Confirm does not undo allocation. |
| BR-11 — Retention and expiry | Persist the original decision and deadline. Effective EXPIRED is derived on read/validation without a background task or GET mutation. REJECTED stays rejected; expired/rejected drafts can be cancelled but never reapproved. Create a new reservation to try again. After lifecycle leaves DRAFT, approval_status displays the recorded decision for history, not permission to act; no deadline is evaluated for CANCELLED/CONFIRMED. |
| BR-12 — Competing actions | Approve, Confirm, and Cancel must produce an outcome equivalent to one serial order. Competing approve/reject: exactly one valid decision succeeds. Approve/Cancel: Cancel succeeds, final CANCELLED; Approve succeeds only if first. Approve/Confirm: Confirm may succeed only if a valid approval precedes its eligibility check; otherwise reject without auto-retry. Concurrent eligible Confirm still obeys BR-02. |

New Room fields: `requires_approval` (default false), `approver_user_id` (nullable
foreign key). A reservation stores `approval_decision`, `approval_deadline`,
`decided_by`, `decided_at`; response also reports derived `approval_status`.
Client-supplied decision metadata is never used by Create. The stored decision
is NOT_REQUIRED/PENDING/APPROVED/REJECTED; EXPIRED is a derived response value.
All timestamps are timezone-aware. Existing migrated reservations keep
NOT_REQUIRED, preserving their prior eligibility and state.

## OP-01 — Create Reservation (v0.2)

**Goal / user value:** record room-use intent and, where required, begin an
approval window without holding the room.

**Trigger:** student submits the v0.1 payload to `POST /reservations`.

**Observable requirement(s):** REQ-01/06: valid input creates one DRAFT and returns
201/id/state/approval metadata; invalid input creates nothing. Protected rooms
start PENDING; ordinary rooms retain NOT_REQUIRED behavior.

**Preconditions:** v0.1 input/reference/capacity conditions; for a protected room,
requested start is strictly after the sampled server Create time.

**Success postcondition:** persisted DRAFT and applicable deadline; no allocation.

**State change:** new → DRAFT with PENDING or NOT_REQUIRED approval.

**Referenced business rule(s) / invariant(s):** BR-01/02/04/05/07/08/10.

**Main success scenario:**

1. Student submits reservation data.
2. System validates existing user/room, time, purpose and capacity.
3. System derives approval requirement and deadline from trusted policy/time.
4. System persists DRAFT and returns its id, lifecycle and approval fields.

**Alternative / failure outcomes:** existing 404/422 outcomes unchanged;
protected-room start at or before now → 422/no create. Ordinary rooms may still
use past intervals. Overlap does not prevent creating a draft.

**Verification examples:** V01 protected Create → PENDING; V02 ordinary
regressions → NOT_REQUIRED; V03 start at now → 422; V04 deadline is the earlier
of +24h and start.

**Rationale / source:** change card requires approval for only some resources;
user-selected deadline policy requires a nonempty window.

## OP-02 — Check Availability (v0.2)

**Goal / user value:** find capacity-suitable, unallocated rooms while seeing
which rooms also require approval.

**Trigger:** GET `/rooms/available` with v0.1 query fields.

**Observable requirement(s):** REQ-02 unchanged: exact qualifying room list,
200, no holds/writes; each returned Room now includes its approval policy.

**Preconditions:** valid interval and positive people per v0.1.

**Success postcondition:** result respects capacity and confirmed overlaps;
reservations unchanged. Available does not imply approval has been granted.

**State change:** none.

**Referenced business rule(s) / invariant(s):** BR-01/02/04/07/08.

**Main success scenario:**

1. User submits interval and people.
2. System validates query and evaluates capacity/confirmed overlaps.
3. System returns qualifying rooms with their approval policy.

**Alternative / failure outcomes:** invalid query → 422; no match → 200/empty.
Pending, approved, rejected and expired DRAFT records never block a room.

**Verification examples:** V05 approve a draft, then search → room still present;
Confirm it → excluded. Existing adjacency and invalid-query tests remain valid.

**Rationale / source:** approval is separate permission; only confirmed allocation
is an exclusive hold. No waiting-list or provisional-hold policy was requested.

## OP-03 — Confirm Reservation (v0.2)

**Goal / user value:** allocate a room once both permission and booking constraints hold.

**Trigger:** POST `/reservations/{id}/confirm` from the existing demo administrator.

**Observable requirement(s):** REQ-03/04: success 200/CONFIRMED only for eligible
DRAFT; preserve exclusive allocation under concurrent attempts. REQ-08 applies
the current deadline at validation, not an earlier search/approval response.

**Preconditions:** v0.1 DRAFT/capacity/no-overlap conditions plus BR-08 and BR-10.

**Success postcondition:** allocation committed; approval metadata retained.

**State change:** DRAFT → CONFIRMED; approval decision is not overwritten.

**Referenced business rule(s) / invariant(s):** BR-01/02/04/06/07/08/10/12.

**Main success scenario:**

1. Caller submits reservation id.
2. System evaluates current lifecycle and effective approval after competing changes.
3. System checks capacity and current confirmed overlaps.
4. System commits CONFIRMED while preserving exclusivity and returns the record.

**Alternative / failure outcomes:** pending, rejected or expired approval →
409/unchanged draft; existing missing-id/state/capacity/overlap failures retain
v0.1 semantics. Approval may succeed after another booking allocated the interval;
Confirm still rejects that overlap. No automatic confirmation on approval.

**Verification examples:** V06 pending/rejected/expired → 409; V07 approved
before deadline → CONFIRMED; V08 delayed approval followed by overlapping Confirm
→ 409; V09 two approved conflicting drafts → one confirmation succeeds.

**Rationale / source:** change card adds a necessary condition, not a replacement
for capacity/availability checks.

## OP-04 — Cancel Reservation (v0.2)

**Goal / user value:** withdraw pending or decided requests and release any allocation.

**Trigger:** POST `/reservations/{id}/cancel` from student or administrator.

**Observable requirement(s):** REQ-05 unchanged: cancel eligible lifecycle state,
retain details and decision attribution, release allocation, reject repeat.

**Preconditions:** DRAFT or CONFIRMED; any approval substate; no time cutoff.

**Success postcondition:** CANCELLED retained record; no later Confirm/Approve allowed.

**State change:** DRAFT/CONFIRMED → CANCELLED; stored decision retained (BR-11).

**Referenced business rule(s) / invariant(s):** BR-02/03/06/07/11/12.

**Main success scenario:**

1. Caller requests cancellation.
2. System checks current lifecycle consistently with competing decisions.
3. System commits CANCELLED, preserves decision history and returns the record.

**Alternative / failure outcomes:** missing → 404; repeated Cancel → 409;
concurrent decision cannot resurrect the cancelled reservation. Effective expiry
is not persisted as a decision; cancellation retains the underlying decision.

**Verification examples:** V10 cancel pending/approved/rejected/expired drafts;
V11 concurrent Approve/Cancel ends CANCELLED; existing confirmed/repeated/past
cancellation cases remain unchanged.

**Rationale / source:** cancellation ends the request regardless of approval progress;
the v0.1 retained-record and unrestricted-time policy remains applicable.

## OP-05 — Approve Reservation

**Goal / user value:** allow the assigned responsible person to approve or reject
use of a protected room, independently of resource allocation.

**Trigger:** assigned Approver submits `{"decision":"APPROVED"}` or
`{"decision":"REJECTED"}` to POST `/reservations/{id}/approve`, asserting demo
identity with `X-User-Id`.

**Observable requirement(s):** REQ-07: only the assigned asserted user can record
one decision on a pending unexpired DRAFT, returning 200 with decision/actor/time
and unchanged DRAFT lifecycle. REQ-08: now at/after deadline rejects a decision.

**Preconditions:** identity provided, existing reservation and assigned actor;
current DRAFT, effective PENDING, time before deadline.

**Success postcondition:** decision and attribution are durable; no room allocated.

**State change:** DRAFT/PENDING → DRAFT/APPROVED or DRAFT/REJECTED.

**Referenced business rule(s) / invariant(s):** BR-02/07/08/09/10/11/12.

**Main success scenario:**

1. Approver selects a pending reservation and an approve decision.
2. System requires the asserted identity and checks per-room assignment.
3. System evaluates current lifecycle, pending status and deadline.
4. System records APPROVED, deciding user and server timestamp atomically.
5. System returns the decision and DRAFT lifecycle, without confirming the room.

**Alternative / failure outcomes:**

- REJECTED input follows the same authorized flow, returning 200/REJECTED;
  this is a successful negative business decision, not an HTTP failure.
- Missing identity → 401; unknown/wrong/non-assigned user → 403. Ordinary rooms
  have no approver, so attempts to decide them are forbidden.
- Existing identity assertion but missing reservation → 404.
- Repeated/reversed decision, EXPIRED, CANCELLED or CONFIRMED → 409/no write.
- Invalid decision or malformed identity → 422/no write.
- Delayed decision before deadline is allowed; overlap is checked later by Confirm.

**Verification examples:** V12 assigned user approves with actor/time persisted;
V13 wrong/missing identity rejected; V14 rejection blocks Confirm and reversal;
V15 one microsecond before deadline allowed, exact deadline and after rejected;
V16 repeated and competing opposite decisions produce only one accepted decision;
V17 Approve/Confirm race either confirms after approval or rejects early Confirm.

**Rationale / source:** Part B introduces a real approval workflow with a new
responsible actor. A single decision operation covers acceptance and rejection
without creating a misleading allocation side effect.

## Changed views and verification plan

See [v0.2 views](baseline-v0.2-diagrams.md) for the actor-goal view, lifecycle,
approval-state view and five activity flows. The full slices above replace the
v0.1 slices for current behavior; v0.1 remains a historical baseline.

| Examples | Executable check in `tests/test_approval.py` |
| --- | --- |
| V01, V05, V07, V12 | `test_approval_is_permission_not_allocation` |
| V02 | existing `tests/test_baseline.py` ordinary-room regression suite |
| V03–V04 | `test_deadline_minimum_and_protected_past_start` |
| V06, V14 | `test_reject_cannot_confirm_but_can_cancel`; deadline tests |
| V08 | `test_delayed_approval_does_not_override_new_conflict` |
| V09 | `test_concurrent_approved_confirms_still_exclusive` |
| V10 | `test_cancel_approval_states_prevents_later_decisions`; rejection test |
| V11, V16–V17 | `test_approval_races`; `test_repeated_decision_and_invalid_input` |
| V13 | `test_only_assigned_approver_can_decide` |
| V15 | `test_deadline_boundary_on_confirm_or_approve` |
| V18: CONFIRMED survives deadline | `test_confirmed_allocation_survives_approval_deadline` |
| V19: old records survive upgrade | `test_migration_preserves_v01_records_and_is_repeatable` |

Exact-time cases replace the server clock deterministically rather than sleeping.
Concurrency cases synchronize two independent PostgreSQL sessions before state
transition locking. Passing cases support those scenarios, not every possible
interleaving or a production security/performance guarantee.

## Requirement gate and consistency review

| Requirement | Meaning / rationale / observable result | State, time, concurrency and falsifier | Feasibility / verification / consistency / unknown |
| --- | --- | --- | --- |
| REQ-01/06 | Intent remains DRAFT; policy sets approval; reject invalid create | Create allocating or accepting protected past start would falsify it | Existing persistence plus metadata; V01–04 and v0.1 negatives; no new auth claim |
| REQ-02 | Available means unallocated with adequate capacity | Any pending/approved draft blocking search would falsify it | Same query; V05/regressions; aligns with BR-02 |
| REQ-03 | Confirm requires permission AND capacity/no conflict | Pending/expired confirming, or late approval bypassing overlap, falsifies it | Guarded transition; V06–08/V15; aligns with lifecycle |
| REQ-04 | One exclusive allocation under competition | Two conflicting committed CONFIRMED rows falsify it | Existing serialization; V09; broader scale remains C03 driver |
| REQ-05 | Withdraw without deleting or reviving | Approve reviving CANCELLED or retained fields disappearing falsifies it | Same lifecycle with decision retention; V10–11 and regressions |
| REQ-07 | Assigned actor records one decision without allocation | Wrong actor succeeds, repeated decision overwrites, or approval allocates falsifies it | Per-room check in trusted demo; V12–14/V16–17; real authentication unresolved for C03 |
| REQ-08 | Exact UTC deadline invalidates pending/approved draft eligibility | Success at deadline, or expiry cancelling CONFIRMED, falsifies it | Derived status and transition-time clock; V15/V18; multi-host clock policy is C03 work |

Cross-view review: all five goals have slices/activity flows; only CONFIRMED
blocks; both approval outcomes retain DRAFT; rejected/expired has no route to
Confirm; cancellation remains available from DRAFT; views use the same exact
time inequality. There is no notification actor or presumed background worker.
Acceptance and execution results are recorded in
[Baseline v0.2 evidence](Baseline%20v0.2-evidence.md).

## Architecture drivers for C03

Carry forward identity integration/per-room authorization, authoritative clock
and expiry semantics, atomic transitions under contention, retry/idempotency
policy, decision audit retention, and schema evolution. The minimal API uses
existing transaction structure and computes expiry on demand. No queue,
scheduler, microservice split or production identity provider is selected here.
Whether stakeholders require proactive expiry/decision notifications remains
unresolved; delivery is outside this version.
