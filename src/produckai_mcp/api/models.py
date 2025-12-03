"""Data models for ProduckAI API."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FeedbackSource(str, Enum):
    """Feedback source types (matches backend enum)."""

    SLACK = "slack"
    JIRA = "jira"
    LINEAR = "linear"
    UPLOAD = "upload"  # CSV uploads, manual feedback
    GDOC = "gdoc"       # Google Drive documents
    ZOOM = "zoom"       # Zoom transcripts


class InsightSeverity(str, Enum):
    """Insight severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class InsightPriority(str, Enum):
    """Insight priority levels."""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class Feedback(BaseModel):
    """Feedback item model (matches backend API response)."""

    id: str
    source: str  # FeedbackSource as string (backend returns string, not enum)
    source_id: Optional[str] = None  # External ID (Slack message ID, JIRA key, etc.) - optional for CSV uploads
    text: str
    account: Optional[str] = None  # Customer/company name (backend field name)
    created_at: str  # ISO format string (backend returns strings, not datetime)
    meta: Optional[Dict[str, Any]] = None  # Additional metadata (backend field name)

    # Deprecated fields for backward compatibility (not in backend response)
    customer_name: Optional[str] = None  # Alias for 'account'
    customer_id: Optional[str] = None    # Not returned by backend
    metadata: Optional[Dict[str, Any]] = None  # Alias for 'meta'
    has_embedding: bool = False  # Not returned by backend

    def __init__(self, **data):
        """Initialize with backward compatibility mapping."""
        # Map account to customer_name for backward compatibility
        if 'account' in data and 'customer_name' not in data:
            data['customer_name'] = data['account']
        # Map meta to metadata for backward compatibility
        if 'meta' in data and 'metadata' not in data:
            data['metadata'] = data['meta']
        super().__init__(**data)


class Theme(BaseModel):
    """Theme model (matches backend schema)."""

    id: str
    label: str  # Backend uses 'label' not 'title'
    description: Optional[str] = None
    version: Optional[int] = None
    created_at: Optional[str] = None  # ISO format string
    updated_at: Optional[str] = None  # ISO format string

    # Computed fields (not in database, calculated on demand)
    feedback_count: Optional[int] = None
    customer_count: Optional[int] = None

    # Backward compatibility alias
    title: Optional[str] = None  # Alias for 'label'

    def __init__(self, **data):
        """Initialize with backward compatibility mapping."""
        # Map label to title for backward compatibility
        if 'label' in data and 'title' not in data:
            data['title'] = data['label']
        super().__init__(**data)


class Insight(BaseModel):
    """Insight model (matches backend API response)."""

    # Core fields (always present in backend response)
    id: str
    title: str
    description: Optional[str] = None
    impact: Optional[str] = None
    recommendation: Optional[str] = None
    severity: str  # Backend returns string, not enum!
    effort: str
    priority_score: int  # Backend returns int, not float!
    created_at: str  # ISO format string
    updated_at: str  # ISO format string

    # Metrics and computed fields
    metrics: Optional[Dict[str, Any]] = None  # Theme metrics (freq, acv, sentiment, etc.)
    feedback_count: int = 0
    customers: List[Dict[str, Any]] = Field(default_factory=list)  # Backend field name
    total_acv: Optional[float] = None

    # Optional fields (not always present)
    theme_id: Optional[str] = None  # Parent theme ID (may be None for competitive insights)
    key_quotes: Optional[List[Dict[str, Any]]] = None  # Only in detail endpoint
    supporting_feedback: Optional[List[Dict[str, Any]]] = None  # Only in detail endpoint

    # Deprecated fields for backward compatibility
    customer_count: Optional[int] = None  # Computed from len(customers)
    affected_customers: Optional[List[Dict[str, Any]]] = None  # Alias for 'customers'
    priority: Optional[InsightPriority] = None  # Not in backend response

    def __init__(self, **data):
        """Initialize with backward compatibility mapping."""
        # Map customers to affected_customers
        if 'customers' in data:
            data['affected_customers'] = data['customers']
            data['customer_count'] = len(data['customers'])
        super().__init__(**data)


class Customer(BaseModel):
    """Customer model (matches backend API response)."""

    id: str
    name: str
    segment: Optional[str] = None
    acv: Optional[float] = None
    feedback_count: Optional[int] = None
    created_at: Optional[str] = None  # ISO format string
    updated_at: Optional[str] = None  # ISO format string


class JIRATicket(BaseModel):
    """JIRA ticket model (matches backend API response)."""

    id: str
    ticket_key: str
    summary: str
    description: Optional[str] = None
    status: str
    priority: Optional[str] = None
    voc_score: Optional[float] = None
    matched_insights: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: Optional[str] = None  # ISO format string
    updated_at: Optional[str] = None  # ISO format string


class UploadResponse(BaseModel):
    """Response from file upload (matches backend API response)."""

    total_files: int
    successful_files: int
    failed_files: int
    total_feedback_items: int
    errors: List[dict] = Field(default_factory=list)
    message: str

    # Backward compatibility alias
    @property
    def feedback_count(self) -> int:
        """Alias for total_feedback_items."""
        return self.total_feedback_items


class ClusteringResponse(BaseModel):
    """Response from clustering operation (matches backend ClusterResponse)."""

    status: str
    message: str
    task_id: Optional[str] = None


class PipelineStatus(BaseModel):
    """Pipeline status information (matches backend ClusterStatusResponse)."""

    is_running: bool
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    themes_created: Optional[int] = None
    insights_created: Optional[int] = None
    error: Optional[str] = None


class SearchResults(BaseModel):
    """Search results."""

    total: int
    results: List[Dict[str, Any]]
    query: str
