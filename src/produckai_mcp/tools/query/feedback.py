"""Feedback query tools - search and retrieve raw feedback."""

from typing import Any, Dict, List, Optional

from produckai_mcp.api.client import ProduckAIClient
from produckai_mcp.api.models import Feedback
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


async def search_feedback(
    api_client: ProduckAIClient,
    query: Optional[str] = None,
    source: Optional[str] = None,
    customer_name: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Search raw feedback items.

    Search through all ingested feedback using natural language queries
    or filters. Useful for finding specific customer mentions, exploring
    feedback from a particular source, or investigating specific topics.

    Args:
        api_client: ProduckAI API client
        query: Natural language search query
        source: Filter by source (csv, slack, gdrive, zoom, jira, manual, pm_conversation)
        customer_name: Filter by specific customer
        limit: Maximum number of results (default: 50)

    Returns:
        Dict with matching feedback items and statistics

    Example:
        PM: "Find all feedback mentioning API performance from Slack"

        Assistant calls:
        search_feedback(
            query="API performance",
            source="slack",
            limit=20
        )

        Returns:
        - List of matching feedback items
        - Source breakdown
        - Customer breakdown
        - Date range
    """
    logger.info(f"Searching feedback: query={query}, source={source}, customer={customer_name}")

    try:
        feedback_items = await api_client.search_feedback(
            query=query,
            source=source,
            customer_name=customer_name,
            limit=limit,
        )

        if not feedback_items:
            return {
                "status": "success",
                "total": 0,
                "feedback": [],
                "message": "No feedback found matching your criteria.",
            }

        # Build statistics
        source_counts = {}
        customer_counts = {}
        customers_with_feedback = set()

        for item in feedback_items:
            # Count by source
            src = item.source.value
            source_counts[src] = source_counts.get(src, 0) + 1

            # Count by customer
            if item.customer_name:
                customer_counts[item.customer_name] = customer_counts.get(item.customer_name, 0) + 1
                customers_with_feedback.add(item.customer_name)

        # Format feedback for display
        formatted_feedback = []
        for i, item in enumerate(feedback_items, 1):
            formatted_feedback.append({
                "rank": i,
                "id": item.id,
                "text": item.text[:300] + "..." if len(item.text) > 300 else item.text,
                "customer_name": item.customer_name,
                "source": item.source.value,
                "created_at": str(item.created_at),
                "has_embedding": item.has_embedding,
                "metadata": item.metadata,
            })

        result = {
            "status": "success",
            "total": len(feedback_items),
            "query": query,
            "filters": {
                "source": source,
                "customer_name": customer_name,
            },
            "feedback": formatted_feedback,
            "statistics": {
                "total_items": len(feedback_items),
                "unique_customers": len(customers_with_feedback),
                "source_breakdown": source_counts,
                "top_customers": dict(sorted(
                    customer_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]),
            },
            "message": _format_feedback_message(feedback_items, query),
        }

        logger.info(f"Found {len(feedback_items)} feedback items")
        return result

    except Exception as e:
        logger.error(f"Failed to search feedback: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to search feedback: {str(e)}",
        }


async def get_customer_feedback(
    api_client: ProduckAIClient,
    customer_name: str,
) -> Dict[str, Any]:
    """
    Get all insights for a specific customer.

    NOTE: Backend endpoint /customers/{name}/insights returns insights, not raw feedback.
    This provides a higher-level view of customer pain points and themes.

    Retrieves all insights associated with a customer. For raw feedback items,
    use search_feedback(customer_name="...") instead.

    Args:
        api_client: ProduckAI API client
        customer_name: Customer name

    Returns:
        Dict with customer insights (returned as feedback-like objects for compatibility)

    Example:
        PM: "Show me all insights from Acme Corp"

        Assistant calls:
        get_customer_feedback(customer_name="Acme Corp")

        Returns:
        - All insights affecting this customer
        - Insights presented as feedback objects (for compatibility)
        - Source breakdown
        - Timeline
        - Metadata includes insight details (severity, priority_score, etc.)
    """
    logger.info(f"Getting insights for customer: {customer_name}")

    try:
        feedback_items = await api_client.get_customer_feedback(customer_name)

        if not feedback_items:
            return {
                "status": "success",
                "customer_name": customer_name,
                "total": 0,
                "feedback": [],
                "message": f"No insights found for customer '{customer_name}'.\n\n"
                          f"Tip: Use search_feedback(customer_name='{customer_name}') to get raw feedback items.",
            }

        # Build statistics
        source_counts = {}
        feedback_by_month = {}
        severity_counts = {}

        for item in feedback_items:
            # Count by source (these are insights, source is "insight")
            src = item.source.value
            source_counts[src] = source_counts.get(src, 0) + 1

            # Count by month
            if item.created_at:
                month = item.created_at.strftime("%Y-%m") if hasattr(item.created_at, 'strftime') else "unknown"
                feedback_by_month[month] = feedback_by_month.get(month, 0) + 1

            # Count by severity (from metadata)
            if item.metadata and 'severity' in item.metadata:
                severity = item.metadata['severity']
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Format feedback (these are actually insights)
        formatted_feedback = []
        for i, item in enumerate(feedback_items, 1):
            formatted_feedback.append({
                "rank": i,
                "id": item.id,
                "text": item.text,  # Insight description/title
                "source": item.source.value,  # Will be "insight"
                "created_at": str(item.created_at) if item.created_at else "unknown",
                "metadata": item.metadata,  # Includes insight_id, title, severity, priority_score
            })

        result = {
            "status": "success",
            "customer_name": customer_name,
            "total": len(feedback_items),
            "feedback": formatted_feedback,  # Actually insights, but formatted as feedback for compatibility
            "statistics": {
                "total_items": len(feedback_items),
                "source_breakdown": source_counts,
                "severity_breakdown": severity_counts,
                "timeline": dict(sorted(feedback_by_month.items())),
            },
            "message": _format_customer_insights_message(customer_name, feedback_items),
            "note": (
                "⚠️  Note: These are INSIGHTS (not raw feedback). "
                "Use search_feedback(customer_name='...') for raw feedback items."
            ),
        }

        logger.info(f"Found {len(feedback_items)} feedback items for {customer_name}")
        return result

    except Exception as e:
        logger.error(f"Failed to get customer feedback: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to get customer feedback: {str(e)}",
        }


def _format_feedback_message(feedback_items: List[Feedback], query: Optional[str]) -> str:
    """Format feedback search results as human-readable message."""
    if not feedback_items:
        return "No feedback found."

    lines = []

    if query:
        lines.append(f"# Feedback matching '{query}'\n")
    else:
        lines.append("# Feedback Items\n")

    # Show first 5 items
    for i, item in enumerate(feedback_items[:5], 1):
        source_emoji = {
            "csv": "📄",
            "slack": "💬",
            "gdrive": "📁",
            "zoom": "🎥",
            "jira": "🎫",
            "manual": "✍️",
            "pm_conversation": "💭",
        }.get(item.source.value, "📝")

        lines.append(f"## {i}. {source_emoji} {item.source.value.upper()}")

        if item.customer_name:
            lines.append(f"**Customer**: {item.customer_name}")

        lines.append(f"**Date**: {item.created_at.strftime('%Y-%m-%d')}")
        lines.append(f"\n{item.text[:200]}...")

        if item.metadata:
            key_metadata = {k: v for k, v in list(item.metadata.items())[:3]}
            if key_metadata:
                lines.append(f"\n*Metadata*: {key_metadata}")

        lines.append("")

    if len(feedback_items) > 5:
        lines.append(f"... and {len(feedback_items) - 5} more feedback items")

    # Summary statistics
    sources = {}
    for item in feedback_items:
        src = item.source.value
        sources[src] = sources.get(src, 0) + 1

    lines.append("\n## Sources")
    for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"- {source}: {count} items")

    return "\n".join(lines)


def _format_customer_feedback_message(customer_name: str, feedback_items: List[Feedback]) -> str:
    """Format customer feedback as human-readable message."""
    lines = [
        f"# Feedback from {customer_name}",
        "",
        f"**Total feedback items**: {len(feedback_items)}",
        "",
    ]

    # Source breakdown
    sources = {}
    for item in feedback_items:
        src = item.source.value
        sources[src] = sources.get(src, 0) + 1

    lines.append("## Sources")
    for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"- {source}: {count} items")

    lines.append("")
    lines.append("## Recent Feedback")

    # Show most recent 5
    for i, item in enumerate(sorted(
        feedback_items,
        key=lambda x: x.created_at,
        reverse=True
    )[:5], 1):
        source_emoji = {
            "csv": "📄",
            "slack": "💬",
            "gdrive": "📁",
            "zoom": "🎥",
            "jira": "🎫",
            "manual": "✍️",
            "pm_conversation": "💭",
        }.get(item.source.value, "📝")

        lines.append(f"### {i}. {source_emoji} {item.created_at.strftime('%Y-%m-%d')}")
        lines.append(f"{item.text[:200]}...")
        lines.append("")

    return "\n".join(lines)


def _format_customer_insights_message(customer_name: str, insight_items: List[Feedback]) -> str:
    """Format customer insights as human-readable message."""
    lines = [
        f"# Insights for {customer_name}",
        "",
        f"**Total insights**: {len(insight_items)}",
        "",
        "⚠️  *Note: These are synthesized insights, not raw feedback.*",
        "*For raw feedback, use search_feedback(customer_name='...')*",
        "",
    ]

    # Severity breakdown
    severities = {}
    for item in insight_items:
        if item.metadata and 'severity' in item.metadata:
            sev = item.metadata['severity']
            severities[sev] = severities.get(sev, 0) + 1

    if severities:
        lines.append("## Severity Breakdown")
        for severity, count in sorted(severities.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"- {severity}: {count} insights")
        lines.append("")

    lines.append("## Top Insights")

    # Show first 5 insights sorted by priority score
    sorted_insights = sorted(
        insight_items,
        key=lambda x: x.metadata.get('priority_score', 0) if x.metadata else 0,
        reverse=True
    )[:5]

    for i, item in enumerate(sorted_insights, 1):
        priority = item.metadata.get('priority_score', 'N/A') if item.metadata else 'N/A'
        severity = item.metadata.get('severity', 'unknown') if item.metadata else 'unknown'
        title = item.metadata.get('title', 'Untitled') if item.metadata else 'Untitled'

        lines.append(f"### {i}. {title}")
        lines.append(f"**Priority**: {priority} | **Severity**: {severity}")
        lines.append(f"\n{item.text[:300]}...")
        lines.append("")

    return "\n".join(lines)
