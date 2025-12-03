"""PRD generation tools - generate and manage Product Requirements Documents."""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from produckai_mcp.analysis.prd_generator import PRDGenerator
from produckai_mcp.api.client import ProduckAIClient
from produckai_mcp.state.database import Database
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


async def generate_prd(
    api_client: ProduckAIClient,
    database: Database,
    insight_id: str,
    include_appendix: bool = True,
    auto_save: bool = True,
) -> Dict[str, Any]:
    """
    Generate a Product Requirements Document (PRD) from an insight.

    Creates a strategic, engineering-ready PRD using AI-powered analysis
    of customer feedback, impact data, and recommendations. The PRD includes:
    - Strategic alignment and evidence
    - Solution hypothesis with success metrics
    - System behavior and guardrails (for AI features)
    - Risk assessment and roadmap

    Args:
        api_client: ProduckAI API client
        database: Database instance
        insight_id: UUID of the insight to generate PRD from
        include_appendix: Include customer breakdown and full quote list
        auto_save: Automatically save PRD to database

    Returns:
        Dict with PRD content, metadata, and save status

    Example:
        PM: "Generate a PRD for the API rate limiting insight"

        Assistant calls:
        generate_prd(
            insight_id="abc-123-def",
            include_appendix=True,
            auto_save=True
        )

        Returns:
        - Full PRD in markdown format
        - Metadata (ACV, segment, persona)
        - Word count and page estimate
        - Cost of generation
        - PRD ID if saved
    """
    logger.info(f"Generating PRD for insight {insight_id}")

    try:
        # Get insight details
        insight = await api_client.get_insight(insight_id)

        # Get Anthropic API key
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            return {
                "status": "error",
                "message": "ANTHROPIC_API_KEY environment variable not set",
            }

        # Initialize PRD generator
        generator = PRDGenerator(anthropic_api_key)

        # Generate PRD
        generated_prd = await generator.generate_prd(
            insight=insight,
            include_appendix=include_appendix,
        )

        # Save to database if requested
        prd_id = None
        if auto_save:
            prd_id = str(uuid.uuid4())
            database.execute_write(
                """
                INSERT INTO prds (
                    id, insight_id, theme_id, title, content, version,
                    status, metadata, word_count, estimated_pages
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prd_id,
                    insight_id,
                    insight.theme_id,
                    generated_prd.title,
                    generated_prd.content,
                    1,
                    "draft",
                    json.dumps(generated_prd.metadata.model_dump(), default=str),
                    generated_prd.word_count,
                    generated_prd.estimated_pages,
                ),
            )
            logger.info(f"PRD saved to database: {prd_id}")

        result = {
            "status": "success",
            "prd_id": prd_id,
            "title": generated_prd.title,
            "content": generated_prd.content,
            "metadata": {
                "insight_id": insight_id,
                "theme_id": insight.theme_id,
                "total_acv": generated_prd.metadata.total_acv,
                "primary_segment": generated_prd.metadata.primary_segment,
                "segment_percentage": generated_prd.metadata.segment_percentage,
                "inferred_persona": generated_prd.metadata.inferred_persona,
                "feedback_count": generated_prd.metadata.feedback_count,
                "customer_count": generated_prd.metadata.customer_count,
            },
            "stats": {
                "word_count": generated_prd.word_count,
                "estimated_pages": generated_prd.estimated_pages,
            },
            "message": _format_prd_message(generated_prd, prd_id),
        }

        logger.info(
            f"PRD generated successfully: {generated_prd.word_count} words"
        )
        return result

    except Exception as e:
        logger.error(f"Failed to generate PRD: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to generate PRD: {str(e)}",
        }


async def list_prds(
    database: Database,
    status: Optional[str] = None,
    theme_id: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    List generated PRDs with optional filters.

    Browse all PRDs created by the PRD generator, filter by status
    (draft/reviewed/approved) or theme, and see metadata at a glance.

    Args:
        database: Database instance
        status: Filter by status (draft, reviewed, approved)
        theme_id: Filter by theme UUID
        limit: Maximum number of results

    Returns:
        Dict with PRD list and summary statistics

    Example:
        PM: "Show me all draft PRDs"

        Assistant calls:
        list_prds(status="draft", limit=10)

        Returns:
        - List of PRDs with titles, status, dates
        - Summary stats (total, by status)
    """
    logger.info(f"Listing PRDs: status={status}, theme_id={theme_id}")

    try:
        # Build query
        query = "SELECT * FROM prds WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        if theme_id:
            query += " AND theme_id = ?"
            params.append(theme_id)

        query += " ORDER BY generated_at DESC LIMIT ?"
        params.append(limit)

        prds = database.execute(query, tuple(params))

        if not prds:
            return {
                "status": "success",
                "total": 0,
                "prds": [],
                "message": "No PRDs found matching your criteria.",
            }

        # Calculate summary stats
        status_counts = {}
        for prd in prds:
            st = prd.get("status", "draft")
            status_counts[st] = status_counts.get(st, 0) + 1

        # Format PRDs for display
        formatted_prds = []
        for i, prd in enumerate(prds, 1):
            formatted_prds.append({
                "rank": i,
                "id": prd["id"],
                "title": prd["title"],
                "status": prd["status"],
                "word_count": prd.get("word_count", 0),
                "estimated_pages": prd.get("estimated_pages", 0),
                "generated_at": prd["generated_at"],
                "insight_id": prd["insight_id"],
                "theme_id": prd.get("theme_id"),
            })

        result = {
            "status": "success",
            "total": len(prds),
            "filters": {
                "status": status,
                "theme_id": theme_id,
            },
            "prds": formatted_prds,
            "summary": {
                "total_prds": len(prds),
                "status_breakdown": status_counts,
            },
            "message": _format_prd_list_message(formatted_prds),
        }

        logger.info(f"Found {len(prds)} PRDs")
        return result

    except Exception as e:
        logger.error(f"Failed to list PRDs: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to list PRDs: {str(e)}",
        }


async def get_prd(
    database: Database,
    prd_id: str,
) -> Dict[str, Any]:
    """
    Get full details for a specific PRD.

    Retrieves complete PRD content including markdown text, metadata,
    generation parameters, and statistics.

    Args:
        database: Database instance
        prd_id: UUID of the PRD

    Returns:
        Dict with complete PRD details

    Example:
        PM: "Show me PRD xyz-789"

        Assistant calls:
        get_prd(prd_id="xyz-789")

        Returns:
        - Full PRD markdown content
        - Metadata (ACV, segment, persona)
        - Stats (word count, pages)
        - Version and status info
    """
    logger.info(f"Getting PRD: {prd_id}")

    try:
        prd = database.execute_one(
            "SELECT * FROM prds WHERE id = ?",
            (prd_id,)
        )

        if not prd:
            return {
                "status": "error",
                "message": f"PRD not found: {prd_id}",
            }

        # Parse metadata
        metadata = json.loads(prd.get("metadata", "{}"))

        result = {
            "status": "success",
            "prd": {
                "id": prd["id"],
                "title": prd["title"],
                "content": prd["content"],
                "status": prd["status"],
                "version": prd.get("version", 1),
                "word_count": prd.get("word_count", 0),
                "estimated_pages": prd.get("estimated_pages", 0),
                "generated_at": prd["generated_at"],
                "updated_at": prd.get("updated_at"),
            },
            "metadata": metadata,
            "related": {
                "insight_id": prd["insight_id"],
                "theme_id": prd.get("theme_id"),
            },
            "message": f"# {prd['title']}\n\n{prd['content']}",
        }

        logger.info(f"Retrieved PRD {prd_id}")
        return result

    except Exception as e:
        logger.error(f"Failed to get PRD: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to get PRD: {str(e)}",
        }


async def update_prd_status(
    database: Database,
    prd_id: str,
    status: str,
) -> Dict[str, Any]:
    """
    Update the status of a PRD.

    Change PRD workflow status between draft, reviewed, and approved.
    Tracks progression through the PRD review process.

    Args:
        database: Database instance
        prd_id: UUID of the PRD
        status: New status (draft, reviewed, approved)

    Returns:
        Dict with update confirmation

    Example:
        PM: "Mark PRD xyz-789 as approved"

        Assistant calls:
        update_prd_status(prd_id="xyz-789", status="approved")

        Returns:
        - Confirmation message
        - Previous and new status
        - Update timestamp
    """
    logger.info(f"Updating PRD status: {prd_id} -> {status}")

    try:
        # Validate status
        valid_statuses = ["draft", "reviewed", "approved"]
        if status not in valid_statuses:
            return {
                "status": "error",
                "message": f"Invalid status: {status}. Must be one of: {', '.join(valid_statuses)}",
            }

        # Check if PRD exists
        prd = database.execute_one(
            "SELECT id, status, title FROM prds WHERE id = ?",
            (prd_id,)
        )

        if not prd:
            return {
                "status": "error",
                "message": f"PRD not found: {prd_id}",
            }

        previous_status = prd["status"]

        # Update status
        database.execute_write(
            """
            UPDATE prds
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, prd_id),
        )

        result = {
            "status": "success",
            "prd_id": prd_id,
            "title": prd["title"],
            "previous_status": previous_status,
            "new_status": status,
            "updated_at": datetime.utcnow().isoformat(),
            "message": f"PRD status updated from '{previous_status}' to '{status}'",
        }

        logger.info(f"PRD status updated: {prd_id} -> {status}")
        return result

    except Exception as e:
        logger.error(f"Failed to update PRD status: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to update PRD status: {str(e)}",
        }


async def regenerate_prd(
    api_client: ProduckAIClient,
    database: Database,
    prd_id: str,
) -> Dict[str, Any]:
    """
    Regenerate a PRD after insight updates.

    Creates a new version of an existing PRD, incorporating any changes
    to the underlying insight data (new feedback, updated severity, etc.).

    Args:
        api_client: ProduckAI API client
        database: Database instance
        prd_id: UUID of the PRD to regenerate

    Returns:
        Dict with regenerated PRD content

    Example:
        PM: "The insight was updated with new feedback. Regenerate the PRD."

        Assistant calls:
        regenerate_prd(prd_id="xyz-789")

        Returns:
        - New PRD content
        - Incremented version number
        - Comparison summary (what changed)
    """
    logger.info(f"Regenerating PRD: {prd_id}")

    try:
        # Get existing PRD
        existing_prd = database.execute_one(
            "SELECT * FROM prds WHERE id = ?",
            (prd_id,)
        )

        if not existing_prd:
            return {
                "status": "error",
                "message": f"PRD not found: {prd_id}",
            }

        insight_id = existing_prd["insight_id"]
        old_version = existing_prd.get("version", 1)

        # Generate new PRD
        result = await generate_prd(
            api_client=api_client,
            database=database,
            insight_id=insight_id,
            include_appendix=True,
            auto_save=False,  # We'll update manually
        )

        if result["status"] == "error":
            return result

        # Update existing PRD with new content
        new_version = old_version + 1
        database.execute_write(
            """
            UPDATE prds
            SET content = ?, version = ?, updated_at = CURRENT_TIMESTAMP,
                word_count = ?, estimated_pages = ?, metadata = ?
            WHERE id = ?
            """,
            (
                result["content"],
                new_version,
                result["stats"]["word_count"],
                result["stats"]["estimated_pages"],
                json.dumps(result["metadata"], default=str),
                prd_id,
            ),
        )

        result["prd_id"] = prd_id
        result["version"] = new_version
        result["previous_version"] = old_version
        result["message"] = f"PRD regenerated successfully (v{old_version} → v{new_version})"

        logger.info(f"PRD regenerated: {prd_id} (v{new_version})")
        return result

    except Exception as e:
        logger.error(f"Failed to regenerate PRD: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to regenerate PRD: {str(e)}",
        }


async def export_prd(
    database: Database,
    prd_id: str,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Export a PRD to a markdown file.

    Saves PRD content to a .md file for sharing, archiving, or
    importing into other tools (Confluence, Notion, etc.).

    Args:
        database: Database instance
        prd_id: UUID of the PRD
        output_path: Optional custom output path (defaults to ~/Downloads)

    Returns:
        Dict with export status and file path

    Example:
        PM: "Export the API rate limiting PRD to a file"

        Assistant calls:
        export_prd(prd_id="xyz-789")

        Returns:
        - File path where PRD was saved
        - File size
        - Export timestamp
    """
    logger.info(f"Exporting PRD: {prd_id}")

    try:
        # Get PRD
        prd = database.execute_one(
            "SELECT * FROM prds WHERE id = ?",
            (prd_id,)
        )

        if not prd:
            return {
                "status": "error",
                "message": f"PRD not found: {prd_id}",
            }

        # Determine output path
        if output_path is None:
            # Default to user's Downloads directory
            downloads_dir = Path.home() / "Downloads"
            downloads_dir.mkdir(parents=True, exist_ok=True)

            # Sanitize filename
            safe_title = "".join(
                c if c.isalnum() or c in (' ', '-', '_') else '_'
                for c in prd["title"]
            ).strip()
            filename = f"PRD_{safe_title}_{prd_id[:8]}.md"
            output_path = str(downloads_dir / filename)

        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(prd["content"])

        file_size = output_file.stat().st_size

        result = {
            "status": "success",
            "prd_id": prd_id,
            "title": prd["title"],
            "output_path": str(output_file),
            "file_size_bytes": file_size,
            "file_size_kb": round(file_size / 1024, 1),
            "exported_at": datetime.utcnow().isoformat(),
            "message": f"PRD exported successfully to: {output_file}",
        }

        logger.info(f"PRD exported: {prd_id} -> {output_file}")
        return result

    except Exception as e:
        logger.error(f"Failed to export PRD: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to export PRD: {str(e)}",
        }


def _format_prd_message(generated_prd: Any, prd_id: Optional[str]) -> str:
    """Format PRD generation result as human-readable message."""
    lines = [
        f"# PRD Generated: {generated_prd.title}",
        "",
        f"**PRD ID:** {prd_id}" if prd_id else "**Note:** PRD not saved (auto_save=False)",
        f"**Word Count:** {generated_prd.word_count}",
        f"**Estimated Pages:** {generated_prd.estimated_pages}",
        "",
        "## Key Metadata",
        f"- **Total ACV at Risk:** ${generated_prd.metadata.total_acv:,.0f}",
        f"- **Primary Segment:** {generated_prd.metadata.primary_segment.title()} ({generated_prd.metadata.segment_percentage:.0f}% of feedback)",
        f"- **Inferred Persona:** {generated_prd.metadata.inferred_persona}",
        f"- **Feedback Count:** {generated_prd.metadata.feedback_count}",
        f"- **Customer Count:** {generated_prd.metadata.customer_count}",
        "",
        "## Preview",
        generated_prd.content[:500] + "..." if len(generated_prd.content) > 500 else generated_prd.content,
        "",
        f"Use `get_prd(prd_id='{prd_id}')` to see the full PRD." if prd_id else "",
        f"Use `export_prd(prd_id='{prd_id}')` to save as markdown file." if prd_id else "",
    ]

    return "\n".join(lines)


def _format_prd_list_message(prds: List[Dict[str, Any]]) -> str:
    """Format PRD list as human-readable message."""
    if not prds:
        return "No PRDs found."

    lines = ["# Product Requirements Documents\n"]

    for i, prd in enumerate(prds[:5], 1):  # Show top 5
        status_emoji = {
            "draft": "📝",
            "reviewed": "👀",
            "approved": "✅",
        }.get(prd["status"], "📄")

        lines.append(f"## {i}. {status_emoji} {prd['title']}")
        lines.append(f"**Status**: {prd['status'].title()}")
        lines.append(f"**Length**: {prd['word_count']} words (~{prd['estimated_pages']} pages)")
        lines.append(f"**Generated**: {prd['generated_at']}")
        lines.append(f"**PRD ID**: {prd['id']}\n")

    if len(prds) > 5:
        lines.append(f"\n... and {len(prds) - 5} more PRDs")

    lines.append(f"\nUse `get_prd(prd_id)` to view full content.")

    return "\n".join(lines)
