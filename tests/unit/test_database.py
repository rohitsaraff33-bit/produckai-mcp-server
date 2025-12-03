"""Tests for database module."""

import tempfile
from pathlib import Path

import pytest

from produckai_mcp.state.database import Database
from produckai_mcp.state.sync_state import SyncStateManager


def test_database_initialization():
    """Test database initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)

        assert db_path.exists()

        # Check that tables were created
        conn = db.get_connection()
        cursor = conn.cursor()

        # Check schema_version table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'")
        assert cursor.fetchone() is not None

        # Check sync_state table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sync_state'")
        assert cursor.fetchone() is not None

        conn.close()


def test_sync_state_manager():
    """Test sync state manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        sync_state = SyncStateManager(db)

        # Test getting non-existent state
        state = sync_state.get_sync_state("slack", "C123456")
        assert state is None

        # Test creating sync state
        sync_state.update_sync_state(
            integration="slack",
            resource_id="C123456",
            resource_name="customer-feedback",
            last_timestamp="2024-01-15T12:00:00Z",
            new_items=100,
            status="success",
        )

        # Test getting state
        state = sync_state.get_sync_state("slack", "C123456")
        assert state is not None
        assert state["integration"] == "slack"
        assert state["resource_id"] == "C123456"
        assert state["resource_name"] == "customer-feedback"
        assert state["total_items_synced"] == 100
        assert state["last_sync_status"] == "success"

        # Test updating state
        sync_state.update_sync_state(
            integration="slack",
            resource_id="C123456",
            last_timestamp="2024-01-16T12:00:00Z",
            new_items=50,
            status="success",
        )

        state = sync_state.get_sync_state("slack", "C123456")
        assert state["total_items_synced"] == 150  # 100 + 50

        # Test should_full_sync
        assert not sync_state.should_full_sync("slack", "C123456")  # Just synced
        assert sync_state.should_full_sync("slack", "C999999")  # Never synced


def test_sync_summary():
    """Test sync summary generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        sync_state = SyncStateManager(db)

        # Add multiple sync states
        sync_state.update_sync_state(
            "slack", "C123", resource_name="channel1",
            last_timestamp="2024-01-15T12:00:00Z",
            new_items=100, status="success"
        )
        sync_state.update_sync_state(
            "slack", "C456", resource_name="channel2",
            last_timestamp="2024-01-15T12:00:00Z",
            new_items=50, status="success"
        )
        sync_state.update_sync_state(
            "gdrive", "F789", resource_name="folder1",
            last_timestamp="2024-01-15T12:00:00Z",
            new_items=200, status="success"
        )

        summary = sync_state.get_sync_summary()

        assert summary["total_resources"] == 3
        assert summary["total_items_synced"] == 350
        assert "slack" in summary["by_integration"]
        assert "gdrive" in summary["by_integration"]
        assert summary["by_integration"]["slack"]["resource_count"] == 2
        assert summary["by_integration"]["slack"]["total_items"] == 150
        assert summary["by_integration"]["gdrive"]["resource_count"] == 1
        assert summary["by_integration"]["gdrive"]["total_items"] == 200
