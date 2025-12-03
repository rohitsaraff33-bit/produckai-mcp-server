"""Bot filtering system for Slack messages."""

import re
from typing import Dict, List

from produckai_mcp.state.database import Database
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


class BotFilter:
    """Filters out bot messages from Slack."""

    def __init__(self, database: Database):
        """
        Initialize bot filter.

        Args:
            database: Database instance for storing/loading bot filters
        """
        self.db = database
        self._ensure_default_filters()

    def _ensure_default_filters(self) -> None:
        """Ensure default bot filters exist in database."""
        existing = self.db.execute("SELECT COUNT(*) as count FROM bot_filters")
        if existing[0]["count"] == 0:
            logger.info("Initializing default bot filters")
            for filter_config in self.get_default_filters():
                self.add_filter(
                    filter_type=filter_config["filter_type"],
                    filter_value=filter_config["filter_value"],
                )

    def is_bot_message(self, message: Dict) -> bool:
        """
        Check if a message is from a bot.

        Args:
            message: Slack message dictionary

        Returns:
            True if message is from a bot
        """
        # Check if message has bot_id (definite bot)
        if message.get("bot_id"):
            return True

        # Check user name against filters
        user_name = message.get("username", "").lower()
        if not user_name:
            return False

        # Get enabled filters from database
        filters = self.db.execute(
            "SELECT filter_type, filter_value FROM bot_filters WHERE enabled = 1"
        )

        for filter_row in filters:
            filter_type = filter_row["filter_type"]
            filter_value = filter_row["filter_value"]

            if filter_type == "name":
                # Exact name match (case-insensitive)
                if user_name == filter_value.lower():
                    logger.debug(f"Filtered bot by name: {user_name}")
                    return True

            elif filter_type == "pattern":
                # Regex pattern match
                try:
                    if re.search(filter_value, user_name, re.IGNORECASE):
                        logger.debug(f"Filtered bot by pattern '{filter_value}': {user_name}")
                        return True
                except re.error as e:
                    logger.warning(f"Invalid bot pattern '{filter_value}': {e}")

            elif filter_type == "bot_id":
                # Bot ID match
                if message.get("bot_id") == filter_value:
                    logger.debug(f"Filtered bot by ID: {filter_value}")
                    return True

        return False

    def add_filter(
        self,
        filter_type: str,
        filter_value: str,
        enabled: bool = True,
    ) -> None:
        """
        Add a new bot filter.

        Args:
            filter_type: Type of filter (name, pattern, bot_id)
            filter_value: Filter value
            enabled: Whether filter is enabled
        """
        try:
            self.db.execute_write(
                """
                INSERT OR REPLACE INTO bot_filters
                (filter_type, filter_value, enabled)
                VALUES (?, ?, ?)
                """,
                (filter_type, filter_value, 1 if enabled else 0),
            )
            logger.info(f"Added bot filter: {filter_type}={filter_value}")
        except Exception as e:
            logger.error(f"Failed to add bot filter: {e}")

    def remove_filter(self, filter_type: str, filter_value: str) -> None:
        """Remove a bot filter."""
        self.db.execute_write(
            "DELETE FROM bot_filters WHERE filter_type = ? AND filter_value = ?",
            (filter_type, filter_value),
        )
        logger.info(f"Removed bot filter: {filter_type}={filter_value}")

    def get_all_filters(self) -> List[Dict]:
        """Get all bot filters."""
        return self.db.execute("SELECT * FROM bot_filters ORDER BY filter_type, filter_value")

    def enable_filter(self, filter_type: str, filter_value: str) -> None:
        """Enable a bot filter."""
        self.db.execute_write(
            "UPDATE bot_filters SET enabled = 1 WHERE filter_type = ? AND filter_value = ?",
            (filter_type, filter_value),
        )

    def disable_filter(self, filter_type: str, filter_value: str) -> None:
        """Disable a bot filter."""
        self.db.execute_write(
            "UPDATE bot_filters SET enabled = 0 WHERE filter_type = ? AND filter_value = ?",
            (filter_type, filter_value),
        )

    @staticmethod
    def get_default_filters() -> List[Dict[str, str]]:
        """
        Get default bot filters.

        Returns:
            List of filter dictionaries
        """
        return [
            # Known bot names
            {"filter_type": "name", "filter_value": "slackbot"},
            {"filter_type": "name", "filter_value": "github"},
            {"filter_type": "name", "filter_value": "jira"},
            {"filter_type": "name", "filter_value": "google calendar"},
            {"filter_type": "name", "filter_value": "zapier"},
            {"filter_type": "name", "filter_value": "zoom"},
            {"filter_type": "name", "filter_value": "salesforce"},
            {"filter_type": "name", "filter_value": "hubspot"},
            {"filter_type": "name", "filter_value": "asana"},
            {"filter_type": "name", "filter_value": "trello"},
            # Bot patterns
            {"filter_type": "pattern", "filter_value": "bot$"},
            {"filter_type": "pattern", "filter_value": "^app-"},
            {"filter_type": "pattern", "filter_value": r"\[bot\]"},
            {"filter_type": "pattern", "filter_value": "webhook"},
            {"filter_type": "pattern", "filter_value": "integration"},
            {"filter_type": "pattern", "filter_value": "^bot_"},
        ]
