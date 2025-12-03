"""Zoom API client wrapper for meeting recordings and transcripts."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


class ZoomClient:
    """Wrapper for Zoom API operations."""

    BASE_URL = "https://api.zoom.us/v2"

    def __init__(self, access_token: str):
        """
        Initialize Zoom client.

        Args:
            access_token: Zoom OAuth access token or Server-to-Server OAuth token
        """
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test Zoom API connection and get user info.

        Returns:
            Connection status and user info
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/users/me",
                    headers=self.headers,
                    timeout=10.0,
                )

                if response.status_code == 200:
                    user_data = response.json()
                    return {
                        "success": True,
                        "user_id": user_data.get("id"),
                        "email": user_data.get("email"),
                        "first_name": user_data.get("first_name"),
                        "last_name": user_data.get("last_name"),
                        "account_id": user_data.get("account_id"),
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API returned status {response.status_code}",
                        "details": response.text,
                    }

        except Exception as e:
            logger.error(f"Zoom connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def list_recordings(
        self,
        user_id: str = "me",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page_size: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        List cloud recordings for a user.

        Args:
            user_id: User ID or 'me' for authenticated user
            from_date: Start date (defaults to 30 days ago)
            to_date: End date (defaults to today)
            page_size: Number of records per page

        Returns:
            List of meeting recordings
        """
        if from_date is None:
            from_date = datetime.utcnow() - timedelta(days=30)
        if to_date is None:
            to_date = datetime.utcnow()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/users/{user_id}/recordings",
                    headers=self.headers,
                    params={
                        "from": from_date.strftime("%Y-%m-%d"),
                        "to": to_date.strftime("%Y-%m-%d"),
                        "page_size": page_size,
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    meetings = data.get("meetings", [])

                    recordings = []
                    for meeting in meetings:
                        recordings.append({
                            "meeting_id": meeting.get("id"),
                            "uuid": meeting.get("uuid"),
                            "topic": meeting.get("topic"),
                            "start_time": meeting.get("start_time"),
                            "duration": meeting.get("duration"),
                            "total_size": meeting.get("total_size"),
                            "recording_count": meeting.get("recording_count"),
                            "recording_files": meeting.get("recording_files", []),
                        })

                    return recordings
                else:
                    logger.error(f"Failed to list recordings: {response.status_code}")
                    return []

        except Exception as e:
            logger.error(f"Failed to list Zoom recordings: {e}")
            return []

    async def get_recording(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details of a specific recording.

        Args:
            meeting_id: Meeting ID

        Returns:
            Recording details
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/meetings/{meeting_id}/recordings",
                    headers=self.headers,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "meeting_id": data.get("id"),
                        "uuid": data.get("uuid"),
                        "host_id": data.get("host_id"),
                        "topic": data.get("topic"),
                        "start_time": data.get("start_time"),
                        "duration": data.get("duration"),
                        "total_size": data.get("total_size"),
                        "recording_count": data.get("recording_count"),
                        "recording_files": data.get("recording_files", []),
                        "participant_audio_files": data.get("participant_audio_files", []),
                    }
                else:
                    logger.error(f"Failed to get recording: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Failed to get Zoom recording: {e}")
            return None

    async def download_transcript(self, download_url: str) -> Optional[str]:
        """
        Download transcript file from Zoom.

        Args:
            download_url: Download URL from recording_files

        Returns:
            Transcript content as string
        """
        try:
            # Add access token to download URL
            url_with_token = f"{download_url}?access_token={self.access_token}"

            async with httpx.AsyncClient() as client:
                response = await client.get(url_with_token, timeout=60.0)

                if response.status_code == 200:
                    return response.text
                else:
                    logger.error(f"Failed to download transcript: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Failed to download transcript: {e}")
            return None

    async def get_meeting_participants(self, meeting_id: str) -> List[Dict[str, Any]]:
        """
        Get list of meeting participants.

        Args:
            meeting_id: Meeting ID

        Returns:
            List of participants
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/past_meetings/{meeting_id}/participants",
                    headers=self.headers,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("participants", [])
                else:
                    logger.error(f"Failed to get participants: {response.status_code}")
                    return []

        except Exception as e:
            logger.error(f"Failed to get meeting participants: {e}")
            return []

    async def list_upcoming_meetings(
        self,
        user_id: str = "me",
        page_size: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        List upcoming scheduled meetings.

        Args:
            user_id: User ID or 'me' for authenticated user
            page_size: Number of records per page

        Returns:
            List of upcoming meetings
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/users/{user_id}/meetings",
                    headers=self.headers,
                    params={
                        "type": "upcoming",
                        "page_size": page_size,
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("meetings", [])
                else:
                    logger.error(f"Failed to list meetings: {response.status_code}")
                    return []

        except Exception as e:
            logger.error(f"Failed to list upcoming meetings: {e}")
            return []

    def parse_vtt_transcript(self, vtt_content: str) -> List[Dict[str, Any]]:
        """
        Parse VTT (WebVTT) transcript format.

        Args:
            vtt_content: Raw VTT file content

        Returns:
            List of transcript segments with speaker, timestamp, and text
        """
        segments = []
        lines = vtt_content.split("\n")

        current_segment = {}
        for line in lines:
            line = line.strip()

            # Skip WEBVTT header and NOTE lines
            if line.startswith("WEBVTT") or line.startswith("NOTE"):
                continue

            # Timestamp line (e.g., "00:00:01.920 --> 00:00:04.800")
            if "-->" in line:
                timestamps = line.split("-->")
                current_segment["start_time"] = timestamps[0].strip()
                current_segment["end_time"] = timestamps[1].strip()

            # Text line (contains speaker and text)
            elif line and "start_time" in current_segment:
                # Extract speaker name if present
                if ":" in line:
                    parts = line.split(":", 1)
                    speaker = parts[0].strip()
                    text = parts[1].strip()
                else:
                    speaker = "Unknown"
                    text = line

                current_segment["speaker"] = speaker
                current_segment["text"] = text

                segments.append(current_segment)
                current_segment = {}

        return segments

    async def get_meeting_summary(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """
        Get AI-generated meeting summary (if available).

        Note: This requires Zoom AI Companion feature.

        Args:
            meeting_id: Meeting ID

        Returns:
            Meeting summary data
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/meetings/{meeting_id}/meeting_summary",
                    headers=self.headers,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    # Not all meetings have summaries
                    logger.debug(f"No summary available for meeting {meeting_id}")
                    return None

        except Exception as e:
            logger.debug(f"Failed to get meeting summary: {e}")
            return None
