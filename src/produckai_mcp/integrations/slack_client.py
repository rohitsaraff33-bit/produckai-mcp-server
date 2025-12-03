"""Slack client wrapper for ProduckAI MCP Server."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


class SlackClientWrapper:
    """Wrapper around Slack SDK for ProduckAI integration."""

    def __init__(self, access_token: str):
        """
        Initialize Slack client.

        Args:
            access_token: Slack OAuth access token
        """
        self.client = WebClient(token=access_token)
        self.bot_id = None
        self._init_bot_id()

    def _init_bot_id(self) -> None:
        """Get the bot's user ID to filter out its own messages."""
        try:
            response = self.client.auth_test()
            self.bot_id = response.get("user_id")
            logger.info(f"Slack bot ID: {self.bot_id}")
        except SlackApiError as e:
            logger.error(f"Failed to get bot ID: {e}")

    def list_channels(self) -> List[Dict[str, Any]]:
        """
        List all channels the bot has access to.

        Returns:
            List of channel dictionaries with id, name, member_count
        """
        try:
            channels = []
            cursor = None

            while True:
                response = self.client.conversations_list(
                    types="public_channel,private_channel",
                    cursor=cursor,
                    limit=100,
                )

                for channel in response["channels"]:
                    # Only include channels the bot is a member of
                    if channel.get("is_member"):
                        channels.append({
                            "id": channel["id"],
                            "name": channel["name"],
                            "member_count": channel.get("num_members", 0),
                            "is_private": channel.get("is_private", False),
                            "purpose": channel.get("purpose", {}).get("value", ""),
                        })

                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break

            logger.info(f"Found {len(channels)} accessible channels")
            return channels

        except SlackApiError as e:
            logger.error(f"Failed to list channels: {e}")
            raise

    def get_channel_history(
        self,
        channel_id: str,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get message history from a channel.

        Args:
            channel_id: Channel ID
            oldest: Oldest message timestamp (for delta sync)
            latest: Latest message timestamp
            limit: Max messages per call (max 1000)

        Returns:
            List of message dictionaries
        """
        try:
            messages = []
            cursor = None

            while True:
                kwargs = {
                    "channel": channel_id,
                    "limit": min(limit, 1000),
                }
                if oldest:
                    kwargs["oldest"] = oldest
                if latest:
                    kwargs["latest"] = latest
                if cursor:
                    kwargs["cursor"] = cursor

                response = self.client.conversations_history(**kwargs)

                # Filter out bot messages and system messages
                for msg in response["messages"]:
                    # Skip bot messages
                    if msg.get("bot_id") or msg.get("user") == self.bot_id:
                        continue

                    # Skip system messages (channel_join, etc.)
                    if msg.get("subtype") in ["channel_join", "channel_leave", "channel_topic"]:
                        continue

                    messages.append(msg)

                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break

                # Safety limit
                if len(messages) >= limit * 10:
                    logger.warning(f"Hit safety limit of {len(messages)} messages")
                    break

            logger.info(f"Retrieved {len(messages)} messages from channel {channel_id}")
            return messages

        except SlackApiError as e:
            logger.error(f"Failed to get channel history: {e}")
            raise

    def get_thread_replies(
        self,
        channel_id: str,
        thread_ts: str,
    ) -> List[Dict[str, Any]]:
        """
        Get all replies in a thread.

        Args:
            channel_id: Channel ID
            thread_ts: Thread timestamp (parent message ts)

        Returns:
            List of reply messages
        """
        try:
            response = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
            )

            replies = []
            for msg in response["messages"]:
                # Skip the parent message (first one)
                if msg["ts"] == thread_ts:
                    continue

                # Skip bot messages
                if msg.get("bot_id") or msg.get("user") == self.bot_id:
                    continue

                replies.append(msg)

            return replies

        except SlackApiError as e:
            logger.error(f"Failed to get thread replies: {e}")
            return []

    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user information.

        Args:
            user_id: Slack user ID

        Returns:
            User info dictionary or None
        """
        try:
            response = self.client.users_info(user=user_id)
            user = response["user"]

            return {
                "id": user["id"],
                "name": user.get("real_name", user.get("name")),
                "display_name": user.get("profile", {}).get("display_name"),
                "email": user.get("profile", {}).get("email"),
                "is_bot": user.get("is_bot", False),
            }

        except SlackApiError as e:
            logger.warning(f"Failed to get user info for {user_id}: {e}")
            return None

    def get_channel_name(self, channel_id: str) -> Optional[str]:
        """
        Get channel name from ID.

        Args:
            channel_id: Channel ID

        Returns:
            Channel name or None
        """
        try:
            response = self.client.conversations_info(channel=channel_id)
            return response["channel"]["name"]
        except SlackApiError as e:
            logger.warning(f"Failed to get channel name for {channel_id}: {e}")
            return None

    def calculate_initial_sync_timestamp(self, days: int = 30) -> str:
        """
        Calculate timestamp for initial sync (X days ago).

        Args:
            days: Number of days to look back

        Returns:
            Slack timestamp string
        """
        dt = datetime.now() - timedelta(days=days)
        return str(dt.timestamp())
