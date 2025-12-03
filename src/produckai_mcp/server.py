"""ProduckAI MCP Server - Main server implementation."""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from produckai_mcp.api.client import ProduckAIClient
from produckai_mcp.config import Config, get_config, get_config_dir
from produckai_mcp.state.database import Database
from produckai_mcp.state.job_manager import JobManager
from produckai_mcp.state.sync_state import SyncStateManager
from produckai_mcp.tools.ingestion import gdrive, jira, manual, slack, zoom
from produckai_mcp.tools.processing import clustering
from produckai_mcp.tools.prd import generation as prd
from produckai_mcp.tools.query import feedback, insights
from produckai_mcp.tools.voc import scoring as voc
from produckai_mcp.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


class ProduckAIMCPServer:
    """ProduckAI MCP Server."""

    def __init__(self):
        """Initialize the MCP server."""
        # Load configuration
        self.config = get_config()

        # Setup logging
        log_file = self.config.get_log_file_path()
        setup_logging(
            log_level=self.config.server.log_level,
            log_file=log_file,
            console=False,
        )

        logger.info("=" * 60)
        logger.info("ProduckAI MCP Server Starting")
        logger.info(f"Version: {self.config.server.version}")
        logger.info(f"Backend URL: {self.config.backend.url}")
        logger.info(f"Config directory: {get_config_dir()}")
        logger.info("=" * 60)

        # Initialize database
        db_path = self.config.get_state_db_path()
        self.db = Database(db_path)
        logger.info(f"Database initialized: {db_path}")

        # Initialize state managers
        self.sync_state = SyncStateManager(self.db)
        self.job_manager = JobManager(self.db)

        # Initialize API client
        self.api_client = ProduckAIClient(self.config.backend)

        # Create MCP server
        self.server = Server(self.config.server.name)

        # Register handlers
        self._register_handlers()

        logger.info("Server initialization complete")

    def _register_handlers(self) -> None:
        """Register MCP protocol handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="ping_backend",
                    description="Test connection to ProduckAI backend. Returns health status and confirms the backend is reachable.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                Tool(
                    name="echo",
                    description="Simple echo tool for testing. Returns the input message back.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Message to echo back",
                            }
                        },
                        "required": ["message"],
                    },
                ),
                Tool(
                    name="get_pipeline_status",
                    description="Get the current status of the ProduckAI data pipeline. Shows feedback counts, theme counts, insight counts, and last clustering run time.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                # Phase 1: Manual Ingestion Tools
                Tool(
                    name="capture_raw_feedback",
                    description="Capture feedback directly from PM's natural language input. Use this when the PM mentions customer feedback during conversation. Automatically links to customer if name is mentioned.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "feedback_text": {
                                "type": "string",
                                "description": "The feedback content",
                            },
                            "customer_name": {
                                "type": "string",
                                "description": "Optional customer name",
                            },
                            "source": {
                                "type": "string",
                                "description": "Source identifier (default: pm_conversation)",
                                "default": "pm_conversation",
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Additional context (urgency, blocker, etc.)",
                            },
                        },
                        "required": ["feedback_text"],
                    },
                ),
                Tool(
                    name="upload_csv_feedback",
                    description="Upload a CSV file containing customer feedback. Supports multiple templates (standard, customer_interview, support_tickets). Use get_csv_template first to see format requirements.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to CSV file (e.g., ~/Desktop/feedback.csv)",
                            },
                            "template_type": {
                                "type": "string",
                                "description": "Template type: standard, customer_interview, or support_tickets",
                                "default": "standard",
                                "enum": ["standard", "customer_interview", "support_tickets"],
                            },
                        },
                        "required": ["file_path"],
                    },
                ),
                Tool(
                    name="upload_zoom_transcript",
                    description="Upload a Zoom transcript (.vtt file) for processing. Automatically extracts speaker segments and identifies feedback. Provide meeting metadata to link feedback to customers.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to .vtt transcript file",
                            },
                            "meeting_metadata": {
                                "type": "object",
                                "description": "Meeting info (customer_name, meeting_type, date, participants)",
                            },
                        },
                        "required": ["file_path"],
                    },
                ),
                Tool(
                    name="get_csv_template",
                    description="Get CSV template specification with column definitions, data types, and example rows. Use this before uploading a CSV to understand the required format.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "template_type": {
                                "type": "string",
                                "description": "Template type: standard, customer_interview, or support_tickets",
                                "default": "standard",
                                "enum": ["standard", "customer_interview", "support_tickets"],
                            },
                        },
                        "required": [],
                    },
                ),
                # Phase 1: Query Tools
                Tool(
                    name="search_insights",
                    description="Search for AI-generated insights using natural language queries or filters. Insights are derived from clustered feedback and include severity, priority scores, and customer impact. Useful for finding product issues, feature requests, and opportunities.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language search query (e.g., 'API performance issues')",
                            },
                            "severity": {
                                "type": "string",
                                "description": "Filter by severity",
                                "enum": ["critical", "high", "medium", "low"],
                            },
                            "min_priority_score": {
                                "type": "number",
                                "description": "Minimum priority score (0-100)",
                            },
                            "limit": {
                                "type": "number",
                                "description": "Maximum number of results",
                                "default": 20,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="get_insight_details",
                    description="Get complete details for a specific insight including full description, impact analysis, recommendations, supporting feedback quotes, customer breakdown by segment, and related JIRA tickets.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "insight_id": {
                                "type": "string",
                                "description": "Insight UUID",
                            },
                        },
                        "required": ["insight_id"],
                    },
                ),
                Tool(
                    name="search_feedback",
                    description="Search raw feedback items using natural language queries or filters. Useful for finding specific customer mentions, exploring feedback from a source, or investigating topics. Returns original feedback with metadata.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language search query",
                            },
                            "source": {
                                "type": "string",
                                "description": "Filter by source",
                                "enum": ["csv", "slack", "gdrive", "zoom", "jira", "manual", "pm_conversation"],
                            },
                            "customer_name": {
                                "type": "string",
                                "description": "Filter by specific customer",
                            },
                            "limit": {
                                "type": "number",
                                "description": "Maximum number of results",
                                "default": 50,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="get_customer_feedback",
                    description="Get all feedback from a specific customer along with insights affecting that customer. Useful for preparing for customer meetings or understanding customer pain points. Includes source breakdown and timeline.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "customer_name": {
                                "type": "string",
                                "description": "Customer name",
                            },
                        },
                        "required": ["customer_name"],
                    },
                ),
                # Phase 2: Clustering & Processing Tools
                Tool(
                    name="run_clustering",
                    description="Trigger the clustering pipeline to analyze feedback and generate themes and insights. Clustering groups similar feedback together using AI to identify patterns and create actionable insights. Run this after uploading new feedback or when you want to refresh the analysis.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "min_feedback_count": {
                                "type": "number",
                                "description": "Minimum feedback items required (default: backend setting, typically 50)",
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="get_themes",
                    description="Get all discovered themes from clustering. Themes are high-level topics that group similar feedback together. Each theme contains multiple related feedback items and generates insights. Use this to see what patterns have been identified across all feedback.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                Tool(
                    name="get_theme_details",
                    description="Get complete details for a specific theme including full description, all feedback items, customer breakdown, and related insights. Use this to deep-dive into a particular theme.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "theme_id": {
                                "type": "string",
                                "description": "UUID of the theme",
                            },
                        },
                        "required": ["theme_id"],
                    },
                ),
                Tool(
                    name="generate_embeddings",
                    description="Generate embeddings for feedback items that don't have them yet. Embeddings are required for clustering and semantic search. They're automatically created when feedback is uploaded, but use this tool to retry failed generations or process direct API uploads.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                # Phase 3: Slack Integration Tools
                Tool(
                    name="setup_slack_integration",
                    description="Set up Slack integration using OAuth. Opens a browser to authorize the app and stores the access token securely. Required before syncing any Slack channels. You'll need Slack Client ID and Client Secret (create an app at api.slack.com).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "client_id": {
                                "type": "string",
                                "description": "Slack OAuth Client ID",
                            },
                            "client_secret": {
                                "type": "string",
                                "description": "Slack OAuth Client Secret",
                            },
                        },
                        "required": ["client_id", "client_secret"],
                    },
                ),
                Tool(
                    name="list_slack_channels",
                    description="List all accessible Slack channels in the connected workspace. Shows channel names, IDs, member counts, and whether they're public/private. Use this to discover which channels to sync for feedback collection.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                Tool(
                    name="sync_slack_channels",
                    description="Sync messages from specified Slack channels and extract customer feedback using AI classification. Uses Claude to identify genuine feedback vs noise. Supports delta sync (only new messages) and automatically links feedback to customers when mentioned. Bot messages are filtered out.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "channel_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of channel names to sync (e.g., ['customer-feedback', 'support'])",
                            },
                            "force_full_sync": {
                                "type": "boolean",
                                "description": "Force full sync instead of delta (default: false)",
                                "default": False,
                            },
                        },
                        "required": ["channel_names"],
                    },
                ),
                Tool(
                    name="get_slack_sync_status",
                    description="View sync history and status for all Slack channels. Shows last sync time, message counts, success/failure status, and identifies channels that need attention. Helpful for monitoring sync health.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                Tool(
                    name="configure_bot_filters",
                    description="Manage bot filters to prevent bot messages from being processed as feedback. View, add, remove, enable/disable filters. Supports exact name matching, regex patterns, and bot IDs. Default filters included for common bots (Slackbot, GitHub, JIRA, etc.).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "Action to perform",
                                "enum": ["list", "add", "remove", "enable", "disable"],
                            },
                            "filter_type": {
                                "type": "string",
                                "description": "Filter type (required for add/remove/enable/disable)",
                                "enum": ["name", "pattern", "bot_id"],
                            },
                            "filter_value": {
                                "type": "string",
                                "description": "Filter value (required for add/remove/enable/disable)",
                            },
                        },
                        "required": ["action"],
                    },
                ),
                # Phase 4: Google Drive Integration Tools
                Tool(
                    name="setup_google_drive_integration",
                    description="Set up Google Drive integration using OAuth. Opens a browser to authorize the app and stores credentials securely. Required before syncing any Drive folders. You'll need Google OAuth Client ID and Client Secret (create credentials at console.cloud.google.com).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "client_id": {
                                "type": "string",
                                "description": "Google OAuth Client ID",
                            },
                            "client_secret": {
                                "type": "string",
                                "description": "Google OAuth Client Secret",
                            },
                        },
                        "required": ["client_id", "client_secret"],
                    },
                ),
                Tool(
                    name="browse_drive_folders",
                    description="Browse Google Drive folders and view statistics. Lists folders with file counts, supported types (Docs, Sheets, PDFs), and nested structure. Use this to discover which folders contain feedback documents before syncing.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "folder_id": {
                                "type": "string",
                                "description": "Optional folder ID to browse (omit for root/My Drive)",
                            },
                            "show_statistics": {
                                "type": "boolean",
                                "description": "Include file counts and type breakdown (default: true)",
                                "default": True,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="sync_drive_folders",
                    description="Sync Google Drive folders and extract customer feedback from documents. Processes Google Docs (with structure and comments), Google Sheets (with format detection), and PDFs (with text extraction). Uses AI to classify content as feedback and extract customer names. Supports delta sync to only process new/modified files.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "folder_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of folder IDs to sync",
                            },
                            "file_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "File types to process: 'docs', 'sheets', 'pdf' (default: all)",
                            },
                            "force_full_sync": {
                                "type": "boolean",
                                "description": "Force full sync instead of delta (default: false)",
                                "default": False,
                            },
                        },
                        "required": ["folder_ids"],
                    },
                ),
                Tool(
                    name="get_drive_sync_status",
                    description="View sync history and status for all Google Drive folders. Shows last sync time, file counts, success/failure status, and identifies folders that need attention. Helpful for monitoring sync health.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                Tool(
                    name="preview_drive_folder",
                    description="Preview what would be synced from a Drive folder without processing. Shows file counts by type, estimated processing time and cost, and lists sample files. Use this before running sync_drive_folders to understand scope.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "folder_id": {
                                "type": "string",
                                "description": "Folder ID to preview",
                            },
                            "file_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "File types to preview: 'docs', 'sheets', 'pdf' (default: all)",
                            },
                        },
                        "required": ["folder_id"],
                    },
                ),
                Tool(
                    name="configure_drive_processing",
                    description="Manage Google Drive processing settings. Configure file size limits, classification thresholds, customer matching rules, and more. View current settings or update specific configurations.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "Action to perform",
                                "enum": ["list", "update"],
                            },
                            "setting": {
                                "type": "string",
                                "description": "Setting to update (required for update action)",
                            },
                            "value": {
                                "description": "New value for the setting (required for update action)",
                            },
                        },
                        "required": ["action"],
                    },
                ),
                # Phase 5: JIRA Integration Tools
                Tool(
                    name="setup_jira_integration",
                    description="Set up JIRA integration with API token authentication. Create API token at id.atlassian.com/manage-profile/security/api-tokens. Required before syncing feedback to JIRA or importing from JIRA.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "server_url": {
                                "type": "string",
                                "description": "JIRA instance URL (e.g., https://yourcompany.atlassian.net)",
                            },
                            "email": {
                                "type": "string",
                                "description": "User email address",
                            },
                            "api_token": {
                                "type": "string",
                                "description": "JIRA API token",
                            },
                        },
                        "required": ["server_url", "email", "api_token"],
                    },
                ),
                Tool(
                    name="browse_jira_projects",
                    description="Browse accessible JIRA projects with metadata. Shows project keys, names, issue types, and components. Use this to discover which projects to sync feedback to.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "show_details": {
                                "type": "boolean",
                                "description": "Include detailed project info (issue types, components)",
                                "default": True,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="sync_feedback_to_jira",
                    description="Create JIRA issues from high-priority feedback. Uses VOC scores to prioritize which feedback to sync. Automatically sets priority based on VOC score and links issues back to feedback.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_key": {
                                "type": "string",
                                "description": "JIRA project key (e.g., 'PROD')",
                            },
                            "theme_id": {
                                "type": "string",
                                "description": "Optional theme ID to create issues from",
                            },
                            "feedback_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional specific feedback IDs to sync",
                            },
                            "issue_type": {
                                "type": "string",
                                "description": "JIRA issue type (Task, Story, Bug, etc.)",
                                "default": "Task",
                            },
                            "min_voc_score": {
                                "type": "number",
                                "description": "Minimum VOC score to sync (0-100)",
                                "default": 60.0,
                            },
                            "auto_link": {
                                "type": "boolean",
                                "description": "Automatically link created issues back to feedback",
                                "default": True,
                            },
                        },
                        "required": ["project_key"],
                    },
                ),
                Tool(
                    name="sync_jira_to_feedback",
                    description="Import feedback from JIRA issues. Extracts customer feedback from JIRA issue descriptions and comments. Useful for centralizing feedback from JIRA tickets.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_key": {
                                "type": "string",
                                "description": "JIRA project key to import from",
                            },
                            "jql_filter": {
                                "type": "string",
                                "description": "Optional JQL filter (e.g., 'labels = customer-feedback')",
                            },
                            "max_issues": {
                                "type": "number",
                                "description": "Maximum issues to process",
                                "default": 50,
                            },
                        },
                        "required": ["project_key"],
                    },
                ),
                Tool(
                    name="link_feedback_to_jira",
                    description="Manually link a feedback item to an existing JIRA issue. Use this to connect feedback to issues created outside the sync process.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "feedback_id": {
                                "type": "string",
                                "description": "Feedback UUID",
                            },
                            "jira_issue_key": {
                                "type": "string",
                                "description": "JIRA issue key (e.g., 'PROJ-123')",
                            },
                        },
                        "required": ["feedback_id", "jira_issue_key"],
                    },
                ),
                Tool(
                    name="get_jira_sync_status",
                    description="View JIRA sync status and linked issues. Shows recent issues, feedback counts, and sync history. Helpful for monitoring JIRA integration health.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                Tool(
                    name="configure_jira_mapping",
                    description="Configure JIRA field mappings and sync settings. Set default project, issue type, priority mapping, and other sync options.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "Action to perform",
                                "enum": ["list", "set", "delete"],
                            },
                            "setting": {
                                "type": "string",
                                "description": "Setting key (for set/delete)",
                            },
                            "value": {
                                "description": "Setting value (for set)",
                            },
                        },
                        "required": ["action"],
                    },
                ),
                Tool(
                    name="get_jira_feedback_report",
                    description="Generate feedback coverage report for JIRA. Shows what percentage of feedback is tracked in JIRA, response times, and other metrics.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                # Phase 5: Enhanced Zoom Integration Tools
                Tool(
                    name="setup_zoom_integration",
                    description="Set up Zoom integration with Server-to-Server OAuth. Create credentials at marketplace.zoom.us/develop/create. Enables auto-fetching of meeting recordings and transcripts.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_id": {
                                "type": "string",
                                "description": "Zoom Account ID",
                            },
                            "client_id": {
                                "type": "string",
                                "description": "Zoom OAuth Client ID",
                            },
                            "client_secret": {
                                "type": "string",
                                "description": "Zoom OAuth Client Secret",
                            },
                        },
                        "required": ["account_id", "client_id", "client_secret"],
                    },
                ),
                Tool(
                    name="sync_zoom_recordings",
                    description="Auto-fetch Zoom recordings and extract feedback. Downloads transcripts, parses speaker segments, and classifies content as feedback using AI. Supports delta sync.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "days_back": {
                                "type": "number",
                                "description": "Number of days to look back",
                                "default": 30,
                            },
                            "auto_classify": {
                                "type": "boolean",
                                "description": "Automatically classify transcript as feedback",
                                "default": True,
                            },
                            "min_duration": {
                                "type": "number",
                                "description": "Minimum meeting duration in minutes",
                                "default": 5,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="analyze_zoom_meeting",
                    description="Analyze a specific Zoom meeting for insights. Extracts key topics, speaker sentiment, action items, and customer pain points using AI.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "meeting_id": {
                                "type": "string",
                                "description": "Zoom meeting ID",
                            },
                            "include_sentiment": {
                                "type": "boolean",
                                "description": "Analyze speaker sentiment",
                                "default": True,
                            },
                            "include_topics": {
                                "type": "boolean",
                                "description": "Extract discussion topics",
                                "default": True,
                            },
                        },
                        "required": ["meeting_id"],
                    },
                ),
                Tool(
                    name="get_zoom_insights",
                    description="Get insights from Zoom meeting data. Shows meeting frequency, most discussed topics, sentiment trends, and customer engagement metrics.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "days_back": {
                                "type": "number",
                                "description": "Number of days to analyze",
                                "default": 30,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="link_zoom_to_customers",
                    description="Link a Zoom meeting to a customer. Updates all feedback from this meeting with the customer name. Useful for correcting customer attribution.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "meeting_id": {
                                "type": "string",
                                "description": "Zoom meeting ID",
                            },
                            "customer_name": {
                                "type": "string",
                                "description": "Customer name",
                            },
                        },
                        "required": ["meeting_id", "customer_name"],
                    },
                ),
                # Phase 5: VOC (Voice of Customer) Scoring Tools
                Tool(
                    name="calculate_voc_scores",
                    description="Calculate VOC (Voice of Customer) scores for feedback or themes. Scores 0-100 based on customer impact, frequency, recency, sentiment, theme alignment, and effort. Higher scores = higher priority.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "target_type": {
                                "type": "string",
                                "description": "Type to score: 'feedback' or 'theme'",
                                "enum": ["feedback", "theme"],
                                "default": "feedback",
                            },
                            "target_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional specific IDs to score",
                            },
                            "theme_id": {
                                "type": "string",
                                "description": "Optional theme ID to score all feedback within",
                            },
                            "min_score": {
                                "type": "number",
                                "description": "Optional minimum score threshold for results",
                            },
                            "store_results": {
                                "type": "boolean",
                                "description": "Store scores in database",
                                "default": True,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="get_top_feedback_by_voc",
                    description="Get top-ranked feedback by VOC score. Shows highest priority feedback with score breakdowns. Use this to identify what to work on next.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "number",
                                "description": "Maximum results to return",
                                "default": 20,
                            },
                            "min_score": {
                                "type": "number",
                                "description": "Minimum VOC score filter",
                            },
                            "theme_id": {
                                "type": "string",
                                "description": "Optional filter by theme",
                            },
                            "customer_tier": {
                                "type": "string",
                                "description": "Optional filter by customer tier",
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="configure_voc_weights",
                    description="Configure VOC scoring weights. Adjust how much each dimension (customer impact, frequency, recency, etc.) contributes to the total score. Weights must sum to 1.0.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "Action to perform",
                                "enum": ["list", "update"],
                                "default": "list",
                            },
                            "customer_impact": {
                                "type": "number",
                                "description": "Weight for customer impact (0-1)",
                            },
                            "frequency": {
                                "type": "number",
                                "description": "Weight for feedback frequency (0-1)",
                            },
                            "recency": {
                                "type": "number",
                                "description": "Weight for feedback recency (0-1)",
                            },
                            "sentiment": {
                                "type": "number",
                                "description": "Weight for sentiment/urgency (0-1)",
                            },
                            "theme_alignment": {
                                "type": "number",
                                "description": "Weight for strategic alignment (0-1)",
                            },
                            "effort_estimate": {
                                "type": "number",
                                "description": "Weight for implementation effort (0-1)",
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="get_voc_trends",
                    description="Analyze VOC score trends over time. Shows how feedback priority is changing. Identifies whether issues are becoming more or less urgent.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "days_back": {
                                "type": "number",
                                "description": "Number of days to analyze",
                                "default": 90,
                            },
                            "group_by": {
                                "type": "string",
                                "description": "Grouping period",
                                "enum": ["day", "week", "month"],
                                "default": "week",
                            },
                        },
                        "required": [],
                    },
                ),
                # Phase 6: PRD Generation Tools
                Tool(
                    name="generate_prd",
                    description="Generate a Product Requirements Document (PRD) from an insight. Creates a strategic, engineering-ready PRD using AI-powered analysis. Includes strategic alignment, evidence-based problem statement, solution hypothesis, success metrics, risk assessment, and roadmap. Perfect for turning customer feedback insights into actionable product specs.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "insight_id": {
                                "type": "string",
                                "description": "UUID of the insight to generate PRD from",
                            },
                            "include_appendix": {
                                "type": "boolean",
                                "description": "Include customer breakdown and full quote list",
                                "default": True,
                            },
                            "auto_save": {
                                "type": "boolean",
                                "description": "Automatically save PRD to database",
                                "default": True,
                            },
                        },
                        "required": ["insight_id"],
                    },
                ),
                Tool(
                    name="list_prds",
                    description="List generated PRDs with optional filters. Browse all PRDs created by the PRD generator. Filter by status (draft/reviewed/approved) or theme. See metadata including word count, pages, and generation date at a glance.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "description": "Filter by status",
                                "enum": ["draft", "reviewed", "approved"],
                            },
                            "theme_id": {
                                "type": "string",
                                "description": "Filter by theme UUID",
                            },
                            "limit": {
                                "type": "number",
                                "description": "Maximum number of results",
                                "default": 20,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="get_prd",
                    description="Get full details for a specific PRD. Retrieves complete PRD content including markdown text, metadata (ACV, segment, persona), generation parameters, statistics (word count, pages), version, and status information. Use this to view or review a generated PRD.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prd_id": {
                                "type": "string",
                                "description": "UUID of the PRD",
                            },
                        },
                        "required": ["prd_id"],
                    },
                ),
                Tool(
                    name="update_prd_status",
                    description="Update the workflow status of a PRD. Change PRD status between draft, reviewed, and approved. Tracks progression through the PRD review process. Use this to mark PRDs as reviewed by stakeholders or approved for implementation.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prd_id": {
                                "type": "string",
                                "description": "UUID of the PRD",
                            },
                            "status": {
                                "type": "string",
                                "description": "New status",
                                "enum": ["draft", "reviewed", "approved"],
                            },
                        },
                        "required": ["prd_id", "status"],
                    },
                ),
                Tool(
                    name="regenerate_prd",
                    description="Regenerate a PRD after insight updates. Creates a new version of an existing PRD, incorporating any changes to the underlying insight data (new feedback, updated severity, changed recommendations, etc.). Increments version number and maintains history.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prd_id": {
                                "type": "string",
                                "description": "UUID of the PRD to regenerate",
                            },
                        },
                        "required": ["prd_id"],
                    },
                ),
                Tool(
                    name="export_prd",
                    description="Export a PRD to a markdown file. Saves PRD content to a .md file for sharing, archiving, or importing into other tools (Confluence, Notion, GitHub, etc.). Defaults to user's Downloads directory with a sanitized filename.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prd_id": {
                                "type": "string",
                                "description": "UUID of the PRD",
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Optional custom output path (defaults to ~/Downloads)",
                            },
                        },
                        "required": ["prd_id"],
                    },
                ),
                Tool(
                    name="tag_slack_message_with_customer",
                    description="Manually link a Slack message to a customer. Use this when AI classification couldn't extract the customer name or made a mistake. Useful for improving customer attribution accuracy.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "feedback_id": {
                                "type": "string",
                                "description": "Feedback UUID from search results",
                            },
                            "customer_name": {
                                "type": "string",
                                "description": "Customer name to link",
                            },
                        },
                        "required": ["feedback_id", "customer_name"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Handle tool calls."""
            try:
                logger.info(f"Tool called: {name} with arguments: {arguments}")

                # Phase 0 tools
                if name == "ping_backend":
                    return await self._handle_ping_backend()
                elif name == "echo":
                    return await self._handle_echo(arguments)
                elif name == "get_pipeline_status":
                    return await self._handle_get_pipeline_status()

                # Phase 1: Manual ingestion tools
                elif name == "capture_raw_feedback":
                    result = await manual.capture_raw_feedback(
                        self.api_client,
                        feedback_text=arguments["feedback_text"],
                        customer_name=arguments.get("customer_name"),
                        source=arguments.get("source", "pm_conversation"),
                        metadata=arguments.get("metadata"),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "upload_csv_feedback":
                    result = await manual.upload_csv_feedback(
                        self.api_client,
                        file_path=arguments["file_path"],
                        template_type=arguments.get("template_type", "standard"),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "upload_zoom_transcript":
                    result = await manual.upload_zoom_transcript(
                        self.api_client,
                        file_path=arguments["file_path"],
                        meeting_metadata=arguments.get("meeting_metadata"),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "get_csv_template":
                    result = await manual.get_csv_template(
                        template_type=arguments.get("template_type", "standard"),
                    )
                    return [TextContent(type="text", text=result.get("formatted_description", str(result)))]

                # Phase 1: Query tools
                elif name == "search_insights":
                    result = await insights.search_insights(
                        self.api_client,
                        query=arguments.get("query"),
                        severity=arguments.get("severity"),
                        min_priority_score=arguments.get("min_priority_score"),
                        limit=arguments.get("limit", 20),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "get_insight_details":
                    result = await insights.get_insight_details(
                        self.api_client,
                        insight_id=arguments["insight_id"],
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "search_feedback":
                    result = await feedback.search_feedback(
                        self.api_client,
                        query=arguments.get("query"),
                        source=arguments.get("source"),
                        customer_name=arguments.get("customer_name"),
                        limit=arguments.get("limit", 50),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "get_customer_feedback":
                    result = await feedback.get_customer_feedback(
                        self.api_client,
                        customer_name=arguments["customer_name"],
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                # Phase 2: Clustering & processing tools
                elif name == "run_clustering":
                    result = await clustering.run_clustering(
                        self.api_client,
                        min_feedback_count=arguments.get("min_feedback_count"),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "get_themes":
                    result = await clustering.get_themes(
                        self.api_client,
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "get_theme_details":
                    result = await clustering.get_theme_details(
                        self.api_client,
                        theme_id=arguments["theme_id"],
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "generate_embeddings":
                    result = await clustering.generate_embeddings(
                        self.api_client,
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                # Phase 3: Slack integration tools
                elif name == "setup_slack_integration":
                    result = await slack.setup_slack_integration(
                        client_id=arguments["client_id"],
                        client_secret=arguments["client_secret"],
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "list_slack_channels":
                    result = await slack.list_slack_channels()
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "sync_slack_channels":
                    result = await slack.sync_slack_channels(
                        self.api_client,
                        self.db,
                        self.sync_state,
                        channel_names=arguments["channel_names"],
                        force_full_sync=arguments.get("force_full_sync", False),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "get_slack_sync_status":
                    result = await slack.get_slack_sync_status(
                        self.sync_state,
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "configure_bot_filters":
                    result = await slack.configure_bot_filters(
                        self.db,
                        action=arguments["action"],
                        filter_type=arguments.get("filter_type"),
                        filter_value=arguments.get("filter_value"),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "tag_slack_message_with_customer":
                    result = await slack.tag_slack_message_with_customer(
                        self.api_client,
                        feedback_id=arguments["feedback_id"],
                        customer_name=arguments["customer_name"],
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                # Phase 4: Google Drive Integration handlers
                elif name == "setup_google_drive_integration":
                    result = await gdrive.setup_google_drive_integration(
                        client_id=arguments["client_id"],
                        client_secret=arguments["client_secret"],
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "browse_drive_folders":
                    result = await gdrive.browse_drive_folders(
                        folder_id=arguments.get("folder_id"),
                        show_statistics=arguments.get("show_statistics", True),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "sync_drive_folders":
                    result = await gdrive.sync_drive_folders(
                        self.api_client,
                        self.db,
                        self.sync_state,
                        folder_ids=arguments["folder_ids"],
                        file_types=arguments.get("file_types"),
                        force_full_sync=arguments.get("force_full_sync", False),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "get_drive_sync_status":
                    result = await gdrive.get_drive_sync_status(
                        self.sync_state,
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "preview_drive_folder":
                    result = await gdrive.preview_drive_folder(
                        folder_id=arguments["folder_id"],
                        file_types=arguments.get("file_types"),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "configure_drive_processing":
                    result = await gdrive.configure_drive_processing(
                        self.db,
                        action=arguments["action"],
                        setting=arguments.get("setting"),
                        value=arguments.get("value"),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                # Phase 5: JIRA Integration handlers
                elif name == "setup_jira_integration":
                    result = await jira.setup_jira_integration(
                        server_url=arguments["server_url"],
                        email=arguments["email"],
                        api_token=arguments["api_token"],
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "browse_jira_projects":
                    result = await jira.browse_jira_projects(
                        show_details=arguments.get("show_details", True),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "sync_feedback_to_jira":
                    result = await jira.sync_feedback_to_jira(
                        self.api_client,
                        self.db,
                        project_key=arguments["project_key"],
                        theme_id=arguments.get("theme_id"),
                        feedback_ids=arguments.get("feedback_ids"),
                        issue_type=arguments.get("issue_type", "Task"),
                        min_voc_score=arguments.get("min_voc_score", 60.0),
                        auto_link=arguments.get("auto_link", True),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "sync_jira_to_feedback":
                    result = await jira.sync_jira_to_feedback(
                        self.api_client,
                        project_key=arguments["project_key"],
                        jql_filter=arguments.get("jql_filter"),
                        max_issues=arguments.get("max_issues", 50),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "link_feedback_to_jira":
                    result = await jira.link_feedback_to_jira(
                        self.db,
                        feedback_id=arguments["feedback_id"],
                        jira_issue_key=arguments["jira_issue_key"],
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "get_jira_sync_status":
                    result = await jira.get_jira_sync_status(
                        self.db,
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "configure_jira_mapping":
                    result = await jira.configure_jira_mapping(
                        self.db,
                        action=arguments["action"],
                        setting=arguments.get("setting"),
                        value=arguments.get("value"),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "get_jira_feedback_report":
                    result = await jira.get_jira_feedback_report(
                        self.api_client,
                        self.db,
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                # Phase 5: Zoom Integration handlers
                elif name == "setup_zoom_integration":
                    result = await zoom.setup_zoom_integration(
                        account_id=arguments["account_id"],
                        client_id=arguments["client_id"],
                        client_secret=arguments["client_secret"],
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "sync_zoom_recordings":
                    result = await zoom.sync_zoom_recordings(
                        self.api_client,
                        self.sync_state,
                        days_back=arguments.get("days_back", 30),
                        auto_classify=arguments.get("auto_classify", True),
                        min_duration=arguments.get("min_duration", 5),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "analyze_zoom_meeting":
                    result = await zoom.analyze_zoom_meeting(
                        meeting_id=arguments["meeting_id"],
                        include_sentiment=arguments.get("include_sentiment", True),
                        include_topics=arguments.get("include_topics", True),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "get_zoom_insights":
                    result = await zoom.get_zoom_insights(
                        self.db,
                        days_back=arguments.get("days_back", 30),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "link_zoom_to_customers":
                    result = await zoom.link_zoom_to_customers(
                        self.api_client,
                        self.db,
                        meeting_id=arguments["meeting_id"],
                        customer_name=arguments["customer_name"],
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                # Phase 5: VOC Scoring handlers
                elif name == "calculate_voc_scores":
                    result = await voc.calculate_voc_scores(
                        self.api_client,
                        self.db,
                        target_type=arguments.get("target_type", "feedback"),
                        target_ids=arguments.get("target_ids"),
                        theme_id=arguments.get("theme_id"),
                        min_score=arguments.get("min_score"),
                        store_results=arguments.get("store_results", True),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "get_top_feedback_by_voc":
                    result = await voc.get_top_feedback_by_voc(
                        self.db,
                        limit=arguments.get("limit", 20),
                        min_score=arguments.get("min_score"),
                        theme_id=arguments.get("theme_id"),
                        customer_tier=arguments.get("customer_tier"),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "configure_voc_weights":
                    result = await voc.configure_voc_weights(
                        self.db,
                        action=arguments.get("action", "list"),
                        customer_impact=arguments.get("customer_impact"),
                        frequency=arguments.get("frequency"),
                        recency=arguments.get("recency"),
                        sentiment=arguments.get("sentiment"),
                        theme_alignment=arguments.get("theme_alignment"),
                        effort_estimate=arguments.get("effort_estimate"),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "get_voc_trends":
                    result = await voc.get_voc_trends(
                        self.db,
                        days_back=arguments.get("days_back", 90),
                        group_by=arguments.get("group_by", "week"),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                # Phase 6: PRD Generation handlers
                elif name == "generate_prd":
                    result = await prd.generate_prd(
                        self.api_client,
                        self.db,
                        insight_id=arguments["insight_id"],
                        include_appendix=arguments.get("include_appendix", True),
                        auto_save=arguments.get("auto_save", True),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "list_prds":
                    result = await prd.list_prds(
                        self.db,
                        status=arguments.get("status"),
                        theme_id=arguments.get("theme_id"),
                        limit=arguments.get("limit", 20),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "get_prd":
                    result = await prd.get_prd(
                        self.db,
                        prd_id=arguments["prd_id"],
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "update_prd_status":
                    result = await prd.update_prd_status(
                        self.db,
                        prd_id=arguments["prd_id"],
                        status=arguments["status"],
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "regenerate_prd":
                    result = await prd.regenerate_prd(
                        self.api_client,
                        self.db,
                        prd_id=arguments["prd_id"],
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                elif name == "export_prd":
                    result = await prd.export_prd(
                        self.db,
                        prd_id=arguments["prd_id"],
                        output_path=arguments.get("output_path"),
                    )
                    return [TextContent(type="text", text=result.get("message", str(result)))]

                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Unknown tool: {name}",
                        )
                    ]

            except Exception as e:
                logger.error(f"Error handling tool {name}: {str(e)}", exc_info=True)
                return [
                    TextContent(
                        type="text",
                        text=f"Error: {str(e)}",
                    )
                ]

    async def _handle_ping_backend(self) -> list[TextContent]:
        """Handle ping_backend tool."""
        try:
            health = await self.api_client.health_check()
            return [
                TextContent(
                    type="text",
                    text=f"✅ Backend is healthy!\n\nBackend URL: {self.config.backend.url}\nStatus: {health.get('status', 'unknown')}\n\nConnection successful.",
                )
            ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Backend connection failed!\n\nBackend URL: {self.config.backend.url}\nError: {str(e)}\n\nPlease ensure the ProduckAI backend is running:\n\ncd /path/to/produckai\ndocker-compose up -d",
                )
            ]

    async def _handle_echo(self, arguments: dict) -> list[TextContent]:
        """Handle echo tool."""
        message = arguments.get("message", "")
        return [
            TextContent(
                type="text",
                text=f"Echo: {message}",
            )
        ]

    async def _handle_get_pipeline_status(self) -> list[TextContent]:
        """Handle get_pipeline_status tool."""
        try:
            status = await self.api_client.get_pipeline_status()

            # Build status message
            lines = [
                "📊 ProduckAI Clustering Pipeline Status",
                "",
            ]

            # Clustering status
            if status.is_running:
                lines.append("**Status:** 🔄 Clustering is currently running...")
                if status.started_at:
                    lines.append(f"**Started at:** {status.started_at}")
            elif status.status == "completed":
                lines.append("**Status:** ✅ Last clustering completed successfully")
                if status.completed_at:
                    lines.append(f"**Completed at:** {status.completed_at}")
                lines.append("")
                lines.append("**Results:**")
                lines.append(f"  • Themes created: {status.themes_created or 0}")
                lines.append(f"  • Insights generated: {status.insights_created or 0}")
            elif status.status == "failed":
                lines.append("**Status:** ❌ Last clustering failed")
                if status.error:
                    lines.append(f"**Error:** {status.error}")
                if status.completed_at:
                    lines.append(f"**Failed at:** {status.completed_at}")
            elif status.status == "idle":
                lines.append("**Status:** ⏸️ No clustering has been run yet")
                lines.append("")
                lines.append("Use `run_clustering()` to start clustering your feedback.")
            else:
                lines.append(f"**Status:** {status.status}")

            lines.append("")
            lines.append("**Next steps:**")
            if status.is_running:
                lines.append("  • Wait for clustering to complete (check status again in a minute)")
            elif status.status == "completed":
                lines.append("  • Use `get_themes()` to see all discovered themes")
                lines.append("  • Use `search_insights()` to explore insights")
            elif status.status == "failed":
                lines.append("  • Check backend logs for error details")
                lines.append("  • Try running clustering again with `run_clustering()`")
            else:
                lines.append("  • Upload feedback with `capture_raw_feedback()` or `upload_csv_feedback()`")
                lines.append("  • Run clustering with `run_clustering()`")

            # Note: The backend's /cluster/status endpoint doesn't return feedback counts
            # or integration status - only clustering task status

            # Add sync summary
            sync_summary = self.sync_state.get_sync_summary()
            if sync_summary["total_resources"] > 0:
                lines.append("")
                lines.append("**Sync Summary:**")
                lines.append(f"  • Total resources synced: {sync_summary['total_resources']}")
                lines.append(f"  • Total items synced: {sync_summary['total_items_synced']}")

                for integration, stats in sync_summary["by_integration"].items():
                    lines.append(
                        f"  • {integration.title()}: {stats['resource_count']} resources, "
                        f"{stats['total_items']} items"
                    )

            return [TextContent(type="text", text="\n".join(lines))]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Failed to get pipeline status: {str(e)}",
                )
            ]

    async def run(self) -> None:
        """Run the MCP server."""
        try:
            logger.info("Starting MCP server...")

            # Run with stdio transport
            async with stdio_server() as (read_stream, write_stream):
                logger.info("Server running with stdio transport")
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options(),
                )

        except Exception as e:
            logger.error(f"Server error: {str(e)}", exc_info=True)
            raise
        finally:
            # Cleanup
            await self.api_client.close()
            logger.info("Server shutdown complete")


async def main() -> None:
    """Main entry point."""
    server = ProduckAIMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
