# C01 Engineering Spike

## Selected spike

**A — Persistence**

## Question / unknown

Can the application persist a DRAFT Reservation in PostgreSQL and
reload its data, including the correct User and Room references,
in a new SQLAlchemy session?

## Experiment

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

## Recorded execution

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

## Result and interpretation

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

## Decision

Retain PostgreSQL, SQLAlchemy 2, and psycopg 3 for the project's
persistence path.

Reuse the shared database configuration and ORM models when extending
the application. The spike provides the persistence foundation for
the CP1 walking skeleton; it does not establish completion of CP1.

## Limitations

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

# Change and Review Cycle

| Item | Record |
| --- | --- |
| Task | C01 engineering spike — PostgreSQL persistence |
| Change author | DAT |
| Reviewer named in the project record | Izaz |
| Pull request | [PR #1 — C01 PostgreSQL persistence spike](https://github.com/benj1011/study-room-reservation/pull/1) |
| Separate issue | No issue URL is recorded in this document. |
| Integration | PR #1 was merged on 2026-09-17. |
| Merge commit | `7bd0b30e9d1c8ecdf6fe5ae618fb9fbd2480c6e8` |

## Review evidence

The Git history confirms the merge of PR #1 and lists
Syed Izaz Huassain as the merge commit author.

The available record does not establish the review comments,
approval outcome, or whether approval occurred before integration.
The merge alone is not treated as proof of peer review.

To complete the review evidence, add a link to the actual GitHub
review or discussion and summarize its outcome.

# Evolution After C01

Subsequent work extended the application with room availability,
reservation confirmation and cancellation, browser pages, and
additional validation and concurrency checks.

These changes build on the persistence foundation established by C01.
Their behavior and verification belong to the later baseline documents.