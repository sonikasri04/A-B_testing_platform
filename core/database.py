import sqlite3
import uuid
from datetime import datetime

import os
DB_PATH = os.environ.get("DB_PATH", "data/ab_platform.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS experiments (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            metric TEXT NOT NULL,
            traffic_split REAL DEFAULT 0.5,
            status TEXT DEFAULT 'running',
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS assignments (
            user_id TEXT NOT NULL,
            experiment_id TEXT NOT NULL,
            variant TEXT NOT NULL,
            assigned_at TEXT,
            PRIMARY KEY (user_id, experiment_id)
        );

        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            experiment_id TEXT NOT NULL,
            variant TEXT NOT NULL,
            event_type TEXT NOT NULL,
            value REAL DEFAULT 1.0,
            created_at TEXT
        );
    """)

    conn.commit()
    conn.close()

def create_experiment(name: str, description: str, metric: str, traffic_split: float = 0.5) -> str:
    experiment_id = str(uuid.uuid4())[:8]
    conn = get_connection()
    conn.execute(
        "INSERT INTO experiments VALUES (?, ?, ?, ?, ?, 'running', ?)",
        (experiment_id, name, description, metric, traffic_split, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return experiment_id

def log_assignment(user_id: str, experiment_id: str, variant: str):
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO assignments VALUES (?, ?, ?, ?)",
        (user_id, experiment_id, variant, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

def log_event(user_id: str, experiment_id: str, variant: str, event_type: str, value: float = 1.0):
    conn = get_connection()
    conn.execute(
        "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), user_id, experiment_id, variant, event_type, value, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

def get_experiment(experiment_id: str) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM experiments WHERE id = ?", (experiment_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_experiments() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM experiments ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_experiment_counts(experiment_id: str, metric: str) -> dict:
    conn = get_connection()

    for variant in ["control", "treatment"]:
        conn.execute(f"""
            CREATE TEMP TABLE IF NOT EXISTS _{variant}_{experiment_id} AS
            SELECT 1 WHERE 0
        """)

    counts = {}
    for variant in ["control", "treatment"]:
        total = conn.execute(
            "SELECT COUNT(DISTINCT user_id) FROM assignments WHERE experiment_id=? AND variant=?",
            (experiment_id, variant)
        ).fetchone()[0]

        conversions = conn.execute(
            "SELECT COUNT(DISTINCT user_id) FROM events WHERE experiment_id=? AND variant=? AND event_type=?",
            (experiment_id, variant, metric)
        ).fetchone()[0]

        counts[variant] = {"total": total, "conversions": conversions}

    conn.close()
    return counts

def update_experiment_status(experiment_id: str, status: str):
    conn = get_connection()
    conn.execute("UPDATE experiments SET status=? WHERE id=?", (status, experiment_id))
    conn.commit()
    conn.close()