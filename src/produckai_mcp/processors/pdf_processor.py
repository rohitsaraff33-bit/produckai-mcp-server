"""PDF document processor."""

from io import BytesIO
from typing import Any, Dict, List

import PyPDF2

from produckai_mcp.ai import FeedbackClassifier
from produckai_mcp.processors.base import DocumentProcessor
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


class PDFProcessor(DocumentProcessor):
    """Process PDF documents."""

    MIME_TYPE = "application/pdf"
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

    def __init__(self, gdrive_client, classifier: FeedbackClassifier):
        """
        Initialize PDF processor.

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
        Process PDF and extract feedback.

        Args:
            file_data: File metadata from Google Drive

        Returns:
            Dictionary with feedback items and metadata
        """
        file_id = file_data["id"]
        file_name = file_data.get("name", "Untitled")
        file_size = int(file_data.get("size", 0))

        logger.info(f"Processing PDF: {file_name} ({file_size} bytes)")

        # Check file size
        if file_size > self.MAX_FILE_SIZE:
            logger.warning(f"PDF too large: {file_name} ({file_size} bytes)")
            return {
                "file_id": file_id,
                "file_name": file_name,
                "feedback_items": [],
                "error": f"File too large ({file_size} bytes, max {self.MAX_FILE_SIZE})",
            }

        try:
            # Download PDF
            pdf_bytes = self.gdrive_client.download_file(file_id)

            if not pdf_bytes:
                logger.warning(f"Empty PDF content for {file_name}")
                return {
                    "file_id": file_id,
                    "file_name": file_name,
                    "feedback_items": [],
                    "error": "Empty PDF",
                }

            # Extract text
            text_content = self._extract_text(pdf_bytes)

            if not text_content:
                logger.warning(f"No text extracted from PDF: {file_name}")
                return {
                    "file_id": file_id,
                    "file_name": file_name,
                    "feedback_items": [],
                    "error": "No text content extracted (may be scanned/image PDF)",
                }

            # Split into chunks
            chunks = self._split_into_chunks(text_content)

            if not chunks:
                return {
                    "file_id": file_id,
                    "file_name": file_name,
                    "feedback_items": [],
                    "error": "No substantial text chunks found",
                }

            # Classify chunks
            try:
                classifications = await self.classifier.classify_messages(
                    [{"text": chunk} for chunk in chunks]
                )

                feedback_items = []
                for chunk, classification in zip(chunks, classifications):
                    if classification["classification"] == "feedback":
                        feedback_items.append({
                            "text": chunk,
                            "confidence": classification["confidence"],
                            "customer_extracted": classification.get("customer_extracted"),
                            "source": "pdf_document",
                        })

                # Extract metadata
                metadata = self.extract_metadata(file_data)

                # Detect page count
                page_count = text_content.count("\f") + 1  # \f is page break

                logger.info(
                    f"Processed PDF {file_name}: {len(feedback_items)} feedback items "
                    f"from {len(chunks)} chunks ({page_count} pages)"
                )

                return {
                    "file_id": file_id,
                    "file_name": file_name,
                    "pages": page_count,
                    "chunks_analyzed": len(chunks),
                    "feedback_items": feedback_items,
                    "metadata": metadata,
                }

            except Exception as e:
                logger.error(f"Failed to classify PDF chunks: {e}")
                return {
                    "file_id": file_id,
                    "file_name": file_name,
                    "feedback_items": [],
                    "error": f"Classification failed: {str(e)}",
                }

        except Exception as e:
            logger.error(f"Failed to process PDF {file_name}: {e}", exc_info=True)
            return {
                "file_id": file_id,
                "file_name": file_name,
                "feedback_items": [],
                "error": str(e),
            }

    def _extract_text(self, pdf_bytes: bytes) -> str:
        """
        Extract text from PDF.

        Args:
            pdf_bytes: PDF file content

        Returns:
            Extracted text with page breaks
        """
        try:
            pdf_file = BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text_parts = []
            for page in pdf_reader.pages:
                try:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                except Exception as e:
                    logger.warning(f"Failed to extract text from page: {e}")
                    continue

            # Join pages with form feed (page break marker)
            full_text = "\f".join(text_parts)

            logger.debug(f"Extracted {len(full_text)} characters from {len(text_parts)} pages")

            return full_text

        except Exception as e:
            logger.error(f"Failed to extract PDF text: {e}")
            return ""

    def _split_into_chunks(self, text: str, max_length: int = 1000) -> List[str]:
        """
        Split text into processable chunks.

        Args:
            text: Full text content
            max_length: Maximum characters per chunk

        Returns:
            List of text chunks
        """
        # Remove page breaks for now (we tracked them already)
        text = text.replace("\f", "\n\n")

        # Split by double newlines (paragraphs)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        chunks = []
        current_chunk = []
        current_length = 0

        for para in paragraphs:
            # Skip very short paragraphs (likely not meaningful)
            if len(para) < 30:
                continue

            para_length = len(para)

            # If adding this paragraph exceeds max_length, save current chunk
            if current_length + para_length > max_length and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0

            # If single paragraph is too long, split it
            if para_length > max_length:
                # Split by sentences
                sentences = para.replace(". ", ".\n").split("\n")
                for sent in sentences:
                    sent = sent.strip()
                    if len(sent) < 30:
                        continue

                    sent_length = len(sent)

                    if current_length + sent_length > max_length and current_chunk:
                        chunks.append(" ".join(current_chunk))
                        current_chunk = []
                        current_length = 0

                    current_chunk.append(sent)
                    current_length += sent_length
            else:
                current_chunk.append(para)
                current_length += para_length

        # Add last chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        logger.debug(f"Split text into {len(chunks)} chunks")

        return chunks
