# Baseline v0.2 — behavior views

Rules and guards reference [v0.2](baseline-v0.2.md). Approval and lifecycle are
separate dimensions. These are logical activity views, not architectural choices.

## Actor-goal view

```mermaid
flowchart LR
    Student[Student]
    Admin[Administrator]
    Approver[Assigned Approver]
    subgraph System[Study Room Reservation System v0.2]
        Create([OP-01 Create Reservation])
        Search([OP-02 Check Availability])
        Confirm([OP-03 Confirm Reservation])
        Cancel([OP-04 Cancel Reservation])
        Approve([OP-05 Approve Reservation])
    end
    Student --- Create
    Student --- Search
    Student --- Cancel
    Admin --- Confirm
    Admin --- Cancel
    Approver --- Approve
```

Approve includes an authorized rejection outcome. An Approver can also be an
administrator, but administrative UI access alone does not grant assignment.
No Notification Service interaction is implemented.

## Reservation lifecycle

```mermaid
stateDiagram-v2
    [*] --> DRAFT: Create [valid input and BR-10 if protected]
    DRAFT --> CONFIRMED: Confirm [BR-08 permission and BR-02/04 booking guards]
    DRAFT --> CANCELLED: Cancel [BR-03]
    CONFIRMED --> CANCELLED: Cancel [BR-03]
    note right of DRAFT
        May be NOT_REQUIRED, PENDING,
        APPROVED, REJECTED or EXPIRED
        No allocation in any substate
    end note
    note right of CONFIRMED
        Allocated
        Deadline no longer affects allocation
    end note
    note right of CANCELLED
        Retained terminal record
        No later approval or confirmation
    end note
```

## Effective approval state while DRAFT

```mermaid
stateDiagram-v2
    [*] --> NOT_REQUIRED: Create [ordinary room]
    [*] --> PENDING: Create [protected room]
    PENDING --> APPROVED: Approve [assigned actor and now before deadline]
    PENDING --> REJECTED: Reject [assigned actor and now before deadline]
    PENDING --> EXPIRED: now at or after deadline
    APPROVED --> EXPIRED: now at or after deadline
    note right of EXPIRED
        Derived, not a scheduled database write
        No reapproval; cancel or create a new request
    end note
```

NOT_REQUIRED and unexpired APPROVED satisfy the permission guard for Confirm;
neither allocates by itself. Cancel ends the DRAFT lifecycle from any substate.
Once outside DRAFT, the API shows the recorded decision as history (BR-11), not
an active approval state. REJECTED has no approval transition; Cancel is still
available through the reservation lifecycle.

## OP-01 activity

```mermaid
flowchart TD
    Start([Submit reservation]) --> Valid{v0.1 validation passes?}
    Valid -- No --> Error[404 or 422; no create]
    Valid -- Yes --> Protected{Room requires approval?}
    Protected -- No --> Ordinary[Set NOT_REQUIRED; no deadline]
    Protected -- Yes --> Future{Start after server now?}
    Future -- No --> Error
    Future -- Yes --> Pending[Set PENDING and BR-10 deadline]
    Pending --> Save[Persist DRAFT without allocation]
    Ordinary --> Save
    Save --> End([201 with lifecycle and approval metadata])
```

## OP-02 activity

```mermaid
flowchart TD
    Start([Submit availability query]) --> Valid{Valid interval and people?}
    Valid -- No --> Error([422; no writes])
    Valid -- Yes --> Filter[Filter capacity and CONFIRMED overlap only]
    Filter --> Result([200 room list with approval policy; no hold])
```

## OP-03 activity

```mermaid
flowchart TD
    Start([Submit Confirm]) --> Exists{Reservation exists?}
    Exists -- No --> Missing([404])
    Exists -- Yes --> Current[Evaluate current data with competing transitions]
    Current --> Draft{DRAFT?}
    Draft -- No --> Conflict([409; unchanged])
    Draft -- Yes --> Permission{BR-08 permission valid at sampled time?}
    Permission -- No --> Conflict
    Permission -- Yes --> Capacity{BR-04 capacity valid?}
    Capacity -- No --> Invalid([422; unchanged])
    Capacity -- Yes --> Free{No BR-02 overlap?}
    Free -- No --> Conflict
    Free -- Yes --> Commit[Commit CONFIRMED preserving exclusivity]
    Commit --> End([200; room allocated])
```

Evaluate-through-commit is consistent with BR-12; the flow does not prescribe
an unsafe non-atomic check/update sequence.

## OP-04 activity

```mermaid
flowchart TD
    Start([Submit Cancel]) --> Exists{Reservation exists?}
    Exists -- No --> Missing([404])
    Exists -- Yes --> Current[Evaluate with competing transitions]
    Current --> Eligible{DRAFT or CONFIRMED?}
    Eligible -- No --> Conflict([409; unchanged])
    Eligible -- Yes --> Save[Commit CANCELLED; retain stored decision and original details]
    Save --> End([200; allocation released])
```

No approval-state or clock restriction is added to cancellation.

## OP-05 activity

```mermaid
flowchart TD
    Start([Submit APPROVED or REJECTED]) --> Shape{Valid decision and identity format?}
    Shape -- No --> Invalid([422; unchanged])
    Shape -- Yes --> Identity{Identity provided?}
    Identity -- No --> MissingIdentity([401])
    Identity -- Yes --> Exists{Reservation exists?}
    Exists -- No --> Missing([404])
    Exists -- Yes --> Current[Evaluate with competing transitions]
    Current --> Assigned{Identity is assigned approver?}
    Assigned -- No --> Forbidden([403; unchanged])
    Assigned -- Yes --> Eligible{DRAFT and PENDING before deadline?}
    Eligible -- No --> Conflict([409; unchanged])
    Eligible -- Yes --> Save[Record chosen decision, actor and server time]
    Save --> End([200; remains DRAFT; no allocation])
```
