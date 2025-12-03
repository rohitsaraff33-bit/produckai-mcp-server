"""AI-powered feedback classification for Slack messages."""

import json
import os
from typing import Dict, List, Optional

from anthropic import AsyncAnthropic

from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


class FeedbackClassifier:
    """Classifies Slack messages as feedback or noise using Claude."""

    def __init__(self, model: str = "claude-3-haiku-20240307"):
        """
        Initialize feedback classifier.

        Args:
            model: Claude model to use for classification
        """
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable not set. "
                "Required for AI-powered feedback classification."
            )

        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        logger.info(f"Initialized feedback classifier with model: {model}")

    async def classify_messages(
        self,
        messages: List[Dict[str, any]],
        batch_size: int = 10,
        confidence_threshold: float = 0.7,
    ) -> List[Dict[str, any]]:
        """
        Classify multiple Slack messages as feedback or noise.

        Args:
            messages: List of Slack message dictionaries
            batch_size: Number of messages to classify at once
            confidence_threshold: Minimum confidence to classify as feedback

        Returns:
            List of classifications with confidence scores

        Example classification:
            {
                "message_id": "1234567890.123456",
                "text": "We need bulk export ASAP",
                "classification": "feedback",  # or "noise"
                "confidence": 0.95,
                "reason": "Feature request for bulk export functionality",
                "customer_extracted": "Acme Corp",  # or None
                "requires_manual_tagging": False,
            }
        """
        logger.info(f"Classifying {len(messages)} messages")

        classifications = []

        # Process in batches
        for i in range(0, len(messages), batch_size):
            batch = messages[i : i + batch_size]
            batch_results = await self._classify_batch(batch, confidence_threshold)
            classifications.extend(batch_results)

        logger.info(
            f"Classified {len(classifications)} messages: "
            f"{sum(1 for c in classifications if c['classification'] == 'feedback')} feedback, "
            f"{sum(1 for c in classifications if c['classification'] == 'noise')} noise"
        )

        return classifications

    async def _classify_batch(
        self,
        messages: List[Dict[str, any]],
        confidence_threshold: float,
    ) -> List[Dict[str, any]]:
        """Classify a batch of messages."""
        prompt = self._build_classification_prompt(messages)

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0,  # Deterministic for consistency
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            response_text = response.content[0].text
            classifications = self._parse_classification_response(
                response_text, messages, confidence_threshold
            )

            return classifications

        except Exception as e:
            logger.error(f"Classification failed: {str(e)}", exc_info=True)
            # Return default classifications (noise) on error
            return [
                {
                    "message_id": msg.get("ts"),
                    "text": msg.get("text", ""),
                    "classification": "noise",
                    "confidence": 0.5,
                    "reason": "Classification failed",
                    "customer_extracted": None,
                    "requires_manual_tagging": True,
                }
                for msg in messages
            ]

    def _build_classification_prompt(self, messages: List[Dict[str, any]]) -> str:
        """Build prompt for Claude to classify messages."""
        messages_text = []
        for i, msg in enumerate(messages, 1):
            text = msg.get("text", "")
            messages_text.append(f"Message {i}:\n{text}")

        messages_str = "\n\n".join(messages_text)

        return f"""Analyze these Slack messages and classify each as either "feedback" or "noise".

**Customer feedback** includes:
- Feature requests or enhancement suggestions
- Bug reports or technical issues
- Usability problems or pain points
- Customer complaints about product functionality
- Product improvement suggestions
- Integration or API requests
- Performance or reliability concerns

**Noise** includes:
- Internal team discussions not related to product feedback
- Greetings, pleasantries, or social chat
- Off-topic conversations
- Scheduling, logistics, or administrative messages
- Questions about processes (not product features)
- General updates or announcements
- Thank you messages or acknowledgments

**Important**: Be strict about classification. Only classify as "feedback" if the message clearly relates to product features, bugs, or user experience.

For each message, also try to extract:
- **Customer name** if mentioned explicitly (e.g., "Acme Corp said...", "feedback from TechStart")
- **Reason** for the classification (1-2 sentences)
- **Confidence** score (0.0 to 1.0)

Messages:
{messages_str}

Return a JSON array with this exact format:
[
  {{
    "message_id": 1,
    "classification": "feedback",
    "confidence": 0.95,
    "reason": "Feature request for bulk export functionality",
    "customer_name": "Acme Corp"
  }},
  {{
    "message_id": 2,
    "classification": "noise",
    "confidence": 0.85,
    "reason": "Internal discussion about meeting schedules",
    "customer_name": null
  }}
]

**Important**:
- Return ONLY the JSON array, no other text
- Ensure valid JSON syntax
- Include all {len(messages)} messages in order
- Set customer_name to null if not mentioned
"""

    def _parse_classification_response(
        self,
        response_text: str,
        messages: List[Dict[str, any]],
        confidence_threshold: float,
    ) -> List[Dict[str, any]]:
        """Parse Claude's classification response."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()

            parsed = json.loads(json_str)

            # Map back to original messages
            classifications = []
            for i, msg in enumerate(messages):
                if i < len(parsed):
                    result = parsed[i]
                    classification = result.get("classification", "noise")
                    confidence = result.get("confidence", 0.5)

                    # Apply confidence threshold
                    if classification == "feedback" and confidence < confidence_threshold:
                        classification = "noise"
                        result["reason"] = f"Low confidence ({confidence:.2f})"

                    classifications.append({
                        "message_id": msg.get("ts"),
                        "text": msg.get("text", ""),
                        "classification": classification,
                        "confidence": confidence,
                        "reason": result.get("reason", ""),
                        "customer_extracted": result.get("customer_name"),
                        "requires_manual_tagging": (
                            classification == "feedback" and not result.get("customer_name")
                        ),
                    })
                else:
                    # Fallback for missing classifications
                    classifications.append({
                        "message_id": msg.get("ts"),
                        "text": msg.get("text", ""),
                        "classification": "noise",
                        "confidence": 0.5,
                        "reason": "No classification returned",
                        "customer_extracted": None,
                        "requires_manual_tagging": False,
                    })

            return classifications

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse classification JSON: {e}")
            logger.debug(f"Response text: {response_text}")
            # Return default classifications
            return [
                {
                    "message_id": msg.get("ts"),
                    "text": msg.get("text", ""),
                    "classification": "noise",
                    "confidence": 0.5,
                    "reason": "JSON parse error",
                    "customer_extracted": None,
                    "requires_manual_tagging": False,
                }
                for msg in messages
            ]
