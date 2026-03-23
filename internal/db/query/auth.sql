-- name: getUserByemail :one
SELECT id, name, email, password_hash
FROM users
WHERE email = $1 AND is_active = true;