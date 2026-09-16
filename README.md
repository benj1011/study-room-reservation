# study-room-reservation

## C01 — PostgreSQL persistence spike

This spike verifies that a DRAFT Reservation can be committed to
a real PostgreSQL database and loaded correctly in a new SQLAlchemy
session.

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
1. Creates an isolated schema and model tables.
2. Persists and commits a User and Room.
3. Persists and commits a DRAFT Reservation.
4. Clears and closes the writing session.
5. Loads the Reservation in a new session.
6. Verifies its fields and related User and Room.
7. Removes the test schema.

The test account needs permission to create schemas in the test
database. The test uses a real PostgreSQL database, not SQLite.

### Scope and limitations

This test demonstrates persistence only.
It does not implement or verify:
- Prevention of overlapping CONFIRMED reservations.
- Enforcement of reservation attendance against room capacity.
- Frontend or FastAPI endpoints.

The tables created by this test are removed after execution.
Running this test does not initialize persistent application tables.

### Finish the local session

```bash
unset PGPASSWORD
deactivate
```

### Evidence

See:
- [Spike evidence](docs/evidence-and-evolution.md)
- [Persistence decisions](docs/architecture-and-decisions.md)