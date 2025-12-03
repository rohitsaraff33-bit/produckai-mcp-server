"""Customer pattern matching for Slack messages."""

import re
from typing import Dict, List, Optional

from produckai_mcp.state.database import Database
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


class CustomerMatcher:
    """Matches Slack messages to customers using patterns."""

    def __init__(self, database: Database):
        """
        Initialize customer matcher.

        Args:
            database: Database instance for storing/loading patterns
        """
        self.db = database
        self._load_patterns()

    def _load_patterns(self) -> None:
        """Load customer patterns from database."""
        patterns = self.db.execute("SELECT * FROM customer_patterns WHERE 1=1")
        logger.info(f"Loaded {len(patterns)} customer patterns from database")

    def match_customer(self, message_text: str) -> Optional[str]:
        """
        Try to match a message to a customer using patterns.

        Args:
            message_text: Slack message text

        Returns:
            Customer name if matched, None otherwise
        """
        # Get all patterns from database
        patterns = self.db.execute(
            "SELECT pattern_type, pattern, customer_name, confidence "
            "FROM customer_patterns ORDER BY confidence DESC"
        )

        for pattern_row in patterns:
            pattern_type = pattern_row["pattern_type"]
            pattern = pattern_row["pattern"]
            customer_name = pattern_row["customer_name"]

            if pattern_type == "exact_name":
                # Case-insensitive exact name match
                if pattern.lower() in message_text.lower():
                    logger.debug(f"Matched customer '{customer_name}' by exact name")
                    return customer_name

            elif pattern_type == "email_domain":
                # Match email domain (e.g., @acmecorp.com -> Acme Corp)
                if f"@{pattern}" in message_text.lower():
                    logger.debug(f"Matched customer '{customer_name}' by email domain")
                    return customer_name

            elif pattern_type == "regex":
                # Regex pattern match
                try:
                    match = re.search(pattern, message_text, re.IGNORECASE)
                    if match:
                        logger.debug(f"Matched customer '{customer_name}' by regex")
                        return customer_name
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{pattern}': {e}")

        return None

    def add_pattern(
        self,
        pattern_type: str,
        pattern: str,
        customer_name: str,
        confidence: float = 1.0,
    ) -> None:
        """
        Add a new customer pattern.

        Args:
            pattern_type: Type of pattern (exact_name, email_domain, regex)
            pattern: Pattern string
            customer_name: Customer name to map to
            confidence: Confidence score (0.0 to 1.0)
        """
        try:
            self.db.execute_write(
                """
                INSERT OR REPLACE INTO customer_patterns
                (pattern_type, pattern, customer_name, confidence)
                VALUES (?, ?, ?, ?)
                """,
                (pattern_type, pattern, customer_name, confidence),
            )
            logger.info(f"Added customer pattern: {pattern_type}={pattern} -> {customer_name}")
        except Exception as e:
            logger.error(f"Failed to add customer pattern: {e}")

    def get_all_patterns(self) -> List[Dict]:
        """Get all customer patterns."""
        return self.db.execute("SELECT * FROM customer_patterns ORDER BY customer_name")

    @staticmethod
    def get_default_patterns() -> List[Dict[str, str]]:
        """
        Get default customer patterns to initialize database.

        Returns:
            List of pattern dictionaries
        """
        return [
            # Common patterns
            {
                "pattern_type": "regex",
                "pattern": r"(?:customer|client):\s*([A-Z][A-Za-z\s&]+)",
                "customer_name": "<extracted>",
                "confidence": 0.9,
            },
            {
                "pattern_type": "regex",
                "pattern": r"feedback from\s+([A-Z][A-Za-z\s&]+)",
                "customer_name": "<extracted>",
                "confidence": 0.9,
            },
            {
                "pattern_type": "regex",
                "pattern": r"([A-Z][A-Za-z\s&]+)\s+(?:said|mentioned|reported)",
                "customer_name": "<extracted>",
                "confidence": 0.8,
            },
        ]
