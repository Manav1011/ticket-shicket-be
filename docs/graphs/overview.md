# Graph: Full Backend Architecture Overview
_Generated: 2026-03-25_
_Entry: cmd/server/main.go_
_Depth: 4_

## Architecture Overview
This Go backend uses a layered architecture with clear separation of concerns. The application follows a modular pattern with User and Guest features operating independently through their own handler → service → repository stacks.

```mermaid
flowchart TD
    entry([🚀 main.go]):::entry
    
    subgraph init ["⚙️ Initialization"]
        config["LoadConfig()"]:::func
        db["NewDB()"]:::func
        queries["sqlc.New()"]:::func
    end
    
    subgraph framework ["🔧 Framework Setup"]
        gin["gin.Default()"]:::external
        cors["CorsMiddleware()"]:::func
        swagger["Swagger()"]:::external
    end
    
    subgraph user_feature ["👤 User Feature"]
        ureg["UserRepository"]:::class_
        usvc["UserService"]:::class_
        uh["UserHandler"]:::class_
    end
    
    subgraph guest_feature ["🧑 Guest Feature"]
        grep["GuestRepository"]:::class_
        gsvc["GuestService"]:::class_
        gh["GuestHandler"]:::class_
    end
    
    subgraph middleware ["🛡️ Middleware Layer"]
        cors_mw["CorsMiddleware()"]:::func
        auth_mw["GuestAuthMiddleware()"]:::func
        rbac_mw["RBAC Middleware"]:::func
    end
    
    subgraph pkg_layer ["📦 Package Layer"]
        jwt["token.JWT"]:::func
        utils["utils.Response"]:::func
        hash["utils.Hash"]:::func
    end
    
    subgraph db_layer ["💾 Data Layer"]
        sqlc_gen["sqlc Generated"]:::module
        db_conn[(PostgreSQL)]:::external
    end
    
    entry -->|1. Load config| config
    entry -->|2. Init DB| db
    entry -->|3. Create queries| queries
    entry -->|4. Setup Gin| gin
    
    entry -->|5. Wire User| ureg
    ureg ==>|cross-file| queries
    usvc ==>|uses| ureg
    uh ==>|uses| usvc
    
    entry -->|6. Wire Guest| grep
    grep ==>|cross-file| queries
    gsvc ==>|uses| grep
    gh ==>|uses| gsvc
    
    entry -->|7. Add middleware| cors_mw
    gin -->|mounts| uh
    gin -->|mounts| gh
    
    usvc ==>|cross-file| jwt
    usvc ==>|cross-file| hash
    gsvc ==>|cross-file| jwt
    uh ==>|cross-file| utils
    gh ==>|cross-file| utils
    
    queries ==>|generated from| sqlc_gen
    sqlc_gen ==>|connects to| db_conn

    classDef entry    fill:#4f46e5,color:#fff,stroke:#3730a3
    classDef module   fill:#0ea5e9,color:#fff,stroke:#0284c7
    classDef func     fill:#10b981,color:#fff,stroke:#059669
    classDef class_   fill:#f59e0b,color:#fff,stroke:#d97706
    classDef external fill:#6b7280,color:#fff,stroke:#4b5563,stroke-dasharray:5 3
```

## Key Observations

- **Layered Architecture**: Each feature (User, Guest) follows Handler → Service → Repository layers
- **Cross-file Dependencies**: Services and handlers depend on utilities in `pkg/` (jwt, hash, response)
- **Database Abstraction**: Using sqlc for type-safe database queries
- **Middleware Pipeline**: CORS and authentication middleware applied at Gin level
- **Framework**: Gin web framework for HTTP routing
