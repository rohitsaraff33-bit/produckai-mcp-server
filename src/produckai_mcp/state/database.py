"""SQLite database management for state persistence."""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


class Database:
    """SQLite database wrapper for state management."""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Path):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_database_exists()

    def _ensure_database_exists(self) -> None:
        """Create database and tables if they don't exist."""
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create tables
        with self.get_connection() as conn:
            self._create_tables(conn)
            logger.info(f"Database initialized at {self.db_path}")

    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """Create all database tables."""
        cursor = conn.cursor()

        # Schema version tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert initial version if not exists
        cursor.execute("SELECT version FROM schema_version WHERE version = ?", (self.SCHEMA_VERSION,))
        if cursor.fetchone() is None:
            cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (self.SCHEMA_VERSION,))

        # Sync state tracking for delta sync
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                integration TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                resource_name TEXT,
                last_sync_timestamp TEXT,
                last_sync_cursor TEXT,
                total_items_synced INTEGER DEFAULT 0,
                last_sync_new_items INTEGER DEFAULT 0,
                last_sync_status TEXT,
                last_sync_error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(integration, resource_id)
            )
        """)

        # Customer pattern matching cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(pattern_type, pattern)
            )
        """)

        # Sync job tracking (for long-running operations)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_jobs (
                id TEXT PRIMARY KEY,
                integration TEXT NOT NULL,
                operation TEXT NOT NULL,
                status TEXT NOT NULL,
                progress REAL DEFAULT 0.0,
                total_items INTEGER,
                processed_items INTEGER DEFAULT 0,
                result TEXT,
                error TEXT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # OAuth token metadata (actual tokens in keyring)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_tokens (
                integration TEXT PRIMARY KEY,
                token_type TEXT,
                expires_at TIMESTAMP,
                scopes TEXT,
                last_refreshed TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Bot filters for Slack
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_filters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filter_type TEXT NOT NULL,
                filter_value TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(filter_type, filter_value)
            )
        """)

        # Insert default bot filters
        default_bots = [
            ("name", "slackbot"),
            ("name", "github"),
            ("name", "jira"),
            ("name", "google calendar"),
            ("name", "zapier"),
            ("name", "zoom"),
            ("name", "salesforce"),
            ("pattern", "bot$"),
            ("pattern", "^app-"),
            ("pattern", "\\[bot\\]"),
            ("pattern", "webhook"),
            ("pattern", "integration"),
        ]

        for filter_type, filter_value in default_bots:
            cursor.execute(
                """
                INSERT OR IGNORE INTO bot_filters (filter_type, filter_value)
                VALUES (?, ?)
                """,
                (filter_type, filter_value),
            )

        # Phase 5: JIRA Integration tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_jira_links (
                feedback_id TEXT NOT NULL,
                jira_issue_key TEXT NOT NULL,
                jira_issue_id TEXT,
                jira_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (feedback_id, jira_issue_key)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jira_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Phase 5: VOC Scoring tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voc_scores (
                feedback_id TEXT UNIQUE,
                theme_id TEXT UNIQUE,
                total_score REAL NOT NULL,
                customer_impact_score REAL,
                frequency_score REAL,
                recency_score REAL,
                sentiment_score REAL,
                theme_alignment_score REAL,
                effort_score REAL,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (
                    (feedback_id IS NOT NULL AND theme_id IS NULL) OR
                    (feedback_id IS NULL AND theme_id IS NOT NULL)
                )
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voc_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Phase 6: PRD Generation tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prds (
                id TEXT PRIMARY KEY,
                insight_id TEXT NOT NULL,
                theme_id TEXT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                status TEXT DEFAULT 'draft',
                metadata TEXT,
                word_count INTEGER,
                estimated_pages REAL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (insight_id) REFERENCES insights(id)
            )
        """)

        # Index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prds_insight_id ON prds(insight_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prds_theme_id ON prds(theme_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prds_status ON prds(status)
        """)

        conn.commit()
        logger.debug("Database tables created/verified")

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection.

        Returns:
            SQLite connection with row factory enabled
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def execute(
        self,
        query: str,
        params: Optional[tuple] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            List of row dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def execute_one(
        self,
        query: str,
        params: Optional[tuple] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a SELECT query and return first result.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Row dictionary or None
        """
        results = self.execute(query, params)
        return results[0] if results else None

    def execute_write(
        self,
        query: str,
        params: Optional[tuple] = None,
    ) -> int:
        """
        Execute an INSERT/UPDATE/DELETE query.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Last row ID (for INSERT) or row count
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor.lastrowid or cursor.rowcount

    def execute_many(
        self,
        query: str,
        params_list: List[tuple],
    ) -> int:
        """
        Execute a query with multiple parameter sets.

        Args:
            query: SQL query
            params_list: List of parameter tuples

        Returns:
            Row count
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount
