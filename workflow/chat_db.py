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
_DB_VERSION = 5

# Default settings configuration
_DEFAULT_SETTINGS = {
    # LLM 配置
    "llm.api_base": ("https://api.openai.com/v1", "string", "LLM API 端点"),
    "llm.api_key": ("", "string", "API 密钥"),
    "llm.model": ("gpt-4o-mini", "string", "对话模型"),
    "llm.system_prompt": ("你是一个友好的 AI 助手。", "string", "系统提示词"),
    "llm.max_tokens": ("1024", "number", "最大 token 数"),
    "llm.temperature": ("0.7", "number", "采样温度"),
    "llm.vision_model": ("volcengine/doubao-embedding-vision", "string", "视觉模型"),
    # 系统开关
    "system.memory_emotion_enabled": ("true", "boolean", "启用记忆和情绪系统"),
    "system.hitl_enabled": ("true", "boolean", "启用 HITL (人机交互) 系统"),
    "system.intent_recognition_enabled": ("true", "boolean", "启用意图识别系统"),
    "system.emotion_confidence_threshold": ("0.5", "number", "情绪识别置信度阈值"),
    # 提醒设置
    "system.reminder_window_enabled": ("true", "boolean", "启用弹窗提醒"),
    "system.os_notification_enabled": ("true", "boolean", "启用系统通知"),
}


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

        # ============ V3: Plan fields in long_term_memory ============
        # Note: V3 originally created a separate plans table, but V4 merged plans
        # into long_term_memory. For new databases, we skip V3 and go directly to V4.

        # ============ V4: Plan fields in long_term_memory ============
        if current_version < 4:
            # Add plan-specific columns to long_term_memory table
            try:
                conn.execute("ALTER TABLE long_term_memory ADD COLUMN target_time TIMESTAMP")
            except sqlite3.OperationalError:
                pass  # Column already exists

            try:
                conn.execute("ALTER TABLE long_term_memory ADD COLUMN reminder_offset_minutes INTEGER DEFAULT 10")
            except sqlite3.OperationalError:
                pass

            try:
                conn.execute("ALTER TABLE long_term_memory ADD COLUMN repeat_type TEXT DEFAULT 'none'")
            except sqlite3.OperationalError:
                pass

            try:
                conn.execute("ALTER TABLE long_term_memory ADD COLUMN plan_status TEXT DEFAULT 'pending'")
            except sqlite3.OperationalError:
                pass

            try:
                conn.execute("ALTER TABLE long_term_memory ADD COLUMN snooze_until TIMESTAMP")
            except sqlite3.OperationalError:
                pass

            # Create index for plan queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ltm_target_time
                ON long_term_memory(target_time)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ltm_plan_status
                ON long_term_memory(plan_status)
            """)

        # ============ V5: App Settings ============
        if current_version < 5:
            # Create app_settings table for configuration storage
            conn.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    value_type TEXT DEFAULT 'string',
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Initialize default settings
            _initialize_default_settings(conn)

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


# ============ Settings Operations ============

def _initialize_default_settings(conn: sqlite3.Connection) -> None:
    """Initialize default settings in the database.

    Also attempts to migrate from chat_config.json if it exists.
    """
    now = datetime.utcnow().isoformat()

    # Check if chat_config.json exists and migrate from it
    config_path = os.path.join(os.path.dirname(__file__), "chat_config.json")
    migrated_values = {}

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            # Map JSON keys to setting keys
            key_mapping = {
                "api_base": "llm.api_base",
                "api_key": "llm.api_key",
                "model": "llm.model",
                "system_prompt": "llm.system_prompt",
                "max_tokens": "llm.max_tokens",
                "temperature": "llm.temperature",
                "vision_model": "llm.vision_model",
            }

            for json_key, setting_key in key_mapping.items():
                if json_key in config_data:
                    migrated_values[setting_key] = str(config_data[json_key])
        except (json.JSONDecodeError, IOError):
            pass  # Ignore errors, use defaults

    # Insert default settings (with migrated values if available)
    for key, (default_value, value_type, description) in _DEFAULT_SETTINGS.items():
        value = migrated_values.get(key, default_value)
        conn.execute(
            """INSERT OR IGNORE INTO app_settings
               (key, value, value_type, description, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (key, value, value_type, description, now, now)
        )


def get_setting(key: str) -> Optional[Any]:
    """Get a single setting value by key.

    Args:
        key: Setting key (e.g., 'llm.api_key')

    Returns:
        Setting value with proper type conversion, or None if not found.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT value, value_type FROM app_settings WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        if row:
            return _convert_setting_value(row["value"], row["value_type"])
    return None


def _convert_setting_value(value: str, value_type: str) -> Any:
    """Convert setting value from string to proper type."""
    if value_type == "number":
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value
    elif value_type == "boolean":
        return value.lower() in ("true", "1", "yes")
    elif value_type == "json":
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def set_setting(key: str, value: Any, value_type: Optional[str] = None) -> bool:
    """Set a single setting value.

    Args:
        key: Setting key
        value: New value (will be converted to string for storage)
        value_type: Optional type hint ('string', 'number', 'boolean', 'json')

    Returns:
        True if setting was updated/inserted successfully.
    """
    now = datetime.utcnow().isoformat()
    str_value = str(value) if not isinstance(value, str) else value

    # Infer value_type if not provided
    if value_type is None:
        if isinstance(value, bool):
            value_type = "boolean"
            str_value = "true" if value else "false"
        elif isinstance(value, (int, float)):
            value_type = "number"
        elif isinstance(value, (dict, list)):
            value_type = "json"
            str_value = json.dumps(value)
        else:
            value_type = "string"

    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO app_settings (key, value, value_type, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET
                   value = excluded.value,
                   value_type = excluded.value_type,
                   updated_at = excluded.updated_at""",
            (key, str_value, value_type, now)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_all_settings() -> Dict[str, Any]:
    """Get all settings as a dictionary.

    Returns:
        Dictionary mapping setting keys to their typed values.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT key, value, value_type FROM app_settings"
        )
        return {
            row["key"]: _convert_setting_value(row["value"], row["value_type"])
            for row in cursor.fetchall()
        }


def get_all_settings_with_metadata() -> List[Dict[str, Any]]:
    """Get all settings with full metadata.

    Returns:
        List of setting dicts with key, value, value_type, description, timestamps.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """SELECT key, value, value_type, description, created_at, updated_at
               FROM app_settings ORDER BY key"""
        )
        result = []
        for row in cursor.fetchall():
            item = dict(row)
            item["typed_value"] = _convert_setting_value(
                row["value"], row["value_type"]
            )
            result.append(item)
        return result


def set_settings(settings_dict: Dict[str, Any]) -> int:
    """Batch update multiple settings.

    Args:
        settings_dict: Dictionary of key-value pairs to update.

    Returns:
        Number of settings updated.
    """
    count = 0
    for key, value in settings_dict.items():
        if set_setting(key, value):
            count += 1
    return count


def reset_settings() -> int:
    """Reset all settings to default values.

    Returns:
        Number of settings reset.
    """
    now = datetime.utcnow().isoformat()
    count = 0

    with get_connection() as conn:
        for key, (default_value, value_type, description) in _DEFAULT_SETTINGS.items():
            cursor = conn.execute(
                """UPDATE app_settings
                   SET value = ?, value_type = ?, description = ?, updated_at = ?
                   WHERE key = ?""",
                (default_value, value_type, description, now, key)
            )
            count += cursor.rowcount
        conn.commit()

    return count


def delete_setting(key: str) -> bool:
    """Delete a setting.

    Args:
        key: Setting key to delete.

    Returns:
        True if setting was deleted, False if not found.
    """
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM app_settings WHERE key = ?", (key,))
        conn.commit()
        return cursor.rowcount > 0
