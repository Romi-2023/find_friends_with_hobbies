-- =========================
-- SOCIAL CORE MIGRATION
-- Adds: last_activity + follows table
-- =========================

ALTER TABLE users
ADD COLUMN IF NOT EXISTS last_activity TIMESTAMPTZ DEFAULT NOW();

CREATE TABLE IF NOT EXISTS follows (
    follower TEXT NOT NULL,
    following TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (follower, following),
    CONSTRAINT fk_follower
        FOREIGN KEY (follower) REFERENCES users(username)
        ON DELETE CASCADE,
    CONSTRAINT fk_following
        FOREIGN KEY (following) REFERENCES users(username)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_follows_follower ON follows(follower);
CREATE INDEX IF NOT EXISTS idx_follows_following ON follows(following);
