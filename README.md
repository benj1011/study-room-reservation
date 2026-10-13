# Study Room Reservation System

## Documentation

The project maintains three documents across C01, C02, C03a, C03b and C05:

- [Intent and change](docs/intent-and-change.md): requirements, rules, scenarios and baseline changes.
- [Architecture and decisions](docs/architecture-and-decisions.md): architecture, ADRs and design.
- [Evidence and evolution](docs/evidence-and-evolution.md): verification, reviews and milestone history.

Historical sections are retained and labelled; raw test output and hash manifests remain in `docs/evidence/`.

## C05 — Detailed Design

Confirm Reservation (OP-03) is the selected detailed-design unit.

- [Design, contracts, UML and algorithm](docs/architecture-and-decisions.md#c05-detailed-design).
- [DD-derived tests, consistency review and execution evidence](docs/evidence-and-evolution.md#c05-verification).
- Delivery tag: `c05-detailed-design`; recorded full-suite result: **68 passed, 2 warnings**.

## Team

Team name: Study Room Reservation Team

Members:

- Pham Tien Dat
- Hussain Syed Izaz
- Wahab Muhammad

Repository:

https://github.com/benj1011/study-room-reservation

## Project overview

The system allows students to check study-room availability and create
reservations for a selected time period.

Administrators can confirm and cancel reservation requests. Confirmed
reservations for the same room must not overlap.

The domain-specific business rule is that the number of people in a
reservation must not exceed the capacity of the selected room.

The selected external boundary is a Notification Service. Notification
delivery is outside the C01 implementation scope.


## Current baseline v0.2 — approval workflow

Part B.12–14 adds approval-required rooms and an assigned Approver. See:

- [Pre-edit impact analysis / change card](docs/intent-and-change.md#c02-change)
- [v0.2 specification and five full slices](docs/intent-and-change.md#c02-v02)
- [Updated actor, lifecycle, approval and activity views](docs/intent-and-change.md#c02-v02-views)
- [C03 architecture baseline and open decisions](docs/architecture-and-decisions.md#c03a-c03-architecture-baseline)
- [C03 architecture design and evidence](docs/architecture-and-decisions.md#c03b)

The v0.2 acceptance and test results are recorded in
[Baseline v0.2 evidence](docs/evidence-and-evolution.md#c02-v02-evidence).
The complete v0.2 interface is API/Swagger.
The existing browser pages remain a v0.1 demonstration and have no Approve UI.

After activating `.venv` and configuring `DATABASE_URL` as below:

- For a **new database**, run `python -m src.init_db`.
- For an **existing v0.1 database**, stop its API and run
  `python -m src.migrate_v02` before restarting. This additive migration preserves
  old records as NOT_REQUIRED; `init_db` alone does not migrate old tables.

Start the API:

```bash
python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

At <http://127.0.0.1:8000/docs>, try the following sequence:

1. Create a student and an approver with `POST /users`; keep their returned ids.
2. Create a room with `POST /rooms`, using the actual approver id:

   ```json
   {"name":"Approval Room","location":"Library","capacity":6,
    "requires_approval":true,"approver_user_id":2}
   ```

3. Create a reservation using the student's id and the returned room id.
   Choose timezone-aware start/end timestamps in the future. It returns
   DRAFT/PENDING with `approval_deadline`.
4. Try Confirm: it returns 409 while approval is pending.
5. Call `POST /reservations/{id}/approve` with `X-User-Id` set to the assigned
   approver's id and body `{"decision":"APPROVED"}`. The result remains DRAFT.
   Use `{"decision":"REJECTED"}` on another pending request to demonstrate rejection.
6. Confirm the approved request before its deadline. It succeeds only if capacity
   and availability still permit it. Cancel retains the record as before.

The deadline is the earlier of Create + 24 hours and the reservation start.
At/after the deadline, pending or approved drafts report EXPIRED and cannot
confirm. Expiry is computed on read/validation; there is no background service.
`X-User-Id` is a trusted demo assertion, not secure authentication. The assigned
user check is implemented; production identity integration remains open.

Run v0.2 and ordinary-room regression checks against a configured test database:

```bash
python -m pytest tests/test_baseline.py tests/test_approval.py -v --tb=short
```

Tests isolate and remove their own schemas. No Uvicorn/frontend process is
needed for the test suite. Deadline tests use a controlled clock, so no 24-hour
wait is needed.

## Historical baseline v0.1 — minimum system specification

[Baseline v0.1](docs/intent-and-change.md#c02-v01) defines the four core operations:
Create Reservation, Check Availability, Confirm Reservation, and Cancel
Reservation. Create stores a DRAFT without allocating a room; Confirm allocates
it; Cancel retains the record and releases any allocation. The baseline has
no approval workflow.

Part A artifacts:

- [Four full operation slices and shared rules](docs/intent-and-change.md#c02-v01)
- [Actor-goal, lifecycle and four activity diagrams](docs/intent-and-change.md#c02-v01-views)
- [Requirement gate, consistency review and team sign-off](docs/evidence-and-evolution.md#c02-v01-review)
- [C02 execution evidence and coverage](docs/evidence-and-evolution.md#c02-v01-evidence)

The selected scope retains trusted demo identity and treats every registered
room as active. Cancellation has no time cutoff; repeated cancellation is a
conflict. These are explicit scope/policy decisions, not authentication or
inactive-room functionality. See the
[baseline review](docs/evidence-and-evolution.md#c02-v01-review-team-acceptance-record) for acceptance status.

Run the separate C02 suite against a configured PostgreSQL test database:

```bash
python -m pytest tests/test_baseline.py -v
```

It creates and removes its own `c02_test_*` schemas and exercises all four API
operations, including synchronized requests on independent DB sessions.
The existing application runs using the backend instructions below; no new UI
is required for Part A.

## C01 — PostgreSQL persistence spike

This spike verifies one runnable end-to-end path: a DRAFT Reservation is
submitted to `POST /reservations`, validated by FastAPI, committed to a real
PostgreSQL database, returned with its generated ID, and loaded again in a new
SQLAlchemy session.

### Prerequisites

- Python 3.13
- A running local PostgreSQL server
- A PostgreSQL account that can create a test database

The experiment was executed with:
- PostgreSQL 17.2
- SQLAlchemy 2.0.54
- psycopg 3.3.5
- pytest 9.1.1

### 1. Set up Python

Run these commands from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

If `.venv` already exists, activate it and install the dependencies.

### 2. Create a dedicated test database

The example uses the local PostgreSQL account `postgres`.
Replace the username if your installation uses a different account.

```bash
createdb -h localhost -p 5432 -U postgres -W study_room_c01_test
```

Enter your own PostgreSQL password when prompted.
If this dedicated test database already exists, reuse it.

Verify access:

```bash
psql -h localhost -p 5432 -U postgres -d study_room_c01_test -W -c "SELECT current_database(), current_user;"
```

### 3. Configure the connection

In macOS zsh:

```bash
export DATABASE_URL='postgresql+psycopg://postgres@localhost:5432/study_room_c01_test'
read -s "PGPASSWORD?PostgreSQL password: "
export PGPASSWORD
```

Type your password at the prompt and press Enter.
The password is hidden while typing.

These variables apply to the current terminal session.
Do not put real passwords in source code, documentation, or Git.

### 4. Run the persistence test

In the same terminal:

```bash
python -m pytest tests/test_persistence.py -v
```

A successful run reports:

```text
tests/test_persistence.py::test_reservation_persists_in_postgresql PASSED
```

The test:

1. Creates an isolated schema and model tables in PostgreSQL.
2. Persists the User and Room required by the reservation.
3. Sends a valid request to `POST /reservations`.
4. Verifies HTTP `201`, the generated reservation ID, and the `DRAFT` state.
5. Opens a new SQLAlchemy session and loads the Reservation by that ID.
6. Verifies its fields and related User and Room.
7. Removes the isolated test schema.

The test account needs permission to create schemas in the test
database. The test uses a real PostgreSQL database, not SQLite.

### Scope and limitations

This test demonstrates the CP1 create-and-persist path. It does not verify:

- Prevention of overlapping CONFIRMED reservations.
- Enforcement of reservation attendance against room capacity.
- Frontend behavior.

The tables created by this test are removed after execution.
Running this test does not initialize persistent application tables.

### Finish the local session

```bash
unset PGPASSWORD
deactivate
```

### Evidence

See:

- [Spike evidence](docs/evidence-and-evolution.md#milestone-evidence)
- [Persistence decisions](docs/architecture-and-decisions.md#c03a)

## CP1 walking skeleton

The CP1 end-to-end path is:

`POST /reservations` → validate the request → persist it in PostgreSQL →
return HTTP `201` with the generated reservation ID → load it again and verify
the stored data.

The automated check is the C01 persistence test:

```bash
python -m pytest tests/test_persistence.py -v
```

The test uses an isolated PostgreSQL schema and removes it when it finishes.

## Run the integrated backend and frontend

Run commands from the repository root. The API reuses `src/database.py`
with psycopg 3 and the shared models in `src/models.py`.

### 1. Install dependencies and configure an application database

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
createdb -h localhost -p 5432 -U postgres -W study_room_app
export DATABASE_URL='postgresql+psycopg://postgres@localhost:5432/study_room_app'
read -s "PGPASSWORD?PostgreSQL password: "
export PGPASSWORD
```

Use your own PostgreSQL account. Create the database only once. This is a
separate application database; C01 continues to use `study_room_c01_test`.

### 2. Initialize tables and start the API

```bash
python -m src.init_db
python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000/docs>. Initialization creates missing tables and
the PostgreSQL state enum; it does **not** migrate tables from a previous schema
version. Use a fresh application database for this integration. Retaining old
data requires a separate migration, especially for timestamps and enum values.
Importing the API does not initialize tables or connect to PostgreSQL.

### 3. Add demo data

For a complete repeatable dataset, run:

```bash
python -m src.seed_demo
```

This creates three rooms, two users, and five reservations covering DRAFT,
CONFIRMED, and CANCELLED states. Reservations are scheduled for the following
day. Running the command again replaces only reservations whose purpose starts
with `[DEMO]`; it does not delete other application data. The command prints
the current frontend user ID and warns if it is not `1`.

Alternatively, add individual records through Swagger. Use `POST /users` with:

```json
{"name": "Dat", "email": "dat@example.com"}
```

Use `POST /rooms` with:

```json
{"name": "A101", "location": "Library", "capacity": 6}
```

The frontend assumes demo user ID `1`; if the seed output or returned user ID differs,
update `CURRENT_USER_ID` in `src/frontend/js/api.js`. Authentication and
admin authorization are not implemented.

### 4. Serve the frontend in another terminal

From the repository root:

```bash
python3 -m http.server 5500 --bind 127.0.0.1 --directory src/frontend
```

Open <http://127.0.0.1:5500>. Search for a room, create a DRAFT, confirm it
on the Admin page, and cancel it from My Reservations. API errors are shown
instead of silently falling back to mock data. Entered times use the browser's
local timezone, are sent as UTC ISO timestamps, and are displayed in local time.

### API contract

- `GET /users`, `POST /users`
- `GET /rooms`, `POST /rooms`
- `GET /rooms/available?start_time=<ISO with timezone>&end_time=<ISO with timezone>&people=4`
- `GET /reservations` (all), `GET /reservations?user_id=1` (filtered)
- `GET /reservations/{id}`, `POST /reservations`
- `POST /reservations/{id}/approve` (assigned approver, using `X-User-Id`)
- `POST /reservations/{id}/confirm`
- `POST /reservations/{id}/cancel` (`PATCH` remains a compatibility alias)

DRAFT reservations do not hold a room. Confirmation rechecks capacity and
conflicts with CONFIRMED reservations. Adjacent time windows are allowed.
Confirm and cancel acquire a PostgreSQL row lock on the room until commit,
serializing state changes for that room under PostgreSQL's default READ COMMITTED
isolation. Direct database writes bypass this API rule; no database exclusion
constraint has been added. The destructive testing-reset endpoint is not exposed.

### Automated verification

Configure `DATABASE_URL` and `PGPASSWORD` for `study_room_c01_test` as in C01,
then run:

```bash
python -m pytest tests/test_persistence.py -v
```

The test uses real PostgreSQL, creates a uniquely named schema, sends a request
to the reservation API, reloads the saved Reservation in a new session, and
removes the schema afterwards.

See [architecture and decisions](docs/architecture-and-decisions.md#c03a) for the
current implementation and its limitations.
