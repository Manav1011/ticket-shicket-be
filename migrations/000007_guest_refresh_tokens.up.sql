CREATE TABLE guest_refresh_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  guest_id UUID NOT NULL
    REFERENCES guests(guest_id) ON DELETE CASCADE,
  token TEXT NOT NULL UNIQUE,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  revoked BOOLEAN DEFAULT FALSE,
  replaced_by_token TEXT,
  user_agent TEXT,
  ip_address TEXT
);
