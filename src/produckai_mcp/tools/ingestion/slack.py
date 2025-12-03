"""Slack integration tools - OAuth setup, channel sync, and configuration."""

from typing import Any, Dict, List, Optional

from produckai_mcp.ai import BotFilter, CustomerMatcher, FeedbackClassifier
from produckai_mcp.api.client import ProduckAIClient
from produckai_mcp.integrations.oauth_handler import OAuthHandler
from produckai_mcp.integrations.slack_client import SlackClientWrapper
from produckai_mcp.state.database import Database
from produckai_mcp.state.sync_state import SyncStateManager
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


async def setup_slack_integration(
    client_id: str,
    client_secret: str,
) -> Dict[str, Any]:
    """
    Set up Slack OAuth integration.

    This starts an OAuth flow that opens your browser to authorize ProduckAI
    to access your Slack workspace. A local web server runs temporarily on
    port 8765 to handle the OAuth callback.

    Required Slack app scopes:
    - channels:history (read messages from public channels)
    - channels:read (view channel information)
    - groups:history (read messages from private channels)
    - groups:read (view private channel information)
    - users:read (view user information)
    - users:read.email (view user email addresses)

    Args:
        client_id: Slack app client ID from https://api.slack.com/apps
        client_secret: Slack app client secret

    Returns:
        Dict with setup status and workspace information

    Example:
        PM: "Set up Slack integration for my workspace"

        Assistant: I'll help you set up Slack integration.
        [Calls setup_slack_integration with credentials]

        A browser window will open for authorization. After you approve:

        ✅ Slack integration successful!
        **Workspace**: Acme Corp
        **Scopes**: channels:history, channels:read, ...
        **Bot User ID**: U01234ABCD

        You can now sync Slack channels using sync_slack_channels().
    """
    logger.info("Setting up Slack integration")

    try:
        oauth_handler = OAuthHandler("slack")
        result = await oauth_handler.start_slack_oauth_flow(client_id, client_secret)

        message_lines = [
            "✅ Slack integration successful!",
            "",
            f"**Workspace**: {result.get('workspace', 'Unknown')}",
            f"**Scopes**: {', '.join(result.get('scopes', []))}",
            f"**Bot User ID**: {result.get('bot_user_id', 'Unknown')}",
            "",
            "Setup complete! You can now:",
            "1. List channels: list_slack_channels()",
            "2. Sync channels: sync_slack_channels(['channel-name'])",
            "",
            "The integration will automatically:",
            "- Filter out bot messages",
            "- Classify messages as feedback using AI",
            "- Match customers using patterns",
            "- Track sync state for delta sync",
        ]

        return {
            "status": "success",
            **result,
            "message": "\n".join(message_lines),
        }

    except Exception as e:
        logger.error(f"Slack setup failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": (
                f"❌ Slack integration failed: {str(e)}\n\n"
                "Please check:\n"
                "1. Client ID and secret are correct\n"
                "2. Redirect URI is set to http://localhost:8765/callback\n"
                "3. Required scopes are enabled in your Slack app\n"
                "4. Port 8765 is not blocked by firewall"
            ),
        }


async def list_slack_channels() -> Dict[str, Any]:
    """
    List all Slack channels the bot has access to.

    Shows public and private channels that the bot is a member of.
    Use this to find channel names/IDs before syncing.

    Returns:
        Dict with list of channels and their details

    Example:
        PM: "What Slack channels can I sync?"

        Assistant: [Calls list_slack_channels]

        # Available Slack Channels (8 channels)

        ## 1. #customer-feedback
        - ID: C01234ABC
        - Members: 45
        - Purpose: Share customer feedback and feature requests

        ## 2. #sales-insights
        - ID: C56789DEF
        - Members: 23
        - Purpose: Customer calls and deal insights

        [Shows all 8 channels]

        Use sync_slack_channels(['customer-feedback', 'sales-insights'])
        to start syncing.
    """
    logger.info("Listing Slack channels")

    try:
        # Get access token from keyring
        access_token = OAuthHandler.get_slack_token()
        if not access_token:
            return {
                "status": "error",
                "message": (
                    "❌ No Slack integration found.\n\n"
                    "Please run setup_slack_integration() first to connect your Slack workspace."
                ),
            }

        # Create Slack client
        slack_client = SlackClientWrapper(access_token)

        # List channels
        channels = slack_client.list_channels()

        if not channels:
            return {
                "status": "success",
                "channels": [],
                "message": (
                    "No channels found.\n\n"
                    "The bot needs to be added to channels first. In Slack:\n"
                    "1. Go to the channel\n"
                    "2. Type: /invite @YourBotName\n"
                    "3. Run list_slack_channels() again"
                ),
            }

        # Format channels
        formatted_channels = []
        for i, channel in enumerate(channels, 1):
            formatted_channels.append({
                "rank": i,
                "id": channel["id"],
                "name": channel["name"],
                "member_count": channel["member_count"],
                "is_private": channel["is_private"],
                "purpose": channel["purpose"],
            })

        # Build message
        lines = [
            f"# Available Slack Channels ({len(channels)} channels)",
            "",
            "These are channels where the bot is a member and can sync messages.",
            "",
        ]

        for i, channel in enumerate(channels[:10], 1):
            lines.append(f"## {i}. #{channel['name']}")
            lines.append(f"- **ID**: {channel['id']}")
            lines.append(f"- **Members**: {channel['member_count']}")
            if channel["purpose"]:
                lines.append(f"- **Purpose**: {channel['purpose']}")
            lines.append("")

        if len(channels) > 10:
            lines.append(f"... and {len(channels) - 10} more channels")
            lines.append("")

        lines.append("To sync channels:")
        lines.append("sync_slack_channels(['customer-feedback', 'sales-insights'])")

        return {
            "status": "success",
            "channels": formatted_channels,
            "message": "\n".join(lines),
        }

    except Exception as e:
        logger.error(f"Failed to list channels: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"❌ Failed to list channels: {str(e)}",
        }


async def sync_slack_channels(
    api_client: ProduckAIClient,
    database: Database,
    sync_state: SyncStateManager,
    channel_names: List[str],
    force_full_sync: bool = False,
) -> Dict[str, Any]:
    """
    Sync messages from specified Slack channels.

    This performs intelligent sync with:
    - **Delta sync**: Only new messages after last sync (zero duplicates)
    - **AI classification**: Each message analyzed to detect feedback
    - **Bot filtering**: Automatic removal of bot messages
    - **Customer matching**: Links messages to customers using patterns
    - **Thread handling**: Processes each reply independently

    **First sync**: Pulls last 30 days of messages
    **Subsequent syncs**: Only messages after last sync timestamp

    Args:
        api_client: ProduckAI API client
        database: Database instance
        sync_state: Sync state manager
        channel_names: List of channel names to sync (e.g., ['customer-feedback'])
        force_full_sync: If True, re-sync last 30 days (default: False)

    Returns:
        Dict with sync results and statistics

    Example:
        PM: "Sync the #customer-feedback and #sales-insights channels"

        Assistant: [Calls sync_slack_channels]

        🔄 Syncing Slack channels...

        **Channel: #customer-feedback**
        - Messages scanned: 234
        - Bot messages filtered: 45
        - Feedback detected: 12
        - Customers matched: 8
        - Requiring manual tagging: 4

        **Channel: #sales-insights**
        - Messages scanned: 156
        - Bot messages filtered: 23
        - Feedback detected: 9
        - Customers matched: 6
        - Requiring manual tagging: 3

        ✅ Sync complete!
        - Total feedback items: 21
        - Ready for clustering: Yes
    """
    logger.info(f"Syncing Slack channels: {channel_names}")

    try:
        # Get access token
        access_token = OAuthHandler.get_slack_token()
        if not access_token:
            return {
                "status": "error",
                "message": "❌ No Slack integration found. Run setup_slack_integration() first.",
            }

        # Create clients
        slack_client = SlackClientWrapper(access_token)
        bot_filter = BotFilter(database)
        customer_matcher = CustomerMatcher(database)
        classifier = FeedbackClassifier()

        # Get all channels
        all_channels = slack_client.list_channels()
        channel_map = {ch["name"]: ch for ch in all_channels}

        results = {}
        total_feedback = 0

        for channel_name in channel_names:
            channel = channel_map.get(channel_name)
            if not channel:
                results[channel_name] = {
                    "status": "error",
                    "message": f"Channel not found or bot not a member",
                }
                continue

            channel_id = channel["id"]

            # Check if we should do delta sync
            should_full = force_full_sync or sync_state.should_full_sync("slack", channel_id)

            if should_full:
                # Full sync: last 30 days
                oldest_ts = slack_client.calculate_initial_sync_timestamp(days=30)
                logger.info(f"Full sync for #{channel_name} (30 days)")
            else:
                # Delta sync: since last sync
                state = sync_state.get_sync_state("slack", channel_id)
                oldest_ts = state["last_sync_timestamp"]
                logger.info(f"Delta sync for #{channel_name} since {oldest_ts}")

            # Get messages
            messages = slack_client.get_channel_history(
                channel_id=channel_id,
                oldest=oldest_ts,
            )

            # Filter bots
            non_bot_messages = [msg for msg in messages if not bot_filter.is_bot_message(msg)]
            bot_count = len(messages) - len(non_bot_messages)

            # Classify messages
            classifications = await classifier.classify_messages(
                non_bot_messages,
                batch_size=10,
                confidence_threshold=0.7,
            )

            # Extract feedback
            feedback_items = [c for c in classifications if c["classification"] == "feedback"]

            # Match customers and store feedback
            stored_count = 0
            manual_tagging_needed = 0

            for item in feedback_items:
                customer_name = item["customer_extracted"]
                if not customer_name:
                    # Try pattern matching
                    customer_name = customer_matcher.match_customer(item["text"])

                if not customer_name:
                    manual_tagging_needed += 1

                # Upload feedback via CSV (backend doesn't support direct POST)
                try:
                    import csv
                    import tempfile
                    from datetime import datetime

                    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=['feedback', 'customer', 'date'])
                        writer.writeheader()
                        writer.writerow({
                            'feedback': item["text"],
                            'customer': customer_name or "Unknown",
                            'source': "slack",
                            'date': datetime.now().strftime('%Y-%m-%d')
                        })
                        temp_path = Path(f.name)

                    try:
                        upload_result = await api_client.upload_csv(temp_path, template_type="standard")
                        if upload_result.feedback_count > 0:
                            stored_count += upload_result.feedback_count
                    finally:
                        if temp_path.exists():
                            temp_path.unlink()
                except Exception as e:
                    logger.error(f"Failed to store feedback: {e}")

            # Update sync state
            if messages:
                latest_ts = max(msg.get("ts", "0") for msg in messages)
                sync_state.update_sync_state(
                    integration="slack",
                    resource_id=channel_id,
                    resource_name=channel_name,
                    last_timestamp=latest_ts,
                    new_items=stored_count,
                    status="success",
                )

            results[channel_name] = {
                "status": "success",
                "messages_scanned": len(messages),
                "bot_messages_filtered": bot_count,
                "feedback_detected": len(feedback_items),
                "feedback_stored": stored_count,
                "customers_matched": len([f for f in feedback_items if f["customer_extracted"]]),
                "manual_tagging_needed": manual_tagging_needed,
            }

            total_feedback += stored_count

        # Build message
        lines = ["🔄 Syncing Slack channels...", ""]

        for channel_name, result in results.items():
            if result["status"] == "error":
                lines.append(f"**Channel: #{channel_name}** ❌")
                lines.append(f"- {result['message']}")
            else:
                lines.append(f"**Channel: #{channel_name}** ✅")
                lines.append(f"- Messages scanned: {result['messages_scanned']}")
                lines.append(f"- Bot messages filtered: {result['bot_messages_filtered']}")
                lines.append(f"- Feedback detected: {result['feedback_detected']}")
                lines.append(f"- Customers matched: {result['customers_matched']}")
                if result["manual_tagging_needed"] > 0:
                    lines.append(f"- Requiring manual tagging: {result['manual_tagging_needed']}")
            lines.append("")

        lines.append("✅ Sync complete!")
        lines.append(f"- Total feedback items: {total_feedback}")
        lines.append(f"- Ready for clustering: {'Yes' if total_feedback >= 50 else 'No (need 50+ items)'}")

        return {
            "status": "success",
            "results": results,
            "total_feedback": total_feedback,
            "message": "\n".join(lines),
        }

    except Exception as e:
        logger.error(f"Slack sync failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"❌ Slack sync failed: {str(e)}",
        }


async def get_slack_sync_status(
    sync_state: SyncStateManager,
) -> Dict[str, Any]:
    """
    Get sync status for all Slack channels.

    Shows which channels have been synced, when they were last synced,
    and how many items were synced.

    Returns:
        Dict with sync status for all channels

    Example:
        PM: "What's the Slack sync status?"

        Assistant: [Calls get_slack_sync_status]

        # Slack Sync Status

        ## Channel: #customer-feedback
        - Last synced: 2024-01-15 14:30:00
        - Total items synced: 145
        - Last sync: 12 new items
        - Status: ✅ Success

        ## Channel: #sales-insights
        - Last synced: 2024-01-15 14:31:00
        - Total items synced: 89
        - Last sync: 8 new items
        - Status: ✅ Success

        Run sync_slack_channels() to sync new messages.
    """
    logger.info("Getting Slack sync status")

    try:
        states = sync_state.get_all_sync_states("slack")

        if not states:
            return {
                "status": "success",
                "channels": [],
                "message": (
                    "No Slack channels have been synced yet.\n\n"
                    "To sync channels:\n"
                    "1. List channels: list_slack_channels()\n"
                    "2. Sync channels: sync_slack_channels(['channel-name'])"
                ),
            }

        lines = ["# Slack Sync Status", ""]

        for state in states:
            status_emoji = "✅" if state["last_sync_status"] == "success" else "❌"
            lines.append(f"## Channel: #{state['resource_name']} {status_emoji}")
            lines.append(f"- **Last synced**: {state['last_sync_timestamp'] or 'Never'}")
            lines.append(f"- **Total items synced**: {state['total_items_synced']}")
            lines.append(f"- **Last sync**: {state['last_sync_new_items']} new items")
            lines.append(f"- **Status**: {state['last_sync_status']}")
            if state["last_sync_error"]:
                lines.append(f"- **Error**: {state['last_sync_error']}")
            lines.append("")

        lines.append("Run sync_slack_channels() to sync new messages.")

        return {
            "status": "success",
            "channels": states,
            "message": "\n".join(lines),
        }

    except Exception as e:
        logger.error(f"Failed to get sync status: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"❌ Failed to get sync status: {str(e)}",
        }


async def configure_bot_filters(
    database: Database,
    add_filters: Optional[List[Dict[str, str]]] = None,
    remove_filters: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Configure bot filters for Slack messages.

    Bot filters automatically remove bot messages during sync. You can
    add custom filters for bots specific to your workspace.

    Args:
        database: Database instance
        add_filters: List of filters to add [{"type": "name", "value": "custombot"}]
        remove_filters: List of filters to remove

    Returns:
        Dict with current bot filter configuration

    Example:
        PM: "Add a bot filter for our custom bot 'deploybot'"

        Assistant: [Calls configure_bot_filters]

        ✅ Bot filter added: deploybot

        **Current bot filters** (18 filters):
        - slackbot
        - github
        - jira
        - deploybot ← NEW
        ...

        These bots will be filtered out during Slack sync.
    """
    logger.info("Configuring bot filters")

    try:
        bot_filter = BotFilter(database)

        # Add filters
        if add_filters:
            for filter_config in add_filters:
                bot_filter.add_filter(
                    filter_type=filter_config["type"],
                    filter_value=filter_config["value"],
                )

        # Remove filters
        if remove_filters:
            for filter_config in remove_filters:
                bot_filter.remove_filter(
                    filter_type=filter_config["type"],
                    filter_value=filter_config["value"],
                )

        # Get all filters
        all_filters = bot_filter.get_all_filters()

        # Build message
        lines = []
        if add_filters:
            lines.append(f"✅ Added {len(add_filters)} bot filter(s)")
        if remove_filters:
            lines.append(f"✅ Removed {len(remove_filters)} bot filter(s)")

        lines.append("")
        lines.append(f"**Current bot filters** ({len(all_filters)} filters):")
        lines.append("")

        # Group by type
        by_type = {}
        for f in all_filters:
            filter_type = f["filter_type"]
            if filter_type not in by_type:
                by_type[filter_type] = []
            by_type[filter_type].append(f["filter_value"])

        for filter_type, values in by_type.items():
            lines.append(f"**{filter_type.title()}**:")
            for value in values[:10]:
                lines.append(f"- {value}")
            if len(values) > 10:
                lines.append(f"... and {len(values) - 10} more")
            lines.append("")

        lines.append("These bots will be filtered out during Slack sync.")

        return {
            "status": "success",
            "filters": all_filters,
            "message": "\n".join(lines),
        }

    except Exception as e:
        logger.error(f"Failed to configure bot filters: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"❌ Failed to configure bot filters: {str(e)}",
        }


async def tag_slack_message_with_customer(
    api_client: ProduckAIClient,
    message_id: str,
    customer_name: str,
) -> Dict[str, Any]:
    """
    Manually link a Slack message to a customer.

    Use this when AI classification detected feedback but couldn't
    automatically match it to a customer. The message_id is the Slack
    timestamp (shown in sync results for items requiring manual tagging).

    Args:
        api_client: ProduckAI API client
        message_id: Slack message timestamp ID
        customer_name: Customer name to link

    Returns:
        Dict with updated feedback information

    Example:
        PM: "Link Slack message 1705320000.123456 to Acme Corp"

        Assistant: [Calls tag_slack_message_with_customer]

        ✅ Updated feedback item!
        - Message: "We need bulk export ASAP"
        - Customer: Acme Corp
        - Feedback ID: abc-123-def

        The feedback is now linked to Acme Corp and will appear in
        customer-specific queries and insights.
    """
    logger.info(f"Tagging Slack message {message_id} with customer {customer_name}")

    try:
        # Search for feedback by message ID in metadata
        feedback_items = await api_client.search_feedback(query=message_id, source="slack")

        if not feedback_items:
            return {
                "status": "error",
                "message": (
                    f"❌ Feedback not found for message ID: {message_id}\n\n"
                    "The message may not have been classified as feedback, "
                    "or the sync may not have completed yet."
                ),
            }

        # Note: This would require a PATCH endpoint on the backend
        # For now, return a helpful message
        feedback = feedback_items[0]

        return {
            "status": "partial",
            "message": (
                f"⚠️ Manual tagging endpoint not yet implemented.\n\n"
                f"**Feedback found**:\n"
                f"- Text: {feedback.text[:100]}...\n"
                f"- ID: {feedback.id}\n"
                f"- Current customer: {feedback.customer_name or 'None'}\n\n"
                f"**Workaround**:\n"
                f"Contact the backend team to manually update feedback {feedback.id} "
                f"with customer_name = '{customer_name}'"
            ),
        }

    except Exception as e:
        logger.error(f"Failed to tag message: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"❌ Failed to tag message: {str(e)}",
        }
