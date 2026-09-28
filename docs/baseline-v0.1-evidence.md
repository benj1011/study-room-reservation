# Baseline v0.1 — C02 execution evidence

## Execution identity

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

## Command and actual result

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

## Fixture and observations

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

## Scenario-to-test traceability

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

## Concurrent behavior and why the result is credible

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

## Satisfaction and remaining limits

All four slices have executed success and relevant rejection/boundary examples.
No application/specification mismatch was found in those executions, so the
existing runnable API was retained. The C02 additions are specification,
review, diagrams and separate executable evidence, not a replacement C01 spike.

A-01 and A-02 are deliberate user-selected scope adaptations: unauthorized
requests and inactive resources are not supported test conditions. No access
control or inactive-room rejection is claimed. Team review must explicitly
accept those adaptations. Notification, browser UI, process-restart recovery,
full production deployment and load performance were not tested by this suite.
Fresh-session persistence is demonstrated; process-restart durability is not
separately exercised. HTTP is exercised in-process; no network/proxy deployment
claim follows from TestClient.

Engineering preparation is complete for the selected scope. The remaining
human step is the genuine team acceptance record in
[the review document](baseline-v0.1-review.md), not another fabricated test result.
