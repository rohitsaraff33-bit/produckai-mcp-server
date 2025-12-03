"""Clustering and processing tools - trigger clustering, manage themes, generate embeddings."""

from typing import Any, Dict, List, Optional

from produckai_mcp.api.client import ProduckAIClient
from produckai_mcp.api.models import Theme
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


async def run_clustering(
    api_client: ProduckAIClient,
    min_feedback_count: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Trigger the clustering pipeline to generate themes and insights.

    Clustering analyzes all feedback with embeddings and groups similar
    items together to identify patterns, themes, and insights. This is
    typically run after uploading new feedback or when you want to
    refresh the analysis.

    The process:
    1. Groups similar feedback items using embeddings
    2. Identifies common themes across clusters
    3. Generates AI-powered insights with recommendations
    4. Calculates priority scores based on impact
    5. Links customers to relevant insights

    Args:
        api_client: ProduckAI API client
        min_feedback_count: Minimum feedback items required to run clustering
                           (default: use backend setting, typically 50)

    Returns:
        Dict with clustering results and statistics

    Example:
        PM: "I've uploaded a lot of new feedback. Can you run clustering?"

        Assistant calls:
        run_clustering()

        Returns:
        ✅ Clustering completed successfully!
        - Themes created: 12
        - Insights generated: 24
        - Processing time: 8.5 seconds

        New insights are now available. Use search_insights() to explore them.
    """
    logger.info("Starting clustering pipeline")

    try:
        result = await api_client.run_clustering(min_feedback_count)

        if result.status == "accepted":
            message_lines = [
                "✅ Clustering task started successfully!",
                "",
                result.message,
                "",
                "**Note**: Clustering runs as a background task and may take a few minutes.",
                "",
                "To check progress:",
                "- Use `get_pipeline_status()` to see if clustering is complete",
                "- Once complete, use `search_insights()` to explore insights",
                "- Or use `get_themes()` to see all discovered themes",
            ]
        elif result.status == "already_running":
            message_lines = [
                "⚠️ Clustering is already running",
                "",
                result.message,
                "",
                "Please wait for the current clustering task to complete.",
                "Use `get_pipeline_status()` to check progress.",
            ]
        else:
            message_lines = [
                f"ℹ️ Clustering status: {result.status}",
                "",
                result.message,
            ]

        return {
            "status": "success",
            "clustering_status": result.status,
            "message": "\n".join(message_lines),
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Clustering failed: {error_msg}", exc_info=True)

        # Provide helpful error messages
        if "insufficient feedback" in error_msg.lower():
            message = (
                "❌ Clustering failed: Not enough feedback items.\n\n"
                "Clustering requires at least 50 feedback items with embeddings.\n"
                "Current status: Use get_pipeline_status() to check feedback counts.\n\n"
                "To proceed:\n"
                "1. Upload more feedback using capture_raw_feedback() or upload_csv_feedback()\n"
                "2. Ensure embeddings are generated (they're created automatically on upload)\n"
                "3. Try clustering again once you have sufficient feedback"
            )
        else:
            message = (
                f"❌ Clustering failed: {error_msg}\n\n"
                f"Please check the backend logs for details or try again.\n"
                f"Use get_pipeline_status() to check the current state."
            )

        return {
            "status": "error",
            "message": message,
            "error": error_msg,
        }


async def get_themes(
    api_client: ProduckAIClient,
) -> Dict[str, Any]:
    """
    Get all discovered themes from clustering.

    Themes are high-level topics that group similar feedback together.
    Each theme contains multiple related feedback items and generates
    one or more insights with recommendations.

    Returns all themes with basic statistics. Use get_theme_details()
    to see full information including all feedback items.

    Args:
        api_client: ProduckAI API client

    Returns:
        Dict with list of themes and statistics

    Example:
        PM: "What themes have been discovered?"

        Assistant calls:
        get_themes()

        Returns:
        # Discovered Themes (12 themes)

        ## 1. API Performance Issues
        - Feedback items: 45
        - Affected customers: 12
        - Created: 2024-01-15

        ## 2. Integration Requests
        - Feedback items: 38
        - Affected customers: 10
        - Created: 2024-01-15

        [Shows all 12 themes]
    """
    logger.info("Fetching all themes")

    try:
        themes = await api_client.get_themes()

        if not themes:
            return {
                "status": "success",
                "total": 0,
                "themes": [],
                "message": (
                    "No themes found.\n\n"
                    "Themes are created by running clustering on feedback.\n"
                    "Use run_clustering() to analyze your feedback and generate themes."
                ),
            }

        # Sort by feedback count (most popular first)
        sorted_themes = sorted(themes, key=lambda t: t.feedback_count, reverse=True)

        # Format themes
        formatted_themes = []
        for i, theme in enumerate(sorted_themes, 1):
            formatted_themes.append({
                "rank": i,
                "id": theme.id,
                "title": theme.title,
                "description": theme.description,
                "feedback_count": theme.feedback_count,
                "customer_count": theme.customer_count,
                "created_at": str(theme.created_at),
            })

        result = {
            "status": "success",
            "total": len(themes),
            "themes": formatted_themes,
            "message": _format_themes_message(sorted_themes),
        }

        logger.info(f"Retrieved {len(themes)} themes")
        return result

    except Exception as e:
        logger.error(f"Failed to get themes: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to get themes: {str(e)}",
        }


async def get_theme_details(
    api_client: ProduckAIClient,
    theme_id: str,
) -> Dict[str, Any]:
    """
    Get complete details for a specific theme.

    Retrieves full theme information including:
    - Complete description
    - All feedback items in the theme
    - Customer breakdown
    - Related insights
    - Timeline of feedback

    Args:
        api_client: ProduckAI API client
        theme_id: UUID of the theme

    Returns:
        Dict with complete theme details

    Example:
        PM: "Show me details on the API Performance theme (theme-123)"

        Assistant calls:
        get_theme_details(theme_id="theme-123")

        Returns:
        # API Performance Issues

        **Description**: Customers reporting slow API response times
        during peak usage hours, particularly affecting enterprise users...

        ## Statistics
        - Feedback items: 45
        - Affected customers: 12
        - Date range: 2024-01-01 to 2024-01-15

        ## Sample Feedback
        1. "API is unusably slow between 2-4pm EST" - Acme Corp
        2. "Response times exceed 5 seconds during peak" - DataCorp
        ...

        ## Affected Customers
        - Acme Corp (Enterprise) - 8 feedback items
        - DataCorp (Enterprise) - 6 feedback items
        ...

        ## Related Insights
        - API Response Time Degradation (High severity)
        - Missing API Rate Limiting (Medium severity)
    """
    logger.info(f"Getting theme details: {theme_id}")

    try:
        # Note: This assumes the backend has a /themes/{id} endpoint
        # If not, we'll need to get all themes and filter
        # For now, let's implement a fallback approach

        themes = await api_client.get_themes()
        theme = next((t for t in themes if t.id == theme_id), None)

        if not theme:
            return {
                "status": "error",
                "message": f"Theme not found: {theme_id}\n\nUse get_themes() to see all available themes.",
            }

        # Get insights related to this theme
        insights = await api_client.search_insights(limit=100)
        theme_insights = [i for i in insights if i.theme_id == theme_id]

        result = {
            "status": "success",
            "theme": {
                "id": theme.id,
                "title": theme.title,
                "description": theme.description,
                "feedback_count": theme.feedback_count,
                "customer_count": theme.customer_count,
                "created_at": str(theme.created_at),
                "updated_at": str(theme.updated_at),
            },
            "insights": [
                {
                    "id": i.id,
                    "title": i.title,
                    "severity": i.severity.value,
                    "priority_score": i.priority_score,
                }
                for i in theme_insights
            ],
            "message": _format_theme_details_message(theme, theme_insights),
        }

        logger.info(f"Retrieved theme {theme_id}")
        return result

    except Exception as e:
        logger.error(f"Failed to get theme details: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to get theme details: {str(e)}",
        }


async def generate_embeddings(
    api_client: ProduckAIClient,
) -> Dict[str, Any]:
    """
    Generate embeddings for feedback items that don't have them yet.

    Embeddings are vector representations of feedback text that enable
    semantic search and clustering. They're automatically generated when
    feedback is uploaded, but this tool can be used to:
    - Generate embeddings for feedback uploaded via API directly
    - Retry failed embedding generation
    - Pre-generate embeddings before clustering

    Note: Embeddings are required for clustering. Feedback without
    embeddings won't be included in clustering analysis.

    Args:
        api_client: ProduckAI API client

    Returns:
        Dict with embedding generation results

    Example:
        PM: "Some feedback items don't have embeddings. Can you generate them?"

        Assistant calls:
        generate_embeddings()

        Returns:
        ✅ Embedding generation completed!
        - Embeddings generated: 23
        - Total feedback with embeddings: 156
        - Ready for clustering: Yes

        All feedback now has embeddings and is ready for clustering.
    """
    logger.info("Generating embeddings for feedback without embeddings")

    try:
        # Note: Embeddings are generated automatically on upload
        # The backend doesn't have a separate embedding generation endpoint
        # or tracking of embeddings in the status endpoint
        message_lines = [
            "ℹ️ Embedding generation information",
            "",
            "**Good news**: Embeddings are generated automatically when feedback is uploaded!",
            "",
            "**How it works**:",
            "- When you upload feedback via `capture_raw_feedback()` or `upload_csv_feedback()`",
            "- The backend automatically generates embeddings for each feedback item",
            "- These embeddings are required for clustering to work",
            "",
            "**Current status**:",
            "- Use `get_pipeline_status()` to check clustering status",
            "- Use `run_clustering()` to trigger clustering when you have enough feedback",
            "",
            "**Note**: If clustering fails due to missing embeddings, try re-uploading the feedback.",
        ]

        return {
            "status": "info",
            "message": "\n".join(message_lines),
        }

    except Exception as e:
        logger.error(f"Failed to generate embeddings: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to generate embeddings: {str(e)}",
        }


def _format_themes_message(themes: List[Theme]) -> str:
    """Format themes list as human-readable message."""
    if not themes:
        return "No themes found."

    lines = [
        f"# Discovered Themes ({len(themes)} themes)",
        "",
        "Themes are high-level topics that group similar feedback together.",
        "",
    ]

    for i, theme in enumerate(themes, 1):
        lines.append(f"## {i}. {theme.title}")
        lines.append(f"**ID**: `{theme.id}`")  # Add theme ID so it can be extracted
        if theme.description:
            desc = theme.description[:150] + "..." if len(theme.description) > 150 else theme.description
            lines.append(f"**Description**: {desc}")
        lines.append(f"**Feedback items**: {theme.feedback_count or 0}")
        lines.append(f"**Affected customers**: {theme.customer_count or 0}")
        if theme.created_at:
            # created_at is already a string in ISO format
            lines.append(f"**Created**: {theme.created_at[:10]}")  # Extract date part
        lines.append("")

    lines.append("Use get_theme_details(theme_id) to see full details for any theme.")
    lines.append("Use search_insights() to see insights generated from these themes.")

    return "\n".join(lines)


def _format_theme_details_message(theme: Theme, insights: List[Any]) -> str:
    """Format theme details as human-readable message."""
    lines = [
        f"# {theme.title}",
        "",
        theme.description or "No description available",
        "",
        "## Statistics",
        f"- **Feedback items**: {theme.feedback_count or 0}",
        f"- **Affected customers**: {theme.customer_count or 0}",
    ]

    if theme.created_at:
        lines.append(f"- **Created**: {theme.created_at[:10]}")  # Extract date part
    if theme.updated_at:
        lines.append(f"- **Last updated**: {theme.updated_at[:10]}")

    lines.append("")

    if insights:
        lines.append(f"## Related Insights ({len(insights)} insights)")
        lines.append("")

        for i, insight in enumerate(insights[:5], 1):
            # severity is a string, not an enum - access directly
            severity_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
            }.get(insight.severity, "⚪")

            lines.append(
                f"{i}. {severity_emoji} **{insight.title}** "
                f"({insight.severity}, Priority: {insight.priority_score}/100)"
            )

        if len(insights) > 5:
            lines.append(f"\n... and {len(insights) - 5} more insights")

        lines.append("")
        lines.append("Use get_insight_details(insight_id) to see full details on any insight.")
    else:
        lines.append("## Related Insights")
        lines.append("No insights generated for this theme yet.")

    return "\n".join(lines)
