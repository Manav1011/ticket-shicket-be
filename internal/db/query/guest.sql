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
