-- name: GetUserByEmail :one
SELECT id, name, email, password_hash
FROM users
WHERE email = $1 AND is_active = true;

-- name: GetUserByID :one
SELECT id, name, email, password_hash
FROM users
WHERE id = $1 AND is_active = true;

-- name: CreateUser :one
INSERT INTO users (name, email, password_hash, is_active)
VALUES ($1, $2, $3, true)
RETURNING id, name, email, password_hash;

-- name: InsertRefreshToken :one
INSERT INTO refresh_tokens (user_id, token, expires_at)
VALUES ($1, $2, $3)
RETURNING id, user_id, token, expires_at, created_at, revoked;


-- name: GetRefreshToken :one
SELECT id, revoked
FROM refresh_tokens
WHERE token = $1;

-- name: RevokeRefreshToken :exec
UPDATE refresh_tokens
SET revoked = true
WHERE token = $1;