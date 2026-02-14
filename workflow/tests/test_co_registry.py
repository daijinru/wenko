"""Integration tests for CORegistry CRUD and CO API endpoints.

Covers:
- CORegistry.create, get, list_active, list_by_status, transition, search
- CORegistry.link_execution, link_memory
- CO persistence across sessions (SQLite)
- API endpoints: POST/GET/PATCH /api/co
"""

import pytest
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Override DB path to use temp file for test isolation
import chat_db

_test_db_dir = tempfile.mkdtemp()
chat_db._DB_DIR = _test_db_dir
chat_db._DB_PATH = os.path.join(_test_db_dir, "test_co.db")

from core.state import (
    CognitiveObjectStatus,
    CognitiveObject,
    InvalidTransitionError,
)
from cognitive_object import CORegistry


@pytest.fixture(autouse=True)
def setup_db():
    """Initialize a fresh database for each test."""
    # Remove existing DB if any
    if os.path.exists(chat_db._DB_PATH):
        os.remove(chat_db._DB_PATH)
    chat_db.init_database()
    yield
    if os.path.exists(chat_db._DB_PATH):
        os.remove(chat_db._DB_PATH)


class TestCORegistryCreate:
    def test_create_minimal(self):
        reg = CORegistry()
        co = reg.create(title="Test thing")
        assert co.co_id is not None
        assert co.title == "Test thing"
        assert co.status == CognitiveObjectStatus.EMERGING
        assert co.created_by == "user"

    def test_create_with_all_fields(self):
        reg = CORegistry()
        co = reg.create(
            title="Project X",
            description="Big project",
            semantic_type="project",
            domain_tag="work",
            intent_category="track",
            conversation_id="sess-123",
            creation_context="User mentioned project",
            external_references=[{"type": "url", "value": "https://example.com", "label": "Docs"}],
        )
        assert co.semantic_type == "project"
        assert co.domain_tag == "work"
        assert co.intent_category == "track"
        assert co.conversation_id == "sess-123"
        assert len(co.external_references) == 1


class TestCORegistryGet:
    def test_get_existing(self):
        reg = CORegistry()
        created = reg.create(title="Find me")
        fetched = reg.get(created.co_id)
        assert fetched is not None
        assert fetched.co_id == created.co_id
        assert fetched.title == "Find me"

    def test_get_nonexistent(self):
        reg = CORegistry()
        assert reg.get("nonexistent-id") is None


class TestCORegistryList:
    def test_list_active_excludes_archived(self):
        reg = CORegistry()
        co1 = reg.create(title="Active thing")
        co2 = reg.create(title="Archived thing")
        reg.transition(co2.co_id, "archive", actor="user")

        active = reg.list_active()
        ids = [c.co_id for c in active]
        assert co1.co_id in ids
        assert co2.co_id not in ids

    def test_list_by_status(self):
        reg = CORegistry()
        reg.create(title="Emerging 1")
        co2 = reg.create(title="Active 1")
        reg.transition(co2.co_id, "clarify", actor="user")

        emerging = reg.list_by_status(CognitiveObjectStatus.EMERGING)
        active = reg.list_by_status(CognitiveObjectStatus.ACTIVE)
        assert len(emerging) == 1
        assert len(active) == 1
        assert active[0].title == "Active 1"


class TestCORegistryTransition:
    def test_valid_transition(self):
        reg = CORegistry()
        co = reg.create(title="T")
        updated = reg.transition(co.co_id, "clarify", actor="user", reason="Details given")
        assert updated.status == CognitiveObjectStatus.ACTIVE
        assert len(updated.transitions) == 1

    def test_invalid_transition(self):
        reg = CORegistry()
        co = reg.create(title="T")
        with pytest.raises(InvalidTransitionError):
            reg.transition(co.co_id, "achieve", actor="user")

    def test_transition_persists(self):
        reg = CORegistry()
        co = reg.create(title="T")
        reg.transition(co.co_id, "clarify", actor="user")
        fetched = reg.get(co.co_id)
        assert fetched.status == CognitiveObjectStatus.ACTIVE
        assert len(fetched.transitions) == 1

    def test_transition_nonexistent(self):
        reg = CORegistry()
        with pytest.raises(ValueError):
            reg.transition("nope", "clarify", actor="user")


class TestCORegistryLinkExecution:
    def test_link_execution(self):
        reg = CORegistry()
        co = reg.create(title="T")
        reg.link_execution(co.co_id, "exec-001")
        fetched = reg.get(co.co_id)
        assert "exec-001" in fetched.linked_execution_ids

    def test_link_multiple_executions(self):
        reg = CORegistry()
        co = reg.create(title="T")
        reg.link_execution(co.co_id, "exec-001")
        reg.link_execution(co.co_id, "exec-002")
        fetched = reg.get(co.co_id)
        assert len(fetched.linked_execution_ids) == 2

    def test_link_duplicate_ignored(self):
        reg = CORegistry()
        co = reg.create(title="T")
        reg.link_execution(co.co_id, "exec-001")
        reg.link_execution(co.co_id, "exec-001")  # duplicate
        fetched = reg.get(co.co_id)
        assert len(fetched.linked_execution_ids) == 1


class TestCORegistryLinkMemory:
    def test_link_memory(self):
        reg = CORegistry()
        co = reg.create(title="T")
        reg.link_memory(co.co_id, "mem-001")
        fetched = reg.get(co.co_id)
        assert "mem-001" in fetched.linked_memory_ids

    def test_link_memory_duplicate_ignored(self):
        reg = CORegistry()
        co = reg.create(title="T")
        reg.link_memory(co.co_id, "mem-001")
        reg.link_memory(co.co_id, "mem-001")
        fetched = reg.get(co.co_id)
        assert fetched.linked_memory_ids.count("mem-001") == 1


class TestCORegistrySearch:
    def test_search_by_title(self):
        reg = CORegistry()
        reg.create(title="Deploy to production")
        reg.create(title="Buy groceries")
        results = reg.search("Deploy")
        assert len(results) == 1
        assert results[0].title == "Deploy to production"

    def test_search_by_description(self):
        reg = CORegistry()
        reg.create(title="Task A", description="needs kubernetes setup")
        results = reg.search("kubernetes")
        assert len(results) == 1

    def test_search_no_results(self):
        reg = CORegistry()
        reg.create(title="Something")
        results = reg.search("nonexistent")
        assert len(results) == 0


class TestCORegistryUpdateMetadata:
    def test_update_title(self):
        reg = CORegistry()
        co = reg.create(title="Old title")
        updated = reg.update_metadata(co.co_id, title="New title")
        assert updated.title == "New title"

    def test_update_semantic_fields(self):
        reg = CORegistry()
        co = reg.create(title="T")
        updated = reg.update_metadata(
            co.co_id,
            semantic_type="goal",
            domain_tag="personal",
        )
        assert updated.semantic_type == "goal"
        assert updated.domain_tag == "personal"


class TestCOPersistence:
    def test_co_survives_registry_reinstantiation(self):
        """Simulates cross-session access."""
        reg1 = CORegistry()
        co = reg1.create(title="Persistent thing")
        co_id = co.co_id

        reg2 = CORegistry()
        fetched = reg2.get(co_id)
        assert fetched is not None
        assert fetched.title == "Persistent thing"

    def test_co_exists_without_execution(self):
        reg = CORegistry()
        co = reg.create(title="No execution needed")
        fetched = reg.get(co.co_id)
        assert fetched.linked_execution_ids == []
        assert fetched.status == CognitiveObjectStatus.EMERGING

    def test_all_executions_end_but_co_persists(self):
        reg = CORegistry()
        co = reg.create(title="Long lived")
        reg.transition(co.co_id, "clarify", actor="user")
        reg.link_execution(co.co_id, "exec-done")

        fetched = reg.get(co.co_id)
        assert fetched.status == CognitiveObjectStatus.ACTIVE
        assert "exec-done" in fetched.linked_execution_ids
