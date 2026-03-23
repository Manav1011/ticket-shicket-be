CREATE TABLE guests (
  guest_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_agent TEXT,
  ip_address TEXT,
  created_at TIMESTAMP,
  last_active TIMESTAMP,
  slug UUID UNIQUE DEFAULT gen_random_uuid()
)
