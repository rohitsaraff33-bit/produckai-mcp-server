"""Base document processor interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentProcessor(ABC):
    """Base class for document processors."""

    @abstractmethod
    async def process(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a document and extract feedback.

        Args:
            file_data: File metadata from Google Drive

        Returns:
            Dictionary with feedback items and metadata
        """
        pass

    @abstractmethod
    def can_process(self, mime_type: str) -> bool:
        """
        Check if this processor can handle the file type.

        Args:
            mime_type: MIME type of the file

        Returns:
            True if processor can handle this type
        """
        pass

    def extract_metadata(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract common metadata from file.

        Args:
            file_data: File metadata from Google Drive

        Returns:
            Standardized metadata dictionary
        """
        owners = file_data.get('owners', [])
        permissions = file_data.get('permissions', [])

        return {
            "title": file_data.get("name", "Untitled"),
            "file_id": file_data.get("id"),
            "created_time": file_data.get("createdTime"),
            "modified_time": file_data.get("modifiedTime"),
            "owner_email": owners[0].get("emailAddress") if owners else None,
            "shared_with": [
                p.get("emailAddress")
                for p in permissions
                if p.get("type") == "user" and p.get("emailAddress")
            ],
            "web_link": file_data.get("webViewLink"),
        }

    def detect_customer_from_metadata(
        self, metadata: Dict[str, Any]
    ) -> Optional[str]:
        """
        Detect customer from file metadata (emails, title).

        Args:
            metadata: File metadata

        Returns:
            Customer name if detected, None otherwise
        """
        title = metadata.get("title", "").lower()

        # Common patterns in file names
        customer_patterns = [
            "feedback",
            "interview",
            "meeting",
            "notes",
        ]

        # Check if title suggests customer document
        if any(pattern in title for pattern in customer_patterns):
            # Try to extract customer from title
            # "Acme Corp - Customer Interview" -> "Acme Corp"
            parts = metadata.get("title", "").split("-")
            if len(parts) >= 2:
                potential_customer = parts[0].strip()
                if len(potential_customer) > 3:  # Not too short
                    return potential_customer

        return None

    def extract_email_domain(self, email: str) -> Optional[str]:
        """
        Extract domain from email address.

        Args:
            email: Email address

        Returns:
            Domain name
        """
        if "@" in email:
            return email.split("@")[1]
        return None
