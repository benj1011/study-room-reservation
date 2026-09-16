## C01 — PostgreSQL persistence spike

### Question
Can the application persist a Reservation to a real PostgreSQL
database and load it again correctly?

### Environment
- Python 3.13.1
- PostgreSQL 17.2
- SQLAlchemy 2.0.54
- psycopg 3.3.5
- pytest 9.1.1
- Local database: study_room_c01_test

### Experiment
1. Connect SQLAlchemy to the local PostgreSQL database.
2. Create an isolated test schema and the User, Room, and Reservation tables.
3. Persist and commit a User and a Room.
4. Persist and commit a DRAFT Reservation.
5. Clear and close the writing SQLAlchemy session.
6. Open a new session and load the Reservation by its ID.
7. Verify all Reservation fields and the related User and Room values.
8. Remove the test schema after the experiment.

The reading session uses the same database connection, but a new
ORM identity map. The data is committed before it is loaded again.

### Execution
Date: 2026-09-16

Command:
python -m pytest tests/test_persistence.py -v

Observed result:
tests/test_persistence.py::test_reservation_persists_in_postgresql PASSED
1 passed in 0.28s

### Conclusion
Yes. The experiment demonstrated that a DRAFT Reservation could
be committed to real PostgreSQL and loaded correctly in a new
SQLAlchemy session, including its User and Room references.

### Limitations and follow-up
- This experiment verifies persistence for one valid reservation.
- It does not verify enforcement of the rule preventing overlapping
  CONFIRMED reservations for the same room.
- It does not verify enforcement of number_of_people <= Room.capacity.
- Concurrent reservations and application restart recovery were not tested.
- Business-rule enforcement requires further team coordination and tests.


### Decision / what changes because of the result

Retain PostgreSQL, SQLAlchemy 2.x, and psycopg for the CP1
persistence path. The executed spike demonstrated that a
committed Reservation can be loaded correctly in a new session.

The backend can now integrate the existing database configuration
and models. Business-rule enforcement requires separate
implementation and testing.