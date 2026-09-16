## Persistence decisions — Person 3 / C01

### Scope
This contribution covers PostgreSQL persistence, SQLAlchemy
configuration, database models, and the C01 persistence test.
Frontend and FastAPI endpoints are outside this scope.

### Database and ORM
Use PostgreSQL for persistent storage and SQLAlchemy 2.x for ORM
mapping. Use psycopg as the PostgreSQL driver.

The C01 experiment uses real PostgreSQL to verify the actual
database integration.

### Configuration
Read the connection URL from the DATABASE_URL environment variable.
For local testing, supply the password through PGPASSWORD.

Do not store credentials in source code or tracked documentation.
Importing the database module does not connect to PostgreSQL
or create tables.

### Data model
- users: id, name, email
- rooms: id, name, location, capacity
- reservations: id, user_id, room_id, start_time, end_time,
  number_of_people, purpose, state

Reservation.user_id and Reservation.room_id are non-null foreign keys.
SQLAlchemy relationships provide access to the associated objects.

Reservation states are stored using a PostgreSQL enum:
DRAFT, CONFIRMED, CANCELLED.

SQLAlchemy supplies DRAFT when an ORM insert omits the state.
This is an ORM default, not a database server default.

### Time representation
Use timezone-aware datetime columns for reservation start and end.
The persistence test supplies UTC datetime values.

### Implemented database constraints
- Primary keys identify each record.
- Foreign keys require referenced users and rooms to exist.
- Required columns are NOT NULL.
- Room capacity must be greater than zero.
- Reservation number_of_people must be greater than zero.
- Reservation end_time must be later than start_time.
- Reservation state must be a supported enum value.

### Business rules requiring further work
The current implementation does not enforce:
1. No overlapping CONFIRMED reservations for the same room.
2. Reservation number_of_people must not exceed Room.capacity.

These rules involve other rows or tables and are not enforced by
the existing row-level check constraints. Their implementation
and concurrency behavior require coordination with the team.

### Session and transaction handling
Explicitly commit writes before reading the reservation again.
Clear and close the writing session, then use a new session
to avoid retrieving the original object from the ORM identity map.

The C01 test uses one database connection across both sessions.

### Test isolation
Create a uniquely named schema for each test run.
Create the model tables inside that schema, then remove only
that schema during cleanup.

### Schema evolution
Use Base.metadata.create_all() to create tables for the C01 test.
It does not migrate existing tables when model definitions change.
A migration strategy remains a future decision.