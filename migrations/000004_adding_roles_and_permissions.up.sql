CREATE TYPE role_type as ENUM ('admin', 'customer', 'guest_user');
CREATE TABLE roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name role_type UNIQUE,
  description TEXT,
  slug UUID UNIQUE DEFAULT gen_random_uuid()
);


CREATE TYPE admin_permission as ENUM ('view', 'edit', 'full_access');

CREATE TABLE permissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name admin_permission UNIQUE,
  description TEXT,
  slug UUID UNIQUE DEFAULT gen_random_uuid()
);