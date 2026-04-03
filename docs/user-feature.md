# Graph: User Feature Call Flow
_Generated: 2026-03-25_
_Entry: internal/user/handler/user_handler.go_
_Depth: 3_

## User Feature Architecture
The User feature handles authentication (login, signup) and token refresh. It follows a clean three-tier pattern with request validation, business logic, and data persistence.

```mermaid
flowchart TD
    entry([🚀 User Routes]):::entry
    
    subgraph router ["🔀 API Routes"]
        login_route["POST /users/login"]:::func
        signup_route["POST /users/signup"]:::func
        refresh_route["POST /users/refresh"]:::func
    end
    
    subgraph handler_layer ["📋 Handler Layer"]
        uh["UserHandler"]:::class_
        login_req["model.LoginRequest"]:::class_
        signup_req["model.SignupRequest"]:::class_
        login_resp["model.LoginSuccessEnvelope"]:::class_
    end
    
    subgraph service_layer ["⚙️ Service Layer"]
        us["UserService"]:::class_
        login_svc["Login()"]:::func
        signup_svc["Signup()"]:::func
        refresh_svc["Refresh()"]:::func
        jwt_util["GenerateToken()"]:::func
        hash_util["HashPassword()"]:::func
    end
    
    subgraph repo_layer ["💾 Repository Layer"]
        ur["UserRepository"]:::class_
        get_by_email["GetUserByEmail()"]:::func
        create_user["CreateUser()"]:::func
        update_token["UpdateRefreshToken()"]:::func
    end
    
    subgraph db_layer ["🗄️ Database"]
        queries["sqlc.Queries"]:::module
        users_table[(users table)]:::external
        tokens_table[(refresh_tokens table)]:::external
    end
    
    subgraph pkg_layer ["📦 Utilities"]
        jwt["token.ParseToken()"]:::func
        hash["utils.HashPassword()"]:::func
        resp["utils.Success()"]:::func
    end
    
    entry --> login_route
    entry --> signup_route
    entry --> refresh_route
    
    login_route -->|validate| login_req
    login_route ==>|calls| uh
    signup_route ==>|calls| uh
    refresh_route ==>|calls| uh
    
    uh -->|parse request| login_req
    uh -->|calls business logic| login_svc
    uh -->|calls| signup_svc
    uh -->|calls| refresh_svc
    uh -->|serialize response| login_resp
    uh ==>|cross-file| resp
    
    login_svc -->|verify credentials| get_by_email
    login_svc ==>|cross-file| hash_util
    login_svc -->|generate token| jwt_util
    login_svc -->|persist token| update_token
    
    signup_svc -->|hash password| hash_util
    signup_svc -->|create user| create_user
    signup_svc -->|generate token| jwt_util
    
    refresh_svc -->|validate token| jwt
    refresh_svc -->|refresh token| jwt_util
    refresh_svc -->|update db| update_token
    
    get_by_email ==>|cross-file| queries
    create_user ==>|cross-file| queries
    update_token ==>|cross-file| queries
    
    queries -.->|query| users_table
    queries -.->|query| tokens_table

    classDef entry    fill:#4f46e5,color:#fff,stroke:#3730a3
    classDef module   fill:#0ea5e9,color:#fff,stroke:#0284c7
    classDef func     fill:#10b981,color:#fff,stroke:#059669
    classDef class_   fill:#f59e0b,color:#fff,stroke:#d97706
    classDef external fill:#6b7280,color:#fff,stroke:#4b5563,stroke-dasharray:5 3
```

## Request Flow

### Login Flow
1. **HTTP Request** → `POST /users/login` with email & password
2. **Handler** validates request model
3. **Service** → `GetUserByEmail()` from repository
4. **Service** → Hash incoming password and compare
5. **Service** → Generate JWT tokens
6. **Handler** → Return tokens in response

### Signup Flow
1. **HTTP Request** → `POST /users/signup`
2. **Service** → Hash password via `HashPassword()`
3. **Service** → `CreateUser()` in database
4. **Service** → Generate JWT tokens
5. **Handler** → Return tokens

### Refresh Flow
1. **HTTP Request** → `POST /users/refresh` with refresh token
2. **Service** → Validate and parse token
3. **Service** → Generate new JWT pair
4. **Repository** → Update refresh token in database
5. **Handler** → Return new tokens
