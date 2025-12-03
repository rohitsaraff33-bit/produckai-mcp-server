"""Tests for configuration module."""

import tempfile
from pathlib import Path

import pytest

from produckai_mcp.config import Config, create_default_config


def test_default_config():
    """Test creating default configuration."""
    config = create_default_config()

    assert config.backend.url == "http://localhost:8000"
    assert config.backend.timeout == 60
    assert config.server.name == "produckai"
    assert config.ai.provider == "anthropic"


def test_config_save_and_load():
    """Test saving and loading configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        # Create and save config
        config = create_default_config()
        config.backend.url = "http://test:9000"
        config.save_to_file(config_path)

        # Load config
        loaded_config = Config.load_from_file(config_path)

        assert loaded_config.backend.url == "http://test:9000"
        assert loaded_config.server.name == "produckai"


def test_config_get_state_db_path():
    """Test getting state database path."""
    config = create_default_config()
    db_path = config.get_state_db_path()

    assert db_path.name == "state.db"
    assert db_path.parent.name == ".produckai"


def test_config_integration_defaults():
    """Test integration default configuration."""
    config = create_default_config()

    assert "slack" in config.integrations
    assert "gdrive" in config.integrations
    assert "jira" in config.integrations
    assert "zoom" in config.integrations

    assert config.integrations["slack"].enabled is False
    assert config.integrations["slack"].sync_config.get("initial_days") == 30
