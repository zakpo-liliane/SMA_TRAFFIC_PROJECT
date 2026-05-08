import os
import json

import psycopg2


class PostgresLogger:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.enabled = False
        try:
            self.conn = psycopg2.connect(
                dbname=os.getenv("TRAFFIC_DB_NAME", "traffic_sma"),
                user=os.getenv("TRAFFIC_DB_USER", "postgres"),
                password=os.getenv("TRAFFIC_DB_PASSWORD", "postgres"),
                host=os.getenv("TRAFFIC_DB_HOST", "localhost"),
                port=os.getenv("TRAFFIC_DB_PORT", "5432"),
            )
            self.cursor = self.conn.cursor()
            self._ensure_tables()
            self.enabled = True
        except Exception:
            self.enabled = False

    def _ensure_tables(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS simulation_metrics (
                id SERIAL PRIMARY KEY,
                step INT,
                vehicle_count INT,
                avg_wait FLOAT,
                avg_queue FLOAT,
                avg_trip_time FLOAT,
                messages_exchanged INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_messages (
                id SERIAL PRIMARY KEY,
                sender VARCHAR(80),
                receiver VARCHAR(80),
                performative VARCHAR(30),
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scenario_events (
                id SERIAL PRIMARY KEY,
                step INT,
                event_type VARCHAR(80),
                payload JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_state_snapshots (
                id SERIAL PRIMARY KEY,
                step INT,
                agent_id VARCHAR(80),
                agent_type VARCHAR(40),
                state JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.commit()

    def log_metrics(self, step, vehicle_count, avg_wait, avg_queue, avg_trip_time, messages_exchanged):
        if not self.enabled:
            return
        self.cursor.execute(
            """
            INSERT INTO simulation_metrics(step, vehicle_count, avg_wait, avg_queue, avg_trip_time, messages_exchanged)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (step, vehicle_count, avg_wait, avg_queue, avg_trip_time, messages_exchanged),
        )
        self.conn.commit()

    def log_message(self, sender, receiver, performative, content):
        if not self.enabled:
            return
        self.cursor.execute(
            """
            INSERT INTO agent_messages(sender, receiver, performative, content)
            VALUES (%s, %s, %s, %s)
            """,
            (sender, receiver, performative, json.dumps(content)),
        )
        self.conn.commit()

    def log_event(self, step, event_type, payload):
        if not self.enabled:
            return
        self.cursor.execute(
            """
            INSERT INTO scenario_events(step, event_type, payload)
            VALUES (%s, %s, %s::jsonb)
            """,
            (step, event_type, json.dumps(payload)),
        )
        self.conn.commit()

    def log_agent_state(self, step, agent_id, agent_type, state):
        if not self.enabled:
            return
        self.cursor.execute(
            """
            INSERT INTO agent_state_snapshots(step, agent_id, agent_type, state)
            VALUES (%s, %s, %s, %s::jsonb)
            """,
            (step, agent_id, agent_type, json.dumps(state)),
        )
        self.conn.commit()

    def close(self):
        if self.cursor is not None:
            self.cursor.close()
        if self.conn is not None:
            self.conn.close()
