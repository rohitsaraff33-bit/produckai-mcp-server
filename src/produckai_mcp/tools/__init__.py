"""MCP tools for ProduckAI."""

from produckai_mcp.tools.ingestion.manual import (
    capture_raw_feedback,
    get_csv_template,
    upload_csv_feedback,
    upload_zoom_transcript,
)
from produckai_mcp.tools.ingestion.slack import (
    configure_bot_filters,
    get_slack_sync_status,
    list_slack_channels,
    setup_slack_integration,
    sync_slack_channels,
    tag_slack_message_with_customer,
)
from produckai_mcp.tools.ingestion.gdrive import (
    browse_drive_folders,
    configure_drive_processing,
    get_drive_sync_status,
    preview_drive_folder,
    setup_google_drive_integration,
    sync_drive_folders,
)
from produckai_mcp.tools.ingestion.jira import (
    browse_jira_projects,
    configure_jira_mapping,
    get_jira_feedback_report,
    get_jira_sync_status,
    link_feedback_to_jira,
    setup_jira_integration,
    sync_feedback_to_jira,
    sync_jira_to_feedback,
)
from produckai_mcp.tools.ingestion.zoom import (
    analyze_zoom_meeting,
    get_zoom_insights,
    link_zoom_to_customers,
    setup_zoom_integration,
    sync_zoom_recordings,
)
from produckai_mcp.tools.processing.clustering import (
    generate_embeddings,
    get_theme_details,
    get_themes,
    run_clustering,
)
from produckai_mcp.tools.query.feedback import get_customer_feedback, search_feedback
from produckai_mcp.tools.query.insights import get_insight_details, search_insights
from produckai_mcp.tools.voc.scoring import (
    calculate_voc_scores,
    configure_voc_weights,
    get_top_feedback_by_voc,
    get_voc_trends,
)
from produckai_mcp.tools.prd.generation import (
    export_prd,
    generate_prd,
    get_prd,
    list_prds,
    regenerate_prd,
    update_prd_status,
)

__all__ = [
    # Ingestion tools - Manual
    "capture_raw_feedback",
    "upload_csv_feedback",
    "upload_zoom_transcript",
    "get_csv_template",
    # Ingestion tools - Slack
    "setup_slack_integration",
    "list_slack_channels",
    "sync_slack_channels",
    "get_slack_sync_status",
    "configure_bot_filters",
    "tag_slack_message_with_customer",
    # Ingestion tools - Google Drive
    "setup_google_drive_integration",
    "browse_drive_folders",
    "sync_drive_folders",
    "get_drive_sync_status",
    "preview_drive_folder",
    "configure_drive_processing",
    # Ingestion tools - JIRA
    "setup_jira_integration",
    "browse_jira_projects",
    "sync_feedback_to_jira",
    "sync_jira_to_feedback",
    "link_feedback_to_jira",
    "get_jira_sync_status",
    "configure_jira_mapping",
    "get_jira_feedback_report",
    # Ingestion tools - Zoom
    "setup_zoom_integration",
    "sync_zoom_recordings",
    "analyze_zoom_meeting",
    "get_zoom_insights",
    "link_zoom_to_customers",
    # Processing tools
    "run_clustering",
    "get_themes",
    "get_theme_details",
    "generate_embeddings",
    # Query tools
    "search_insights",
    "get_insight_details",
    "search_feedback",
    "get_customer_feedback",
    # VOC Scoring tools
    "calculate_voc_scores",
    "get_top_feedback_by_voc",
    "configure_voc_weights",
    "get_voc_trends",
    # PRD Generation tools
    "generate_prd",
    "list_prds",
    "get_prd",
    "update_prd_status",
    "regenerate_prd",
    "export_prd",
]
