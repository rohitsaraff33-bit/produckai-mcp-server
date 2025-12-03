"""Enhanced Zoom integration tools for meeting recordings and transcripts."""

import keyring
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from anthropic import AsyncAnthropic

from produckai_mcp.ai.feedback_classifier import FeedbackClassifier
from produckai_mcp.api.client import ProduckAIClient
from produckai_mcp.integrations.zoom_client import ZoomClient
from produckai_mcp.state.database import Database
from produckai_mcp.state.sync_state import SyncStateManager
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)

SERVICE_NAME = "produckai-mcp-zoom"


async def setup_zoom_integration(
    account_id: str,
    client_id: str,
    client_secret: str,
) -> Dict[str, Any]:
    """
    Set up Zoom integration with Server-to-Server OAuth.

    Create credentials at: https://marketplace.zoom.us/develop/create

    Args:
        account_id: Zoom Account ID
        client_id: Zoom OAuth Client ID
        client_secret: Zoom OAuth Client Secret

    Returns:
        Setup status with connection test
    """
    logger.info("Setting up Zoom integration")

    try:
        # Exchange credentials for access token (Server-to-Server OAuth)
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://zoom.us/oauth/token",
                params={
                    "grant_type": "account_credentials",
                    "account_id": account_id,
                },
                auth=(client_id, client_secret),
                timeout=30.0,
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "message": f"❌ Failed to get access token: {response.text}",
                    "error": response.text,
                }

            token_data = response.json()
            access_token = token_data.get("access_token")

        # Test connection
        zoom_client = ZoomClient(access_token=access_token)
        test_result = await zoom_client.test_connection()

        if not test_result.get("success"):
            return {
                "success": False,
                "message": f"❌ Failed to connect to Zoom: {test_result.get('error')}",
                "error": test_result.get("error"),
            }

        # Store credentials securely
        keyring.set_password(SERVICE_NAME, "account_id", account_id)
        keyring.set_password(SERVICE_NAME, "client_id", client_id)
        keyring.set_password(SERVICE_NAME, "client_secret", client_secret)
        keyring.set_password(SERVICE_NAME, "access_token", access_token)

        message = f"""✅ Zoom integration successfully set up!

**Account ID:** {account_id}
**User:** {test_result.get('first_name')} {test_result.get('last_name')}
**Email:** {test_result.get('email')}

You can now use Zoom integration tools to:
- Auto-fetch meeting recordings
- Extract and classify feedback from transcripts
- Analyze meeting sentiment
- Link meetings to customers

Next steps:
1. Use `sync_zoom_recordings()` to fetch recent meetings
2. Use `analyze_zoom_meeting()` to extract insights
3. Use `link_zoom_to_customers()` to match meetings to customers
"""

        return {
            "success": True,
            "message": message,
            "user_email": test_result.get("email"),
        }

    except Exception as e:
        logger.error(f"Failed to set up Zoom integration: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Setup failed: {str(e)}",
            "error": str(e),
        }


async def sync_zoom_recordings(
    api_client: ProduckAIClient,
    sync_state: SyncStateManager,
    days_back: int = 30,
    auto_classify: bool = True,
    min_duration: int = 5,
) -> Dict[str, Any]:
    """
    Auto-fetch Zoom recordings and extract feedback.

    Args:
        api_client: ProduckAI API client
        sync_state: Sync state manager
        days_back: Number of days to look back (default: 30)
        auto_classify: Automatically classify transcript as feedback
        min_duration: Minimum meeting duration in minutes

    Returns:
        Summary of synced recordings
    """
    logger.info(f"Syncing Zoom recordings from last {days_back} days")

    try:
        # Get credentials and refresh token if needed
        account_id = keyring.get_password(SERVICE_NAME, "account_id")
        client_id = keyring.get_password(SERVICE_NAME, "client_id")
        client_secret = keyring.get_password(SERVICE_NAME, "client_secret")
        access_token = keyring.get_password(SERVICE_NAME, "access_token")

        if not all([account_id, client_id, client_secret]):
            return {
                "success": False,
                "message": "❌ Zoom not configured. Run `setup_zoom_integration()` first.",
            }

        # Refresh token (Server-to-Server tokens expire hourly)
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://zoom.us/oauth/token",
                params={
                    "grant_type": "account_credentials",
                    "account_id": account_id,
                },
                auth=(client_id, client_secret),
                timeout=30.0,
            )

            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get("access_token")
                keyring.set_password(SERVICE_NAME, "access_token", access_token)

        # Initialize Zoom client
        zoom_client = ZoomClient(access_token=access_token)

        # Get sync state
        last_sync = sync_state.get_sync_state(integration="zoom", resource_id="recordings")
        last_sync_date = None
        if last_sync and last_sync.get("last_sync_timestamp"):
            last_sync_date = datetime.fromisoformat(last_sync["last_sync_timestamp"])

        # Fetch recordings
        from_date = datetime.utcnow() - timedelta(days=days_back)
        if last_sync_date and last_sync_date > from_date:
            from_date = last_sync_date

        recordings = await zoom_client.list_recordings(
            user_id="me",
            from_date=from_date,
            to_date=datetime.utcnow(),
        )

        if not recordings:
            return {
                "success": True,
                "message": "No new recordings found.",
                "processed_count": 0,
            }

        # Filter by duration
        recordings = [r for r in recordings if r.get("duration", 0) >= min_duration]

        # Process each recording
        processed_meetings = []
        total_feedback = 0

        # Initialize classifier if auto_classify enabled
        classifier = None
        if auto_classify:
            anthropic_client = AsyncAnthropic()
            classifier = FeedbackClassifier(client=anthropic_client)

        for recording in recordings:
            meeting_id = recording["meeting_id"]
            topic = recording.get("topic", "Untitled Meeting")

            logger.info(f"Processing recording: {topic}")

            # Find transcript file
            transcript_file = None
            for file in recording.get("recording_files", []):
                if file.get("file_type") == "TRANSCRIPT" or file.get("recording_type") == "audio_transcript":
                    transcript_file = file
                    break

            if not transcript_file:
                logger.warning(f"No transcript available for meeting {topic}")
                continue

            # Download transcript
            download_url = transcript_file.get("download_url")
            if not download_url:
                continue

            transcript_content = await zoom_client.download_transcript(download_url)
            if not transcript_content:
                continue

            # Parse transcript
            segments = zoom_client.parse_vtt_transcript(transcript_content)

            if not segments:
                logger.warning(f"No segments found in transcript for {topic}")
                continue

            # Combine segments into chunks for classification
            chunks = []
            current_chunk = []
            current_length = 0

            for segment in segments:
                text = segment.get("text", "")
                current_chunk.append(f"{segment['speaker']}: {text}")
                current_length += len(text)

                # Create chunks of ~1000 characters
                if current_length >= 1000:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0

            # Add remaining
            if current_chunk:
                chunks.append("\n".join(current_chunk))

            # Classify chunks as feedback
            feedback_items = []

            if auto_classify and classifier:
                for chunk in chunks:
                    # Prepare for classification
                    messages = [{"text": chunk}]
                    classifications = await classifier.classify_messages(messages)

                    if classifications[0]["classification"] == "feedback":
                        feedback_items.append({
                            "text": chunk,
                            "confidence": classifications[0]["confidence"],
                            "customer": classifications[0].get("customer_extracted"),
                        })
            else:
                # If not auto-classifying, treat all chunks as feedback
                feedback_items = [{"text": chunk} for chunk in chunks]

            # Upload feedback to ProduckAI via CSV (backend doesn't support direct POST)
            for item in feedback_items:
                try:
                    import csv
                    import tempfile
                    from datetime import datetime

                    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=['feedback', 'customer', 'date'])
                        writer.writeheader()
                        writer.writerow({
                            'feedback': item["text"],
                            'customer': item.get("customer") or "Unknown",
                            'source': "zoom_recording",
                            'date': datetime.now().strftime('%Y-%m-%d')
                        })
                        temp_path = Path(f.name)

                    try:
                        upload_result = await api_client.upload_csv(temp_path, template_type="standard")
                    finally:
                        if temp_path.exists():
                            temp_path.unlink()
                except Exception as e:
                    logger.error(f"Failed to upload feedback: {e}")
                    continue

            total_feedback += len(feedback_items)
            processed_meetings.append({
                "meeting_id": meeting_id,
                "topic": topic,
                "date": recording.get("start_time"),
                "feedback_count": len(feedback_items),
            })

        # Update sync state
        sync_state.save_sync_state(
            integration="zoom",
            resource_id="recordings",
            sync_data={
                "last_sync_timestamp": datetime.utcnow().isoformat(),
                "meetings_processed": len(processed_meetings),
                "feedback_extracted": total_feedback,
            },
        )

        message = f"""✅ **Synced {len(processed_meetings)} Zoom Recordings**

**Date Range:** {from_date.strftime('%Y-%m-%d')} to {datetime.utcnow().strftime('%Y-%m-%d')}
**Total Feedback Extracted:** {total_feedback}

**Processed Meetings:**
"""
        for meeting in processed_meetings[:10]:
            message += f"\n• {meeting['topic']} ({meeting['date']})"
            message += f"\n  {meeting['feedback_count']} feedback items"

        if len(processed_meetings) > 10:
            message += f"\n\n...and {len(processed_meetings) - 10} more meetings"

        return {
            "success": True,
            "message": message,
            "processed_count": len(processed_meetings),
            "feedback_count": total_feedback,
            "meetings": processed_meetings,
        }

    except Exception as e:
        logger.error(f"Failed to sync Zoom recordings: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Sync failed: {str(e)}",
            "error": str(e),
        }


async def analyze_zoom_meeting(
    meeting_id: str,
    include_sentiment: bool = True,
    include_topics: bool = True,
) -> Dict[str, Any]:
    """
    Analyze a specific Zoom meeting for insights.

    Extracts:
    - Key discussion topics
    - Speaker sentiment
    - Action items
    - Customer pain points

    Args:
        meeting_id: Zoom meeting ID
        include_sentiment: Analyze speaker sentiment
        include_topics: Extract discussion topics

    Returns:
        Meeting analysis results
    """
    logger.info(f"Analyzing Zoom meeting {meeting_id}")

    try:
        # Get Zoom credentials
        access_token = keyring.get_password(SERVICE_NAME, "access_token")

        if not access_token:
            return {
                "success": False,
                "message": "❌ Zoom not configured. Run `setup_zoom_integration()` first.",
            }

        # Initialize client
        zoom_client = ZoomClient(access_token=access_token)

        # Get recording details
        recording = await zoom_client.get_recording(meeting_id)

        if not recording:
            return {
                "success": False,
                "message": f"❌ Meeting {meeting_id} not found or has no recordings.",
            }

        # Find transcript
        transcript_file = None
        for file in recording.get("recording_files", []):
            if file.get("file_type") == "TRANSCRIPT" or file.get("recording_type") == "audio_transcript":
                transcript_file = file
                break

        if not transcript_file:
            return {
                "success": False,
                "message": "❌ No transcript available for this meeting.",
            }

        # Download and parse transcript
        download_url = transcript_file.get("download_url")
        transcript_content = await zoom_client.download_transcript(download_url)

        if not transcript_content:
            return {
                "success": False,
                "message": "❌ Failed to download transcript.",
            }

        segments = zoom_client.parse_vtt_transcript(transcript_content)

        # Build full transcript text
        full_transcript = "\n".join([
            f"{seg['speaker']}: {seg['text']}" for seg in segments
        ])

        # Use Claude to analyze the meeting
        anthropic_client = AsyncAnthropic()

        analysis_prompt = f"""Analyze this customer meeting transcript and extract:

1. Key discussion topics (3-5 topics)
2. Customer pain points mentioned
3. Feature requests or suggestions
4. Action items
{f"5. Overall sentiment (positive/neutral/negative)" if include_sentiment else ""}

Transcript:
{full_transcript[:4000]}  # Limit to avoid token limits

Provide analysis in this format:
**Topics:** [list]
**Pain Points:** [list]
**Feature Requests:** [list]
**Action Items:** [list]
{f"**Sentiment:** [sentiment]" if include_sentiment else ""}
"""

        response = await anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            messages=[{"role": "user", "content": analysis_prompt}],
        )

        analysis_text = response.content[0].text

        message = f"""📊 **Zoom Meeting Analysis**

**Meeting:** {recording.get('topic')}
**Date:** {recording.get('start_time')}
**Duration:** {recording.get('duration')} minutes
**Participants:** {len(segments)} speakers detected

{analysis_text}

**Full Transcript:** {len(segments)} segments, {len(full_transcript)} characters
"""

        return {
            "success": True,
            "message": message,
            "meeting_id": meeting_id,
            "topic": recording.get("topic"),
            "analysis": analysis_text,
            "segment_count": len(segments),
        }

    except Exception as e:
        logger.error(f"Failed to analyze meeting: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Analysis failed: {str(e)}",
            "error": str(e),
        }


async def get_zoom_insights(
    database: Database,
    days_back: int = 30,
) -> Dict[str, Any]:
    """
    Get insights from Zoom meeting data.

    Metrics:
    - Meeting frequency
    - Most discussed topics
    - Sentiment trends
    - Customer engagement

    Args:
        database: Database connection
        days_back: Number of days to analyze

    Returns:
        Zoom insights summary
    """
    logger.info("Generating Zoom insights")

    try:
        # Query feedback from Zoom source
        from_date = datetime.utcnow() - timedelta(days=days_back)

        cursor = database.execute(
            """
            SELECT COUNT(*) as feedback_count,
                   COUNT(DISTINCT customer_name) as customer_count
            FROM feedback
            WHERE source LIKE 'zoom%'
              AND created_at >= ?
            """,
            (from_date.isoformat(),),
        )

        stats = cursor.fetchone()

        # Get most active customers
        cursor = database.execute(
            """
            SELECT customer_name, COUNT(*) as meeting_count
            FROM feedback
            WHERE source LIKE 'zoom%'
              AND created_at >= ?
              AND customer_name IS NOT NULL
            GROUP BY customer_name
            ORDER BY meeting_count DESC
            LIMIT 10
            """,
            (from_date.isoformat(),),
        )

        top_customers = cursor.fetchall()

        message = f"""📈 **Zoom Insights (Last {days_back} Days)**

**Overall Stats:**
• Total Feedback from Zoom: {stats['feedback_count']}
• Unique Customers: {stats['customer_count']}

**Most Active Customers:**
"""

        for customer in top_customers:
            message += f"\n• {customer['customer_name']}: {customer['meeting_count']} feedback items"

        return {
            "success": True,
            "message": message,
            "feedback_count": stats["feedback_count"],
            "customer_count": stats["customer_count"],
            "top_customers": [dict(c) for c in top_customers],
        }

    except Exception as e:
        logger.error(f"Failed to get Zoom insights: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Failed to get insights: {str(e)}",
            "error": str(e),
        }


async def link_zoom_to_customers(
    api_client: ProduckAIClient,
    database: Database,
    meeting_id: str,
    customer_name: str,
) -> Dict[str, Any]:
    """
    Link a Zoom meeting to a customer.

    Updates all feedback from this meeting with the customer name.

    Args:
        api_client: ProduckAI API client
        database: Database connection
        meeting_id: Zoom meeting ID
        customer_name: Customer name

    Returns:
        Link status
    """
    logger.info(f"Linking Zoom meeting {meeting_id} to {customer_name}")

    try:
        # Find feedback from this meeting
        cursor = database.execute(
            """
            SELECT id FROM feedback
            WHERE source = 'zoom_recording'
              AND metadata LIKE ?
            """,
            (f'%"meeting_id": "{meeting_id}"%',),
        )

        feedback_ids = [row["id"] for row in cursor.fetchall()]

        if not feedback_ids:
            return {
                "success": False,
                "message": f"❌ No feedback found for meeting {meeting_id}",
            }

        # Update customer name for all feedback
        updated_count = 0
        for fid in feedback_ids:
            result = await api_client.update_feedback(
                feedback_id=fid,
                customer_name=customer_name,
            )
            if result.get("success"):
                updated_count += 1

        return {
            "success": True,
            "message": f"✅ Linked {updated_count} feedback items to {customer_name}",
            "updated_count": updated_count,
            "feedback_ids": feedback_ids,
        }

    except Exception as e:
        logger.error(f"Failed to link Zoom meeting: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Link failed: {str(e)}",
            "error": str(e),
        }
