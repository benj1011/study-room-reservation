# Architecture and Decisions

## System overview

The Study Room Reservation System is a small web application with
three main parts:

1. A browser frontend written in HTML, CSS, and JavaScript.
2. A FastAPI backend that implements reservation operations.
3. A PostgreSQL database accessed through SQLAlchemy.

The system reserves study rooms for users during defined time
intervals.

## Technology stack

- Python 3.13
- FastAPI
- Pydantic 2
- SQLAlchemy 2
- PostgreSQL
- psycopg 3
- pytest
- HTML
- CSS
- JavaScript

## Stack rationale

Python and FastAPI provide a small and understandable HTTP API suitable
for the project's walking skeleton.

Pydantic validates incoming API data before it reaches the persistence
layer.

SQLAlchemy provides explicit ORM mappings and separates database
configuration from endpoint logic.

PostgreSQL was selected because reservations require:

- Durable relational data.
- Foreign keys.
- Check constraints.
- Transactions.
- Enum values.
- Concurrency control.

The persistence spike uses a real PostgreSQL database rather than
SQLite so that the experiment verifies the selected production
database technology.

pytest provides an executable and repeatable persistence check.

The frontend uses plain HTML, CSS, and JavaScript because the current
interface is small and does not require a frontend framework.

## Application components

### Frontend

The frontend provides pages for:

- Searching room availability.
- Creating a reservation.
- Viewing a user's reservations.
- Administering all reservations.

The frontend communicates with the backend through HTTP and JSON.

Dates and times entered in the browser are converted into timezone-aware
ISO timestamps before being sent to the API.

### Backend API

The FastAPI backend provides operations for:

- Creating and viewing users.
- Creating and viewing rooms.
- Checking room availability.
- Creating reservations.
- Viewing reservations.
- Filtering reservations by user.
- Confirming reservations.
- Cancelling reservations.

### Persistence layer

`src/database.py` contains:

- The shared SQLAlchemy declarative base.
- Engine creation.
- Session factory creation.
- Environment-based database configuration.

`src/models.py` contains the shared ORM model definitions.

The backend and persistence tests use the same model definitions.

## Database configuration

The database connection URL is read from the `DATABASE_URL`
environment variable.

Example:

```text
postgresql+psycopg://postgres@localhost:5432/study_room_app
```

The password can be supplied through PostgreSQL's `PGPASSWORD`
environment variable.

Credentials are not stored in source code or tracked documentation.

Importing the database module does not connect to PostgreSQL and does
not create tables.

## Data model

### User

Table: `users`

Fields:

- `id` — primary key.
- `name` — required string, maximum length 100.
- `email` — required string, maximum length 255.

Relationships:

- A User can have multiple Reservations.

### Room

Table: `rooms`

Fields:

- `id` — primary key.
- `name` — required string, maximum length 100.
- `location` — required string, maximum length 255.
- `capacity` — required integer.

Constraints:

- `capacity > 0`

Relationships:

- A Room can have multiple Reservations.

### Reservation

Table: `reservations`

Fields:

- `id` — primary key.
- `user_id` — required foreign key to User.
- `room_id` — required foreign key to Room.
- `start_time` — required timezone-aware datetime.
- `end_time` — required timezone-aware datetime.
- `number_of_people` — required integer.
- `purpose` — required text.
- `state` — required Reservation state.

Constraints:

- `end_time > start_time`
- `number_of_people > 0`
- User must exist.
- Room must exist.
- State must be a supported enum value.

Relationships:

- A Reservation belongs to one User.
- A Reservation belongs to one Room.

The API derives `room_name` through the Room relationship. The room
name is not duplicated in the Reservation table.

## Reservation state representation

Reservation states are represented by the PostgreSQL enum
`reservation_state`.

Supported values:

```text
DRAFT
CONFIRMED
CANCELLED
```

SQLAlchemy supplies `DRAFT` when an ORM insert omits the state.

This is currently an ORM default rather than a PostgreSQL server
default.

## Time representation

Reservation start and end values use timezone-aware datetime columns.

The API requires timestamps that include a timezone or UTC offset.

The browser converts local date and time input into an ISO UTC
timestamp before sending it to the backend.

PostgreSQL may return the same instant using the timezone configured
for the database session. Tests compare instants rather than requiring
one particular displayed offset.

## API validation

The API validates:

- User identifier is positive.
- Room identifier is positive.
- User exists.
- Room exists.
- Start and end timestamps include timezone information.
- End time is later than start time.
- Number of people is greater than zero.
- Number of people does not exceed room capacity.
- Purpose is not empty.
- Names and locations respect the model length limits.

The database retains its own row-level constraints as a second layer of
protection.

## Availability decision

Only `CONFIRMED` reservations block room availability.

`DRAFT` reservations do not block a room because they have not yet been
approved.

`CANCELLED` reservations never block a room.

Availability also filters out rooms whose capacity is smaller than the
requested number of people.

## Overlap decision

Two confirmed reservations overlap when they reference the same Room
and satisfy:

```text
existing.start_time < requested.end_time
AND
existing.end_time > requested.start_time
```

Adjacent reservations are allowed.

For example:

```text
Reservation A: 10:00–11:00
Reservation B: 11:00–12:00
```

These reservations do not overlap.

## Confirmation and concurrency

Confirmation performs the following steps:

1. Load the Reservation.
2. Lock the related Room row using PostgreSQL `FOR UPDATE`.
3. Refresh the Reservation after acquiring the lock.
4. Verify that the Reservation is `DRAFT`.
5. Verify room capacity.
6. Check for overlapping `CONFIRMED` reservations.
7. Change the state to `CONFIRMED`.
8. Commit the transaction.

Confirm and cancel operations acquire the same Room lock.

Under PostgreSQL's default `READ COMMITTED` isolation, this serializes
state-changing operations for the same Room through the API.

This protects the API workflow from two simultaneous confirmations for
the same room and time.

This is application transaction behavior, not a database exclusion
constraint. Direct database writes can bypass the rule.

## Session and transaction handling

The backend opens one SQLAlchemy Session for each request.

Successful state-changing operations are explicitly committed.

If request processing raises an exception, the Session is rolled back.

The Session is closed after request processing.

The persistence spike creates the Reservation through `POST /reservations`
and reads it by the returned identifier in a new SQLAlchemy session. This
avoids mistaking SQLAlchemy's identity map or only an HTTP response for real
persistence.

## HTTP error decisions

The API uses:

- `404 Not Found` when User, Room, or Reservation does not exist.
- `409 Conflict` when a state transition or reservation confirmation
  conflicts with current state.
- `422 Unprocessable Entity` when request data violates validation or
  business constraints.

Business errors are not returned as successful HTTP 200 responses.

## Schema initialization

Application tables are initialized explicitly with:

```text
python -m src.init_db
```

Importing or starting the API does not create tables automatically.

`Base.metadata.create_all()` creates missing tables but does not migrate
existing tables when model definitions change.

A formal migration tool has not yet been selected.

A future schema change must introduce a migration strategy before
existing application data must be retained across model changes.

## Test isolation

The C01 persistence test uses a real PostgreSQL database.

For each test execution, it:

1. Creates a uniquely named PostgreSQL schema.
2. Creates the model tables in that schema.
3. Executes the persistence experiment.
4. Removes only the schema created by the test.

The test does not use SQLite and does not delete application tables.

## External boundary

The selected external boundary is a Notification Service.

The current system does not implement notification delivery.

A future integration may notify users after confirmation or
cancellation. Failure handling, retries, and delivery guarantees remain
open decisions.

## Security and current limitations

Authentication and authorization are not implemented.

The frontend currently assumes a demonstration user identity.

The Admin page is not protected by an authorization mechanism.

Notification delivery is not implemented.

Database migrations are not implemented.

These limitations are explicit and remain outside the C01 persistence
spike.

## Current decisions

The project currently retains the following decisions:

- Use PostgreSQL for persistent storage.
- Use SQLAlchemy 2 for ORM mapping.
- Use psycopg 3 as the PostgreSQL driver.
- Read database configuration from environment variables.
- Keep credentials out of source code.
- Use timezone-aware reservation timestamps.
- Create new reservations as `DRAFT`.
- Allow only `CONFIRMED` reservations to block availability.
- Enforce capacity in the API and through database row constraints
  where possible.
- Serialize state changes for the same Room with a PostgreSQL row lock.
- Treat Notification Service as an external boundary.
- Use Persistence as the single official C01 engineering spike.
