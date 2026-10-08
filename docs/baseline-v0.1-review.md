# Baseline v0.1 — acceptance gate and consistency review

Review scope: assignment Part A, adapted explicitly by A-01 (trusted demo
identity) and A-02 (all registered rooms active). The tables below record the
engineering self-review; team acceptance is recorded at the end.

## Requirement acceptance gate

Each cell records the result of applying the named question to that requirement.
The shared BR definitions and operation slices are authoritative; evidence is
linked in the [execution report](baseline-v0.1-evidence.md).

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

## Cross-slice and cross-view findings

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

## Team acceptance record

**Specification Baseline v0.1 — Accepted by Team.**

The review was prepared on 2026-09-28 and covers A-01, A-02 and BR-03.
The record does not include reviewer names or a separate acceptance date.

C03 adds the architecture work. The CP1 freeze follows C03, with review in C04.
