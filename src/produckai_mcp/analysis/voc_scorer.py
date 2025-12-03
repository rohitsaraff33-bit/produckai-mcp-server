"""Voice of Customer (VOC) scoring engine for feedback prioritization."""

import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from produckai_mcp.api.client import ProduckAIClient
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


class VOCScoreWeights(BaseModel):
    """Configurable weights for VOC score calculation."""

    customer_impact: float = Field(default=0.30, ge=0.0, le=1.0)
    frequency: float = Field(default=0.20, ge=0.0, le=1.0)
    recency: float = Field(default=0.15, ge=0.0, le=1.0)
    sentiment: float = Field(default=0.15, ge=0.0, le=1.0)
    theme_alignment: float = Field(default=0.10, ge=0.0, le=1.0)
    effort_estimate: float = Field(default=0.10, ge=0.0, le=1.0)

    def validate_sum(self) -> bool:
        """Check if weights sum to 1.0."""
        total = (
            self.customer_impact
            + self.frequency
            + self.recency
            + self.sentiment
            + self.theme_alignment
            + self.effort_estimate
        )
        return abs(total - 1.0) < 0.01


class VOCScore(BaseModel):
    """Voice of Customer Score for a feedback item or theme."""

    feedback_id: Optional[str] = None
    theme_id: Optional[str] = None

    # Component scores (0-100)
    customer_impact_score: float = Field(default=0.0, ge=0.0, le=100.0)
    frequency_score: float = Field(default=0.0, ge=0.0, le=100.0)
    recency_score: float = Field(default=0.0, ge=0.0, le=100.0)
    sentiment_score: float = Field(default=0.0, ge=0.0, le=100.0)
    theme_alignment_score: float = Field(default=0.0, ge=0.0, le=100.0)
    effort_score: float = Field(default=0.0, ge=0.0, le=100.0)

    # Overall score (0-100)
    total_score: float = Field(default=0.0, ge=0.0, le=100.0)

    # Metadata
    calculated_at: datetime = Field(default_factory=datetime.utcnow)
    weights_used: VOCScoreWeights = Field(default_factory=VOCScoreWeights)

    # Supporting data
    customer_tier: Optional[str] = None
    customer_revenue: Optional[float] = None
    mention_count: int = 0
    unique_customers: int = 0
    days_since_last_mention: Optional[int] = None
    sentiment_label: Optional[str] = None  # positive, neutral, negative, urgent
    theme_name: Optional[str] = None
    effort_estimate_label: Optional[str] = None  # small, medium, large

    def calculate_total(self, weights: Optional[VOCScoreWeights] = None) -> float:
        """
        Calculate weighted total score.

        Args:
            weights: Custom weights (uses default if None)

        Returns:
            Weighted total score (0-100)
        """
        if weights is None:
            weights = self.weights_used

        total = (
            self.customer_impact_score * weights.customer_impact
            + self.frequency_score * weights.frequency
            + self.recency_score * weights.recency
            + self.sentiment_score * weights.sentiment
            + self.theme_alignment_score * weights.theme_alignment
            + self.effort_score * weights.effort_estimate
        ) * 100

        self.total_score = round(total, 2)
        return self.total_score


class VOCScorer:
    """Calculate Voice of Customer scores for feedback and themes."""

    # Customer tier scoring
    TIER_SCORES = {
        "enterprise": 100,
        "business": 75,
        "professional": 50,
        "basic": 25,
        "free": 10,
        "unknown": 5,
    }

    # Sentiment scoring
    SENTIMENT_SCORES = {
        "urgent": 100,  # Critical issue, blocker
        "negative": 75,  # Pain point, frustration
        "neutral": 50,  # Feature request, suggestion
        "positive": 25,  # Nice to have, enhancement
    }

    # Effort scoring (inverted - lower effort = higher score)
    EFFORT_SCORES = {
        "small": 100,  # Quick win
        "medium": 60,  # Moderate effort
        "large": 30,  # Major undertaking
        "unknown": 50,  # Default
    }

    def __init__(
        self,
        api_client: ProduckAIClient,
        weights: Optional[VOCScoreWeights] = None,
    ):
        """
        Initialize VOC scorer.

        Args:
            api_client: ProduckAI API client for data access
            weights: Custom scoring weights
        """
        self.api_client = api_client
        self.weights = weights or VOCScoreWeights()

        if not self.weights.validate_sum():
            logger.warning(
                f"VOC weights don't sum to 1.0, scores may be skewed: {self.weights}"
            )

    async def score_feedback(
        self,
        feedback_id: str,
        customer_data: Optional[Dict[str, Any]] = None,
        theme_data: Optional[Dict[str, Any]] = None,
    ) -> VOCScore:
        """
        Calculate VOC score for a single feedback item.

        Args:
            feedback_id: Feedback UUID
            customer_data: Optional customer metadata (revenue, tier)
            theme_data: Optional theme metadata for alignment scoring

        Returns:
            VOC score with component breakdowns
        """
        # Fetch feedback data
        try:
            feedback = await self.api_client.get_feedback_by_id(feedback_id)
        except Exception as e:
            logger.error(f"Failed to fetch feedback {feedback_id}: {e}")
            return VOCScore(feedback_id=feedback_id)

        score = VOCScore(feedback_id=feedback_id, weights_used=self.weights)

        # 1. Customer Impact Score
        score.customer_impact_score = self._calculate_customer_impact(
            customer_data or feedback.get("customer_data", {})
        )
        if customer_data:
            score.customer_tier = customer_data.get("tier")
            score.customer_revenue = customer_data.get("revenue")

        # 2. Frequency Score (how often this feedback appears)
        score.frequency_score = self._calculate_frequency(
            feedback.get("text", ""),
            feedback.get("theme_id"),
        )
        score.mention_count = 1  # This feedback + similar ones

        # 3. Recency Score
        created_at = feedback.get("created_at")
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            score.recency_score = self._calculate_recency(created_at)
            score.days_since_last_mention = (datetime.utcnow() - created_at).days

        # 4. Sentiment Score
        sentiment = self._detect_sentiment(feedback.get("text", ""))
        score.sentiment_score = self.SENTIMENT_SCORES.get(sentiment, 50)
        score.sentiment_label = sentiment

        # 5. Theme Alignment Score
        if theme_data:
            score.theme_alignment_score = self._calculate_theme_alignment(theme_data)
            score.theme_name = theme_data.get("name")

        # 6. Effort Score
        effort = self._estimate_effort(feedback.get("text", ""))
        score.effort_score = self.EFFORT_SCORES.get(effort, 50)
        score.effort_estimate_label = effort

        # Calculate weighted total
        score.calculate_total(self.weights)

        logger.debug(f"VOC score for {feedback_id}: {score.total_score}")
        return score

    async def score_theme(
        self,
        theme_id: str,
        feedback_items: Optional[List[Dict[str, Any]]] = None,
    ) -> VOCScore:
        """
        Calculate aggregate VOC score for a theme.

        Args:
            theme_id: Theme UUID
            feedback_items: Optional list of feedback in this theme

        Returns:
            Aggregate VOC score for the theme
        """
        # Fetch theme and associated feedback
        try:
            theme = await self.api_client.get_theme_by_id(theme_id)
            if not feedback_items:
                # Fetch feedback for this theme
                # Note: This assumes the API has a method to get feedback by theme
                # You may need to adjust based on actual API
                pass
        except Exception as e:
            logger.error(f"Failed to fetch theme {theme_id}: {e}")
            return VOCScore(theme_id=theme_id)

        if not feedback_items:
            feedback_items = []

        score = VOCScore(theme_id=theme_id, weights_used=self.weights)

        # 1. Customer Impact Score (aggregate across all customers)
        customers = {f.get("customer_name") for f in feedback_items if f.get("customer_name")}
        score.unique_customers = len(customers)
        score.customer_impact_score = self._calculate_aggregate_customer_impact(
            feedback_items
        )

        # 2. Frequency Score (number of mentions)
        score.mention_count = len(feedback_items)
        score.frequency_score = self._calculate_theme_frequency(score.mention_count)

        # 3. Recency Score (most recent feedback in theme)
        if feedback_items:
            most_recent = max(
                (
                    f.get("created_at")
                    for f in feedback_items
                    if f.get("created_at")
                ),
                default=None,
            )
            if most_recent:
                if isinstance(most_recent, str):
                    most_recent = datetime.fromisoformat(most_recent.replace("Z", "+00:00"))
                score.recency_score = self._calculate_recency(most_recent)
                score.days_since_last_mention = (datetime.utcnow() - most_recent).days

        # 4. Sentiment Score (average across feedback)
        sentiments = [self._detect_sentiment(f.get("text", "")) for f in feedback_items]
        avg_sentiment = sum(
            self.SENTIMENT_SCORES.get(s, 50) for s in sentiments
        ) / max(len(sentiments), 1)
        score.sentiment_score = avg_sentiment

        # 5. Theme Alignment Score (strategic importance)
        score.theme_alignment_score = self._calculate_strategic_importance(theme)
        score.theme_name = theme.get("name")

        # 6. Effort Score (aggregate estimate)
        efforts = [self._estimate_effort(f.get("text", "")) for f in feedback_items]
        avg_effort = sum(
            self.EFFORT_SCORES.get(e, 50) for e in efforts
        ) / max(len(efforts), 1)
        score.effort_score = avg_effort

        # Calculate weighted total
        score.calculate_total(self.weights)

        logger.info(f"VOC score for theme {theme_id}: {score.total_score}")
        return score

    def _calculate_customer_impact(self, customer_data: Dict[str, Any]) -> float:
        """
        Calculate customer impact score (0-100).

        Factors:
        - Customer tier (50%)
        - Revenue/ARR (30%)
        - Strategic importance flags (20%)

        Args:
            customer_data: Customer metadata

        Returns:
            Impact score (0-100)
        """
        tier = customer_data.get("tier", "unknown").lower()
        tier_score = self.TIER_SCORES.get(tier, 5)

        # Revenue scoring (logarithmic scale)
        revenue = customer_data.get("revenue", 0) or customer_data.get("arr", 0)
        if revenue > 0:
            # Scale: $1k = 20, $10k = 40, $100k = 60, $1M+ = 100
            revenue_score = min(100, 20 + (math.log10(revenue / 1000) * 20))
        else:
            revenue_score = 0

        # Strategic importance
        strategic_score = 100 if customer_data.get("is_strategic") else 50

        # Weighted combination
        total = tier_score * 0.5 + revenue_score * 0.3 + strategic_score * 0.2
        return round(total, 2)

    def _calculate_frequency(self, feedback_text: str, theme_id: Optional[str]) -> float:
        """
        Calculate frequency score based on similar feedback.

        In real implementation, this would query for similar feedback.
        For now, uses a simple heuristic.

        Args:
            feedback_text: Feedback text
            theme_id: Associated theme ID

        Returns:
            Frequency score (0-100)
        """
        # Placeholder: Would query database for similar feedback
        # For now, return moderate score
        if theme_id:
            return 60.0  # Part of a theme = moderate frequency
        return 20.0  # Standalone = low frequency

    def _calculate_theme_frequency(self, mention_count: int) -> float:
        """
        Calculate frequency score for a theme based on mentions.

        Scale:
        - 1-2 mentions: 20
        - 3-5 mentions: 40
        - 6-10 mentions: 60
        - 11-20 mentions: 80
        - 21+ mentions: 100

        Args:
            mention_count: Number of feedback items in theme

        Returns:
            Frequency score (0-100)
        """
        if mention_count <= 2:
            return 20.0
        elif mention_count <= 5:
            return 40.0
        elif mention_count <= 10:
            return 60.0
        elif mention_count <= 20:
            return 80.0
        else:
            return 100.0

    def _calculate_recency(self, created_at: datetime) -> float:
        """
        Calculate recency score with exponential decay.

        Scale:
        - Today: 100
        - 1 week: 90
        - 1 month: 70
        - 3 months: 40
        - 6 months: 20
        - 1 year+: 10

        Args:
            created_at: When feedback was created

        Returns:
            Recency score (0-100)
        """
        days_ago = (datetime.utcnow() - created_at).days

        if days_ago <= 1:
            return 100.0
        elif days_ago <= 7:
            return 90.0
        elif days_ago <= 30:
            return 70.0
        elif days_ago <= 90:
            return 40.0
        elif days_ago <= 180:
            return 20.0
        else:
            return 10.0

    def _detect_sentiment(self, feedback_text: str) -> str:
        """
        Detect sentiment/urgency from feedback text.

        This is a simple keyword-based approach.
        Could be enhanced with ML sentiment analysis.

        Args:
            feedback_text: Feedback text

        Returns:
            Sentiment label: urgent, negative, neutral, positive
        """
        text_lower = feedback_text.lower()

        # Urgent indicators
        urgent_keywords = [
            "critical",
            "blocker",
            "urgent",
            "asap",
            "immediately",
            "broken",
            "not working",
            "can't use",
            "unusable",
        ]
        if any(kw in text_lower for kw in urgent_keywords):
            return "urgent"

        # Negative indicators
        negative_keywords = [
            "frustrated",
            "annoying",
            "painful",
            "difficult",
            "confusing",
            "problem",
            "issue",
            "bug",
            "error",
            "missing",
        ]
        if any(kw in text_lower for kw in negative_keywords):
            return "negative"

        # Positive indicators
        positive_keywords = [
            "would be nice",
            "enhancement",
            "suggestion",
            "could improve",
            "minor",
            "nice to have",
        ]
        if any(kw in text_lower for kw in positive_keywords):
            return "positive"

        return "neutral"

    def _calculate_theme_alignment(self, theme_data: Dict[str, Any]) -> float:
        """
        Calculate theme alignment score based on strategic importance.

        Args:
            theme_data: Theme metadata

        Returns:
            Alignment score (0-100)
        """
        # Placeholder: Could check against roadmap priorities
        # For now, use theme metadata if available
        priority = theme_data.get("priority", "medium")

        priority_scores = {
            "critical": 100,
            "high": 80,
            "medium": 50,
            "low": 20,
        }

        return priority_scores.get(priority, 50)

    def _calculate_strategic_importance(self, theme_data: Dict[str, Any]) -> float:
        """
        Calculate strategic importance of a theme.

        Factors:
        - Roadmap alignment
        - Business goals
        - Market trends

        Args:
            theme_data: Theme metadata

        Returns:
            Strategic importance score (0-100)
        """
        # Placeholder implementation
        # In real system, would check against:
        # - OKRs
        # - Roadmap items
        # - Competitive analysis
        # - Market research

        importance = theme_data.get("strategic_importance", "medium")

        scores = {
            "critical": 100,
            "high": 75,
            "medium": 50,
            "low": 25,
        }

        return scores.get(importance, 50)

    def _estimate_effort(self, feedback_text: str) -> str:
        """
        Estimate implementation effort from feedback text.

        This is a very simple heuristic.
        Real implementation would use ML or developer input.

        Args:
            feedback_text: Feedback text

        Returns:
            Effort estimate: small, medium, large, unknown
        """
        text_lower = feedback_text.lower()

        # Small effort indicators
        small_keywords = [
            "button",
            "label",
            "text",
            "color",
            "typo",
            "wording",
            "copy",
            "ui",
            "tooltip",
        ]
        if any(kw in text_lower for kw in small_keywords):
            return "small"

        # Large effort indicators
        large_keywords = [
            "integration",
            "api",
            "infrastructure",
            "architecture",
            "migration",
            "rebuild",
            "overhaul",
            "completely",
        ]
        if any(kw in text_lower for kw in large_keywords):
            return "large"

        return "medium"

    def _calculate_aggregate_customer_impact(
        self, feedback_items: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate aggregate customer impact for a theme.

        Args:
            feedback_items: List of feedback items with customer data

        Returns:
            Aggregate impact score (0-100)
        """
        if not feedback_items:
            return 0.0

        # Get unique customers and their data
        customer_scores = []
        for item in feedback_items:
            customer_data = item.get("customer_data", {})
            score = self._calculate_customer_impact(customer_data)
            customer_scores.append(score)

        # Use max score (most important customer)
        # Alternative: could use average or sum
        return max(customer_scores) if customer_scores else 0.0
