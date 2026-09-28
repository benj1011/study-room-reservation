# Baseline v0.1 — complete minimum system

Status: specification and executable verification prepared; team acceptance pending.
Executed results are recorded separately in [C02 evidence](baseline-v0.1-evidence.md).
The scenario catalogue defines expected behavior, not proof by itself.

## C02 scope and CP1 connection

C02 assumes C01 is complete and primarily builds Requirements + Evidence.
The existing [C01 evidence](evidence-and-evolution.md) is reused without
recreating its experiment or outputs. This specification defines the complete
minimum behavior, independently of how much the existing test proves.

C03 adds Architecture and turns the running baseline into a defensible
walking skeleton. References below to existing implementation mechanisms
describe current code, not completion or validation of C03. CP1 is frozen
after C03 and reviewed during C04; this C02 specification does not freeze CP1.

## Purpose and boundary

Students reserve study rooms for a time interval. A Room is the Resource;
a Reservation links one existing User to one existing Room. The minimum
system has exactly four core operations: Create Reservation, Check
Availability, Confirm Reservation, and Cancel Reservation.

The browser, reservation API, and PostgreSQL storage are inside the system.
The Notification Service is an identified external boundary; delivery is
not required or invoked in v0.1. Its future failure policy remains open.

Students create reservations, check availability, view their records, and
cancel them. The current administrator interface offers confirmation and
cancellation. This is an interface responsibility, not a business approval
workflow: Confirm checks system constraints and allocates the room. There
is no Approve operation, approval decision, approver field, or approval state.

The baseline assumes an existing user identity and prepared room records.
Authentication and enforced role/ownership authorization are outside this
demonstration baseline; the current Admin page and API do not enforce them.
User/room setup and reservation reads support the four operations.

**A-01 — Demo identity boundary:** the user explicitly selected the existing
trusted demo identity for C02. “Authorized User” in the assignment reference
is an environmental assumption here, not a verified access-control feature.
Unknown user ids are rejected, but that is not authentication. No 401/403 or
ownership enforcement is claimed. This is an explicit adaptation of the
reference example, to be included in the team's acceptance review.

**A-02 — Active resources:** the user explicitly selected the policy that
all registered rooms are active. There is no inactive state or deactivate
operation in v0.1. Thus the reference Confirm “active” guard is satisfied
by an existing room within this restricted domain. Inactive-room rejection
cannot be demonstrated and is not claimed. A later inactive-room feature
must extend the model, availability rules, Confirm guard, and tests.

## Minimum persistent model

| Entity | Required stored fields |
| --- | --- |
| User | `id`, `name`, `email` |
| Room | `id`, `name`, `location`, `capacity` |
| Reservation | `id`, `user_id`, `room_id`, `start_time`, `end_time`, `number_of_people`, `purpose`, `state` |

## Shared business rules and invariants

These are the authoritative definitions. Slices and diagrams reference their
identifiers; short labels in diagrams do not redefine them.

| ID | Rule / invariant |
| --- | --- |
| BR-01 — Time | Start and end are timezone-aware instants with start < end. Intervals are half-open `[start,end)`. Overlap means `a.start < b.end AND a.end > b.start`. Adjacent intervals do not overlap. |
| BR-02 — Exclusive resource | In every committed state reachable through the supported API, no two CONFIRMED reservations overlap for the same room. Only CONFIRMED blocks availability, regardless of unused seats. This includes concurrent attempts. |
| BR-03 — Cancellation | DRAFT and CONFIRMED may be cancelled, with no start-time deadline. Before, at, or after start has the same outcome; no wall clock is consulted. Repeated Cancel is rejected with 409. Original details and identifier are retained. Cancel/Confirm races must be equivalent to one serial order: confirm then cancel both succeed, or cancel succeeds then confirm conflicts; final state is CANCELLED. |
| BR-04 — Capacity (from C01) | Room capacity and attendance are positive integers; attendance must not exceed room capacity at Create and Confirm. Availability excludes rooms below requested attendance. |
| BR-05 — Identity and data | Each reservation has a unique generated id and references existing User and Room records. Purpose is nonblank. All registered rooms are active under A-02; identity is assumed under A-01. |
| BR-06 — Lifecycle | Create makes DRAFT without allocation. Confirm permits only DRAFT → CONFIRMED. Cancel follows BR-03 and ends in CANCELLED, which is terminal. No edit, reopen, reschedule, automatic expiry or completion exists. |
| BR-07 — Observation and atomicity | Successful writes commit and remain readable in a new session. Business rejection leaves stored records unchanged. Availability never writes or reserves a hold; its result reflects committed data visible to the query and can become stale. |

BR-02 is the business invariant the application must preserve. Direct database
writes are outside the supported mutation boundary and can bypass the current
application enforcement. Verification and limitations must state this scope.

## OP-01 — Create Reservation

**Goal / user value:** record a student's intended room use without prematurely
allocating the room.

**Trigger:** student submits `user_id`, `room_id`, `start_time`, `end_time`,
`number_of_people`, and `purpose` to `POST /reservations`.

**Observable requirement(s):**

- **REQ-01:** given BR-01, BR-04 and BR-05, create exactly one durable DRAFT
  and return its generated id and state (201), without allocating the room.
- **REQ-06:** reject invalid input or missing references without creating a record.
  A valid repeated submission creates another draft; no deduplication is promised.

**Preconditions:** A-01; existing User and Room; input satisfies BR-01, BR-04,
and BR-05. Availability is not a precondition.

**Success postcondition:** one new record is readable with submitted values,
a generated id and DRAFT state; prior allocations are unchanged.

**State change:** no record → DRAFT (BR-06).

**Referenced business rule(s) / invariant(s):** BR-01, BR-02, BR-04–BR-07.

**Main success scenario:**

1. Student submits the reservation details.
2. System validates input, referenced User and Room, and capacity.
3. System persists a DRAFT without allocating the room.
4. System returns the reservation with its identifier and state.

**Alternative / failure outcomes:**

- Missing User or Room → 404; no record created.
- Invalid/missing timestamp, nonpositive interval or attendance, capacity
  exceeded, or blank purpose → 422; no record created.
- Overlapping draft or confirmed booking → Create still succeeds if its own
  input is valid; eligibility for allocation is decided by Confirm.
- A-01 does not provide an unauthorized-request rejection path.

**Verification examples:** B01–B02, B06–B08. Given A101 capacity 6, when a user
requests 4 people at 10:00–11:00 UTC, then 201/DRAFT and unchanged availability.
When end equals start, then 422 and no new row. Unknown Room → 404/no new row.

**Rationale / source:** assignment A.1/A.4 separates recording intent from
allocation; C01 supplies persistence and room-capacity rules. A-01 explicitly
adapts the reference authorization precondition.

## OP-02 — Check Availability

**Goal / user value:** identify rooms suitable for the student's requested interval
and group size.

**Trigger:** a search sends `start_time`, `end_time`, and `people` (default 1)
to `GET /rooms/available`.

**Observable requirement(s):** **REQ-02:** for valid input, return exactly the
registered rooms satisfying BR-02 and BR-04 (200, possibly an empty list),
without altering reservations or promising a hold.

**Preconditions:** BR-01 and positive integer `people`; A-02 defines room activity.

**Success postcondition:** response contains id, name, location and capacity for
each qualifying room. Stored records are unchanged.

**State change:** none (BR-07).

**Referenced business rule(s) / invariant(s):** BR-01, BR-02, BR-04, BR-05, BR-07.

**Main success scenario:**

1. User submits search interval and group size.
2. System validates the query.
3. System evaluates registered rooms using capacity and confirmed overlaps.
4. System returns qualifying rooms, including an empty list when none qualify.

**Alternative / failure outcomes:** invalid interval/timestamps or nonpositive
people → 422/no writes. No matching rooms → 200/empty list, not an error.
DRAFT and CANCELLED do not exclude a room. A later concurrent Confirm may
change availability; the returned list is not a guarantee.

**Verification examples:** B03–B06, B17. Given a CONFIRMED interval
[10:00,11:00), searches [09:00,10:00) and [11:00,12:00) include the room;
[10:30,11:30) excludes it. Equal endpoints → 422. Seven people with only
capacity-6 and capacity-2 rooms → 200/empty list.

**Rationale / source:** assignment A.5 specifies half-open interval semantics;
C01 adds capacity filtering. This API expresses availability as a list of
qualifying rooms rather than an AVAILABLE/UNAVAILABLE label for one room.

## OP-03 — Confirm Reservation

**Goal / user value:** turn a recorded intention into exclusive room allocation.

**Trigger:** administrator submits a reservation id to
`POST /reservations/{id}/confirm`. This actor mapping reflects the demo UI,
not enforced role authorization.

**Observable requirement(s):**

- **REQ-03:** an eligible DRAFT becomes durable CONFIRMED (200), blocking its
  room for its interval; an ineligible request is rejected without allocation.
- **REQ-04:** concurrent conflicting confirmation attempts leave at most one
  reservation CONFIRMED. For two otherwise eligible drafts and successful
  database service, one succeeds and the other conflicts.

**Preconditions:** existing DRAFT, existing active Room under A-02, capacity
satisfies BR-04, and no conflict under BR-02.

**Success postcondition:** confirmed record is readable and its interval is
unavailable for that room. BR-02 remains true.

**State change:** DRAFT → CONFIRMED (BR-06).

**Referenced business rule(s) / invariant(s):** BR-01–BR-07.

**Main success scenario:**

1. Administrator requests confirmation of a draft.
2. System evaluates the current state, room capacity and confirmed conflicts
   together with any competing state changes.
3. System commits confirmation while preserving BR-02.
4. System returns the updated reservation.

**Alternative / failure outcomes:** missing reservation → 404; CONFIRMED or
CANCELLED source state → 409; overlapping confirmed interval → 409; capacity
no longer sufficient → 422. Rejection preserves the pre-operation record.
For an overlap/capacity rejection, the record remains DRAFT. Inactive-room
handling is outside the explicitly restricted A-02 model. Cancel race follows
BR-03; a stale request cannot resurrect CANCELLED.

**Verification examples:** B08–B12, B16. A conflict-free draft → 200/CONFIRMED;
an overlapping draft → 409/still DRAFT. Synchronize two conflicting Confirm
requests using independent DB sessions → statuses 200 and 409, with only one
persisted CONFIRMED. An adjacent interval can also be confirmed.

**Rationale / source:** assignment A.6 requires allocation and concurrent
exclusivity. Confirm is not Approve; no discretionary approval workflow exists.
A-02 narrows the active-resource model explicitly.

## OP-04 — Cancel Reservation

**Goal / user value:** withdraw a reservation and release any room allocation
while retaining the record.

**Trigger:** student or administrator submits a reservation id to
`POST /reservations/{id}/cancel`.

**Observable requirement(s):** **REQ-05:** cancel a reservation allowed by
BR-03 (200), preserve its details and release its allocation; reject disallowed
states or missing records without modifying them.

**Preconditions:** existing DRAFT or CONFIRMED. No time precondition (BR-03).

**Success postcondition:** same id, owner, room, interval, attendance and purpose
remain readable with CANCELLED state; this record no longer blocks availability.
Other confirmed reservations can still block the room.

**State change:** DRAFT or CONFIRMED → CANCELLED (BR-06).

**Referenced business rule(s) / invariant(s):** BR-02, BR-03, BR-05–BR-07.

**Main success scenario:**

1. User requests cancellation.
2. System checks the current record and cancellation eligibility.
3. System commits CANCELLED and removes the reservation's allocation effect.
4. System returns the retained record with its updated state.

**Alternative / failure outcomes:** missing reservation → 404; already CANCELLED
→ 409, unchanged. BR-03 defines both valid serial outcomes for a Cancel/Confirm
race. No physical deletion or notification delivery is part of cancellation.

**Verification examples:** B13–B16, B18. Cancel CONFIRMED → 200/CANCELLED,
unchanged details and a subsequent eligible draft can confirm. Repeat Cancel
→ 409, same record. Cancel DRAFT also succeeds. An interval in the past does
not prevent cancellation under the selected policy.

**Rationale / source:** assignment A.7 explicitly leaves the policy to the team.
This specification retains the existing application's unrestricted cancellation
policy, avoiding an invented deadline or clock dependency. Team sign-off on
BR-03 remains part of acceptance, not an unspecified runtime rule.

## API mapping and persistence

| Core operation | Canonical endpoint |
| --- | --- |
| Create Reservation | `POST /reservations` |
| Check Availability | `GET /rooms/available?start_time=...&end_time=...&people=...` |
| Confirm Reservation | `POST /reservations/{id}/confirm` |
| Cancel Reservation | `POST /reservations/{id}/cancel` |

Reservation responses include all stored reservation fields and the derived
`room_name`. Supporting reads are `GET /reservations`, optional `user_id`
filtering, and `GET /reservations/{id}`; these retain visibility of cancelled
records. User and room list/create endpoints provide setup data. The existing
PATCH cancellation alias does not introduce another core operation.

Successful writes must survive a fresh database session and application
restart. Failed transactions roll back; business rejections are not HTTP
200 successes. Transport or database failures are not successful operations;
if a response is lost after commit, the client may need to read current
state before retrying. Automatic retry/deduplication is not specified.

The current implementation uses PostgreSQL Room row locks for Confirm and
Cancel under READ COMMITTED isolation. Direct database writes bypass the
application overlap check; no exclusion constraint is currently provided.

## Acceptance scenarios

Requirements are falsifiable claims. The following table states their scope,
what would refute them, and the evidence needed to demonstrate satisfaction.
Scenario identifiers refer to the concrete checks immediately below.

| Requirement | Conditions of application | What would falsify it | Demonstration required |
| --- | --- | --- | --- |
| R01 — Create persists without allocation | Valid input, existing User and Room, attendance within capacity | No durable record, initial state other than DRAFT, or a newly created draft blocks availability | B01–B02: capture request/response, reload in a fresh session, compare availability before/after |
| R02 — Availability reflects capacity and confirmed overlaps | Valid query evaluated against committed records visible to that query | A qualifying room is omitted or an undersized/blocked room is returned; query changes records | B03–B05, B17: known fixtures, expected vs actual room ids, unchanged stored state |
| R03 — Confirm allocates only eligible drafts | Existing DRAFT with adequate capacity and no confirmed overlap | Eligible confirmation does not persist CONFIRMED, or conflicting/ineligible confirmation allocates | B08–B12: responses plus independently reloaded states and availability |
| R04 — Cancel retains the record and removes its allocation | Existing DRAFT or CONFIRMED | Record disappears, original details change, or its cancelled interval still blocks another eligible booking | B13–B14, B18: before/after field comparison, fresh read, availability and subsequent confirmation |
| R05 — Invalid requests and transitions leave state unchanged | Invalid data, missing references/record, or disallowed lifecycle transition | Successful response to rejection case, partial write, or changed state | B06–B08, B12, B15: error status and independent before/after database comparison |
| R06 — Concurrent operations preserve lifecycle and exclusive allocation | Confirm/Cancel requests through the API for the same room using supported transaction configuration | Overlapping confirmed records or a cancelled record becomes confirmed through a stale request | B11, B16: synchronized concurrent requests in separate sessions, outcomes and final persisted records |

For each executed check, record the requirement/scenario id, code revision,
environment, fixture and inputs, command or repeatable steps, expected result,
actual result, and pass/fail with an evidence location. A failing observation
refutes the corresponding claim within its stated conditions. Passing examples
demonstrate those cases; a concurrency claim also needs a transaction rationale
and controlled concurrent execution, not just sequential happy-path requests.

Evidence status: C01 supports its original create-and-reload claim only.
New C02 executions and scenario mappings are recorded in
[baseline-v0.1-evidence.md](baseline-v0.1-evidence.md). The following table
remains the acceptance catalogue; consult the evidence for actual coverage.

| ID | Given / when | Required outcome |
| --- | --- | --- |
| B01 | Create a valid reservation | 201, generated id, DRAFT; fresh session reads the same data; availability unchanged |
| B02 | Create overlapping drafts, including over a confirmed interval | Drafts persist without allocating the room |
| B03 | Query an interval blocked only by DRAFT or CANCELLED | Room remains available if capacity fits |
| B04 | Query across an overlapping CONFIRMED reservation | Room is absent; another room is unaffected |
| B05 | Query or confirm an interval beginning at the previous confirmed end | Adjacency is allowed |
| B06 | Use invalid/missing timestamps, end at/before start, or nonpositive attendance | 422; no writes |
| B07 | Create with nonexistent User or Room | 404; no new record |
| B08 | Create above capacity, or confirm a draft after capacity falls below its attendance | 422; no allocation |
| B09 | Confirm a valid non-conflicting DRAFT | 200, CONFIRMED; room blocked for that interval |
| B10 | Confirm an overlapping draft after another confirmation | 409; losing record remains DRAFT |
| B11 | Concurrently confirm overlapping drafts for one room | Exactly one succeeds when both are otherwise valid; at most one allocation |
| B12 | Confirm a CONFIRMED or CANCELLED record | 409; record unchanged |
| B13 | Cancel a DRAFT | 200, CANCELLED; original fields retained |
| B14 | Cancel a CONFIRMED reservation, then query and confirm a waiting draft | Allocation released; query and confirmation reflect remaining constraints |
| B15 | Cancel CANCELLED, or confirm/cancel a missing record | 409 for repeated cancel; 404 for missing record |
| B16 | Confirm and cancel the same DRAFT concurrently | Either confirm then cancel both succeed, or cancel succeeds and confirm conflicts; final state CANCELLED |
| B17 | Query with more people than any room supports | 200 with empty list; no writes |
| B18 | Read a cancelled reservation in a fresh session | Same id and details, CANCELLED; no physical deletion |

The C02 suite is separate from the unchanged C01 experiment. The evidence
report distinguishes executed cases from untested variants and limitations.

## Views, review, and acceptance

See [behavior views](baseline-v0.1-diagrams.md) for the actor-goal view,
Reservation statechart, and all four activity flows. See the
[acceptance gate and consistency review](baseline-v0.1-review.md) for the
per-requirement review and team acceptance record.

## Deferred changes

Approval workflows, authentication/authorization, notification delivery,
payments, waiting lists, temporary holds, booking deadlines, opening hours,
future-only timestamps, duration limits, recurrence, and deployment recovery
are outside v0.1. No unstated policy of these kinds should reject a baseline
operation. A later change introducing approval must explicitly define its
actors, decisions, states, and effect on allocation rather than renaming Confirm.
