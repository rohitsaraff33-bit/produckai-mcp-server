"""VOC (Voice of Customer) scoring tools for feedback prioritization."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from produckai_mcp.analysis.voc_scorer import VOCScore, VOCScorer, VOCScoreWeights
from produckai_mcp.api.client import ProduckAIClient
from produckai_mcp.state.database import Database
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


async def calculate_voc_scores(
    api_client: ProduckAIClient,
    database: Database,
    target_type: str = "feedback",
    target_ids: Optional[List[str]] = None,
    theme_id: Optional[str] = None,
    min_score: Optional[float] = None,
    store_results: bool = True,
) -> Dict[str, Any]:
    """
    Calculate VOC scores for feedback or themes.

    Args:
        api_client: ProduckAI API client
        database: Database connection
        target_type: Type to score: "feedback" or "theme"
        target_ids: Optional specific IDs to score
        theme_id: Optional theme ID to score all feedback within
        min_score: Optional minimum score threshold for results
        store_results: Store scores in database

    Returns:
        Calculated VOC scores
    """
    logger.info(f"Calculating VOC scores for {target_type}")

    try:
        # Initialize scorer
        scorer = VOCScorer(api_client=api_client)

        scores = []

        if target_type == "feedback":
            # Score feedback items
            feedback_to_score = []

            if target_ids:
                # Score specific feedback IDs
                feedback_to_score = target_ids
            elif theme_id:
                # Score all feedback in a theme
                # Note: Adjust based on actual API
                cursor = database.execute(
                    """
                    SELECT id FROM feedback
                    WHERE theme_id = ?
                    """,
                    (theme_id,),
                )
                feedback_to_score = [row["id"] for row in cursor.fetchall()]
            else:
                # Score recent feedback (last 30 days)
                cutoff = datetime.utcnow() - timedelta(days=30)
                cursor = database.execute(
                    """
                    SELECT id FROM feedback
                    WHERE created_at >= ?
                    ORDER BY created_at DESC
                    LIMIT 100
                    """,
                    (cutoff.isoformat(),),
                )
                feedback_to_score = [row["id"] for row in cursor.fetchall()]

            # Calculate scores
            for fid in feedback_to_score:
                score = await scorer.score_feedback(fid)

                if min_score is None or score.total_score >= min_score:
                    scores.append(score)

                    # Store in database if requested
                    if store_results:
                        database.execute(
                            """
                            INSERT INTO voc_scores
                            (feedback_id, total_score, customer_impact_score,
                             frequency_score, recency_score, sentiment_score,
                             theme_alignment_score, effort_score, calculated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(feedback_id) DO UPDATE SET
                                total_score = excluded.total_score,
                                customer_impact_score = excluded.customer_impact_score,
                                frequency_score = excluded.frequency_score,
                                recency_score = excluded.recency_score,
                                sentiment_score = excluded.sentiment_score,
                                theme_alignment_score = excluded.theme_alignment_score,
                                effort_score = excluded.effort_score,
                                calculated_at = excluded.calculated_at
                            """,
                            (
                                fid,
                                score.total_score,
                                score.customer_impact_score,
                                score.frequency_score,
                                score.recency_score,
                                score.sentiment_score,
                                score.theme_alignment_score,
                                score.effort_score,
                                score.calculated_at.isoformat(),
                            ),
                        )

        elif target_type == "theme":
            # Score themes
            themes_to_score = []

            if target_ids:
                themes_to_score = target_ids
            else:
                # Score all active themes
                cursor = database.execute(
                    "SELECT DISTINCT theme_id FROM feedback WHERE theme_id IS NOT NULL"
                )
                themes_to_score = [row["theme_id"] for row in cursor.fetchall()]

            # Calculate scores
            for tid in themes_to_score:
                # Get feedback for this theme
                cursor = database.execute(
                    "SELECT * FROM feedback WHERE theme_id = ?",
                    (tid,),
                )
                feedback_items = [dict(row) for row in cursor.fetchall()]

                score = await scorer.score_theme(tid, feedback_items=feedback_items)

                if min_score is None or score.total_score >= min_score:
                    scores.append(score)

                    if store_results:
                        database.execute(
                            """
                            INSERT INTO voc_scores
                            (theme_id, total_score, customer_impact_score,
                             frequency_score, recency_score, sentiment_score,
                             theme_alignment_score, effort_score, calculated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(theme_id) DO UPDATE SET
                                total_score = excluded.total_score,
                                customer_impact_score = excluded.customer_impact_score,
                                frequency_score = excluded.frequency_score,
                                recency_score = excluded.recency_score,
                                sentiment_score = excluded.sentiment_score,
                                theme_alignment_score = excluded.theme_alignment_score,
                                effort_score = excluded.effort_score,
                                calculated_at = excluded.calculated_at
                            """,
                            (
                                tid,
                                score.total_score,
                                score.customer_impact_score,
                                score.frequency_score,
                                score.recency_score,
                                score.sentiment_score,
                                score.theme_alignment_score,
                                score.effort_score,
                                score.calculated_at.isoformat(),
                            ),
                        )

        # Sort scores by total (highest first)
        scores.sort(key=lambda s: s.total_score, reverse=True)

        # Build summary
        message = f"""📊 **VOC Scores Calculated**

**Type:** {target_type}
**Items Scored:** {len(scores)}
{f"**Min Score Filter:** {min_score}" if min_score else ""}

**Top 10 by VOC Score:**
"""

        for i, score in enumerate(scores[:10], 1):
            if target_type == "feedback":
                message += f"\n{i}. Feedback {score.feedback_id[:8]}... - Score: {score.total_score:.1f}"
            else:
                message += f"\n{i}. Theme {score.theme_name or score.theme_id[:8]}... - Score: {score.total_score:.1f}"

            message += f"\n   • Customer Impact: {score.customer_impact_score:.1f}"
            message += f"\n   • Frequency: {score.frequency_score:.1f}"
            message += f"\n   • Recency: {score.recency_score:.1f}"
            message += f"\n   • Sentiment: {score.sentiment_score:.1f} ({score.sentiment_label})"

        if len(scores) > 10:
            message += f"\n\n...and {len(scores) - 10} more"

        return {
            "success": True,
            "message": message,
            "scored_count": len(scores),
            "scores": [s.dict() for s in scores[:20]],  # Return top 20
        }

    except Exception as e:
        logger.error(f"Failed to calculate VOC scores: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Scoring failed: {str(e)}",
            "error": str(e),
        }


async def get_top_feedback_by_voc(
    database: Database,
    limit: int = 20,
    min_score: Optional[float] = None,
    theme_id: Optional[str] = None,
    customer_tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get top-ranked feedback by VOC score.

    Args:
        database: Database connection
        limit: Maximum results to return
        min_score: Minimum VOC score filter
        theme_id: Optional filter by theme
        customer_tier: Optional filter by customer tier

    Returns:
        Top feedback ranked by VOC score
    """
    logger.info("Getting top feedback by VOC score")

    try:
        # Build query
        query = """
            SELECT
                v.feedback_id,
                v.total_score,
                v.customer_impact_score,
                v.frequency_score,
                v.recency_score,
                v.sentiment_score,
                f.text,
                f.customer_name,
                f.source,
                f.created_at
            FROM voc_scores v
            JOIN feedback f ON v.feedback_id = f.id
            WHERE 1=1
        """

        params = []

        if min_score is not None:
            query += " AND v.total_score >= ?"
            params.append(min_score)

        if theme_id:
            query += " AND f.theme_id = ?"
            params.append(theme_id)

        if customer_tier:
            query += " AND f.customer_tier = ?"
            params.append(customer_tier)

        query += " ORDER BY v.total_score DESC LIMIT ?"
        params.append(limit)

        cursor = database.execute(query, params)
        results = cursor.fetchall()

        if not results:
            return {
                "success": True,
                "message": "No scored feedback found. Run `calculate_voc_scores()` first.",
                "count": 0,
            }

        # Build message
        message = f"""🏆 **Top {len(results)} Feedback by VOC Score**

{f"**Theme Filter:** {theme_id}" if theme_id else ""}
{f"**Customer Tier Filter:** {customer_tier}" if customer_tier else ""}
{f"**Min Score:** {min_score}" if min_score else ""}

"""

        for i, row in enumerate(results, 1):
            message += f"\n**{i}. Score: {row['total_score']:.1f}** - {row['customer_name'] or 'Unknown'}"
            message += f"\n   {row['text'][:100]}..."
            message += f"\n   • Source: {row['source']}"
            message += f"\n   • Impact: {row['customer_impact_score']:.1f} | Frequency: {row['frequency_score']:.1f} | Recency: {row['recency_score']:.1f}"
            message += "\n"

        return {
            "success": True,
            "message": message,
            "count": len(results),
            "feedback": [dict(row) for row in results],
        }

    except Exception as e:
        logger.error(f"Failed to get top feedback: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Query failed: {str(e)}",
            "error": str(e),
        }


async def configure_voc_weights(
    database: Database,
    action: str = "list",
    customer_impact: Optional[float] = None,
    frequency: Optional[float] = None,
    recency: Optional[float] = None,
    sentiment: Optional[float] = None,
    theme_alignment: Optional[float] = None,
    effort_estimate: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Configure VOC scoring weights.

    Args:
        database: Database connection
        action: "list" to show current, "update" to change
        customer_impact: Weight for customer impact (0-1)
        frequency: Weight for feedback frequency (0-1)
        recency: Weight for feedback recency (0-1)
        sentiment: Weight for sentiment/urgency (0-1)
        theme_alignment: Weight for strategic alignment (0-1)
        effort_estimate: Weight for implementation effort (0-1)

    Returns:
        Configuration status

    Note: Weights must sum to 1.0
    """
    logger.info(f"Configuring VOC weights: {action}")

    try:
        if action == "list":
            # Get current weights
            cursor = database.execute(
                "SELECT setting_key, setting_value FROM voc_settings WHERE setting_key LIKE 'weight_%'"
            )
            settings = {row["setting_key"]: float(row["setting_value"]) for row in cursor.fetchall()}

            # Use defaults if not configured
            if not settings:
                settings = {
                    "weight_customer_impact": 0.30,
                    "weight_frequency": 0.20,
                    "weight_recency": 0.15,
                    "weight_sentiment": 0.15,
                    "weight_theme_alignment": 0.10,
                    "weight_effort_estimate": 0.10,
                }

            message = f"""⚙️ **VOC Scoring Weights**

**Current Configuration:**
• Customer Impact: {settings.get('weight_customer_impact', 0.30):.2f} (30%)
• Frequency: {settings.get('weight_frequency', 0.20):.2f} (20%)
• Recency: {settings.get('weight_recency', 0.15):.2f} (15%)
• Sentiment: {settings.get('weight_sentiment', 0.15):.2f} (15%)
• Theme Alignment: {settings.get('weight_theme_alignment', 0.10):.2f} (10%)
• Effort Estimate: {settings.get('weight_effort_estimate', 0.10):.2f} (10%)

**Total:** {sum(settings.values()):.2f} (must equal 1.0)

To update, use:
`configure_voc_weights(action='update', customer_impact=0.35, frequency=0.25, ...)`
"""

            return {
                "success": True,
                "message": message,
                "weights": settings,
            }

        elif action == "update":
            # Build new weights
            new_weights = {}

            if customer_impact is not None:
                new_weights["weight_customer_impact"] = customer_impact
            if frequency is not None:
                new_weights["weight_frequency"] = frequency
            if recency is not None:
                new_weights["weight_recency"] = recency
            if sentiment is not None:
                new_weights["weight_sentiment"] = sentiment
            if theme_alignment is not None:
                new_weights["weight_theme_alignment"] = theme_alignment
            if effort_estimate is not None:
                new_weights["weight_effort_estimate"] = effort_estimate

            if not new_weights:
                return {
                    "success": False,
                    "message": "❌ No weights provided for update",
                }

            # Validate weights sum to 1.0
            total = sum(new_weights.values())
            if abs(total - 1.0) > 0.01:
                return {
                    "success": False,
                    "message": f"❌ Weights must sum to 1.0 (current sum: {total:.2f})",
                }

            # Store weights
            for key, value in new_weights.items():
                database.execute(
                    """
                    INSERT INTO voc_settings (setting_key, setting_value, updated_at)
                    VALUES (?, ?, datetime('now'))
                    ON CONFLICT(setting_key) DO UPDATE SET
                        setting_value = excluded.setting_value,
                        updated_at = datetime('now')
                    """,
                    (key, str(value)),
                )

            return {
                "success": True,
                "message": f"✅ Updated {len(new_weights)} VOC weights. Run `calculate_voc_scores()` to recalculate with new weights.",
                "weights": new_weights,
            }

        else:
            return {
                "success": False,
                "message": f"❌ Unknown action: {action}. Use 'list' or 'update'.",
            }

    except Exception as e:
        logger.error(f"Failed to configure VOC weights: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Configuration failed: {str(e)}",
            "error": str(e),
        }


async def get_voc_trends(
    database: Database,
    days_back: int = 90,
    group_by: str = "week",
) -> Dict[str, Any]:
    """
    Analyze VOC score trends over time.

    Shows how feedback priority is changing.

    Args:
        database: Database connection
        days_back: Number of days to analyze
        group_by: Grouping: "day", "week", or "month"

    Returns:
        VOC trend analysis
    """
    logger.info(f"Analyzing VOC trends for last {days_back} days")

    try:
        # Build grouping SQL
        if group_by == "day":
            group_sql = "DATE(f.created_at)"
            format_str = "%Y-%m-%d"
        elif group_by == "week":
            group_sql = "strftime('%Y-W%W', f.created_at)"
            format_str = "%Y-W%W"
        else:  # month
            group_sql = "strftime('%Y-%m', f.created_at)"
            format_str = "%Y-%m"

        cutoff = datetime.utcnow() - timedelta(days=days_back)

        # Query trends
        cursor = database.execute(
            f"""
            SELECT
                {group_sql} as time_period,
                COUNT(*) as feedback_count,
                AVG(v.total_score) as avg_score,
                MAX(v.total_score) as max_score,
                MIN(v.total_score) as min_score
            FROM voc_scores v
            JOIN feedback f ON v.feedback_id = f.id
            WHERE f.created_at >= ?
            GROUP BY time_period
            ORDER BY time_period
            """,
            (cutoff.isoformat(),),
        )

        trends = cursor.fetchall()

        if not trends:
            return {
                "success": True,
                "message": "No VOC score data available for trend analysis.",
                "trend_count": 0,
            }

        # Calculate overall stats
        total_feedback = sum(t["feedback_count"] for t in trends)
        avg_score = sum(t["avg_score"] * t["feedback_count"] for t in trends) / total_feedback

        # Build message
        message = f"""📈 **VOC Score Trends (Last {days_back} Days)**

**Overall:**
• Total Feedback: {total_feedback}
• Average VOC Score: {avg_score:.1f}
• Time Periods: {len(trends)}

**Trend by {group_by.capitalize()}:**
"""

        for trend in trends[-10:]:  # Show last 10 periods
            message += f"\n• {trend['time_period']}: Avg {trend['avg_score']:.1f} ({trend['feedback_count']} items)"
            message += f"\n  Range: {trend['min_score']:.1f} - {trend['max_score']:.1f}"

        # Identify trending direction
        if len(trends) >= 2:
            recent_avg = sum(t["avg_score"] for t in trends[-3:]) / min(3, len(trends))
            older_avg = sum(t["avg_score"] for t in trends[:3]) / min(3, len(trends))

            if recent_avg > older_avg + 5:
                message += "\n\n📈 **Trend:** Feedback priority is **increasing**"
            elif recent_avg < older_avg - 5:
                message += "\n\n📉 **Trend:** Feedback priority is **decreasing**"
            else:
                message += "\n\n➡️  **Trend:** Feedback priority is **stable**"

        return {
            "success": True,
            "message": message,
            "trend_count": len(trends),
            "total_feedback": total_feedback,
            "avg_score": avg_score,
            "trends": [dict(t) for t in trends],
        }

    except Exception as e:
        logger.error(f"Failed to get VOC trends: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Trend analysis failed: {str(e)}",
            "error": str(e),
        }
