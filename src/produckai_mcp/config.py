"""Configuration management for ProduckAI MCP Server."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class BackendConfig(BaseModel):
    """ProduckAI backend configuration."""

    url: str = Field(default="http://localhost:8000", description="Backend API URL")
    timeout: int = Field(default=60, description="Request timeout in seconds")
    api_key: Optional[str] = Field(default=None, description="API key (if required)")


class ServerConfig(BaseModel):
    """MCP server configuration."""

    name: str = Field(default="produckai", description="Server name")
    version: str = Field(default="0.7.0", description="Server version")
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(
        default=None, description="Log file path (None for console only)"
    )


class AIConfig(BaseModel):
    """AI/LLM configuration."""

    provider: str = Field(default="anthropic", description="AI provider (anthropic, openai)")
    model: str = Field(
        default="claude-3-haiku-20240307", description="Model to use for classification"
    )
    api_key_source: str = Field(
        default="environment", description="Where to get API key (environment, keyring)"
    )
    classification: Dict[str, Any] = Field(
        default_factory=lambda: {
            "batch_size": 10,
            "confidence_threshold": 0.7,
        }
    )


class IntegrationConfig(BaseModel):
    """Integration configuration."""

    enabled: bool = Field(default=False, description="Whether integration is enabled")
    sync_config: Dict[str, Any] = Field(default_factory=dict)


class StateConfig(BaseModel):
    """State management configuration."""

    database: str = Field(
        default="~/.produckai/state.db", description="SQLite database path"
    )
    backup_enabled: bool = Field(default=True, description="Enable automatic backups")
    backup_frequency: str = Field(default="daily", description="Backup frequency")


class Config(BaseSettings):
    """Main configuration class."""

    backend: BackendConfig = Field(default_factory=BackendConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    state: StateConfig = Field(default_factory=StateConfig)
    integrations: Dict[str, IntegrationConfig] = Field(
        default_factory=lambda: {
            "slack": IntegrationConfig(),
            "gdrive": IntegrationConfig(),
            "jira": IntegrationConfig(),
            "zoom": IntegrationConfig(),
        }
    )

    class Config:
        """Pydantic config."""

        env_prefix = "PRODUCKAI_"
        env_nested_delimiter = "__"
        case_sensitive = False

    @classmethod
    def load_from_file(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = get_config_dir() / "config.yaml"

        if not config_path.exists():
            # Return default config if file doesn't exist
            return cls()

        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)

        return cls(**config_data)

    def save_to_file(self, config_path: Optional[Path] = None) -> None:
        """Save configuration to YAML file."""
        if config_path is None:
            config_path = get_config_dir() / "config.yaml"

        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and save
        config_dict = self.model_dump()
        with open(config_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)

    def get_state_db_path(self) -> Path:
        """Get resolved state database path."""
        db_path = Path(self.state.database).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path

    def get_log_file_path(self) -> Optional[Path]:
        """Get resolved log file path."""
        if self.server.log_file is None:
            return None
        log_path = Path(self.server.log_file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return log_path


def get_config_dir() -> Path:
    """Get the configuration directory path."""
    config_dir = Path.home() / ".produckai"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_logs_dir() -> Path:
    """Get the logs directory path."""
    logs_dir = get_config_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def create_default_config() -> Config:
    """Create default configuration with sensible defaults."""
    config = Config()
    # Set default log file
    config.server.log_file = str(get_logs_dir() / "mcp-server.log")
    # Set default state database
    config.state.database = str(get_config_dir() / "state.db")
    return config


def get_config() -> Config:
    """Get the global configuration instance."""
    return Config.load_from_file()


# Example config template
DEFAULT_CONFIG_TEMPLATE = """# ProduckAI MCP Server Configuration

# ProduckAI Backend
backend:
  url: http://localhost:8000
  timeout: 60  # seconds
  api_key: null  # Optional API key

# MCP Server Settings
server:
  name: produckai
  version: 0.7.0
  log_level: INFO  # DEBUG, INFO, WARNING, ERROR
  log_file: ~/.produckai/logs/mcp-server.log

# AI Classification Settings
ai:
  provider: anthropic  # anthropic or openai
  model: claude-3-haiku-20240307
  api_key_source: environment  # environment or keyring
  classification:
    batch_size: 10
    confidence_threshold: 0.7

# Integration Settings
integrations:
  slack:
    enabled: false
    sync_config:
      initial_days: 30
      delta_sync: true

  gdrive:
    enabled: false
    sync_config:
      recursive: true

  jira:
    enabled: false
    sync_config:
      label: customer_feedback
      since_days: 90

  zoom:
    enabled: false
    sync_config:
      since_days: 7

# Sync State
state:
  database: ~/.produckai/state.db
  backup_enabled: true
  backup_frequency: daily
"""


def save_default_config_template() -> Path:
    """Save the default config template to the config directory."""
    config_path = get_config_dir() / "config.yaml"
    if not config_path.exists():
        with open(config_path, "w") as f:
            f.write(DEFAULT_CONFIG_TEMPLATE)
    return config_path
