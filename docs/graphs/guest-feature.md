# Graph: Guest Feature Call Flow
_Generated: 2026-03-25_
_Entry: internal/guest/handler/guest_handler.go_
_Depth: 3_

## Guest Feature Architecture
The Guest feature enables anonymous user access without email/password. Guests are identified by user agent and IP address, and receive JWT tokens for subsequent authenticated requests.

```mermaid
flowchart TD
    entry([🚀 Guest Routes]):::entry
    
    subgraph router ["🔀 API Routes"]
        register_route["POST /guests/register"]:::func
        refresh_route["POST /guests/refresh"]:::func
    end
    
    subgraph handler_layer ["📋 Handler Layer"]
        gh["GuestHandler"]:::class_
        register_req["model.GuestRegisterRequest"]:::class_
        register_resp["model.GuestRegisterSuccessEnvelope"]:::class_
    end
    
    subgraph service_layer ["⚙️ Service Layer"]
        gs["GuestService"]:::class_
        register_svc["Register()"]:::func
        refresh_svc["Refresh()"]:::func
        jwt_util["GenerateToken()"]:::func
        get_or_create["GetOrCreateGuest()"]:::func
    end
    
    subgraph repo_layer ["💾 Repository Layer"]
        gr["GuestRepository"]:::class_
        find_by_sig["FindBySignature()"]:::func
        create_guest["CreateGuest()"]:::func
        update_token["UpdateRefreshToken()"]:::func
        save_token["SaveGuestRefreshToken()"]:::func
    end
    
    subgraph db_layer ["🗄️ Database"]
        queries["sqlc.Queries"]:::module
        guests_table[(guests table)]:::external
        guest_tokens_table[(guest_refresh_tokens table)]:::external
    end
    
    subgraph pkg_layer ["📦 Utilities"]
        jwt["token.ParseToken()"]:::func
        resp["utils.Success()"]:::func
    end
    
    entry --> register_route
    entry --> refresh_route
    
    register_route -->|extract user agent + IP| register_req
    register_route ==>|calls| gh
    refresh_route ==>|calls| gh
    
    gh -->|parse request| register_req
    gh -->|calls business logic| register_svc
    gh -->|calls| refresh_svc
    gh -->|serialize response| register_resp
    gh ==>|cross-file| resp
    
    register_svc -->|compute signature| get_or_create
    get_or_create -->|lookup or create| find_by_sig
    find_by_sig -.->|cache lookup| guests_table
    get_or_create -->|fallback: create new| create_guest
    
    register_svc -->|generate tokens| jwt_util
    register_svc -->|persist token| save_token
    save_token ==>|cross-file| update_token
    
    refresh_svc -->|validate token| jwt
    refresh_svc -->|lookup guest| find_by_sig
    refresh_svc -->|generate new token| jwt_util
    refresh_svc -->|persist new token| update_token
    
    find_by_sig ==>|cross-file| queries
    create_guest ==>|cross-file| queries
    update_token ==>|cross-file| queries
    save_token ==>|cross-file| queries
    
    queries -.->|query| guests_table
    queries -.->|query| guest_tokens_table

    classDef entry    fill:#4f46e5,color:#fff,stroke:#3730a3
    classDef module   fill:#0ea5e9,color:#fff,stroke:#0284c7
    classDef func     fill:#10b981,color:#fff,stroke:#059669
    classDef class_   fill:#f59e0b,color:#fff,stroke:#d97706
    classDef external fill:#6b7280,color:#fff,stroke:#4b5563,stroke-dasharray:5 3
```

## Request Flow

### Guest Registration Flow
1. **HTTP Request** → `POST /guests/register`
2. **Handler** extracts `User-Agent` and client IP from request
3. **Service** → Compute signature from user agent + IP
4. **Repository** → Check if guest already exists via signature
   - If exists: return existing guest data
   - If not: create new guest record
5. **Service** → Generate JWT tokens (access + refresh)
6. **Repository** → Save guest refresh token
7. **Handler** → Return tokens in response

### Guest Token Refresh Flow
1. **HTTP Request** → `POST /guests/refresh` with refresh token
2. **Service** → Validate and parse refresh token
3. **Repository** → Lookup guest by ID from token claims
4. **Service** → Generate new JWT token pair
5. **Repository** → Update refresh token in database
6. **Handler** → Return new tokens

## Key Differences from User Feature

| Aspect | User | Guest |
|--------|------|-------|
| **Identification** | Email/Password | User Agent + IP Signature |
| **Database Tables** | `users`, `refresh_tokens` | `guests`, `guest_refresh_tokens` |
| **Signup** | Credential validation required | Anonymous, automatic on first request |
| **Persistence** | User records stored indefinitely | Guest records based on signature |
