# Evidence and Evolution

Owns recorded verification, acceptance reviews, changes, limitations and version provenance. Results below retain their original dates and scope; reorganizing these records does not constitute a new test execution.

## Contents

- [C05 verification](#c05-verification)
- [Acceptance confirmation and C05 handoff](#acceptance-and-c05-handoff)
- [milestone-evidence: C01 Engineering Spike](#milestone-evidence)
- [c02-v01-review: Baseline v0.1 — acceptance gate and consistency review](#c02-v01-review)
- [c02-v01-evidence: Baseline v0.1 — C02 execution evidence](#c02-v01-evidence)
- [c02-v02-evidence: Baseline v0.2 — evidence](#c02-v02-evidence)

<a id="milestone-evidence"></a>

<a id="c01-engineering-spike"></a>
<a id="milestone-evidence-c01-engineering-spike"></a>

## C01 Engineering Spike

<a id="selected-spike"></a>
<a id="milestone-evidence-selected-spike"></a>

### Selected spike

**A — Persistence**

<a id="question--unknown"></a>
<a id="milestone-evidence-question--unknown"></a>

### Question / unknown

Can the application persist a DRAFT Reservation in PostgreSQL and
reload its data, including the correct User and Room references,
in a new SQLAlchemy session?

<a id="experiment"></a>
<a id="milestone-evidence-experiment"></a>

### Experiment

The spike uses PostgreSQL, SQLAlchemy 2, and psycopg 3.

Implementation evidence:

- `src/database.py`: database engine and session configuration.
- `src/models.py`: User, Room, and Reservation mappings.
- `src/main.py`: reservation creation and commit.
- `tests/test_persistence.py`: automated persistence verification.

The test:

1. Creates an isolated PostgreSQL schema and the required tables.
2. Creates and commits a User and a Room.
3. Sends a valid request to `POST /reservations`.
4. Checks HTTP 201, a generated identifier, and DRAFT state.
5. Opens a new SQLAlchemy session and loads the Reservation by ID.
6. Checks its stored fields and related User and Room.
7. Removes the test schema and disposes the engine.

The verified path is:

```text
POST /reservations
→ validate input
→ persist Reservation
→ commit to PostgreSQL
→ return generated ID
→ reload in a new ORM session
→ verify fields and relationships
```

<a id="recorded-execution"></a>
<a id="milestone-evidence-recorded-execution"></a>

### Recorded execution

Execution date: 2026-09-16.

The original experiment records this environment:

| Component | Version / value |
| --- | --- |
| Python | 3.13.1 |
| PostgreSQL | 17.2 |
| SQLAlchemy | 2.0.54 |
| psycopg | 3.3.5 |
| pytest | 9.1.1 |
| Test database | study_room_c01_test |

Command:

```bash
python -m pytest tests/test_persistence.py -v
```

Recorded result:

```text
tests/test_persistence.py::test_reservation_persists_in_postgresql PASSED
1 passed in 0.28s
```

This is the recorded C01 result, not a new execution performed during
this documentation revision.

<a id="result-and-interpretation"></a>
<a id="milestone-evidence-result-and-interpretation"></a>

### Result and interpretation

The valid request returned HTTP 201 with a generated Reservation ID
and DRAFT state.

A new SQLAlchemy session reloaded the Reservation and verified:

- Reservation ID.
- User and Room IDs.
- Start and end times.
- Number of people.
- Purpose.
- DRAFT state.
- Related User and Room data.

This supports the persistence path through the API and PostgreSQL,
rather than relying on the original ORM session's cached object.

The test uses a new ORM session on the same database connection.
It does not demonstrate recovery after an application or database restart.

<a id="decision"></a>
<a id="milestone-evidence-decision"></a>

### Decision

Retain PostgreSQL, SQLAlchemy 2, and psycopg 3 for the project's
persistence path.

Reuse the shared database configuration and ORM models when extending
the application. The spike provides the persistence foundation for
the CP1 walking skeleton; it does not establish completion of CP1.

<a id="limitations"></a>
<a id="milestone-evidence-limitations"></a>

### Limitations

The spike covers one valid Reservation creation and reload.

It does not independently verify:

- Rejection of invalid requests.
- Capacity-rule enforcement.
- Prevention of overlapping confirmed reservations.
- Concurrent state changes.
- Authentication or authorization.
- Notification delivery.
- Schema migration.
- Production deployment, backup, or restart recovery.

Later tests and features provide separate evidence and do not expand
what this C01 experiment originally demonstrated.

<a id="change-and-review-cycle"></a>
<a id="milestone-evidence-change-and-review-cycle"></a>

## Change and Review Cycle

| Item | Record |
| --- | --- |
| Task | C01 engineering spike — PostgreSQL persistence |
| Change author | DAT |
| Reviewer named in the project record | Izaz |
| Pull request | [PR #1 — C01 PostgreSQL persistence spike](https://github.com/benj1011/study-room-reservation/pull/1) |
| Separate issue | No issue URL is recorded in this document. |
| Integration | PR #1 was merged on 2026-09-17. |
| Merge commit | `7bd0b30e9d1c8ecdf6fe5ae618fb9fbd2480c6e8` |

<a id="review-evidence"></a>
<a id="milestone-evidence-review-evidence"></a>

### Review evidence

The Git history confirms the merge of PR #1 and lists
Syed Izaz Huassain as the merge commit author.

Status: accepted, as confirmed by the project owner in the conversation on
2026-10-13. This records the acceptance confirmation; it does not assert a
GitHub approval event or its historical timestamp. The existing reviewer and
merge evidence above are retained. No separate issue is required by this record.

<a id="evolution-after-c01"></a>
<a id="milestone-evidence-evolution-after-c01"></a>

## Evolution After C01

Subsequent work extended the application with room availability,
reservation confirmation and cancellation, browser pages, and
additional validation and concurrency checks.

These changes build on the persistence foundation established by C01.
Their behavior and verification belong to the later baseline documents.

<a id="c03--architecture-evidence"></a>
<a id="milestone-evidence-c03--architecture-evidence"></a>

### C03 — Architecture Evidence

**Baseline:** v0.2

**Part A:** Existing implementation map and Confirm trace in
[architecture-and-decisions.md](architecture-and-decisions.md#c03a-c03-architecture-baseline).

**Drivers:** Exclusive allocation under contention; assigned-approver
authorization; deadline correctness; notification failure semantics.

**Decision question:** Where should the authoritative Confirm decision be
enforced so BR-02 remains true for competing reservation requests?

**Alternatives:** Per-Room application transaction/row lock (selected) versus
a PostgreSQL exclusion constraint. See the comparison and concurrent scenario
walkthrough in [c03-architecture.md](architecture-and-decisions.md#c03b).

**ADR:** ADR-01 selects the existing lock-refresh-commit protocol for supported
API writers. Direct database writers remain outside that guarantee.

**Views:** Domain class model, system context, logical architecture, state
transition ownership, runtime mapping, concurrent Confirm sequence, and
focused design class diagram are in [c03-architecture.md](architecture-and-decisions.md#c03b).

**Cross-view issues found/resolved:** The existing code co-locates HTTP
handlers and reservation operations in `src/main.py`; the design labels them
as separate logical responsibilities within the same module and process. The database row-lock guarantee is explicitly limited to supported
API writers.

**AS-IS → TO-BE delta:** Lifecycle ownership, shared transition locking,
PostgreSQL persistence, and derived expiry are KEEP; lifecycle assignment
ownership is VERIFY. No application behavior change was required.

**Implementation changes:** Added
`tests/test_architecture.py`, an AST-based ownership check; linked the C03
design from README. No application code was refactored.

**Behavior verification:** The recorded v0.2 PostgreSQL suite reports 55
passed and 2 warnings on 2026-09-28. This historical suite was not rerun for
the C03 documentation/test change. The architecture check result is recorded
in [c03-architecture.md](architecture-and-decisions.md#c03b-l2-architecture-conformance).

**Architecture conformance rule:** Only Confirm and Cancel may assign the
lifecycle state of an existing reservation; creation initializes DRAFT.
**Check:** `tests/test_architecture.py`.
**Result:** 1 passed.

**Remaining uncertainty / risk:** `X-User-Id` is not authenticated;
multi-instance clock policy is open; direct database writers can bypass the
row lock; notification requirements and production deployment policy are
unresolved.

**Commit/tag:** `c265c90ad4dbd34635c5bef6d7fc39c561013a57` — C03 architecture
design, evidence, and conformance test.


---

<a id="c02-v01-review"></a>

<a id="c02-v01-review-baseline-v01--acceptance-gate-and-consistency-review"></a>

## Baseline v0.1 — acceptance gate and consistency review

Review scope: assignment Part A, adapted explicitly by A-01 (trusted demo
identity) and A-02 (all registered rooms active). The tables below record the
engineering self-review; team acceptance is recorded at the end.

<a id="c02-v01-review-requirement-acceptance-gate"></a>

### Requirement acceptance gate

Each cell records the result of applying the named question to that requirement.
The shared BR definitions and operation slices are authoritative; evidence is
linked in the [execution report](evidence-and-evolution.md#c02-v01-evidence).

| Gate question | REQ-01 Create | REQ-02 Availability | REQ-03 Confirm |
| --- | --- | --- | --- |
| Meaning | One DRAFT, existing references; no allocation | Qualifying room list for valid interval and group size | DRAFT becomes CONFIRMED only if eligible |
| Need / rationale | A.4: record intent | A.5: discover usable rooms | A.6: allocate exclusive room |
| Observable | 201, id, DRAFT, fresh read | 200 and exact room ids; no writes | 200/CONFIRMED and room excluded |
| Feasible | Existing Create path persists DRAFT | Existing query applies BR-01/02/04 | Existing state transition enforces guards |
| Verifiable | B01–B02; new row with unchanged availability | B03–B05/B17; expected room membership | B08–B12; persisted state and status |
| State / time | BR-01 validity; BR-06 initial state | Half-open boundaries; only CONFIRMED blocks | Current source state and overlapping intervals |
| Concurrency | Drafts may coexist; no resource promise | Snapshot may become stale; no hold | REQ-04 and BR-03 govern competing changes |
| Consistency | Matches OP-01, initial statechart edge and activity | Same blocking rule used by OP-03 | Matches OP-03 and DRAFT → CONFIRMED guard |
| Unknown? | A-01 explicit; auth not claimed | A-02 explicit; inactive rooms not modelled | A-02 explicit; no approval step |

| Gate question | REQ-04 Concurrent Confirm | REQ-05 Cancel | REQ-06 Create rejection |
| --- | --- | --- | --- |
| Meaning | At most one conflicting CONFIRMED in committed API state | BR-03 defines states, repeat and time policy | Invalid data/missing references cause no create |
| Need / rationale | A.6: preserve exclusive allocation under contention | A.7: withdraw and release allocation | A.4: prevent invalid persisted requests |
| Observable | Responses and final states in separate sessions | 200/CANCELLED, retained fields, availability | 404/422 and unchanged rows |
| Feasible | Room serialization already exists | Current Cancel shares serialization with Confirm | Existing validation and foreign-reference checks |
| Verifiable | B11: synchronized independent requests, persisted count | B13–B16/B18, plus past-interval case | B06–B08: rejection and no writes |
| State / time | Current committed conflicts matter, not old search results | Before/at/after start allowed; repeat is 409 | Equal/reversed interval rejected |
| Concurrency | Core requirement; no double allocation | BR-03 allows only valid serial outcomes with Confirm | Rejection creates no allocation or record |
| Consistency | Preserves BR-02; OP-03 evaluation is indivisible | Same guards in OP-04, statechart and activity | OP-01 failure branches match examples |
| Unknown? | All-schedule/load proof not claimed; scope stated | Policy documented in BR-03 | Missing reference is not an auth failure |

R01–R06 in the specification's falsification table are verification claims:
R01 maps to REQ-01; R02 to REQ-02; R03 to REQ-03; R04 to REQ-05;
R05 to REQ-06 plus failure branches of all slices; R06 to REQ-04 and BR-03.
They are not additional operations or alternative definitions.

<a id="c02-v01-review-cross-slice-and-cross-view-findings"></a>

### Cross-slice and cross-view findings

| Check | Finding / resolution |
| --- | --- |
| Create vs Confirm allocation | Create allows overlapping drafts; only successful Confirm allocates. Same in OP-01/03 and statechart. |
| Availability vs Confirm | Both use BR-01/02 and BR-04. CANCELLED and DRAFT do not block either decision. |
| Cancel vs lifecycle | BR-03 permits DRAFT/CONFIRMED, retains record, rejects repeat. No outgoing CANCELLED edge and no time guard. |
| Interval semantics | All slices/examples use half-open intervals, including adjacent endpoints. |
| Actor goals vs slices | Student: Create/Check/Cancel; administrator: Confirm/Cancel. Exactly four system goals; actor associations do not claim access enforcement. |
| External actor | Notification delivery is absent; no fictitious runtime actor appears in the goal view. |
| Concurrency | OP-03/04 require serially valid outcomes; diagrams refer to these requirements without prescribing locks. |
| Design leakage | Observable requirements do not require FastAPI, SQLAlchemy or row locks. Current implementation mapping/rationale is explicitly separated. |
| Reference authorization | A-01 limits this baseline to trusted demo identity; unauthorized access is outside the test scope. |
| Reference active resource | A-02 makes every registered room active. Inactive rejection is not implemented or claimed. |
| Cancellation example | The assignment's before-start example is not mandatory. Existing unrestricted policy is selected explicitly, with no clock ambiguity. |
| Evidence vs claims | Tests run through the API with real PostgreSQL; C01 history remains unchanged. Untested scope is listed in the evidence report. |

The earlier documentation used “approve” as a synonym for Confirm; those
references were corrected. Existing implementation already fits the selected
baseline, so no application regeneration was necessary. The new C02 test suite
provides executable examples; it does not replace the C01 spike.

<a id="c02-v01-review-team-acceptance-record"></a>

### Team acceptance record

**Specification Baseline v0.1 — Accepted by Team.**

The review was prepared on 2026-09-28 and covers A-01, A-02 and BR-03.
Acceptance was reconfirmed by the project owner in the conversation on
2026-10-13. This is the confirmation date, not a reconstructed historical
review date. Individual reviewer names were not supplied and are not inferred.

C03 adds the architecture work. The CP1 freeze follows C03, with review in C04.


---

<a id="c02-v01-evidence"></a>

<a id="c02-v01-evidence-baseline-v01--c02-execution-evidence"></a>

## Baseline v0.1 — C02 execution evidence

<a id="c02-v01-evidence-execution-identity"></a>

### Execution identity

- Date: 2026-09-28 (Europe/Prague).
- Base revision: `16f1a47d6240ca53502308cc3bd6c206d1d0492a` plus the uncommitted
  C02 documentation and `tests/test_baseline.py` added in this work.
- Application source was reused unchanged. Exact tested source and test hashes:
  [SHA-256 manifest](evidence/c02-code-sha256.json).
- Runtime: macOS, Python 3.13.1, PostgreSQL 17.2, FastAPI 0.141.1,
  SQLAlchemy 2.0.54, psycopg 3.3.5, Pydantic 2.13.5, pytest 9.1.1,
  httpx 0.28.1.
- PostgreSQL isolation verified: `read committed`.
- Database: separate temporary local cluster, database `postgres`, Unix socket
  `/private/tmp/study-room-c02-socket`, port 55432. No application database used.
- Each test creates a unique `c02_test_<uuid>` schema and removes only that schema.
  After the suite, the count of remaining C02 schemas was verified as zero.

The first sandboxed attempt could not connect to the local socket (“Operation
not permitted”). It failed during fixture setup, before business scenarios ran.
The authorized local execution below resolved that environment restriction;
it was not an application defect. The C01 experiment was not rerun or rewritten.

<a id="c02-v01-evidence-command-and-actual-result"></a>

### Command and actual result

With the temporary cluster running, the actual command was:

```bash
DATABASE_URL='postgresql+psycopg://dat.pham@/postgres?host=/private/tmp/study-room-c02-socket&port=55432' \
  .venv/bin/python -m pytest tests/test_baseline.py -v --tb=short \
  > docs/evidence/c02-baseline-pytest.txt 2>&1
```

Actual result:

```text
29 passed, 2 warnings in 1.38s
```

The two warnings are dependency deprecations from Starlette's TestClient/httpx
and AnyIO BlockingPortal. No test failures occurred in the final execution.
The [raw pytest output](evidence/c02-baseline-pytest.txt) preserves test ids and
results. Earlier, 28 cases passed before the additional past-interval policy
case was added; the final log is from the complete 29-case suite.

To reproduce, configure `DATABASE_URL` (and `PGPASSWORD` when needed) for a
PostgreSQL test database with schema-creation permission using the existing
README instructions, then run:

```bash
python -m pytest tests/test_baseline.py -v --tb=short
```

The temporary cluster used for this run is stopped after verification. Its
socket is not an always-running service or a prerequisite for future runs.
Use your own configured test database; the suite creates no permanent tables.

<a id="c02-v01-evidence-fixture-and-observations"></a>

### Fixture and observations

Each case starts with one user, A101 (capacity 6), B201 (capacity 2), and no
reservations. Default input is 4 people, purpose `C02 acceptance example`,
2030-10-01 10:00–11:00 UTC. Individual tests override these inputs explicitly.
Responses are checked through the real FastAPI routes using TestClient and
application lifespan; ORM persistence is real PostgreSQL, not mocked or SQLite.
Independent sessions reload records to verify final state and unchanged data.

| Slice | Executed success example | Executed negative / boundary example | Result |
| --- | --- | --- | --- |
| OP-01 / REQ-01, REQ-06 | Valid create → 201/DRAFT, fresh-session read, unchanged availability; overlapping drafts allowed | Equal/reversed endpoints, no offset, null timestamp, zero people, excess capacity, blank purpose → 422/no write; unknown User/Room → 404/no write | PASS |
| OP-02 / REQ-02 | Before and after confirmed interval return A101; DRAFT/CANCELLED do not block | Overlap excludes A101; unrelated B201 remains available for one person; seven people → empty; invalid interval/zero people → 422/no writes | PASS |
| OP-03 / REQ-03, REQ-04 | Valid draft → 200/CONFIRMED; adjacent interval confirms | Overlap → 409/DRAFT; changed capacity → 422/DRAFT; invalid source → 409; missing id → 404; concurrent conflicts → one 200 and one 409 | PASS |
| OP-04 / REQ-05 | Cancel both DRAFT and CONFIRMED → 200/CANCELLED with unchanged details; room released and replacement confirms | Repeated Cancel → 409/unchanged; missing id → 404; past interval allowed; Confirm/Cancel race ends CANCELLED | PASS |

<a id="c02-v01-evidence-scenario-to-test-traceability"></a>

### Scenario-to-test traceability

Test names below refer to [tests/test_baseline.py](../tests/test_baseline.py).
Parameterized cases appear individually in the raw log.

| Scenarios | Test function(s) |
| --- | --- |
| B01–B02 | `test_create_durable_draft_without_allocation`; `test_confirm_success_conflict_and_adjacent_interval` |
| B03–B05, B17 | `test_availability_boundaries_blocking_and_capacity`; `test_confirm_success_conflict_and_adjacent_interval` |
| B06–B08 | `test_create_rejection_has_no_write`; `test_availability_invalid_query`; `test_confirm_rechecks_capacity` |
| B09–B10 | `test_confirm_success_conflict_and_adjacent_interval` |
| B11 | `test_concurrent_confirms_allocate_at_most_once` (3 executions) |
| B12 | `test_confirm_invalid_source_state` (CONFIRMED and CANCELLED) |
| B13–B14, B18 | `test_cancel_retains_details_releases_allocation_and_rejects_repeat` (DRAFT and CONFIRMED) |
| B15 | `test_missing_reservation`; repeated-cancel checks in the cancellation test |
| B16 | `test_concurrent_confirm_cancel_never_resurrects` (3 executions) |
| BR-03 no cutoff | `test_cancel_past_interval_has_no_deadline` |

B06 is covered by representative invalid/null/unzoned timestamp examples,
not every possible malformed or omitted field. The table maps coverage,
not an assertion that every input combination was tested.

<a id="c02-v01-evidence-concurrent-behavior-and-why-the-result-is-credible"></a>

### Concurrent behavior and why the result is credible

The concurrent tests use two worker requests and a barrier immediately before
room locking. They assert distinct PostgreSQL backend process ids, proving
separate database sessions rather than two calls sharing one transaction.
Each worker then executes the existing lock/check/update/commit code. Tests
check both response statuses and the final records from a fresh session.

The implementation rationale is that Confirm and Cancel acquire the same Room
row lock and refresh the Reservation after acquiring it. Under READ COMMITTED,
a waiting operation subsequently sees the prior committed state. The overlap
check runs while that lock is held. This explains why competing Confirm requests
cannot both allocate and why Cancel cannot be undone by a stale Confirm through
the supported API. This is a current implementation explanation, not a required
technology choice in REQ-04.

The examples demonstrate concurrent submissions; they do not exhaust every
scheduler interleaving, guarantee both possible race orderings were observed,
or establish a high-load performance target. Direct DB writes can bypass
application rules. No database exclusion constraint is claimed.

<a id="c02-v01-evidence-satisfaction-and-remaining-limits"></a>

### Satisfaction and remaining limits

All four slices have executed success and relevant rejection/boundary examples.
No application/specification mismatch was found in those executions, so the
existing runnable API was retained. The C02 additions are specification,
review, diagrams and separate executable evidence, not a replacement C01 spike.

A-01 and A-02 define the baseline scope: unauthorized
requests and inactive resources are not supported test conditions. No access
control or inactive-room rejection is implemented. Notification, browser UI, process-restart recovery,
full production deployment and load performance were not tested by this suite.
Fresh-session persistence is demonstrated; process-restart durability is not
separately exercised. HTTP is exercised in-process; no network/proxy deployment
claim follows from TestClient.

The selected scope has been implemented and tested. Team acceptance is recorded
in [the review document](evidence-and-evolution.md#c02-v01-review-team-acceptance-record).


---

<a id="c02-v02-evidence"></a>

<a id="c02-v02-evidence-baseline-v02--evidence"></a>

## Baseline v0.2 — evidence

<a id="c02-v02-evidence-accepted-baseline"></a>

### Accepted baseline

The approval-workflow baseline was accepted by the team on 2026-09-28.

- The baseline includes Create Reservation, Check Availability, Confirm Reservation, Cancel Reservation, and Approve Reservation. Approval is separate from resource allocation.

<a id="c02-v02-evidence-core-operations-demonstrated"></a>

### Core operations demonstrated

- Create Reservation persists a DRAFT without allocating a room. Reservations for approval-required rooms start with PENDING approval.
- Check Availability considers room capacity and overlapping CONFIRMED reservations.
- Approve Reservation allows the assigned approver to record APPROVED or REJECTED without allocating the room.
- Confirm Reservation allocates the room only when approval, capacity, and overlap conditions are satisfied.
- Cancel Reservation retains the record and releases any allocation.

<a id="c02-v02-evidence-executed-verification-examples"></a>

### Executed verification examples

Run recorded on 2026-09-28 at 21:46: **55 passed, 2 warnings in 4.72s**.

Executed examples covered valid and invalid creation, interval boundaries, capacity, confirmation conflicts, cancellation, assigned-approver checks, rejection, approval expiry, concurrent operations, and preservation of existing records during migration.

```bash
python -m pytest tests/test_baseline.py tests/test_approval.py -v --tb=short
```

The run included 29 baseline tests and 26 approval tests.

Tests used isolated database schemas. Deadline tests used a controlled clock.

<a id="c02-v02-evidence-mismatch-found-and-resolved"></a>

### Mismatch found and resolved
Impact analysis identified a gap between v0.1 and the changed requirements: confirmation had no approval guard, and the model had no approval policy, decision, or deadline.
This was resolved by adding room-level approval configuration, reservation approval metadata, an assigned-approver decision operation, and approval eligibility checks during confirmation.

No remaining mismatch was observed in the executed test cases.

<a id="c02-v02-evidence-change-impact-summary"></a>

### Change impact summary
Confirm requires valid approval in addition to the existing booking constraints. A new Approve Reservation operation records approval or rejection.
Availability continues to be blocked only by CONFIRMED reservations. Cancellation retains its existing lifecycle policy and supports drafts in every approval substate.

<a id="c02-v02-evidence-assumptions-and-open-questions"></a>

### Assumptions and open questions

Identity remains a trusted demo assertion through X-User-Id; production authentication is not implemented. All registered rooms are assumed active.

Approval expires at the earlier of 24 hours after creation and the reservation start. Rejected or expired requests require a new reservation.

<a id="c02-v02-evidence-architecture-drivers-carried-into-c03"></a>

### Architecture drivers carried into C03
- Trusted identity integration and per-resource authorization.
- Atomic approval, confirmation, and cancellation under concurrency.
- Authoritative time and consistent expiry evaluation.
- Notification and delivery requirements if introduced later.

<a id="c02-v02-evidence-application-version"></a>

### Application version

The original execution record does not include an application commit or tag.
This is a retained historical evidence limitation, not an unfilled field.
The C02 source/documentation milestone is commit
`809344c5d75145005b2774873a35e7bd9c12b218`; it is not asserted to be the exact
version used in the historical test run. C05 verification will record the
actual tested revision and any working-tree changes alongside its results.



## Documentation consolidation and milestone history

Recorded on 2026-10-13. The working tree was clean before consolidation.
The following existing commits preserve the milestone history; they are
traceability references, not newly asserted acceptance or test-run versions.
No Git tags existed at the time of this check. In particular, the v0.2 test
execution record still has no recorded application commit; a documentation
commit below does not fill that evidence gap.

| Milestone / record | Existing commit |
| --- | --- |
| C01 persistence spike | `5df13340825e554f4b184721c275f69f313470f6` |
| C01 follow-up | `16f1a47d6240ca53502308cc3bd6c206d1d0492a` |
| C02 v0.1/v0.2 records and approval workflow | `809344c5d75145005b2774873a35e7bd9c12b218` |
| C03a architecture baseline | `1696d847bad6ff3751bce7a1cdfbbdca78a00728` |
| C03a Confirm trace | `5a87f9d054a18ab6fd4b5a9b736fd6988bf25e3e` |
| C03b design, evidence and conformance test | `c265c90ad4dbd34635c5bef6d7fc39c561013a57` |
| C03b commit evidence | `595f3e8c00ff58f99fd0b57eb316a10f7a47b4b7` |
| Pre-consolidation documentation snapshot | `6686be32fa6485e07098304cdb8575947813c56f` |

To inspect an original file without changing the working tree, use
`git show <commit>:docs/<original-file-name>`. The pre-consolidation snapshot
contains all twelve original Markdown documents.

The consolidation places intent, specifications and behavior views in
`intent-and-change.md`; C03a/C03b architecture and historical C01 decisions in
`architecture-and-decisions.md`; and reviews and execution evidence here.
Original milestone content is retained, including historical overlap, so
that this structural edit does not silently alter design or acceptance claims.
Existing links were redirected to uniquely named section anchors. Raw files
in `docs/evidence/` and application/test sources are unchanged.

Validation: local Markdown file/section links, unique explicit anchors,
preservation of original non-heading content and fenced diagrams/code, and
`git diff --check`. Application tests were not rerun for this documentation-only
change. This reorganization is included in the C05 delivery tag recorded below.


<a id="acceptance-and-c05-handoff"></a>

## Acceptance confirmation and C05 handoff

On 2026-10-13, the project owner confirmed in the conversation that the
preceding work had been accepted and requested preparation for C05.
This confirmation updates acceptance status; it does not establish new test
results, individual reviewer identities, historical approval dates or a C04
review record.

| Milestone | Status for handoff | Evidence basis |
| --- | --- | --- |
| C01 | Accepted | Existing persistence and PR merge evidence; owner confirmation above |
| C02 v0.1 | Accepted | Existing team acceptance record; owner reconfirmation above |
| C02 v0.2 | Accepted | Existing 2026-09-28 acceptance and execution record; owner confirmation above |
| C03a | Accepted | Architecture baseline and Confirm trace commits; owner confirmation above |
| C03b | Accepted | ADR-01, design and conformance evidence; owner confirmation above |

**Next work:** [C05 preparation](architecture-and-decisions.md#c05-preparation).
The selected scope is Confirm Reservation (OP-03). Its DD-derived tests and
implementation comparison will be recorded here after design and execution.
This historical handoff preceded C05 work. See [C05 verification](#c05-verification) for subsequent design, tests and results.

Production identity, multi-instance clock behavior, direct database writers
and notification requirements remain explicit limits of the accepted scope.
They are not blank fields blocking the start of C05.

<a id="c05-verification"></a>

## C05 — DD-derived verification

Design source: [Confirm detailed design](architecture-and-decisions.md#c05-detailed-design).
Test cases below follow explicit contracts and decisions; existing cases are
reused where they already verify the same intent.

| DD element / decision | What must hold? | Test level | Executable test case |
| --- | --- | --- | --- |
| DD-08 domain query | Before deadline retain PENDING/APPROVED; at/after deadline derive EXPIRED; preserve fields and timezone-equivalent results | Unit | `test_detailed_design.py::test_effective_expiry_is_a_pure_boundary_query` (6 cases) |
| DD-08 lifecycle | Expiry cannot undo CONFIRMED/CANCELLED lifecycle | Unit | `test_detailed_design.py::test_expiry_does_not_rewrite_terminal_lifecycle` (2 cases) |
| DD-08 decision branches | NOT_REQUIRED and REJECTED remain unchanged after time passes | Unit | `test_detailed_design.py::test_non_expiring_decisions_are_preserved` (2 cases) |
| DD-03 clock ordering | Crossing deadline at lock acquisition prevents confirmation, preserves durable decision and attribution | Component + PostgreSQL integration | `test_approval.py::test_confirm_evaluates_deadline_after_room_lock` |
| DD-02 invalid lifecycle | Repeat Confirm and cancelled Confirm reject without writes | Component + PostgreSQL integration | `test_baseline.py::test_confirm_invalid_source_state` |
| DD-03 approval guard | PENDING/REJECTED fail; valid APPROVED permits allocation | Component + PostgreSQL integration | `test_approval.py::test_approval_is_permission_not_allocation`, `test_reject_cannot_confirm_but_can_cancel` |
| DD-03 deadline boundary | Approved DRAFT rejects at/after deadline; succeeds just before | Component + PostgreSQL integration | `test_approval.py::test_deadline_boundary_on_confirm_or_approve` |
| DD-04 capacity | Reduced capacity after Create is respected, rejection leaves stored state unchanged | Component + PostgreSQL integration | `test_baseline.py::test_confirm_rechecks_capacity` |
| DD-05 interval algorithm | Conflict rejects; adjacent booking confirms; rejection preserves state | Component + PostgreSQL integration | `test_baseline.py::test_confirm_success_conflict_and_adjacent_interval` |
| DD-01/05 concurrency | Two eligible overlapping drafts cannot both allocate | Integration, separate PostgreSQL sessions | `test_approval.py::test_concurrent_approved_confirms_still_exclusive`; `test_baseline.py::test_concurrent_confirms_allocate_at_most_once` |
| DD-01 collaboration | Confirm/Cancel cannot resurrect a cancelled record; approval races serialize | Integration, separate PostgreSQL sessions | `test_baseline.py::test_concurrent_confirm_cancel_never_resurrects`; `test_approval.py::test_approval_races` |
| DD-07 missing entity | Missing reservation returns 404 without a stored mutation | Component + PostgreSQL integration | `test_baseline.py::test_missing_reservation` |

**Level rationale — pure expiry query:** Unit level is sufficient because the
contract is a deterministic function of supplied time and entity data. An
unpersisted ORM object lets the test assert boundary values and absence of
mutation without confusing database behavior with the domain rule.

**Level rationale — concurrent allocation:** Integration with real PostgreSQL
is necessary because READ COMMITTED visibility, row locking and separate
transactions implement the exclusivity decision. The existing synchronization
helper verifies distinct backend process IDs. Mock sessions or SQLite cannot
establish this guarantee.

**Level rationale — post-lock clock:** The new component test executes the real
HTTP/ORM/Room lock path, advancing a controlled clock immediately after lock
acquisition. It proves that Confirm samples the decision time after this boundary
and that rejection preserves persisted fields. It does not simulate a timed lock
wait; independent concurrency tests establish the separate serialization property.

<a id="c05-consistency"></a>

### DD ↔ implementation comparison

| DD decision | Implemented? | Evidence | Action |
| --- | --- | --- | --- |
| DD-01 shared Room lock then refresh | YES | `src/main.py::lock_reservation_room`; concurrency cases above | Keep |
| DD-02 DRAFT-only transition | YES | `src/main.py::confirm_reservation`; invalid-state test | Keep |
| DD-03 clock after lock, approval guard | YES | `src/main.py::confirm_reservation`; new post-lock test and existing boundary tests | Keep; add targeted verification |
| DD-04 current capacity | YES | `src/main.py::confirm_reservation`; capacity recheck test | Keep |
| DD-05 half-open overlap against CONFIRMED | YES | Confirm SQL predicates; adjacent/conflict and concurrency tests | Keep |
| DD-06 commit without rewriting attribution | YES | Confirm assigns only lifecycle; `save`; approval-permission test | Keep |
| DD-07 rollback/error ownership | YES | `get_db` rollback, `save` IntegrityError mapping; rejected-operation tests | Keep; unexpected database failures are not fault-injected |
| DD-08 pure derived expiry | YES | `src/models.py::effective_approval_status`; new unit cases | Keep; add isolated domain verification |

No application-code mismatch was found against this selected DD. The change
adds verification and explicit contracts; application source remains unchanged.
The C03a future PostgreSQL clock policy is not implemented: C05 intentionally
uses the accepted single-process clock scope and retains the multi-host risk.

### Remaining risk and limits

- Direct database writers bypass the shared Room protocol; no exclusion constraint.
- Trusted demo identity and absent Confirm authentication remain unchanged.
- Clock skew across processes, database outages, lock timeouts and post-commit
  response failure are not proven by the successful-path tests.
- The post-lock clock test controls time; the concurrency cases cover selected
  schedules, not all possible interleavings or load behavior.
- Existing IntegrityError mapping is reviewed in code; commit-failure injection
  and production recovery remain outside this verification run.

### C05 execution record

- Date: 2026-10-13 (Europe/Prague).
- Tested base: `6686be32fa6485e07098304cdb8575947813c56f`, plus the C05 test
  additions and documentation consolidation in the working tree. Application
  files in `src/` were unchanged.
- Source/test identity: [SHA-256 manifest](evidence/c05-code-sha256.json).
- Command: `.venv/bin/python -m pytest tests -v --tb=short` with `DATABASE_URL`
  pointing to the temporary PostgreSQL cluster described below.
- Result: **68 passed, 2 warnings in 2.38s**. Complete output:
  [C05 pytest log](evidence/c05-pytest.txt).
- Python 3.13.1; PostgreSQL 17.2; pytest 9.1.1; SQLAlchemy 2.0.54;
  psycopg 3.3.5; FastAPI 0.141.1; Pydantic 2.13.5; httpx 0.28.1.
- Database: isolated temporary cluster `/tmp/study-room-c05-pg`, database
  `postgres`, Unix socket `/tmp/study-room-c05-socket`, port 55435, TCP disabled.
  Isolation verified as `read committed`. Tests use unique disposable schemas;
  post-run C01/C02 test-schema count was zero. Temporary server was stopped.
- The first sandboxed cluster initialization failed on shared-memory permission;
  the permitted retry and the full suite completed successfully.
- Two warnings concern deprecated Starlette/httpx TestClient and AnyIO portal
  APIs. They did not fail tests and remain dependency-maintenance work.
- Added coverage: 10 pure domain cases in `tests/test_detailed_design.py` and
  one post-lock deadline case in `tests/test_approval.py`. Existing persistence,
  approval, baseline and architecture tests were run together as regression checks.
- Documentation checks: local file/anchor targets and `git diff --check`.

**Commit/tag:** `c05-detailed-design` identifies the consolidated documentation,
C05 design, executable verification and evidence snapshot. Historical C01–C03b
commits remain in the milestone table; this tag does not relabel their test runs.

### C05 Definition of Done

- [x] Selected one architecture unit and traced its requirements/scenarios/rules.
- [x] Derived responsibilities and assigned ownership/data.
- [x] Specified meaningful interfaces and contracts.
- [x] Added focused structural UML and detailed sequence.
- [x] Specified significant operations, decision logic and failure behavior.
- [x] Derived at least five tests and justified at least two test levels.
- [x] Executed verification on real PostgreSQL and isolated domain objects.
- [x] Compared DD and code; recorded limitations and actions.
- [x] Recorded the delivery tag with the tested source/test manifest.
