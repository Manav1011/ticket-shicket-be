# Advanced Mermaid Patterns for Code Graphs

## Node Shape Reference

| Shape | Mermaid Syntax | Best For |
|---|---|---|
| Rectangle | `A[label]` | Modules, files |
| Rounded rect | `A(label)` | Functions, methods |
| Stadium/pill | `A([label])` | Entry points |
| Cylinder | `A[(label)]` | Databases, storage |
| Diamond | `A{label}` | Conditionals, branches |
| Parallelogram | `A[/label/]` | I/O, data |
| Flag | `A>label]` | External libs/services |
| Hexagon | `A{{label}}` | Config, constants |
| Circle | `A((label))` | Events |

## Color Schemes (classDef)

### Standard Code Graph Palette
```
classDef entry     fill:#4f46e5,color:#fff,stroke:#3730a3
classDef module    fill:#0ea5e9,color:#fff,stroke:#0284c7
classDef func      fill:#10b981,color:#fff,stroke:#059669
classDef class_    fill:#f59e0b,color:#fff,stroke:#d97706
classDef external  fill:#6b7280,color:#fff,stroke:#4b5563,stroke-dasharray:5 3
classDef error     fill:#ef4444,color:#fff,stroke:#dc2626
classDef async_    fill:#8b5cf6,color:#fff,stroke:#7c3aed
```

### Dark-friendly variant
```
classDef entry     fill:#6d28d9,color:#fff,stroke:#5b21b6
classDef module    fill:#1d4ed8,color:#fff,stroke:#1e40af
classDef func      fill:#065f46,color:#fff,stroke:#064e3b
classDef external  fill:#374151,color:#9ca3af,stroke:#4b5563,stroke-dasharray:4
```

## Subgraph Patterns

### Feature grouping
```mermaid
flowchart TD
    entry([🚀 main]):::entry

    subgraph auth ["🔐 Auth Layer"]
        login["login()"]
        logout["logout()"]
        validate["validate_token()"]
    end

    subgraph data ["💾 Data Layer"]
        query["db_query()"]
        cache["cache_get()"]
    end

    entry --> auth
    login --> data
```

### Layer architecture
```mermaid
flowchart TD
    subgraph api ["API Layer"]
        r1["/users route"]
        r2["/posts route"]
    end
    subgraph svc ["Service Layer"]
        us["UserService"]
        ps["PostService"]
    end
    subgraph dal ["Data Layer"]
        db[(PostgreSQL)]
        rd[(Redis)]
    end
    r1 --> us
    r2 --> ps
    us --> db
    us --> rd
    ps --> db
```

## Edge Label Patterns

```
A -->|calls| B           # solid arrow with label
A -.->|imports| B        # dashed (weak/optional dependency)
A ==>|inherits| B        # thick arrow (strong relationship)
A --o B                  # circle end (aggregation)
A --x B                  # cross end (blocked/excluded)
A <-->|bidirectional| B  # two-way
```

## Handling Scale

### For 30–60 nodes: Use subgraphs to reduce visual noise
Group low-level utilities under a single collapsed node, then offer a drill-down graph.

### For 60+ nodes: Two-tier approach
**Tier 1** — Module graph (1 node per file/package)
**Tier 2** — Function graph per module (generated on demand)

Example transition message:
> "Here's the high-level module map. Which module would you like to drill into?"

## Circular Dependency Display

```mermaid
flowchart LR
    A["moduleA"] -->|imports| B["moduleB"]
    B -->|imports| C["moduleC"]
    C -.->|⚠️ circular| A

    classDef warn stroke:#ef4444,stroke-width:2px
    class A,C warn
```

## Async / Event-Driven Patterns

```mermaid
flowchart TD
    trigger([HTTP Request]):::entry
    handler["requestHandler()"]:::async_
    worker["backgroundWorker()"]:::async_
    queue[(Message Queue)]:::external

    trigger -->|async| handler
    handler -.->|emits event| queue
    queue -.->|triggers| worker

    classDef async_ fill:#8b5cf6,color:#fff,stroke:#7c3aed
    classDef entry fill:#4f46e5,color:#fff,stroke:#3730a3
    classDef external fill:#6b7280,color:#fff,stroke:#4b5563
```

## Quick Template: Full Codebase Graph

```mermaid
flowchart TD
    entry([🚀 Entry Point]):::entry

    subgraph core ["Core Modules"]
        m1[Module A]:::module
        m2[Module B]:::module
    end

    subgraph features ["Features"]
        f1["feature_1()"]:::func
        f2["feature_2()"]:::func
    end

    ext1>External Lib]:::external
    db1[(Database)]:::external

    entry --> m1
    entry --> m2
    m1 --> f1
    m2 --> f2
    f1 --> db1
    f2 --> ext1

    classDef entry fill:#4f46e5,color:#fff,stroke:#3730a3
    classDef module fill:#0ea5e9,color:#fff,stroke:#0284c7
    classDef func fill:#10b981,color:#fff,stroke:#059669
    classDef external fill:#6b7280,color:#fff,stroke:#4b5563,stroke-dasharray:5 3
```

## Quick Template: Feature Sub-graph

```mermaid
flowchart TD
    caller([Caller / Entry]):::entry

    subgraph feature ["Feature: <name>"]
        root["rootFunction()"]:::func
        helper1["helper_a()"]:::func
        helper2["helper_b()"]:::func
        util["shared_util()"]:::func
    end

    ext>External]:::external
    db[(Storage)]:::external

    caller --> root
    root --> helper1
    root --> helper2
    helper1 --> util
    helper2 --> db
    util --> ext

    classDef entry fill:#4f46e5,color:#fff,stroke:#3730a3
    classDef func fill:#10b981,color:#fff,stroke:#059669
    classDef external fill:#6b7280,color:#fff,stroke:#4b5563,stroke-dasharray:5 3
```
