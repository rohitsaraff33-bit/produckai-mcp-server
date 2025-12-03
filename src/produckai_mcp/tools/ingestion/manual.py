"""Manual ingestion tools - CSV, transcripts, and direct feedback capture."""

from pathlib import Path
from typing import Any, Dict, Optional

from produckai_mcp.api.client import ProduckAIClient
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


# CSV Templates
CSV_TEMPLATES = {
    "standard": {
        "name": "Standard Feedback Template",
        "description": "General purpose feedback template with customer attribution",
        "columns": [
            {"name": "feedback_text", "type": "string", "required": True, "description": "The feedback content"},
            {"name": "customer_name", "type": "string", "required": False, "description": "Customer name"},
            {"name": "source", "type": "string", "required": False, "description": "Source of feedback (e.g., email, call)"},
            {"name": "date", "type": "date", "required": False, "description": "Date feedback was received (YYYY-MM-DD)"},
            {"name": "sentiment", "type": "string", "required": False, "description": "Sentiment: positive, neutral, negative"},
            {"name": "priority", "type": "string", "required": False, "description": "Priority: low, medium, high, critical"},
        ],
        "example_rows": [
            {
                "feedback_text": "The bulk export feature is too slow for large datasets",
                "customer_name": "Acme Corp",
                "source": "customer_call",
                "date": "2024-01-15",
                "sentiment": "negative",
                "priority": "high",
            },
            {
                "feedback_text": "Love the new dashboard design, very intuitive",
                "customer_name": "TechStart Inc",
                "source": "email",
                "date": "2024-01-16",
                "sentiment": "positive",
                "priority": "low",
            },
        ],
    },
    "customer_interview": {
        "name": "Customer Interview Template",
        "description": "Template for structured customer interview feedback",
        "columns": [
            {"name": "feedback_text", "type": "string", "required": True},
            {"name": "customer_name", "type": "string", "required": True},
            {"name": "interview_date", "type": "date", "required": True},
            {"name": "interviewer", "type": "string", "required": False},
            {"name": "topic", "type": "string", "required": False, "description": "Interview topic or theme"},
            {"name": "quote", "type": "string", "required": False, "description": "Direct customer quote"},
            {"name": "impact", "type": "string", "required": False, "description": "Business impact mentioned"},
        ],
        "example_rows": [
            {
                "feedback_text": "Integration with Salesforce is critical for our workflow",
                "customer_name": "Enterprise Co",
                "interview_date": "2024-01-15",
                "interviewer": "Sarah PM",
                "topic": "Integrations",
                "quote": "We can't scale without Salesforce integration",
                "impact": "Blocking Q2 rollout",
            },
        ],
    },
    "support_tickets": {
        "name": "Support Tickets Template",
        "description": "Template for support ticket feedback",
        "columns": [
            {"name": "feedback_text", "type": "string", "required": True},
            {"name": "customer_name", "type": "string", "required": True},
            {"name": "ticket_id", "type": "string", "required": False},
            {"name": "ticket_date", "type": "date", "required": False},
            {"name": "severity", "type": "string", "required": False, "description": "P0, P1, P2, P3"},
            {"name": "category", "type": "string", "required": False, "description": "Bug, feature request, question"},
            {"name": "resolution_time", "type": "number", "required": False, "description": "Hours to resolve"},
        ],
        "example_rows": [
            {
                "feedback_text": "API returns 500 error when uploading files larger than 10MB",
                "customer_name": "DataCorp",
                "ticket_id": "SUP-1234",
                "ticket_date": "2024-01-15",
                "severity": "P1",
                "category": "bug",
                "resolution_time": 4,
            },
        ],
    },
}


async def capture_raw_feedback(
    api_client: ProduckAIClient,
    feedback_text: str,
    customer_name: Optional[str] = None,
    source: str = "pm_conversation",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Capture raw feedback directly from PM's natural language input.

    NOTE: Direct feedback creation is not supported by the backend.
    Use file upload methods instead (upload_csv_feedback).

    This tool creates a temporary CSV file and uploads it to maintain
    the same user experience.

    Args:
        api_client: ProduckAI API client
        feedback_text: The feedback content
        customer_name: Optional customer name to associate with feedback
        source: Source identifier (default: pm_conversation)
        metadata: Additional context (urgency, blocker, etc.)

    Returns:
        Dict with upload status

    Example:
        PM: "Met with Acme Corp today. They're frustrated with lack of
             bulk export functionality. This is blocking their Q2 rollout."

        Assistant calls:
        capture_raw_feedback(
            feedback_text="Lack of bulk export functionality blocking Q2 rollout",
            customer_name="Acme Corp",
            metadata={"urgency": "high", "blocker": True}
        )

        This will create a CSV file and upload it via upload_csv_feedback().
    """
    logger.info(f"Capturing raw feedback from {source} (via CSV upload)")

    try:
        # Backend doesn't support direct POST /feedback
        # Create a temporary CSV file instead
        import csv
        import tempfile
        from datetime import datetime

        # Create temp CSV with correct column names
        # Backend expects: "feedback", "text", "comment", or "description" for feedback text
        # Backend expects: "customer", "customer_name", or "company" for customer name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['feedback', 'customer', 'date'])
            writer.writeheader()
            writer.writerow({
                'feedback': feedback_text,
                'customer': customer_name or '',
                'date': datetime.now().strftime('%Y-%m-%d')
            })
            temp_path = Path(f.name)

        # Upload the CSV
        try:
            response = await api_client.upload_csv(temp_path, template_type="standard")

            result = {
                "status": "success",
                "feedback_count": response.feedback_count,
                "message": f"Feedback captured successfully via CSV upload! {response.feedback_count} item(s) created.",
            }

            if customer_name:
                result["message"] += f"\nLinked to customer: {customer_name}"

            logger.info(f"Captured feedback via CSV: {response.feedback_count} items")
            return result

        finally:
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()

    except NotImplementedError:
        logger.warning("Direct feedback creation not supported by backend")
        return {
            "status": "error",
            "message": (
                "❌ Direct feedback capture is not supported.\n\n"
                "The backend does not support POST /feedback endpoint.\n"
                "Please use one of these alternatives:\n\n"
                "1. **Upload CSV**: Use upload_csv_feedback() with a CSV file\n"
                "2. **Upload Transcript**: Use upload_zoom_transcript() for .vtt files\n"
                "3. **Integration Sync**: Use Slack, Google Drive, Zoom, or JIRA sync\n\n"
                "Tip: You can quickly create a CSV file with your feedback and upload it."
            ),
        }

    except Exception as e:
        logger.error(f"Failed to capture feedback: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to capture feedback: {str(e)}",
        }


async def upload_csv_feedback(
    api_client: ProduckAIClient,
    file_path: str,
    template_type: str = "standard",
) -> Dict[str, Any]:
    """
    Upload a CSV file containing customer feedback.

    The CSV file should follow one of the standard templates. Use
    get_csv_template() to see template formats and download examples.

    Args:
        api_client: ProduckAI API client
        file_path: Path to CSV file
        template_type: Template type (standard, customer_interview, support_tickets)

    Returns:
        Dict with upload status and counts

    Example:
        PM: "Upload this feedback CSV: ~/Desktop/customer_feedback_q1.csv"

        Assistant calls:
        upload_csv_feedback(
            file_path="/Users/pm/Desktop/customer_feedback_q1.csv",
            template_type="standard"
        )
    """
    logger.info(f"Uploading CSV from {file_path}")

    try:
        # Validate file exists
        path = Path(file_path).expanduser()

        # Check if this is Claude Desktop's internal path
        if file_path.startswith("/mnt/user-data/"):
            return {
                "status": "error",
                "message": (
                    f"❌ Cannot access Claude Desktop's internal file path: {file_path}\n\n"
                    "Claude Desktop stores uploaded files in an internal location that the MCP server cannot access.\n\n"
                    "**Workaround:** Please save the CSV file to your local filesystem first, then provide that path:\n\n"
                    "1. Download/save the CSV to your computer (e.g., ~/Downloads/feedback.csv)\n"
                    "2. Use the local file path in the upload command\n\n"
                    "Example: upload_csv_feedback(file_path='~/Downloads/feedback.csv')\n\n"
                    "Or paste the CSV content directly and I'll help you upload it."
                ),
            }

        if not path.exists():
            return {
                "status": "error",
                "message": (
                    f"❌ File not found: {file_path}\n\n"
                    "Please check that:\n"
                    "1. The file path is correct\n"
                    "2. The file exists at this location\n"
                    "3. You have permission to read the file\n\n"
                    "Tip: Use the full path (e.g., ~/Downloads/feedback.csv or /Users/yourusername/Desktop/feedback.csv)"
                ),
            }

        if not path.suffix.lower() == ".csv":
            return {
                "status": "error",
                "message": f"File must be a CSV file, got: {path.suffix}",
            }

        # Validate template type
        if template_type not in CSV_TEMPLATES:
            return {
                "status": "error",
                "message": f"Invalid template type: {template_type}. "
                f"Valid options: {', '.join(CSV_TEMPLATES.keys())}",
            }

        # Upload to backend
        response = await api_client.upload_csv(path, template_type)

        result = {
            "status": response.status,
            "message": response.message,
            "feedback_count": response.feedback_count,
            "template_type": template_type,
        }

        if response.errors:
            result["errors"] = response.errors
            result["message"] += f"\n\nValidation errors found ({len(response.errors)} rows):"
            for i, error in enumerate(response.errors[:5], 1):
                result["message"] += f"\n  {i}. {error}"
            if len(response.errors) > 5:
                result["message"] += f"\n  ... and {len(response.errors) - 5} more errors"

        logger.info(f"CSV upload completed: {response.feedback_count} feedback items")
        return result

    except Exception as e:
        logger.error(f"Failed to upload CSV: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to upload CSV: {str(e)}",
        }


async def upload_zoom_transcript(
    api_client: ProduckAIClient,
    file_path: str,
    meeting_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Upload a Zoom transcript (.vtt file) for processing.

    Zoom transcripts are automatically parsed to extract speaker segments
    and identify customer feedback. Provide meeting metadata to link
    feedback to specific customers.

    Args:
        api_client: ProduckAI API client
        file_path: Path to .vtt transcript file
        meeting_metadata: Optional metadata (customer_name, meeting_type, date, participants)

    Returns:
        Dict with upload status and extracted feedback count

    Example:
        PM: "Upload this Zoom transcript: ~/Downloads/customer_call_acme.vtt
             This was a call with Acme Corp on 2024-01-15"

        Assistant calls:
        upload_zoom_transcript(
            file_path="/Users/pm/Downloads/customer_call_acme.vtt",
            meeting_metadata={
                "customer_name": "Acme Corp",
                "meeting_type": "customer_feedback_call",
                "date": "2024-01-15",
                "participants": ["John (Acme)", "Sarah (PM)"]
            }
        )
    """
    logger.info(f"Uploading Zoom transcript from {file_path}")

    try:
        # Validate file exists
        path = Path(file_path).expanduser()

        # Check if this is Claude Desktop's internal path
        if file_path.startswith("/mnt/user-data/"):
            return {
                "status": "error",
                "message": (
                    f"❌ Cannot access Claude Desktop's internal file path: {file_path}\n\n"
                    "Claude Desktop stores uploaded files in an internal location that the MCP server cannot access.\n\n"
                    "**Workaround:** Please save the .vtt file to your local filesystem first, then provide that path:\n\n"
                    "1. Download/save the transcript to your computer (e.g., ~/Downloads/meeting.vtt)\n"
                    "2. Use the local file path in the upload command\n\n"
                    "Example: upload_zoom_transcript(file_path='~/Downloads/meeting.vtt')"
                ),
            }

        if not path.exists():
            return {
                "status": "error",
                "message": (
                    f"❌ File not found: {file_path}\n\n"
                    "Please check that:\n"
                    "1. The file path is correct\n"
                    "2. The file exists at this location\n"
                    "3. You have permission to read the file\n\n"
                    "Tip: Use the full path (e.g., ~/Downloads/meeting.vtt)"
                ),
            }

        if not path.suffix.lower() == ".vtt":
            return {
                "status": "error",
                "message": f"File must be a .vtt file, got: {path.suffix}",
            }

        # Upload to backend
        response = await api_client.upload_transcript(path, meeting_metadata)

        result = {
            "status": response.status,
            "message": response.message,
            "feedback_count": response.feedback_count,
        }

        if meeting_metadata and "customer_name" in meeting_metadata:
            result["customer_name"] = meeting_metadata["customer_name"]
            result["message"] += f"\nLinked to customer: {meeting_metadata['customer_name']}"

        if response.errors:
            result["errors"] = response.errors

        logger.info(f"Transcript upload completed: {response.feedback_count} feedback items extracted")
        return result

    except Exception as e:
        logger.error(f"Failed to upload transcript: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to upload transcript: {str(e)}",
        }


async def get_csv_template(
    template_type: str = "standard",
) -> Dict[str, Any]:
    """
    Get CSV template specification and examples.

    Returns the template structure with column definitions, data types,
    and example rows. Use this to understand what format your CSV
    should follow.

    Args:
        template_type: Template type (standard, customer_interview, support_tickets)

    Returns:
        Dict with template specification and examples

    Example:
        PM: "What format should my CSV be in?"

        Assistant calls:
        get_csv_template(template_type="standard")

        Returns template with:
        - Column names and types
        - Required vs optional fields
        - Example rows
        - Best practices
    """
    logger.info(f"Getting CSV template: {template_type}")

    if template_type not in CSV_TEMPLATES:
        return {
            "status": "error",
            "message": f"Invalid template type: {template_type}",
            "available_templates": list(CSV_TEMPLATES.keys()),
        }

    template = CSV_TEMPLATES[template_type]

    # Build formatted response
    result = {
        "status": "success",
        "template_type": template_type,
        "name": template["name"],
        "description": template["description"],
        "columns": template["columns"],
        "example_rows": template["example_rows"],
        "formatted_description": _format_template_description(template),
    }

    return result


def _format_template_description(template: Dict[str, Any]) -> str:
    """Format template as human-readable text."""
    lines = [
        f"# {template['name']}",
        "",
        template['description'],
        "",
        "## Columns",
        "",
    ]

    for col in template['columns']:
        required = "**Required**" if col['required'] else "Optional"
        desc = col.get('description', '')
        lines.append(f"- **{col['name']}** ({col['type']}) - {required}")
        if desc:
            lines.append(f"  {desc}")

    lines.extend([
        "",
        "## Example Rows",
        "",
    ])

    for i, row in enumerate(template['example_rows'], 1):
        lines.append(f"### Example {i}")
        for key, value in row.items():
            lines.append(f"- {key}: {value}")
        lines.append("")

    lines.extend([
        "## CSV Format",
        "",
        "Your CSV should have a header row with these column names:",
        "",
        ", ".join([col['name'] for col in template['columns']]),
        "",
        "## Tips",
        "",
        "- Use UTF-8 encoding",
        "- Enclose text with commas in quotes",
        "- One feedback item per row",
        "- Leave optional fields empty if not applicable",
        "- Date format: YYYY-MM-DD",
    ])

    return "\n".join(lines)
