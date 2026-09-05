"""
Database module for Agentic Payment Recovery System.

Provides SQLite connection management, schema initialization, and
database utility functions.
"""

import sqlite3
from pathlib import Path


def get_connection() -> sqlite3.Connection:
    """
    Get a SQLite connection with row factory and foreign keys enabled.

    Returns:
        sqlite3.Connection: Configured database connection
    """
    db_path = Path(__file__).parent.parent / "data" / "recovery.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """
    Initialize the database schema with all required tables.

    Creates tables: customers, payments, recovery_attempts, audit_log
    with appropriate indexes and foreign key constraints.
    Idempotent - safe to call multiple times.
    """
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS customers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                tenure_days INTEGER NOT NULL,
                total_payments INTEGER NOT NULL,
                lifetime_value REAL NOT NULL,
                do_not_contact BOOLEAN NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS payments (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD',
                subscription_plan TEXT NOT NULL,
                status TEXT NOT NULL,
                failure_reason TEXT,
                failure_timestamp TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS recovery_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_id TEXT NOT NULL,
                attempt_number INTEGER NOT NULL,
                attempted_at TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                outcome TEXT,
                completed_at TEXT,
                FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                payment_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                failure_reason TEXT,
                payment_amount REAL,
                customer_tenure_days INTEGER,
                prior_failures_count INTEGER,
                stopping_rule_triggered TEXT,
                escalation_rule_triggered TEXT,
                llm_prompt TEXT,
                llm_response TEXT,
                llm_model_used TEXT DEFAULT 'gemini-3.6-flash',
                llm_tokens_used INTEGER,
                parsed_action TEXT,
                parsed_reasoning TEXT,
                llm_confidence REAL,
                final_decision TEXT NOT NULL,
                final_outcome TEXT,
                human_reviewed BOOLEAN DEFAULT 0,
                human_reviewer_notes TEXT,
                FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_payments_customer_id ON payments(customer_id);
            CREATE INDEX IF NOT EXISTS idx_recovery_attempts_payment_id ON recovery_attempts(payment_id);
            CREATE INDEX IF NOT EXISTS idx_audit_log_payment_id ON audit_log(payment_id);
        """)
        conn.commit()
    finally:
        conn.close()