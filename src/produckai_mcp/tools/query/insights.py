"""Insight query tools - search and retrieve insights."""

from typing import Any, Dict, List, Optional

from produckai_mcp.api.client import ProduckAIClient
from produckai_mcp.api.models import Insight
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


async def search_insights(
    api_client: ProduckAIClient,
    query: Optional[str] = None,
    severity: Optional[str] = None,
    min_priority_score: Optional[float] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Search for insights using natural language or filters.

    Insights are AI-generated recommendations derived from clustered
    feedback. Use this tool to find relevant product issues, feature
    requests, and opportunities.

    Args:
        api_client: ProduckAI API client
        query: Natural language search query (e.g., "API performance issues")
        severity: Filter by severity (critical, high, medium, low)
        min_priority_score: Minimum priority score (0-100)
        limit: Maximum number of results (default: 20)

    Returns:
        Dict with matching insights and summary statistics

    Example:
        PM: "Show me high-severity insights about API performance"

        Assistant calls:
        search_insights(
            query="API performance",
            severity="high",
            limit=10
        )

        Returns:
        - List of matching insights
        - Total count
        - Severity breakdown
        - Affected customer count
    """
    logger.info(f"Searching insights: query={query}, severity={severity}, limit={limit}")

    try:
        insights = await api_client.search_insights(
            query=query,
            severity=severity,
            min_priority_score=min_priority_score,
            limit=limit,
        )

        if not insights:
            return {
                "status": "success",
                "total": 0,
                "insights": [],
                "message": "No insights found matching your criteria.",
            }

        # Build summary statistics
        severity_counts = {}
        total_customers = set()
        total_feedback = 0

        for insight in insights:
            # Count by severity
            sev = insight.severity
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

            # Track unique customers
            total_customers.update(
                [c.get("name") for c in insight.affected_customers if c.get("name")]
            )

            # Sum feedback
            total_feedback += insight.feedback_count

        # Format insights for display
        formatted_insights = []
        for i, insight in enumerate(insights, 1):
            formatted_insights.append({
                "rank": i,
                "id": insight.id,
                "title": insight.title,
                "severity": insight.severity,
                "priority_score": insight.priority_score,
                "priority": insight.priority if insight.priority else "Not set",
                "feedback_count": insight.feedback_count,
                "customer_count": insight.customer_count,
                "impact": insight.impact[:200] + "..." if len(insight.impact) > 200 else insight.impact,
                "recommendation": insight.recommendation[:200] + "..." if len(insight.recommendation) > 200 else insight.recommendation,
            })

        result = {
            "status": "success",
            "total": len(insights),
            "query": query,
            "filters": {
                "severity": severity,
                "min_priority_score": min_priority_score,
            },
            "insights": formatted_insights,
            "summary": {
                "total_insights": len(insights),
                "total_feedback_items": total_feedback,
                "total_customers_affected": len(total_customers),
                "severity_breakdown": severity_counts,
            },
            "message": _format_insights_message(insights, query),
        }

        logger.info(f"Found {len(insights)} insights")
        return result

    except Exception as e:
        logger.error(f"Failed to search insights: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to search insights: {str(e)}",
        }


async def get_insight_details(
    api_client: ProduckAIClient,
    insight_id: str,
) -> Dict[str, Any]:
    """
    Get full details for a specific insight.

    Retrieves complete insight information including:
    - Full description and impact analysis
    - Detailed recommendation
    - All supporting feedback items with quotes
    - Customer breakdown with segments and ACV
    - Related JIRA tickets (if any)
    - Severity and priority metrics

    Args:
        api_client: ProduckAI API client
        insight_id: UUID of the insight

    Returns:
        Dict with complete insight details

    Example:
        PM: "Show me the full details for insight abc-123-def"

        Assistant calls:
        get_insight_details(insight_id="abc-123-def")

        Returns:
        - Full description
        - Impact assessment
        - Recommendation with action items
        - Customer list with segments
        - Supporting feedback with direct quotes
        - JIRA tickets if linked
    """
    logger.info(f"Getting insight details: {insight_id}")

    try:
        insight = await api_client.get_insight(insight_id)

        # Format customer breakdown
        customers_by_segment = {}
        total_acv = 0.0

        for customer in insight.affected_customers:
            segment = customer.get("segment", "Unknown")
            if segment not in customers_by_segment:
                customers_by_segment[segment] = []

            customers_by_segment[segment].append({
                "name": customer.get("name"),
                "acv": customer.get("acv", 0),
                "feedback_count": customer.get("feedback_count", 0),
            })

            total_acv += customer.get("acv", 0)

        result = {
            "status": "success",
            "insight": {
                "id": insight.id,
                "title": insight.title,
                "description": insight.description,
                "impact": insight.impact,
                "recommendation": insight.recommendation,
                "severity": insight.severity,
                "effort": insight.effort,
                "priority_score": insight.priority_score,
                "priority": insight.priority if insight.priority else "Not set",
                "created_at": str(insight.created_at),
                "updated_at": str(insight.updated_at),
            },
            "metrics": {
                "feedback_count": insight.feedback_count,
                "customer_count": insight.customer_count,
                "total_acv": total_acv,
            },
            "customers": {
                "by_segment": customers_by_segment,
                "total": insight.customer_count,
            },
            "supporting_feedback": insight.supporting_feedback[:10],  # Top 10 quotes
            "message": _format_insight_details_message(insight),
        }

        logger.info(f"Retrieved insight {insight_id}")
        return result

    except Exception as e:
        logger.error(f"Failed to get insight details: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to get insight details: {str(e)}",
        }


def _format_insights_message(insights: List[Insight], query: Optional[str]) -> str:
    """Format insights search results as human-readable message."""
    if not insights:
        return "No insights found."

    lines = []

    if query:
        lines.append(f"# Insights matching '{query}'\n")
    else:
        lines.append("# Insights\n")

    for i, insight in enumerate(insights[:5], 1):  # Show top 5 in message
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
        }.get(insight.severity, "⚪")

        lines.append(f"## {i}. {severity_emoji} {insight.title}")
        lines.append(f"**ID**: `{insight.id}`")  # Add insight ID so it can be extracted
        lines.append(f"**Severity**: {insight.severity.title()}")
        lines.append(f"**Priority Score**: {insight.priority_score:.1f}/100")
        lines.append(f"**Impact**: {insight.feedback_count} feedback items, {insight.customer_count} customers")
        lines.append(f"\n{insight.impact[:150]}...")
        lines.append(f"\n**Recommendation**: {insight.recommendation[:150]}...\n")

    if len(insights) > 5:
        lines.append(f"\n... and {len(insights) - 5} more insights")

    lines.append(f"\nUse get_insight_details(insight_id) to see full details for any insight.")

    return "\n".join(lines)


def _format_insight_details_message(insight: Insight) -> str:
    """Format single insight details as human-readable message."""
    severity_emoji = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢",
    }.get(insight.severity, "⚪")

    lines = [
        f"# {severity_emoji} {insight.title}",
        "",
        f"**ID**: {insight.id}",
        f"**Severity**: {insight.severity.title()}",
        f"**Priority**: {insight.priority if insight.priority else 'Not set'}",
        f"**Priority Score**: {insight.priority_score:.1f}/100",
        f"**Effort**: {insight.effort}",
        "",
        "## Description",
        insight.description,
        "",
        "## Impact",
        insight.impact,
        "",
        "## Recommendation",
        insight.recommendation,
        "",
        "## Metrics",
        f"- Feedback items: {insight.feedback_count}",
        f"- Affected customers: {insight.customer_count}",
        "",
    ]

    if insight.affected_customers:
        lines.append("## Affected Customers")
        for customer in insight.affected_customers[:10]:
            name = customer.get("name", "Unknown")
            segment = customer.get("segment", "Unknown")
            acv = customer.get("acv", 0)
            lines.append(f"- **{name}** ({segment}) - ACV: ${acv:,.0f}")

    if insight.supporting_feedback:
        lines.append("")
        lines.append("## Supporting Feedback (Sample Quotes)")
        for i, quote in enumerate(insight.supporting_feedback[:5], 1):
            lines.append(f"{i}. \"{quote}\"")

    return "\n".join(lines)
