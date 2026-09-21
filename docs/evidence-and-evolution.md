# C01 Engineering Spike

## Selected spike

`A — Persistence`

The experiment verifies:

```text
Reservation
→ POST /reservations
→ validate request
→ real PostgreSQL database
→ commit
→ return generated ID
→ new SQLAlchemy session
→ load Reservation
→ verify persisted data
```

## Question / unknown

Can the application persist a `DRAFT` Reservation to a real PostgreSQL
database and load it correctly in a new SQLAlchemy session?

The experiment must also verify that the loaded Reservation still
references the correct User and Room.

## What we did

We configured SQLAlchemy 2 to connect to a real PostgreSQL database
through psycopg 3.

The executed test is:

```text
tests/test_persistence.py
```

The test performs the following steps:

1. Creates a unique PostgreSQL schema for the test run.
2. Configures PostgreSQL to use the isolated schema.
3. Creates User, Room, and Reservation tables.
4. Creates and commits the required User and Room.
5. Sends a valid request to `POST /reservations`.
6. Verifies HTTP `201`, the generated identifier, and the `DRAFT` state.
7. Opens a new SQLAlchemy session.
8. Loads the Reservation using the returned identifier.
9. Verifies the Reservation fields and its related User and Room.
10. Removes the isolated test schema.

The Reservation used in the experiment contains:

- A valid User reference.
- A valid Room reference.
- Timezone-aware start and end times.
- A positive number of people.
- A purpose.
- The `DRAFT` state.

## Environment

The original experiment was executed with:

- Python 3.13.1
- PostgreSQL 17.2
- SQLAlchemy 2.0.54
- psycopg 3.3.5
- pytest 9.1.1
- Local test database: `study_room_c01_test`

## Execution

Execution date: 2026-09-16

Command:

```bash
python -m pytest tests/test_persistence.py -v
```

## Observed result

Observed output:

```text
tests/test_persistence.py::test_reservation_persists_in_postgresql PASSED
1 passed in 0.28s
```

The API validated and committed the Reservation successfully and returned its
generated identifier.

A new SQLAlchemy session loaded the Reservation from PostgreSQL.

The loaded record contained the expected:

- Reservation identifier.
- User identifier.
- Room identifier.
- Start time.
- End time.
- Number of people.
- Purpose.
- `DRAFT` state.

The related User and Room were also loaded successfully.

This demonstrates real database persistence rather than reuse of an
object still held by the original SQLAlchemy session.

## Decision / what changes because of the result

Retain PostgreSQL, SQLAlchemy 2, and psycopg 3 for the CP1 persistence
path.

The selected stack successfully persists and loads the core Reservation
data, including its User and Room references.

The backend can integrate the shared database configuration and models
instead of creating a second persistence implementation.

The result also establishes the persistence portion of the CP1 walking
skeleton:

```text
validate Reservation
→ persist to PostgreSQL
→ commit
→ return generated Reservation identifier
→ verify through an automated check
```

## Limitations of the spike

This spike verifies persistence for one valid Reservation.

The C01 spike does not itself verify:

- Prevention of overlapping confirmed reservations.
- Capacity enforcement across Room and Reservation.
- Concurrent confirmation behavior.
- Notification Service success or failure.
- Authentication.
- Authorization.
- Schema migrations.
- Deployment or production recovery.

These concerns require separate implementation and testing.

Additional API tests may exist in the repository, but they do not
change the selected C01 spike. The single official C01 engineering
spike remains Persistence.

# Change and Review Cycle

## Task

Task name:

```text
C01 engineering spike
```

Issue:

```text
<INSERT GITHUB ISSUE URL>
```

## Change author

```text
<AUTHOR NAME>
```

The author implemented the PostgreSQL persistence configuration, ORM
models, persistence test, and supporting documentation.

## Reviewer

```text
<REVIEWER NAME>
```

The reviewer must be a different team member from the change author.

## Pull request

```text
https://github.com/benj1011/study-room-reservation/pull/1
```

If Pull Request #1 was not reviewed by another team member before it
was merged, replace the link above with the URL of a new Pull Request
that completes a real review cycle.

## Review result

```text
<REPLACE WITH THE REAL REVIEW RESULT>
```

Example, only if it actually happened:

```text
The reviewer checked the persistence test, database configuration,
credential handling, test isolation, and documentation. The reviewer
approved the change before integration.
```

## Integration

The reviewed change was merged into the shared `main` branch.

Merge commit for Pull Request #1:

```text
7bd0b30e9d1c8ecdf6fe5ae618fb9fbd2480c6e8
```

This section is complete only when the repository contains evidence
that another team member reviewed the change before integration.

# Evolution After the Spike

After the persistence spike, the project added an integrated FastAPI
backend and browser frontend.

The backend now includes:

- Reservation creation.
- Room availability.
- User-based reservation filtering.
- Reservation confirmation.
- Reservation cancellation.
- Capacity validation.
- Overlap checking.
- PostgreSQL row locking for state changes.
- Explicit HTTP error responses.

These additions build on the database configuration and models selected
by the C01 persistence spike.
