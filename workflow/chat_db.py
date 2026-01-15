"""Chat History SQLite Database Module

Provides persistent storage for Live2D AI chat conversations.
Database file is stored at workflow/data/chat_history.db (relative path for portability).

Extended with Memory and Emotion System (v2):
- working_memory: Session-scoped working memory
- long_term_memory: Cross-session persistent memories
- memory_fts: FTS5 full-text search index for memories
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager


# Database path (relative to this file's directory)
_DB_DIR = os.path.join(os.path.dirname(__file__), "data")
_DB_PATH = os.path.join(_DB_DIR, "chat_history.db")

# Database schema version for migrations
_DB_VERSION = 2


@contextmanager
def get_connection():
    """Get database connection with WAL mode enabled."""
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def _get_db_version(conn: sqlite3.Connection) -> int:
    """Get current database schema version."""
    try:
        cursor = conn.execute("SELECT version FROM schema_version LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0


def _set_db_version(conn: sqlite3.Connection, version: int) -> None:
    """Set database schema version."""
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER)")
    conn.execute("DELETE FROM schema_version")
    conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))


def init_database() -> None:
    """Initialize database: create data directory and tables if not exist."""
    # Create data directory if not exists
    if not os.path.exists(_DB_DIR):
        os.makedirs(_DB_DIR)

    with get_connection() as conn:
        # Enable WAL mode for better concurrent performance
        conn.execute("PRAGMA journal_mode=WAL")

        current_version = _get_db_version(conn)

        # ============ V1: Original schema ============
        if current_version < 1:
            # Create sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    title TEXT
                )
            """)

            # Create messages table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)

            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_updated
                ON sessions(updated_at DESC)
            """)

        # ============ V2: Memory and Emotion System ============
        if current_version < 2:
            # Create working_memory table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS working_memory (
                    session_id TEXT PRIMARY KEY,
                    current_topic TEXT,
                    context_variables TEXT DEFAULT '{}',
                    turn_count INTEGER DEFAULT 0,
                    last_emotion TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create long_term_memory table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS long_term_memory (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    source TEXT DEFAULT 'inferred',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0
                )
            """)

            # Create indexes for long_term_memory
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ltm_category
                ON long_term_memory(category)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ltm_key
                ON long_term_memory(key)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ltm_last_accessed
                ON long_term_memory(last_accessed DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ltm_confidence
                ON long_term_memory(confidence DESC)
            """)

            # Create FTS5 virtual table for full-text search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    memory_id,
                    key,
                    value_text,
                    category,
                    tokenize='unicode61 remove_diacritics 2'
                )
            """)

            # Create triggers to sync FTS5 with long_term_memory
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memory_fts_insert
                AFTER INSERT ON long_term_memory
                BEGIN
                    INSERT INTO memory_fts(memory_id, key, value_text, category)
                    VALUES (NEW.id, NEW.key, NEW.value, NEW.category);
                END
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memory_fts_delete
                AFTER DELETE ON long_term_memory
                BEGIN
                    DELETE FROM memory_fts WHERE memory_id = OLD.id;
                END
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memory_fts_update
                AFTER UPDATE ON long_term_memory
                BEGIN
                    DELETE FROM memory_fts WHERE memory_id = OLD.id;
                    INSERT INTO memory_fts(memory_id, key, value_text, category)
                    VALUES (NEW.id, NEW.key, NEW.value, NEW.category);
                END
            """)

        # Update schema version
        if current_version < _DB_VERSION:
            _set_db_version(conn, _DB_VERSION)

        conn.commit()


# ============ Session Operations ============

def create_session(session_id: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
    """Create a new chat session.

    Args:
        session_id: Optional UUID string. If not provided, one will be generated.
        title: Optional session title.

    Returns:
        Session dict with id, created_at, updated_at, title.
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    now = datetime.utcnow().isoformat()

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (id, created_at, updated_at, title) VALUES (?, ?, ?, ?)",
            (session_id, now, now, title)
        )
        conn.commit()

    return {
        "id": session_id,
        "created_at": now,
        "updated_at": now,
        "title": title
    }


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session by ID.

    Returns:
        Session dict or None if not found.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT id, created_at, updated_at, title FROM sessions WHERE id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None


def get_or_create_session(session_id: str, title: Optional[str] = None) -> Dict[str, Any]:
    """Get session by ID or create if not exists.

    Args:
        session_id: Session UUID string.
        title: Title to use if creating new session.

    Returns:
        Session dict.
    """
    session = get_session(session_id)
    if session:
        return session
    return create_session(session_id, title)


def list_sessions(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """List all sessions ordered by updated_at descending.

    Returns:
        List of session dicts with message_count included.
    """
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT
                s.id,
                s.created_at,
                s.updated_at,
                s.title,
                COUNT(m.id) as message_count
            FROM sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))

        return [dict(row) for row in cursor.fetchall()]


def update_session(session_id: str, title: Optional[str] = None) -> bool:
    """Update session title and updated_at timestamp.

    Returns:
        True if session was updated, False if not found.
    """
    now = datetime.utcnow().isoformat()

    with get_connection() as conn:
        if title is not None:
            cursor = conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title, now, session_id)
            )
        else:
            cursor = conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id)
            )
        conn.commit()
        return cursor.rowcount > 0


def delete_session(session_id: str) -> bool:
    """Delete session and all its messages (cascade).

    Returns:
        True if session was deleted, False if not found.
    """
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        return cursor.rowcount > 0


def delete_all_sessions() -> int:
    """Delete all sessions and messages.

    Returns:
        Number of sessions deleted.
    """
    with get_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM sessions")
        count = cursor.fetchone()[0]
        conn.execute("DELETE FROM sessions")
        conn.commit()
        return count


# ============ Message Operations ============

def add_message(session_id: str, role: str, content: str) -> Dict[str, Any]:
    """Add a message to a session.

    If session doesn't exist, it will be created first.
    Session's updated_at will be updated.
    If this is the first user message, it will be used as session title.

    Args:
        session_id: Session UUID string.
        role: 'user' or 'assistant'.
        content: Message content.

    Returns:
        Message dict with id, session_id, role, content, created_at.
    """
    now = datetime.utcnow().isoformat()

    with get_connection() as conn:
        # Check if session exists
        cursor = conn.execute("SELECT id, title FROM sessions WHERE id = ?", (session_id,))
        session = cursor.fetchone()

        if not session:
            # Create session with first user message as title
            title = content[:50] + "..." if len(content) > 50 else content if role == "user" else None
            conn.execute(
                "INSERT INTO sessions (id, created_at, updated_at, title) VALUES (?, ?, ?, ?)",
                (session_id, now, now, title)
            )
        else:
            # Update session's updated_at
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id)
            )
            # If no title and this is user message, set title
            if not session["title"] and role == "user":
                title = content[:50] + "..." if len(content) > 50 else content
                conn.execute(
                    "UPDATE sessions SET title = ? WHERE id = ?",
                    (title, session_id)
                )

        # Insert message
        cursor = conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, now)
        )
        message_id = cursor.lastrowid
        conn.commit()

    return {
        "id": message_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "created_at": now
    }


def get_messages_by_session(session_id: str) -> List[Dict[str, Any]]:
    """Get all messages in a session ordered by created_at ascending.

    Returns:
        List of message dicts.
    """
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT id, session_id, role, content, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at ASC
        """, (session_id,))

        return [dict(row) for row in cursor.fetchall()]


def get_session_with_messages(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session with all its messages.

    Returns:
        Dict with session info and messages list, or None if session not found.
    """
    session = get_session(session_id)
    if not session:
        return None

    messages = get_messages_by_session(session_id)

    return {
        "session": session,
        "messages": messages
    }
