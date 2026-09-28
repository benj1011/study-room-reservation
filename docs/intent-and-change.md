# Project Frame

This document records the v0.1 foundation. For the current approval change,
see [Baseline v0.2](baseline-v0.2.md) and its explicit scope and C03 drivers.

## Reservation domain

The system reserves study rooms for students.

A Room is the resource being reserved. A Reservation connects a User
to a Room for a specific time interval.

## Purpose

The Study Room Reservation System allows students to find available
study rooms and create reservations for a selected time period.

Administrators can review, confirm, and cancel reservation requests
while the system prevents conflicting confirmed reservations.

## Users / Stakeholders

### Student

A student searches for available rooms, creates reservations, views
their reservations, and cancels reservations they no longer need.

### Administrator

An administrator reviews reservation requests and can confirm or
cancel them.

### Facility manager

A facility manager is interested in room information, capacity, and
how rooms are being reserved.

## Core concepts

### User

The person who creates a reservation.

A User contains:

- Identifier
- Name
- Email

### Room

The study room that can be reserved.

A Room contains:

- Identifier
- Name or room code
- Location
- Capacity

### Reservation

A request to use a room during a specific time interval.

A Reservation contains:

- Identifier
- User identifier
- Room identifier
- Start time
- End time
- Number of people
- Purpose
- State

## Core operations

The system supports the following core operations:

- Create a reservation.
- Confirm a reservation.
- Cancel a reservation.
- Check room availability.

Viewing reservations belonging to a user and viewing all reservations are
supporting queries, not additional core operations.

The complete minimum contract is defined in [Baseline v0.1](baseline-v0.1.md).

## Persistent state

The system stores User, Room, and Reservation records in PostgreSQL.

For each User, the system stores:

- Identifier
- Name
- Email

For each Room, the system stores:

- Identifier
- Name
- Location
- Capacity

For each Reservation, the system stores:

- Identifier
- User identifier
- Room identifier
- Start time
- End time
- Number of people
- Purpose
- State

The Reservation references an existing User and an existing Room
through foreign keys.

## Reservation states

The system uses the following Reservation states:

- `DRAFT` — the reservation has been created but does not allocate the room.
- `CONFIRMED` — the reservation allocates the room for its time interval.
- `CANCELLED` — the reservation is no longer active and does not hold
  the room.

## State-changing operation

A new reservation starts in the `DRAFT` state.

The supported state transitions are:

```text
Create reservation:
new → DRAFT

Confirm reservation:
DRAFT → CONFIRMED

Cancel draft:
DRAFT → CANCELLED

Cancel confirmed reservation:
CONFIRMED → CANCELLED
```

A `CANCELLED` reservation cannot be confirmed again.

A `CONFIRMED` reservation cannot be confirmed a second time.

## Common business rule

Two `CONFIRMED` reservations for the same room must not overlap.

Reservations overlap when:

```text
existing.start_time < requested.end_time
AND
existing.end_time > requested.start_time
```

A `DRAFT` reservation does not hold a room.

A `CANCELLED` reservation does not hold a room.

Adjacent reservations are allowed. For example, a reservation ending
at 11:00 does not overlap another reservation starting at 11:00.

## Domain-specific business rule

The number of people in a reservation must be greater than zero and
must not exceed the capacity of the selected room.

For example, a Room with capacity 6 cannot accept a Reservation for
7 people.

Room capacity must also be greater than zero.

## External / system boundary

The selected external boundary is a Notification Service.

The reservation system may request the Notification Service to notify
a user when a reservation is confirmed or cancelled.

The Notification Service is outside the current application boundary.
It is identified as a dependency during C01 but is not implemented as
part of the C01 persistence spike.

A future version must decide whether notification delivery is
synchronous or asynchronous and what should happen when delivery fails.

## Assumption

The current application assumes that users are already authenticated
and that a valid user identity is available.

Authentication and authorization are outside the current C01 scope.
The frontend currently uses a configured demonstration user.

## Unknown

We do not yet know how a failed or delayed notification should affect
a successful reservation state change.

In particular, it is not yet decided whether a notification failure
should:

- Roll back the reservation state change.
- Be retried asynchronously.
- Be recorded for later manual handling.

## Selected future pressure

Category: `Q — Quality / Scale`

### Concrete pressure

The system may need to support ten times more students attempting to
reserve popular study rooms concurrently.

### Why it is relevant to our reservation system

Several students may try to confirm reservations for the same room and
time at nearly the same moment.

A simple application-level “check and then update” sequence can allow
two conflicting reservations when requests run concurrently.

The current backend serializes confirmation operations for the same
room by acquiring a PostgreSQL row lock. Future work should verify this
behavior under higher load and evaluate whether additional database
constraints or transaction strategies are required.
