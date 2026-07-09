-- Database schema for resilience testing
-- Initialize database with tables and indexes

-- Create transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    amount DECIMAL(10,2) NOT NULL,
    description TEXT,
    user_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);

-- Create application state table for checkpoint metadata
CREATE TABLE IF NOT EXISTS app_state (
    id SERIAL PRIMARY KEY,
    checkpoint_id VARCHAR(255) UNIQUE NOT NULL,
    state_data JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create health metrics table
CREATE TABLE IF NOT EXISTS health_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    uptime DECIMAL(10,2),
    active_connections INTEGER,
    request_count BIGINT,
    error_count BIGINT,
    recovery_time DECIMAL(10,2)
);

-- Insert initial application state
INSERT INTO app_state (checkpoint_id, state_data)
VALUES ('initial', '{"request_count": 0, "failures_simulated": 0, "recovery_count": 0, "checkpoint_count": 0}');

-- Grant permissions (for test user)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO testuser;
GRANT USAGE, CREATE ON SCHEMA public TO testuser;
