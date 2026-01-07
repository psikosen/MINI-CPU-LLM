"""
Memory management using SQLite
"""

import sqlite3
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


class MemoryStore:
    """SQLite-based memory storage"""

    def __init__(self, db_path: str = "/var/lib/voice_assistant/memory.db"):
        self.db_path = db_path
        self.local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.local.conn.row_factory = sqlite3.Row
        return self.local.conn

    def _init_db(self):
        """Initialize database schema"""
        try:
            # Create directory if needed
            import os
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            conn = self._get_connection()
            cursor = conn.cursor()

            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    user_transcript TEXT NOT NULL,
                    assistant_response TEXT NOT NULL,
                    tool_calls TEXT,
                    tool_results TEXT,
                    session_id TEXT
                )
            """)

            # Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    data TEXT,
                    session_id TEXT
                )
            """)

            # Metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    session_id TEXT
                )
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_timestamp
                ON conversations(timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                ON events(timestamp DESC)
            """)

            conn.commit()
            logger.info(f"Memory database initialized at {self.db_path}")

        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def store_conversation(self, user_transcript: str, assistant_response: str,
                          tool_calls: Optional[List[Dict]] = None,
                          tool_results: Optional[List[Dict]] = None,
                          session_id: Optional[str] = None) -> int:
        """
        Store a conversation turn

        Returns:
            ID of inserted record
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO conversations
                (timestamp, user_transcript, assistant_response, tool_calls, tool_results, session_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().timestamp(),
                user_transcript,
                assistant_response,
                json.dumps(tool_calls) if tool_calls else None,
                json.dumps(tool_results) if tool_results else None,
                session_id
            ))

            conn.commit()
            return cursor.lastrowid

        except Exception as e:
            logger.error(f"Error storing conversation: {e}")
            return -1

    def get_recent_conversations(self, limit: int = 10,
                                session_id: Optional[str] = None) -> List[Dict]:
        """Get recent conversation turns"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if session_id:
                cursor.execute("""
                    SELECT * FROM conversations
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (session_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM conversations
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting conversations: {e}")
            return []

    def store_event(self, event_type: str, data: Optional[Dict] = None,
                   session_id: Optional[str] = None):
        """Store an event"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO events (timestamp, event_type, data, session_id)
                VALUES (?, ?, ?, ?)
            """, (
                datetime.now().timestamp(),
                event_type,
                json.dumps(data) if data else None,
                session_id
            ))

            conn.commit()

        except Exception as e:
            logger.error(f"Error storing event: {e}")

    def store_metric(self, metric_name: str, metric_value: float,
                    session_id: Optional[str] = None):
        """Store a metric"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO metrics (timestamp, metric_name, metric_value, session_id)
                VALUES (?, ?, ?, ?)
            """, (
                datetime.now().timestamp(),
                metric_name,
                metric_value,
                session_id
            ))

            conn.commit()

        except Exception as e:
            logger.error(f"Error storing metric: {e}")

    def cleanup_old_data(self, max_age_days: int = 30):
        """Clean up old data"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cutoff_timestamp = (datetime.now().timestamp() -
                              (max_age_days * 24 * 60 * 60))

            cursor.execute("DELETE FROM conversations WHERE timestamp < ?",
                         (cutoff_timestamp,))
            cursor.execute("DELETE FROM events WHERE timestamp < ?",
                         (cutoff_timestamp,))
            cursor.execute("DELETE FROM metrics WHERE timestamp < ?",
                         (cutoff_timestamp,))

            conn.commit()
            logger.info(f"Cleaned up data older than {max_age_days} days")

        except Exception as e:
            logger.error(f"Error cleaning up data: {e}")

    def close(self):
        """Close database connection"""
        if hasattr(self.local, 'conn'):
            self.local.conn.close()
            delattr(self.local, 'conn')
