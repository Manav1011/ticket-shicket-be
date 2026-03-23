ALTER TABLE users
ADD COLUMN slug UUID UNIQUE DEFAULT gen_random_uuid();