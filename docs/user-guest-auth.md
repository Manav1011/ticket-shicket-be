# User & Guest Authentication Documentation

**For Frontend Developers** — Last Updated: April 2026

---

## Overview

The system uses **JWT-based authentication** with two user types:
- **User**: Registered users with email/phone/password credentials
- **Guest**: Anonymous users identified by a device ID (UUID)

### Token Architecture

| Token Type | Lifetime | Storage | Purpose |
|------------|----------|---------|---------|
| Access Token | 1 hour | Not stored in DB (JWT) | API authentication |
| Refresh Token | 24 hours | SHA256 hash in database | Token rotation |

**Token Format:** All tokens are Bearer tokens returned in both response body and HttpOnly cookies.

---

## Configuration

```python
ACCESS_TOKEN_EXP: 3600    # 1 hour in seconds
REFRESH_TOKEN_EXP: 86400 # 24 hours in seconds
JWT_ALGORITHM: "HS256"
```

---

## Standard Response Format

All responses follow this structure:

```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": { ... },
  "message": "Optional message"
}
```

**Error Response (401 Unauthorized):**
```json
{
  "status": "ERROR",
  "code": 401,
  "data": null,
  "message": "Invalid or expired token"
}
```

---

## Guest Endpoints

Guests are identified by a `device_id` (UUID) passed via the `X-Device-ID` header.

### 1. Generate Device ID

**Endpoint:** `GET /api/guest/device`
**Auth:** None (Public)
**Purpose:** Generate a new device ID for the client to store locally.

**Response (200):**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "device_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Frontend Implementation:**
```javascript
// On first app launch
const response = await fetch('/api/guest/device');
const { device_id } = await response.json();
localStorage.setItem('device_id', device_id);
```

---

### 2. Guest Login / Register

**Endpoint:** `POST /api/guest/login`
**Auth:** None (Public)
**Headers:** `X-Device-ID: <device_id>`

**Purpose:** Login or register a guest by device ID. Creates a new guest if device ID is not found.

**Response (200):**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "guest_id": "uuid",
    "device_id": "uuid",
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
  }
}
```

**Note:** Both tokens are also set as HttpOnly cookies automatically.

---

### 3. Guest Token Refresh

**Endpoint:** `POST /api/guest/refresh`
**Auth:** None (Public)
**Purpose:** Rotate tokens using a valid refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Frontend Implementation:**
```javascript
// Before access token expires (within 1 hour), refresh
const refresh = localStorage.getItem('refresh_token');
if (refresh) {
  const response = await fetch('/api/guest/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refresh })
  });
}
```

---

### 4. Guest Self Info

**Endpoint:** `GET /api/guest/self`
**Auth:** Bearer Token (Guest)
**Purpose:** Get current authenticated guest info.

**Response (200):**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "id": "uuid",
    "device_id": "uuid",
    "is_converted": false,
    "converted_user_id": null
  }
}
```

---

### 5. Convert Guest to User

**Endpoint:** `POST /api/guest/convert`
**Auth:** Bearer Token (Guest)
**Purpose:** Convert guest account to a full user account (e.g., at checkout).

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "user@example.com",
  "phone": "+1234567890",
  "password": "securePassword123"
}
```

**Response (200):**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "user_id": "uuid",
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
  }
}
```

**Important:**
- Old guest tokens are revoked
- New user tokens are returned
- Guest's `is_converted` flag is set to `true`
- After conversion, the guest can no longer use guest endpoints

**Frontend Implementation:**
```javascript
const response = await fetch('/api/guest/convert', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    first_name, last_name, email, phone, password
  })
});
// Store new user tokens, remove guest tokens
```

---

### 6. Guest Logout

**Endpoint:** `POST /api/guest/logout`
**Auth:** Bearer Token (Guest)
**Purpose:** Logout guest and invalidate tokens.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200):**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": null,
  "message": "Logged out successfully"
}
```

---

## User Endpoints

### 1. User Sign In

**Endpoint:** `POST /api/user/sign-in`
**Auth:** None (Public)
**Purpose:** Login with email and password.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "string"
}
```

**Response (200):**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
  }
}
```

---

### 2. User Register

**Endpoint:** `POST /api/user/create`
**Auth:** None (Public)
**Purpose:** Register a new user account.

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "user@example.com",
  "phone": "+1234567890",
  "password": "securePassword123"
}
```

**Response (201):**
```json
{
  "status": "SUCCESS",
  "code": 201,
  "data": {
    "id": "uuid",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

---

### 3. User Token Refresh

**Endpoint:** `POST /api/user/refresh`
**Auth:** None (Public)
**Purpose:** Rotate tokens using a valid refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

---

### 4. User Self Info

**Endpoint:** `GET /api/user/self`
**Auth:** Bearer Token (User)
**Purpose:** Get current authenticated user info.

**Response (200):**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "id": "uuid",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

---

### 5. User Logout

**Endpoint:** `POST /api/user/logout`
**Auth:** Bearer Token (User)
**Purpose:** Logout and invalidate tokens.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200):**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": null,
  "message": "Logged out successfully"
}
```

---

### 6. Delete User Account

**Endpoint:** `DELETE /api/user/`
**Auth:** Bearer Token (User)
**Query Params:** `?user_id=uuid`

**Purpose:** Delete user account and all associated data.

**Response (200):**
```json
{
  "status": "SUCCESS",
  "code": 200,
  "data": {
    "id": "uuid",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

---

## JWT Token Structure

### Payload

```json
{
  "sub": "uuid-of-user-or-guest",
  "user_type": "user" | "guest",
  "type": "access" | "refresh",
  "exp": 1234567890,
  "iat": 1234567890
}
```

### Cookie Settings

| Setting | Value |
|---------|-------|
| `HttpOnly` | `true` |
| `Secure` | `true` |
| `SameSite` | `lax` (production) / `none` (development) |
| `Domain` | Configured via `COOKIES_DOMAIN` |

---

## Frontend Integration Guide

### 1. Guest Flow

```javascript
// Step 1: Check for existing device_id
let deviceId = localStorage.getItem('device_id');

// Step 2: If no device_id, generate one
if (!deviceId) {
  const res = await fetch('/api/guest/device');
  const { data } = await res.json();
  deviceId = data.device_id;
  localStorage.setItem('device_id', deviceId);
}

// Step 3: Guest login (automatically creates guest if new)
const loginRes = await fetch('/api/guest/login', {
  method: 'POST',
  headers: { 'X-Device-ID': deviceId }
});
const { data: tokens } = await loginRes.json();
localStorage.setItem('access_token', tokens.access_token);
localStorage.setItem('refresh_token', tokens.refresh_token);

// Step 4: Make authenticated requests
const guestRes = await fetch('/api/guest/self', {
  headers: { 'Authorization': `Bearer ${tokens.access_token}` }
});
```

### 2. Token Refresh Logic

```javascript
async function fetchWithAuth(url, options = {}) {
  let accessToken = localStorage.getItem('access_token');
  let refreshToken = localStorage.getItem('refresh_token');

  // Add auth header
  options.headers = options.headers || {};
  options.headers['Authorization'] = `Bearer ${accessToken}`;

  let response = await fetch(url, options);

  // If unauthorized, try refresh
  if (response.status === 401) {
    const refreshRes = await fetch('/api/guest/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken })
    });

    if (refreshRes.ok) {
      const newTokens = await refreshRes.json();
      localStorage.setItem('access_token', newTokens.access_token);
      localStorage.setItem('refresh_token', newTokens.refresh_token);

      // Retry original request with new token
      options.headers['Authorization'] = `Bearer ${newTokens.access_token}`;
      response = await fetch(url, options);
    }
  }

  return response;
}
```

### 3. Guest Conversion Flow

```javascript
async function convertGuest(userData) {
  const accessToken = localStorage.getItem('access_token');

  const response = await fetch('/api/guest/convert', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(userData)
  });

  if (response.ok) {
    const { data } = await response.json();
    // Store new user tokens
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    // Clear guest-specific data
    localStorage.removeItem('device_id');
    return { success: true, userId: data.user_id };
  }

  return { success: false, error: await response.json() };
}
```

### 4. User Login Flow

```javascript
async function userLogin(email, password) {
  const response = await fetch('/api/user/sign-in', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });

  if (response.ok) {
    const { data } = await response.json();
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    return { success: true };
  }

  return { success: false, error: await response.json() };
}
```

### 5. Logout Flow

```javascript
async function guestLogout() {
  const accessToken = localStorage.getItem('access_token');
  const refreshToken = localStorage.getItem('refresh_token');

  await fetch('/api/guest/logout', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ refresh_token: refreshToken })
  });

  // Clear local storage
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}
```

---

## Error Handling

| HTTP Code | Meaning | Action |
|-----------|---------|--------|
| 400 | Bad Request | Check request body format |
| 401 | Unauthorized | Token invalid/expired, try refresh or re-login |
| 403 | Forbidden | User lacks permission for this action |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Email/phone already exists (registration) |
| 500 | Server Error | Log error, show generic message |

---

## Key File Reference

| Purpose | Path |
|---------|------|
| User routes | `src/apps/user/urls.py` |
| Guest routes | `src/apps/guest/urls.py` |
| User models | `src/apps/user/models.py` |
| Guest models | `src/apps/guest/models.py` |
| Auth dependencies | `src/auth/dependencies.py` |
| JWT utilities | `src/auth/jwt.py` |
| Token blocklist | `src/auth/blocklist.py` |
| Cookie helpers | `src/utils/cookies.py` |
| Config | `src/config.py` |
