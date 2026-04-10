"""
database.py - Secure database management with context managers
"""
import sqlite3
import os
import bcrypt
from contextlib import contextmanager

DB_PATH = os.path.join("data", "app.db")


@contextmanager
def get_db():
    """Context manager for safe database connections — auto-commit/rollback/close."""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Initialize all database tables and run migrations."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT    UNIQUE NOT NULL,
                password   TEXT    NOT NULL,
                is_admin   INTEGER DEFAULT 0,
                is_active  INTEGER DEFAULT 1,
                created_at TEXT    DEFAULT CURRENT_TIMESTAMP,
                last_login TEXT
            );

            CREATE TABLE IF NOT EXISTS login_attempts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                username     TEXT NOT NULL,
                ip_info      TEXT DEFAULT '',
                success      INTEGER DEFAULT 0,
                attempted_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER,
                username   TEXT,
                feedback   TEXT,
                rating     INTEGER DEFAULT 5,
                created_at TEXT    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS saved_dashboards (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          INTEGER NOT NULL,
                dashboard_name   TEXT    NOT NULL,
                dashboard_config TEXT    NOT NULL,
                description      TEXT    DEFAULT '',
                thumbnail        TEXT    DEFAULT '',
                created_at       TEXT    DEFAULT CURRENT_TIMESTAMP,
                updated_at       TEXT    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS user_activity (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER,
                event_type TEXT,
                event_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT NOT NULL,
                token      TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used       INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Safe migrations
        safe_migrations = [
            "ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1",
            "ALTER TABLE users ADD COLUMN last_login TEXT",
            "ALTER TABLE users ADD COLUMN security_question TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN security_answer TEXT DEFAULT ''",
            "ALTER TABLE feedback ADD COLUMN rating INTEGER DEFAULT 5",
            "ALTER TABLE saved_dashboards ADD COLUMN thumbnail TEXT DEFAULT ''",
        ]
        for sql in safe_migrations:
            try:
                conn.execute(sql)
            except Exception:
                pass

        # Create default admin account if it does not exist
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cur.fetchone():
            hashed = bcrypt.hashpw("Admin@12345".encode(), bcrypt.gensalt(rounds=12)).decode()
            conn.execute(
                "INSERT INTO users (username, password, is_admin) VALUES (?, ?, 1)",
                ("admin", hashed),
            )


def log_activity(user_id: int, event_type: str, event_data: str = ""):
    """Log a user activity event."""
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO user_activity (user_id, event_type, event_data) VALUES (?, ?, ?)",
                (user_id, event_type, event_data),
            )
    except Exception:
        pass
    