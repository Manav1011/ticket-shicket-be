-- name: CreateGuest :one
INSERT INTO guests (user_agent, ip_address, created_at, last_active)
VALUES ($1, $2, NOW(), NOW())
RETURNING guest_id, user_agent, ip_address, created_at, last_active, slug;

-- name: GetGuestByID :one
SELECT guest_id, user_agent, ip_address, created_at, last_active, slug
FROM guests
WHERE guest_id = $1;

-- name: UpdateGuestLastActive :one
UPDATE guests
SET last_active = NOW()
WHERE guest_id = $1
RETURNING guest_id, user_agent, ip_address, created_at, last_active, slug;

-- name: InsertGuestRefreshToken :one
INSERT INTO guest_refresh_tokens (guest_id, token, expires_at, user_agent, ip_address)
VALUES ($1, $2, $3, $4, $5)
RETURNING id, guest_id, token, expires_at, created_at, revoked, replaced_by_token, user_agent, ip_address;

-- name: GetGuestRefreshToken :one
SELECT id, guest_id, token, expires_at, created_at, revoked, replaced_by_token, user_agent, ip_address
FROM guest_refresh_tokens
WHERE token = $1;

-- name: RevokeGuestRefreshToken :exec
UPDATE guest_refresh_tokens
SET revoked = TRUE
WHERE token = $1;
