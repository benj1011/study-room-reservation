# Baseline v0.1 — behavior views

These diagrams reference the authoritative [operation slices and shared
rules](baseline-v0.1.md). They describe observable behavior, not database
or framework structure. Actor associations are demo responsibilities under
A-01, not security enforcement.

## Actor-goal view

```mermaid
flowchart LR
    Student[Student]
    Admin[Administrator]
    subgraph System[Study Room Reservation System]
        Create([OP-01 Create Reservation])
        Availability([OP-02 Check Availability])
        Confirm([OP-03 Confirm Reservation])
        Cancel([OP-04 Cancel Reservation])
    end
    Student --- Create
    Student --- Availability
    Student --- Cancel
    Admin --- Confirm
    Admin --- Cancel
```

The Notification Service has no interaction in v0.1 and is therefore not
shown as a supporting actor. User/room setup and reads are supporting
capabilities, not additional core goals.

## Reservation lifecycle statechart

```mermaid
stateDiagram-v2
    [*] --> DRAFT: Create [BR-01, BR-04, BR-05]
    DRAFT --> CONFIRMED: Confirm [BR-02, BR-04, A-02]
    DRAFT --> CANCELLED: Cancel [BR-03]
    CONFIRMED --> CANCELLED: Cancel [BR-03]
    note right of DRAFT
        No allocation
    end note
    note right of CONFIRMED
        Allocates room interval
    end note
    note right of CANCELLED
        Retained terminal record
        No outgoing transitions
    end note
```

Rejected operations do not transition. Repeated Confirm and repeated Cancel
are rejected as defined in the slices. Check Availability reads state without
transitioning. Concurrent transitions must obey BR-02 and BR-03.

## OP-01 activity — Create Reservation

```mermaid
flowchart TD
    Start([Start]) --> Submit[Submit room, user, interval, people, purpose]
    Submit --> Valid{BR-01 and input valid?}
    Valid -- No --> Invalid[422: no create]
    Valid -- Yes --> Exists{User and Room exist?}
    Exists -- No --> Missing[404: no create]
    Exists -- Yes --> Capacity{BR-04 satisfied?}
    Capacity -- No --> Invalid
    Capacity -- Yes --> Persist[Persist DRAFT without allocation]
    Persist --> Response[201: identifier and state]
    Response --> End([End])
    Invalid --> End
    Missing --> End
```

A-01 is assumed at entry. An occupied interval does not prevent Create.

## OP-02 activity — Check Availability

```mermaid
flowchart TD
    Start([Start]) --> Query[Submit interval and group size]
    Query --> Valid{BR-01 and positive people?}
    Valid -- No --> Invalid[422: no writes]
    Valid -- Yes --> Select[Evaluate registered rooms under A-02]
    Select --> Filter[Apply BR-04 capacity and BR-02 confirmed overlap rules]
    Filter --> Response[200: matching rooms, possibly empty; no hold]
    Response --> End([End])
    Invalid --> End
```

## OP-03 activity — Confirm Reservation

```mermaid
flowchart TD
    Start([Start]) --> Submit[Submit reservation id]
    Submit --> Exists{Reservation exists?}
    Exists -- No --> Missing[404: unchanged]
    Exists -- Yes --> Evaluate[Evaluate against competing changes under BR-02 and BR-03]
    Evaluate --> Draft{Current state DRAFT?}
    Draft -- No --> Conflict[409: unchanged]
    Draft -- Yes --> Capacity{BR-04 satisfied?}
    Capacity -- No --> Invalid[422: remains DRAFT]
    Capacity -- Yes --> Free{No BR-02 overlap?}
    Free -- No --> Conflict
    Free -- Yes --> Commit[Commit CONFIRMED preserving exclusivity]
    Commit --> Response[200: updated record; room interval allocated]
    Response --> End([End])
    Missing --> End
    Conflict --> End
    Invalid --> End
```

A-02 supplies the active-resource condition. The evaluate-through-commit
behavior is indivisible with respect to conflicting operations; the boxes
do not authorize an unsafe check-then-update implementation.

## OP-04 activity — Cancel Reservation

```mermaid
flowchart TD
    Start([Start]) --> Submit[Submit reservation id]
    Submit --> Exists{Reservation exists?}
    Exists -- No --> Missing[404: unchanged]
    Exists -- Yes --> Evaluate[Evaluate current state with competing changes under BR-03]
    Evaluate --> Allowed{DRAFT or CONFIRMED?}
    Allowed -- No --> Conflict[409: unchanged]
    Allowed -- Yes --> Commit[Commit CANCELLED; retain details; release allocation]
    Commit --> Response[200: updated record]
    Response --> End([End])
    Missing --> End
    Conflict --> End
```

BR-03 has no time cutoff, so this flow contains no clock decision.
