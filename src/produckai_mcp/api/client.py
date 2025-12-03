"""HTTP client for ProduckAI API."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from produckai_mcp.api.models import (
    ClusteringResponse,
    Customer,
    Feedback,
    Insight,
    JIRATicket,
    PipelineStatus,
    SearchResults,
    Theme,
    UploadResponse,
)
from produckai_mcp.config import BackendConfig
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class ProduckAIClient:
    """Client for interacting with ProduckAI backend API."""

    def __init__(self, config: BackendConfig):
        """
        Initialize the API client.

        Args:
            config: Backend configuration
        """
        self.config = config
        self.base_url = config.url.rstrip("/")
        self.timeout = config.timeout

        # Create HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self._get_headers(),
        )

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for requests."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ProduckAI-MCP-Server/0.1.0",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the API.

        Args:
            method: HTTP method
            endpoint: API endpoint
            json_data: JSON data for request body
            params: Query parameters
            files: Files to upload

        Returns:
            Response data as dict

        Raises:
            APIError: If the request fails
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"{method} {url}")

        try:
            if files:
                # For file uploads, don't set Content-Type (let httpx handle it)
                headers = {k: v for k, v in self._get_headers().items() if k != "Content-Type"}

                # Create a fresh httpx client for file uploads
                # Note: The pre-configured client with base_url doesn't handle
                # multipart file uploads correctly when using relative endpoints.
                # Using a fresh client with full URL resolves this issue.
                async with httpx.AsyncClient(timeout=self.timeout) as upload_client:
                    response = await upload_client.request(
                        method,
                        url,  # Use full URL, not endpoint
                        params=params,
                        files=files,
                        headers=headers,
                    )
            else:
                response = await self.client.request(
                    method,
                    endpoint,
                    json=json_data,
                    params=params,
                )

            response.raise_for_status()

            # Try to parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError:
                # If response is not JSON, return empty dict
                return {}

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise APIError(error_msg, status_code=e.response.status_code, details=e.response.text)
        except httpx.RequestError as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            raise APIError(error_msg)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    # Health & Status
    async def health_check(self) -> Dict[str, Any]:
        """Check if backend is healthy."""
        return await self._request("GET", "/healthz")

    async def get_pipeline_status(self) -> PipelineStatus:
        """Get current pipeline status."""
        # Backend uses /cluster/status instead of /pipeline/status
        data = await self._request("GET", "/cluster/status")
        return PipelineStatus(**data)

    # Feedback Management
    async def create_feedback(
        self,
        text: str,
        source: str,
        customer_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Feedback:
        """
        Create a new feedback item.

        Args:
            text: Feedback text
            source: Source of feedback
            customer_name: Optional customer name
            metadata: Additional metadata

        Returns:
            Created feedback item

        Raises:
            NotImplementedError: Backend doesn't support POST /feedback endpoint.
                Use file upload via /upload/upload-feedback instead.

        Note: This method is not supported by the backend.
        Backend only supports feedback ingestion via file uploads or integrations.
        Use upload_csv() or upload_transcript() methods instead.
        """
        raise NotImplementedError(
            "Direct feedback creation not supported by backend. "
            "Backend does not have POST /feedback endpoint. "
            "Use file upload methods (upload_csv, upload_transcript) "
            "or integration sync methods (Slack, Google Drive, Zoom, JIRA) instead."
        )

    async def search_feedback(
        self,
        query: Optional[str] = None,
        source: Optional[str] = None,
        customer_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[Feedback]:
        """
        Search feedback items.

        Args:
            query: Search query (note: backend doesn't support query param,
                   use /search endpoint for full-text search)
            source: Filter by source
            customer_name: Filter by customer (note: backend uses 'account' not 'customer_name')
            limit: Maximum results

        Returns:
            List of matching feedback items
        """
        params = {"limit": limit, "offset": 0}

        if query:
            logger.warning(
                "Text search query not supported on /feedback endpoint. "
                "Use /search endpoint for full-text search. Query ignored: %s",
                query
            )

        if source:
            params["source"] = source

        if customer_name:
            # Note: Backend doesn't support filtering by customer on /feedback endpoint
            logger.warning(
                "Customer name filtering not supported on /feedback endpoint. "
                "Filter will be applied client-side."
            )

        data = await self._request("GET", "/feedback", params=params)
        # Backend returns array directly, not wrapped in {"results": []}
        # Backend uses "account" field instead of "customer_name"
        feedback_items = [
            Feedback(
                id=item["id"],
                text=item["text"],
                source=item["source"],
                customer_name=item.get("account"),  # Map "account" to "customer_name"
                created_at=item["created_at"],
                metadata=item.get("meta", {})
            )
            for item in data
        ]

        # Client-side filtering by customer_name if provided
        if customer_name:
            feedback_items = [
                f for f in feedback_items
                if f.customer_name and customer_name.lower() in f.customer_name.lower()
            ]

        return feedback_items

    # File Uploads
    async def upload_csv(
        self,
        file_path: Path,
        template_type: str = "standard",
    ) -> UploadResponse:
        """
        Upload a CSV file with feedback.

        Args:
            file_path: Path to CSV file
            template_type: CSV template type (note: backend ignores this, accepts all formats)

        Returns:
            Upload response
        """
        # Read file contents first (httpx needs the file data, not just the handle)
        with open(file_path, "rb") as f:
            file_content = f.read()

        # Backend expects "files" as a list of files
        # httpx format: list of (field_name, (filename, content, mime_type)) tuples
        files = [("files", (file_path.name, file_content, "text/csv"))]
        # Backend uses /upload/upload-feedback for all file uploads
        data = await self._request(
            "POST",
            "/upload/upload-feedback",
            files=files,
        )
        return UploadResponse(**data)

    async def upload_transcript(
        self,
        file_path: Path,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UploadResponse:
        """
        Upload a Zoom transcript (.vtt file).

        Args:
            file_path: Path to .vtt file
            metadata: Meeting metadata (note: backend handles metadata extraction automatically)

        Returns:
            Upload response
        """
        # Read file contents first (httpx needs the file data, not just the handle)
        with open(file_path, "rb") as f:
            file_content = f.read()

        # Backend expects "files" as a list of files
        # httpx format: list of (field_name, (filename, content, mime_type)) tuples
        files = [("files", (file_path.name, file_content, "text/vtt"))]
        # Backend uses /upload/upload-feedback for all file uploads
        data = await self._request(
            "POST",
            "/upload/upload-feedback",
            files=files,
        )
        return UploadResponse(**data)

    # Insights & Themes
    async def search_insights(
        self,
        query: Optional[str] = None,
        severity: Optional[str] = None,
        min_priority_score: Optional[float] = None,
        limit: int = 20,
    ) -> List[Insight]:
        """
        Search insights.

        Args:
            query: Search query (note: backend doesn't support text search on /themes,
                   use /search endpoint instead for full-text search)
            severity: Filter by severity
            min_priority_score: Minimum priority score
            limit: Maximum results

        Returns:
            List of matching insights
        """
        params = {"limit": limit, "offset": 0}

        if query:
            # Backend doesn't support query param on /themes
            # Log warning and ignore for now
            logger.warning(
                "Text search query not supported on /themes endpoint. "
                "Use /search endpoint for full-text search. Query ignored: %s",
                query
            )

        if severity:
            # Backend expects severity as a list
            params["severity"] = [severity] if isinstance(severity, str) else severity

        if min_priority_score is not None:
            # Backend uses priority_min instead of min_priority_score
            params["priority_min"] = int(min_priority_score)

        # Backend uses /themes instead of /insights
        data = await self._request("GET", "/themes", params=params)
        # Backend returns array directly, not wrapped in {"results": []}
        return [Insight(**item) for item in data]

    async def get_insight(self, insight_id: str) -> Insight:
        """
        Get insight details.

        Args:
            insight_id: Insight ID

        Returns:
            Insight details
        """
        # Backend uses /themes/{id} instead of /insights/{id}
        data = await self._request("GET", f"/themes/{insight_id}")
        return Insight(**data)

    async def get_themes(self) -> List[Theme]:
        """
        Get all themes.

        Note: Backend /themes endpoint returns insights, not themes.
        This method maps insights to theme objects for compatibility.
        """
        data = await self._request("GET", "/themes")
        # Backend returns insights array directly (not themes), need to map fields
        return [
            Theme(
                id=item["id"],
                label=item["title"],  # Backend uses "title" not "label"
                description=item.get("description"),
                insight_count=1,  # Each item is an insight
                feedback_count=item.get("feedback_count", 0)
            )
            for item in data
        ]

    # Customers
    async def get_customers(self) -> List[Customer]:
        """
        Get all customers.

        Note: Backend returns {"customers": [...], "total_customers": N}
        instead of {"results": [...]}.
        """
        data = await self._request("GET", "/customers")
        # Backend wraps in "customers" key, not "results"
        return [Customer(**item) for item in data.get("customers", [])]

    async def get_customer_feedback(self, customer_name: str) -> List[Feedback]:
        """
        Get feedback for a specific customer.

        Args:
            customer_name: Customer name

        Returns:
            List of insights (not raw feedback) for the customer

        Note: Backend endpoint returns insights, not feedback.
        The endpoint is /customers/{name}/insights, not /feedback.
        """
        # Backend uses /customers/{name}/insights instead of /feedback
        data = await self._request("GET", f"/customers/{customer_name}/insights")
        # Backend returns {"customer": "...", "insights": [...], "count": N}
        # Return insights as Insight objects (not Feedback)
        # TODO: This should probably return List[Insight] not List[Feedback]
        insights = data.get("insights", [])
        # For now, convert insights to feedback-like objects to maintain compatibility
        return [
            Feedback(
                id=item["id"],
                text=item.get("description", item.get("title", "")),
                source="insight",
                customer_name=customer_name,
                created_at=item.get("created_at", ""),
                metadata={
                    "insight_id": item["id"],
                    "title": item.get("title"),
                    "severity": item.get("severity"),
                    "priority_score": item.get("priority_score"),
                }
            )
            for item in insights
        ]

    # Clustering
    async def run_clustering(self, min_feedback_count: Optional[int] = None) -> ClusteringResponse:
        """
        Trigger clustering pipeline.

        Args:
            min_feedback_count: Minimum feedback count

        Returns:
            Clustering response
        """
        json_data = {}
        if min_feedback_count is not None:
            json_data["min_feedback_count"] = min_feedback_count

        data = await self._request("POST", "/cluster/run", json_data=json_data)
        return ClusteringResponse(**data)

    # JIRA Integration
    async def sync_jira_tickets(
        self,
        label: str = "customer_feedback",
        projects: Optional[List[str]] = None,
        since_days: int = 90,
    ) -> Dict[str, Any]:
        """
        Sync JIRA tickets.

        Args:
            label: Label to filter tickets
            projects: Specific projects to sync
            since_days: How far back to sync

        Returns:
            Sync result

        Raises:
            NotImplementedError: Backend doesn't support /jira/sync endpoint.
                Use JIRA API directly or create tickets manually via /jira/tickets POST.

        Note: This method is not supported by the backend.
        JIRA sync must be done client-side using JIRA API.
        """
        raise NotImplementedError(
            "JIRA sync not supported by backend. "
            "Backend does not have /jira/sync endpoint. "
            "Use JIRA API directly via jira_client.py integration, "
            "or create tickets manually using POST /jira/tickets endpoint."
        )

    async def calculate_voc_score(
        self,
        ticket_key: str,
        similarity_threshold: float = 0.6,
    ) -> Dict[str, Any]:
        """
        Calculate VOC score for a JIRA ticket.

        Args:
            ticket_key: JIRA ticket key
            similarity_threshold: Minimum similarity threshold

        Returns:
            VOC score details
        """
        return await self._request(
            "POST",
            f"/jira/tickets/{ticket_key}/calculate-voc",
            json_data={"similarity_threshold": similarity_threshold},
        )

    async def get_jira_backlog(
        self,
        min_voc_score: Optional[float] = None,
        sort_by: str = "voc_score",
    ) -> List[JIRATicket]:
        """
        Get prioritized JIRA backlog.

        Args:
            min_voc_score: Minimum VOC score
            sort_by: Sort field

        Returns:
            List of JIRA tickets

        Note: Backend returns array with nested structure:
        [{"ticket": {...}, "voc_score": {...}, "matched_insights": [...]}]
        """
        params = {"sort_by": sort_by}
        if min_voc_score is not None:
            params["min_voc_score"] = min_voc_score

        data = await self._request("GET", "/jira/tickets", params=params)
        # Backend returns array directly with nested structure
        return [
            JIRATicket(
                jira_key=item["ticket"]["jira_key"],
                title=item["ticket"]["title"],
                status=item["ticket"]["status"],
                priority=item["ticket"]["priority"],
                # VOC score is nested in separate object
                voc_score=item["voc_score"]["voc_score"] if item.get("voc_score") else 0,
                customer_count=item["voc_score"]["customer_count"] if item.get("voc_score") else 0,
                total_acv=item["voc_score"]["total_acv"] if item.get("voc_score") else 0,
                # Additional fields from ticket
                description=item["ticket"].get("description"),
                assignee=item["ticket"].get("assignee"),
                reporter=item["ticket"].get("reporter"),
                labels=item["ticket"].get("labels", []),
                created_at=item["ticket"]["created_at"],
                updated_at=item["ticket"]["updated_at"],
            )
            for item in data
        ]
