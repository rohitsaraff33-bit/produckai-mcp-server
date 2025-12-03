"""Google Docs document processor."""

from typing import Any, Dict, List, Optional

from produckai_mcp.ai import FeedbackClassifier
from produckai_mcp.processors.base import DocumentProcessor
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleDocsProcessor(DocumentProcessor):
    """Process Google Docs documents."""

    MIME_TYPE = "application/vnd.google-apps.document"

    def __init__(self, gdrive_client, classifier: FeedbackClassifier):
        """
        Initialize Google Docs processor.

        Args:
            gdrive_client: GoogleDriveClient instance
            classifier: FeedbackClassifier instance
        """
        self.gdrive_client = gdrive_client
        self.classifier = classifier

    def can_process(self, mime_type: str) -> bool:
        """Check if this processor can handle the file type."""
        return mime_type == self.MIME_TYPE

    async def process(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Google Doc and extract feedback.

        Args:
            file_data: File metadata from Google Drive

        Returns:
            Dictionary with feedback items and metadata
        """
        file_id = file_data["id"]
        file_name = file_data.get("name", "Untitled")

        logger.info(f"Processing Google Doc: {file_name}")

        try:
            # Get document content with structure
            doc_content = self.gdrive_client.export_google_doc(file_id)

            if not doc_content:
                logger.warning(f"Empty document content for {file_name}")
                return {
                    "file_id": file_id,
                    "file_name": file_name,
                    "feedback_items": [],
                    "error": "Empty document",
                }

            # Extract structured content
            structured_content = self._extract_structure(doc_content)

            # Detect document type
            doc_type = self._detect_document_type(structured_content)

            # Extract paragraphs for classification
            paragraphs = self._extract_paragraphs(structured_content)

            # Classify content as feedback
            feedback_from_content = []
            if paragraphs:
                classifications = await self.classifier.classify_messages(
                    [{"text": p} for p in paragraphs]
                )

                for text, classification in zip(paragraphs, classifications):
                    if classification["classification"] == "feedback":
                        feedback_from_content.append({
                            "text": text,
                            "source": "document_content",
                            "confidence": classification["confidence"],
                            "customer_extracted": classification.get("customer_extracted"),
                        })

            # Get and process comments
            comments = self.gdrive_client.get_file_comments(file_id)
            feedback_from_comments = await self._process_comments(comments)

            # Combine feedback
            all_feedback = feedback_from_content + feedback_from_comments

            # Extract metadata
            metadata = self.extract_metadata(file_data)

            # Try to detect customer from metadata if not found in content
            if all_feedback and not any(f.get("customer_extracted") for f in all_feedback):
                detected_customer = self.detect_customer_from_metadata(metadata)
                if detected_customer:
                    logger.info(f"Detected customer from metadata: {detected_customer}")
                    for item in all_feedback:
                        if not item.get("customer_extracted"):
                            item["customer_extracted"] = detected_customer

            logger.info(
                f"Processed {file_name}: {len(all_feedback)} feedback items "
                f"({len(feedback_from_content)} from content, {len(feedback_from_comments)} from comments)"
            )

            return {
                "file_id": file_id,
                "file_name": file_name,
                "document_type": doc_type,
                "structure": structured_content,
                "feedback_items": all_feedback,
                "comments_processed": len(comments),
                "paragraphs_analyzed": len(paragraphs),
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Failed to process Google Doc {file_name}: {e}", exc_info=True)
            return {
                "file_id": file_id,
                "file_name": file_name,
                "feedback_items": [],
                "error": str(e),
            }

    def _extract_structure(self, doc_content: Dict) -> List[Dict]:
        """
        Extract document structure (headings, paragraphs).

        Args:
            doc_content: Google Docs API response

        Returns:
            List of structured elements
        """
        structure = []

        body_content = doc_content.get("body", {}).get("content", [])

        for element in body_content:
            if "paragraph" in element:
                para = element["paragraph"]
                style = para.get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")

                text = self._get_text(para)
                if not text:  # Skip empty paragraphs
                    continue

                if style.startswith("HEADING"):
                    level = int(style[-1]) if style[-1].isdigit() else 1
                    structure.append({
                        "type": "heading",
                        "level": level,
                        "text": text,
                    })
                else:
                    structure.append({
                        "type": "paragraph",
                        "text": text,
                    })

            elif "table" in element:
                # Mark tables for potential future processing
                structure.append({
                    "type": "table",
                    "text": "[Table content]",
                })

        return structure

    def _get_text(self, paragraph: Dict) -> str:
        """
        Extract text from paragraph elements.

        Args:
            paragraph: Paragraph element from Google Docs

        Returns:
            Extracted text
        """
        text_parts = []

        for element in paragraph.get("elements", []):
            if "textRun" in element:
                content = element["textRun"].get("content", "")
                text_parts.append(content)

        return "".join(text_parts).strip()

    def _detect_document_type(self, structure: List[Dict]) -> str:
        """
        Detect document type based on structure and content.

        Args:
            structure: Document structure

        Returns:
            Document type string
        """
        # Combine all text
        all_text = " ".join([s.get("text", "") for s in structure])
        text_lower = all_text.lower()

        # Pattern matching for common document types
        if "interview" in text_lower or "q&a" in text_lower or "q:" in text_lower:
            return "interview_notes"
        elif "meeting" in text_lower or "agenda" in text_lower:
            return "meeting_notes"
        elif "survey" in text_lower or "questionnaire" in text_lower:
            return "survey"
        elif "feedback" in text_lower or "customer feedback" in text_lower:
            return "feedback_collection"
        elif "product requirements" in text_lower or "prd" in text_lower:
            return "product_requirements"
        else:
            return "general_document"

    def _extract_paragraphs(self, structure: List[Dict]) -> List[str]:
        """
        Extract paragraph text for classification.

        Args:
            structure: Document structure

        Returns:
            List of paragraph texts
        """
        paragraphs = []

        for item in structure:
            if item["type"] == "paragraph":
                text = item["text"]
                # Skip very short paragraphs (likely not feedback)
                if len(text) > 20:
                    paragraphs.append(text)

        return paragraphs

    async def _process_comments(self, comments: List[Dict]) -> List[Dict[str, Any]]:
        """
        Process document comments as feedback.

        Args:
            comments: List of comments from Google Drive

        Returns:
            List of feedback items from comments
        """
        if not comments:
            return []

        logger.debug(f"Processing {len(comments)} comments")

        # Prepare comments for classification
        comment_data = []
        for comment in comments:
            content = comment.get("content", "")
            if not content or len(content) < 10:  # Skip very short comments
                continue

            comment_data.append({
                "text": content,
                "author": comment.get("author", {}).get("emailAddress"),
                "created": comment.get("createdTime"),
                "quoted_text": comment.get("quotedFileContent", {}).get("value", ""),
                "replies": comment.get("replies", []),
            })

        if not comment_data:
            return []

        # Classify comments
        try:
            classifications = await self.classifier.classify_messages(
                [{"text": c["text"]} for c in comment_data]
            )

            feedback_items = []
            for comment, classification in zip(comment_data, classifications):
                if classification["classification"] == "feedback":
                    feedback_items.append({
                        "text": comment["text"],
                        "source": "document_comment",
                        "author_email": comment["author"],
                        "confidence": classification["confidence"],
                        "quoted_text": comment["quoted_text"],
                        "customer_extracted": classification.get("customer_extracted"),
                        "has_replies": len(comment["replies"]) > 0,
                    })

            logger.debug(f"Found {len(feedback_items)} feedback items in comments")
            return feedback_items

        except Exception as e:
            logger.error(f"Failed to classify comments: {e}")
            return []
