"""CORegistry — Cognitive Object lifecycle management, CRUD, and state transitions.

Provides persistence via SQLite (chat_db tables: cognitive_objects, co_execution_links).
Does not depend on Execution or GraphRunner — COL owns Execution, not the other way around.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4

import chat_db
from core.state import (
    CognitiveObject,
    CognitiveObjectStatus,
    InvalidTransitionError,
)

logger = logging.getLogger(f"workflow.{__name__}")


def _row_to_co(row: dict) -> CognitiveObject:
    """Convert a SQLite row dict to a CognitiveObject."""
    return CognitiveObject(
        co_id=row["co_id"],
        title=row["title"],
        description=row["description"] or "",
        semantic_type=row["semantic_type"],
        domain_tag=row["domain_tag"],
        intent_category=row["intent_category"],
        status=CognitiveObjectStatus(row["status"]),
        transitions=json.loads(row["transitions"]) if row["transitions"] else [],
        external_references=json.loads(row["external_references"]) if row["external_references"] else [],
        related_co_ids=json.loads(row["related_co_ids"]) if row["related_co_ids"] else [],
        linked_memory_ids=json.loads(row["linked_memory_ids"]) if row["linked_memory_ids"] else [],
        created_by=row["created_by"],
        conversation_id=row["conversation_id"],
        creation_context=row["creation_context"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _co_to_row(co: CognitiveObject) -> Dict[str, Any]:
    """Convert a CognitiveObject to a dict suitable for SQLite insertion."""
    return {
        "co_id": co.co_id,
        "title": co.title,
        "description": co.description,
        "semantic_type": co.semantic_type,
        "domain_tag": co.domain_tag,
        "intent_category": co.intent_category,
        "status": co.status.value,
        "transitions": json.dumps(co.transitions, ensure_ascii=False),
        "external_references": json.dumps(co.external_references, ensure_ascii=False),
        "related_co_ids": json.dumps(co.related_co_ids, ensure_ascii=False),
        "linked_memory_ids": json.dumps(co.linked_memory_ids, ensure_ascii=False),
        "created_by": co.created_by,
        "conversation_id": co.conversation_id,
        "creation_context": co.creation_context,
        "created_at": co.created_at,
        "updated_at": co.updated_at,
    }


class CORegistry:
    """Cognitive Object CRUD and lifecycle management service."""

    def create(
        self,
        title: str,
        created_by: str = "user",
        description: str = "",
        semantic_type: Optional[str] = None,
        domain_tag: Optional[str] = None,
        intent_category: Optional[str] = None,
        conversation_id: Optional[str] = None,
        creation_context: Optional[str] = None,
        external_references: Optional[List[Dict[str, str]]] = None,
    ) -> CognitiveObject:
        """Create a new CognitiveObject and persist it."""
        co = CognitiveObject(
            co_id=str(uuid4()),
            title=title,
            description=description,
            semantic_type=semantic_type,
            domain_tag=domain_tag,
            intent_category=intent_category,
            created_by=created_by,
            conversation_id=conversation_id,
            creation_context=creation_context,
            external_references=external_references or [],
        )
        row = _co_to_row(co)

        with chat_db.get_connection() as conn:
            conn.execute(
                """INSERT INTO cognitive_objects
                   (co_id, title, description, semantic_type, domain_tag, intent_category,
                    status, transitions, external_references, related_co_ids,
                    linked_memory_ids, created_by, conversation_id, creation_context,
                    created_at, updated_at)
                   VALUES (:co_id, :title, :description, :semantic_type, :domain_tag,
                           :intent_category, :status, :transitions, :external_references,
                           :related_co_ids, :linked_memory_ids, :created_by,
                           :conversation_id, :creation_context, :created_at, :updated_at)""",
                row,
            )
            conn.commit()

        logger.info(f"[CORegistry] Created CO: {co.co_id[:8]} title={title!r}")
        return co

    def get(self, co_id: str) -> Optional[CognitiveObject]:
        """Get a CognitiveObject by ID."""
        with chat_db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM cognitive_objects WHERE co_id = ?", (co_id,)
            )
            row = cursor.fetchone()
            if row:
                co = _row_to_co(dict(row))
                # Load linked execution IDs from join table
                exec_cursor = conn.execute(
                    "SELECT execution_id FROM co_execution_links WHERE co_id = ? ORDER BY linked_at",
                    (co_id,),
                )
                co.linked_execution_ids = [r["execution_id"] for r in exec_cursor.fetchall()]
                return co
        return None

    def list_active(self) -> List[CognitiveObject]:
        """List all non-archived COs, ordered by updated_at descending."""
        with chat_db.get_connection() as conn:
            cursor = conn.execute(
                """SELECT * FROM cognitive_objects
                   WHERE status != 'archived'
                   ORDER BY updated_at DESC""",
            )
            results = []
            for row in cursor.fetchall():
                co = _row_to_co(dict(row))
                exec_cursor = conn.execute(
                    "SELECT execution_id FROM co_execution_links WHERE co_id = ?",
                    (co.co_id,),
                )
                co.linked_execution_ids = [r["execution_id"] for r in exec_cursor.fetchall()]
                results.append(co)
            return results

    def list_by_status(self, status: CognitiveObjectStatus) -> List[CognitiveObject]:
        """List COs by specific status."""
        with chat_db.get_connection() as conn:
            cursor = conn.execute(
                """SELECT * FROM cognitive_objects
                   WHERE status = ?
                   ORDER BY updated_at DESC""",
                (status.value,),
            )
            results = []
            for row in cursor.fetchall():
                co = _row_to_co(dict(row))
                exec_cursor = conn.execute(
                    "SELECT execution_id FROM co_execution_links WHERE co_id = ?",
                    (co.co_id,),
                )
                co.linked_execution_ids = [r["execution_id"] for r in exec_cursor.fetchall()]
                results.append(co)
            return results

    def transition(
        self, co_id: str, trigger: str, actor: str, reason: str = ""
    ) -> CognitiveObject:
        """Apply a state transition to a CO.

        Raises:
            ValueError: If CO not found.
            InvalidTransitionError: If transition is invalid.
        """
        co = self.get(co_id)
        if co is None:
            raise ValueError(f"CognitiveObject not found: {co_id}")

        co.transition(trigger, actor, reason)

        # Persist updated state
        with chat_db.get_connection() as conn:
            conn.execute(
                """UPDATE cognitive_objects
                   SET status = ?, transitions = ?, updated_at = ?
                   WHERE co_id = ?""",
                (
                    co.status.value,
                    json.dumps(co.transitions, ensure_ascii=False),
                    co.updated_at,
                    co_id,
                ),
            )
            conn.commit()

        logger.info(
            f"[CORegistry] Transition CO:{co_id[:8]} trigger={trigger} "
            f"actor={actor} -> {co.status.value}"
        )
        return co

    def link_execution(self, co_id: str, execution_id: str) -> None:
        """Link an ExecutionContract to a CO."""
        now = datetime.now().timestamp()
        with chat_db.get_connection() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO co_execution_links (co_id, execution_id, linked_at)
                   VALUES (?, ?, ?)""",
                (co_id, execution_id, now),
            )
            conn.execute(
                "UPDATE cognitive_objects SET updated_at = ? WHERE co_id = ?",
                (now, co_id),
            )
            conn.commit()
        logger.info(f"[CORegistry] Linked execution {execution_id[:8]} to CO:{co_id[:8]}")

    def link_memory(self, co_id: str, memory_id: str) -> None:
        """Link a long-term memory entry to a CO."""
        co = self.get(co_id)
        if co is None:
            raise ValueError(f"CognitiveObject not found: {co_id}")

        if memory_id not in co.linked_memory_ids:
            co.linked_memory_ids.append(memory_id)
            now = datetime.now().timestamp()
            with chat_db.get_connection() as conn:
                conn.execute(
                    """UPDATE cognitive_objects
                       SET linked_memory_ids = ?, updated_at = ?
                       WHERE co_id = ?""",
                    (json.dumps(co.linked_memory_ids), now, co_id),
                )
                conn.commit()
            logger.info(f"[CORegistry] Linked memory {memory_id} to CO:{co_id[:8]}")

    def update_metadata(
        self,
        co_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        semantic_type: Optional[str] = None,
        domain_tag: Optional[str] = None,
        intent_category: Optional[str] = None,
    ) -> CognitiveObject:
        """Update mutable metadata fields on a CO."""
        co = self.get(co_id)
        if co is None:
            raise ValueError(f"CognitiveObject not found: {co_id}")

        updates = {}
        if title is not None:
            updates["title"] = title
        if description is not None:
            updates["description"] = description
        if semantic_type is not None:
            updates["semantic_type"] = semantic_type
        if domain_tag is not None:
            updates["domain_tag"] = domain_tag
        if intent_category is not None:
            updates["intent_category"] = intent_category

        if not updates:
            return co

        now = datetime.now().timestamp()
        updates["updated_at"] = now
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [co_id]

        with chat_db.get_connection() as conn:
            conn.execute(
                f"UPDATE cognitive_objects SET {set_clause} WHERE co_id = ?",
                values,
            )
            conn.commit()

        return self.get(co_id)

    def search(self, query: str) -> List[CognitiveObject]:
        """Search COs by title/description (LIKE match)."""
        pattern = f"%{query}%"
        with chat_db.get_connection() as conn:
            cursor = conn.execute(
                """SELECT * FROM cognitive_objects
                   WHERE title LIKE ? OR description LIKE ?
                   ORDER BY updated_at DESC""",
                (pattern, pattern),
            )
            results = []
            for row in cursor.fetchall():
                co = _row_to_co(dict(row))
                exec_cursor = conn.execute(
                    "SELECT execution_id FROM co_execution_links WHERE co_id = ?",
                    (co.co_id,),
                )
                co.linked_execution_ids = [r["execution_id"] for r in exec_cursor.fetchall()]
                results.append(co)
            return results
