"""PRD (Product Requirements Document) generation engine."""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

from produckai_mcp.api.models import Insight
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


class PRDMetadata(BaseModel):
    """Metadata for generated PRD."""

    insight_id: str
    theme_id: Optional[str] = None  # Optional - backend may not link insights to themes
    total_acv: float
    primary_segment: str
    segment_percentage: float
    inferred_persona: str
    feedback_count: int
    customer_count: int
    generation_model: str = "claude-3-opus-20240229"
    generation_timestamp: datetime = Field(default_factory=datetime.utcnow)


class GeneratedPRD(BaseModel):
    """Generated PRD result."""

    title: str
    content: str
    metadata: PRDMetadata
    word_count: int
    estimated_pages: float


class PRDGenerator:
    """PRD generation engine using Claude API."""

    # Persona inference keywords
    PERSONA_KEYWORDS = {
        "admin": ["permission", "access", "user management", "security", "sso", "authentication", "authorization", "role"],
        "pm": ["roadmap", "prioritize", "feedback", "insight", "analytics", "dashboard", "reporting"],
        "engineer": ["api", "integration", "deployment", "performance", "error", "sdk", "webhook", "latency"],
        "cs_support": ["customer", "support ticket", "response time", "sla", "resolution", "escalation"],
        "executive": ["dashboard", "reporting", "roi", "revenue", "churn", "retention", "growth"],
    }

    # Default personas by segment
    DEFAULT_PERSONAS = {
        "enterprise": "Admins & IT Leaders",
        "mid-market": "Product & Operations Teams",
        "smb": "Founders & Operators",
        "startup": "Founding Teams",
    }

    def __init__(self, anthropic_api_key: str):
        """
        Initialize PRD generator.

        Args:
            anthropic_api_key: Anthropic API key for Claude
        """
        self.client = AsyncAnthropic(api_key=anthropic_api_key)
        logger.info("PRD Generator initialized")

    async def generate_prd(
        self,
        insight: Insight,
        model: str = "claude-3-opus-20240229",
        include_appendix: bool = True,
    ) -> GeneratedPRD:
        """
        Generate a PRD from an insight.

        Args:
            insight: ProduckAI Insight object
            model: Claude model to use
            include_appendix: Whether to include appendix section

        Returns:
            GeneratedPRD with content and metadata
        """
        logger.info(f"Generating PRD for insight {insight.id}")

        # Calculate derived fields
        metadata = self._prepare_metadata(insight)

        # Build prompt
        prompt = self._build_prompt(insight, metadata, include_appendix)

        # Call Claude API
        try:
            response = await self.client.messages.create(
                model=model,
                max_tokens=4096,  # Claude 3 Opus limit
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            prd_content = response.content[0].text

            # Calculate word count and estimated pages
            word_count = len(prd_content.split())
            estimated_pages = word_count / 500  # ~500 words per page

            result = GeneratedPRD(
                title=insight.title,
                content=prd_content,
                metadata=metadata,
                word_count=word_count,
                estimated_pages=round(estimated_pages, 1),
            )

            logger.info(
                f"PRD generated successfully: {word_count} words, ~{estimated_pages:.1f} pages"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to generate PRD: {str(e)}", exc_info=True)
            raise

    def _prepare_metadata(self, insight: Insight) -> PRDMetadata:
        """
        Prepare metadata by calculating derived fields.

        Args:
            insight: Insight object

        Returns:
            PRDMetadata with calculated fields
        """
        # Calculate total ACV
        total_acv = sum(
            customer.get("acv", 0) for customer in insight.affected_customers
        )

        # Calculate primary segment
        segment_counts: Dict[str, int] = {}
        for customer in insight.affected_customers:
            segment = customer.get("segment", "unknown")
            feedback_count = customer.get("feedback_count", 1)
            segment_counts[segment] = segment_counts.get(segment, 0) + feedback_count

        primary_segment = (
            max(segment_counts, key=segment_counts.get)
            if segment_counts
            else "unknown"
        )

        # Calculate segment percentage
        segment_percentage = (
            (segment_counts.get(primary_segment, 0) / insight.feedback_count * 100)
            if insight.feedback_count > 0
            else 0
        )

        # Infer persona
        inferred_persona = self._infer_persona(insight, primary_segment)

        return PRDMetadata(
            insight_id=insight.id,
            theme_id=insight.theme_id,
            total_acv=total_acv,
            primary_segment=primary_segment,
            segment_percentage=segment_percentage,
            inferred_persona=inferred_persona,
            feedback_count=insight.feedback_count,
            customer_count=insight.customer_count,
        )

    def _infer_persona(self, insight: Insight, primary_segment: str) -> str:
        """
        Infer user persona from insight content and segment.

        Args:
            insight: Insight object
            primary_segment: Primary customer segment

        Returns:
            Inferred persona string
        """
        # Combine text for keyword matching
        combined_text = (
            f"{insight.title} {insight.description} {insight.recommendation}"
        ).lower()

        # Count keyword matches
        persona_scores: Dict[str, int] = {}
        for persona, keywords in self.PERSONA_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            if score > 0:
                persona_scores[persona] = score

        # Get best matching persona
        if persona_scores:
            best_persona = max(persona_scores, key=persona_scores.get)
            persona_names = {
                "admin": f"{primary_segment.title()} Admins & IT Leaders",
                "pm": f"{primary_segment.title()} Product Managers",
                "engineer": f"{primary_segment.title()} Engineers & Developers",
                "cs_support": f"{primary_segment.title()} Customer Success Teams",
                "executive": f"{primary_segment.title()} Executives",
            }
            return persona_names.get(best_persona, self.DEFAULT_PERSONAS.get(primary_segment, "Users"))

        # Fallback to segment-based default
        return self.DEFAULT_PERSONAS.get(primary_segment, "Users")

    def _build_prompt(
        self,
        insight: Insight,
        metadata: PRDMetadata,
        include_appendix: bool,
    ) -> str:
        """
        Build the Claude API prompt for PRD generation.

        Args:
            insight: Insight object
            metadata: Pre-calculated metadata
            include_appendix: Whether to include appendix

        Returns:
            Complete prompt string
        """
        # Format ACV
        formatted_acv = f"${metadata.total_acv:,.0f}"

        # Severity emoji
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
        }.get(insight.severity, "⚪")

        # Format customer list for appendix
        customer_table = ""
        if include_appendix and insight.affected_customers:
            sorted_customers = sorted(
                insight.affected_customers,
                key=lambda c: c.get("acv", 0),
                reverse=True,
            )[:10]
            customer_rows = []
            for customer in sorted_customers:
                name = customer.get("name", "Unknown")
                segment = customer.get("segment", "Unknown").title()
                acv = customer.get("acv", 0)
                fb_count = customer.get("feedback_count", 0)
                customer_rows.append(f"| {name} | {segment} | ${acv:,.0f} | {fb_count} |")
            customer_table = "\n".join(customer_rows)

        # Format supporting feedback
        feedback_quotes = "\n".join(
            f'{i}. "{quote}"'
            for i, quote in enumerate(insight.supporting_feedback[:10], 1)
        )

        # Build prompt with system instructions
        theme_info = f"**Theme ID:** {insight.theme_id}\n" if insight.theme_id else ""

        prompt = f"""You are an expert Group Product Manager at a B2B SaaS company. Generate a strategic, engineering-ready Product Requirements Document (PRD) based on the ProduckAI Insight provided below.

# Input Data

**Insight ID:** {insight.id}
{theme_info}**Title:** {insight.title}
**Description:** {insight.description}
**Impact:** {insight.impact}
**Recommendation:** {insight.recommendation}
**Severity:** {insight.severity} ({severity_emoji})
**Effort:** {insight.effort}
**Priority:** {insight.priority if insight.priority else "Not set"}
**Priority Score:** {insight.priority_score:.1f}/100
**Feedback Count:** {insight.feedback_count}
**Customer Count:** {insight.customer_count}

**Calculated Metadata:**
- **Total ACV at Risk:** {formatted_acv}
- **Primary Segment:** {metadata.primary_segment.title()} ({metadata.segment_percentage:.0f}% of feedback)
- **Inferred Persona:** {metadata.inferred_persona}

**Supporting Feedback (Customer Quotes):**
{feedback_quotes}

**Affected Customers:**
{len(insight.affected_customers)} customers, with top customers by ACV:
{customer_table if customer_table else "No customer data available"}

# Your Task

Generate a 2-page PRD using the template structure from the PRD_GENERATION_PROMPT.md guide. Follow these critical guidelines:

1. **Strategic Framing:** Use the Total ACV ({formatted_acv}), Severity ({insight.severity}), and Priority Score ({insight.priority_score:.1f}) to explain "why now"

2. **Evidence-Based:** Quote at least 2-3 direct customer quotes from Supporting Feedback in Section 1

3. **Segment & Persona Specificity:** Reference that {metadata.segment_percentage:.0f}% of feedback is from {metadata.primary_segment.title()} segment, affecting {metadata.inferred_persona}

4. **AI-Native Awareness:** If recommendation implies AI/ML (keywords: auto, suggest, classify, detect, predict), include safety guardrails in Section 3

5. **Effort-Based Risk:** Use Effort estimate ({insight.effort}) to assess implementation risk in Section 5

6. **Gap Filling:** If baseline metrics are unknown, use "[TBD - Analytics to Confirm]" - do NOT hallucinate numbers

# Output Format

Generate the PRD in Markdown format following this structure:

1. Header table with Status, Severity, Priority, ACV, Customers, Priority Score
2. Section 1: The Opportunity & Evidence (with direct quotes)
3. Section 2: The Solution Hypothesis (testable hypothesis with metric + target)
4. Section 3: System Behavior & Guardrails (AI safety if applicable)
5. Section 4: Success Metrics (Business, Operational, AI Quality)
6. Section 5: Risks & Mitigation (effort-based assessment)
7. Section 6: Rough Roadmap (3 phases: MVP, Enhancement, Optimization)
{"8. Appendix: Supporting Evidence (customer breakdown table, full quote list)" if include_appendix else ""}

**Tone:** Concise, objective, evidence-backed, action-oriented
**Length:** Target 2 pages (~1000 words) excluding appendix
**Audience:** Executive Leadership (VP/C-Level) and Engineering Leads

Generate the PRD now:"""

        return prompt

    async def regenerate_prd(
        self,
        insight: Insight,
        previous_prd_content: str,
        changes_description: str,
    ) -> GeneratedPRD:
        """
        Regenerate a PRD with updates based on insight changes.

        Args:
            insight: Updated insight object
            previous_prd_content: Previous PRD content
            changes_description: Description of what changed

        Returns:
            Updated GeneratedPRD
        """
        logger.info(f"Regenerating PRD for insight {insight.id}")

        # For now, just generate fresh
        # TODO: Implement smart diff-based regeneration
        return await self.generate_prd(insight)

    def estimate_generation_cost(self, insight: Insight) -> Dict[str, Any]:
        """
        Estimate the cost of generating a PRD.

        Args:
            insight: Insight object

        Returns:
            Cost estimation dict
        """
        # Rough token estimation
        input_tokens = (
            len(insight.title.split())
            + len(insight.description.split())
            + len(insight.impact.split())
            + len(insight.recommendation.split())
            + sum(len(quote.split()) for quote in insight.supporting_feedback)
            + 2000  # System prompt overhead
        ) * 1.3  # Token to word ratio

        output_tokens = 2500  # Typical PRD length

        # Claude Sonnet pricing (as of Nov 2024)
        input_cost = (input_tokens / 1_000_000) * 3.00  # $3/MTok
        output_cost = (output_tokens / 1_000_000) * 15.00  # $15/MTok
        total_cost = input_cost + output_cost

        return {
            "estimated_input_tokens": int(input_tokens),
            "estimated_output_tokens": output_tokens,
            "estimated_cost_usd": round(total_cost, 4),
            "model": "claude-3-opus-20240229",
        }
