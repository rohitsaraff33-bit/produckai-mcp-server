"""Sync state management for delta synchronization."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from produckai_mcp.state.database import Database
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


class SyncStateManager:
    """Manages sync state for delta synchronization across integrations."""

    def __init__(self, database: Database):
        """
        Initialize sync state manager.

        Args:
            database: Database instance
        """
        self.db = database

    def get_sync_state(self, integration: str, resource_id: str) -> Optional[Dict]:
        """
        Get last sync state for a resource.

        Args:
            integration: Integration name (slack, gdrive, etc.)
            resource_id: Resource identifier (channel ID, folder ID, etc.)

        Returns:
            Sync state dictionary or None if never synced
        """
        return self.db.execute_one(
            """
            SELECT * FROM sync_state
            WHERE integration = ? AND resource_id = ?
            """,
            (integration, resource_id),
        )

    def update_sync_state(
        self,
        integration: str,
        resource_id: str,
        resource_name: Optional[str] = None,
        last_timestamp: Optional[str] = None,
        new_items: int = 0,
        status: str = "success",
        error: Optional[str] = None,
        cursor: Optional[str] = None,
    ) -> None:
        """
        Update sync state after a sync operation.

        Args:
            integration: Integration name
            resource_id: Resource identifier
            resource_name: Human-readable resource name
            last_timestamp: Last synced timestamp
            new_items: Number of new items synced
            status: Sync status (success, failed, in_progress)
            error: Error message if failed
            cursor: Integration-specific cursor for pagination
        """
        # Get current state
        current = self.get_sync_state(integration, resource_id)

        if current:
            # Update existing record
            total = current["total_items_synced"] + new_items
            self.db.execute_write(
                """
                UPDATE sync_state
                SET last_sync_timestamp = ?,
                    last_sync_cursor = ?,
                    total_items_synced = ?,
                    last_sync_new_items = ?,
                    last_sync_status = ?,
                    last_sync_error = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE integration = ? AND resource_id = ?
                """,
                (
                    last_timestamp,
                    cursor,
                    total,
                    new_items,
                    status,
                    error,
                    integration,
                    resource_id,
                ),
            )
            logger.info(
                f"Updated sync state for {integration}:{resource_id} - "
                f"{new_items} new items, total: {total}"
            )
        else:
            # Insert new record
            self.db.execute_write(
                """
                INSERT INTO sync_state (
                    integration, resource_id, resource_name,
                    last_sync_timestamp, last_sync_cursor,
                    total_items_synced, last_sync_new_items,
                    last_sync_status, last_sync_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    integration,
                    resource_id,
                    resource_name,
                    last_timestamp,
                    cursor,
                    new_items,
                    new_items,
                    status,
                    error,
                ),
            )
            logger.info(
                f"Created sync state for {integration}:{resource_id} - {new_items} items"
            )

    def should_full_sync(
        self,
        integration: str,
        resource_id: str,
        max_age_days: int = 30,
    ) -> bool:
        """
        Check if a full sync should be performed instead of delta.

        Args:
            integration: Integration name
            resource_id: Resource identifier
            max_age_days: Maximum age of last sync before triggering full sync

        Returns:
            True if full sync is needed
        """
        state = self.get_sync_state(integration, resource_id)

        if not state:
            # Never synced before
            logger.info(f"No previous sync found for {integration}:{resource_id}, doing full sync")
            return True

        if not state["last_sync_timestamp"]:
            logger.info(f"No timestamp found for {integration}:{resource_id}, doing full sync")
            return True

        if state["last_sync_status"] == "failed":
            logger.info(f"Last sync failed for {integration}:{resource_id}, doing full sync")
            return True

        # Check age
        try:
            last_sync = datetime.fromisoformat(state["last_sync_timestamp"])
            age = datetime.now() - last_sync

            if age > timedelta(days=max_age_days):
                logger.info(
                    f"Last sync for {integration}:{resource_id} is {age.days} days old, "
                    f"doing full sync"
                )
                return True
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not parse timestamp for {integration}:{resource_id}: {e}")
            return True

        return False

    def get_all_sync_states(self, integration: Optional[str] = None) -> List[Dict]:
        """
        Get all sync states, optionally filtered by integration.

        Args:
            integration: Optional integration name to filter

        Returns:
            List of sync state dictionaries
        """
        if integration:
            return self.db.execute(
                "SELECT * FROM sync_state WHERE integration = ? ORDER BY updated_at DESC",
                (integration,),
            )
        else:
            return self.db.execute(
                "SELECT * FROM sync_state ORDER BY updated_at DESC"
            )

    def delete_sync_state(self, integration: str, resource_id: str) -> None:
        """
        Delete sync state for a resource.

        Args:
            integration: Integration name
            resource_id: Resource identifier
        """
        self.db.execute_write(
            "DELETE FROM sync_state WHERE integration = ? AND resource_id = ?",
            (integration, resource_id),
        )
        logger.info(f"Deleted sync state for {integration}:{resource_id}")

    def get_sync_summary(self) -> Dict[str, any]:
        """
        Get summary of all sync states.

        Returns:
            Summary dictionary with counts per integration
        """
        all_states = self.get_all_sync_states()

        summary = {
            "total_resources": len(all_states),
            "by_integration": {},
            "total_items_synced": 0,
            "recent_failures": [],
        }

        for state in all_states:
            integration = state["integration"]

            if integration not in summary["by_integration"]:
                summary["by_integration"][integration] = {
                    "resource_count": 0,
                    "total_items": 0,
                    "successful": 0,
                    "failed": 0,
                }

            summary["by_integration"][integration]["resource_count"] += 1
            summary["by_integration"][integration]["total_items"] += state["total_items_synced"]
            summary["total_items_synced"] += state["total_items_synced"]

            if state["last_sync_status"] == "success":
                summary["by_integration"][integration]["successful"] += 1
            elif state["last_sync_status"] == "failed":
                summary["by_integration"][integration]["failed"] += 1
                summary["recent_failures"].append({
                    "integration": integration,
                    "resource_id": state["resource_id"],
                    "resource_name": state["resource_name"],
                    "error": state["last_sync_error"],
                    "timestamp": state["updated_at"],
                })

        return summary
