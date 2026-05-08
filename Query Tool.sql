CREATE TABLE IF NOT EXISTS simulation_metrics (
    id SERIAL PRIMARY KEY,
    step INT,
    vehicle_count INT,
    avg_wait FLOAT,
    avg_queue FLOAT,
    avg_trip_time FLOAT,
    messages_exchanged INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_messages (
    id SERIAL PRIMARY KEY,
    sender VARCHAR(80),
    receiver VARCHAR(80),
    performative VARCHAR(30),
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scenario_events (
    id SERIAL PRIMARY KEY,
    step INT,
    event_type VARCHAR(80),
    payload JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_state_snapshots (
    id SERIAL PRIMARY KEY,
    step INT,
    agent_id VARCHAR(80),
    agent_type VARCHAR(40),
    state JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
