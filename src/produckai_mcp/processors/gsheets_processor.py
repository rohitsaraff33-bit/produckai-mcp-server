"""Google Sheets document processor."""

from typing import Any, Dict, List, Optional

from produckai_mcp.ai import FeedbackClassifier
from produckai_mcp.processors.base import DocumentProcessor
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleSheetsProcessor(DocumentProcessor):
    """Process Google Sheets documents."""

    MIME_TYPE = "application/vnd.google-apps.spreadsheet"

    def __init__(self, gdrive_client, classifier: FeedbackClassifier):
        """
        Initialize Google Sheets processor.

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
        Process Google Sheet and extract feedback.

        Args:
            file_data: File metadata from Google Drive

        Returns:
            Dictionary with feedback items and metadata
        """
        file_id = file_data["id"]
        file_name = file_data.get("name", "Untitled")

        logger.info(f"Processing Google Sheet: {file_name}")

        try:
            # Get sheet data
            sheet_data = self.gdrive_client.get_google_sheet_data(file_id)

            if not sheet_data or not sheet_data.get("sheets"):
                logger.warning(f"Empty sheet data for {file_name}")
                return {
                    "file_id": file_id,
                    "file_name": file_name,
                    "feedback_items": [],
                    "error": "Empty spreadsheet",
                }

            # Detect format
            format_type = self._detect_sheet_format(sheet_data)

            # Process based on format
            if format_type == "survey_responses":
                feedback_items = await self._process_survey(sheet_data)
            elif format_type == "feedback_table":
                feedback_items = await self._process_feedback_table(sheet_data)
            else:
                feedback_items = await self._process_generic(sheet_data)

            # Extract metadata
            metadata = self.extract_metadata(file_data)

            logger.info(
                f"Processed {file_name}: {len(feedback_items)} feedback items "
                f"(format: {format_type})"
            )

            return {
                "file_id": file_id,
                "file_name": file_name,
                "format_type": format_type,
                "feedback_items": feedback_items,
                "sheets_processed": len(sheet_data.get("sheets", [])),
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Failed to process Google Sheet {file_name}: {e}", exc_info=True)
            return {
                "file_id": file_id,
                "file_name": file_name,
                "feedback_items": [],
                "error": str(e),
            }

    def _detect_sheet_format(self, sheet_data: Dict) -> str:
        """
        Detect sheet format based on headers.

        Args:
            sheet_data: Spreadsheet data from Google Sheets API

        Returns:
            Format type string
        """
        if not sheet_data.get("sheets"):
            return "unknown"

        first_sheet = sheet_data["sheets"][0]
        headers = self._get_headers(first_sheet)

        if not headers:
            return "generic"

        headers_lower = " ".join(headers).lower()

        # Check for survey format
        survey_indicators = ["timestamp", "response", "feedback", "comment", "rating"]
        if any(ind in headers_lower for ind in survey_indicators):
            return "survey_responses"

        # Check for feedback table format
        table_indicators = ["customer", "feature", "priority", "status", "request"]
        if any(ind in headers_lower for ind in table_indicators):
            return "feedback_table"

        return "generic"

    def _get_headers(self, sheet: Dict) -> List[str]:
        """
        Extract header row from sheet.

        Args:
            sheet: Sheet data

        Returns:
            List of header strings
        """
        try:
            data = sheet.get("data", [])
            if not data:
                return []

            row_data = data[0].get("rowData", [])
            if not row_data:
                return []

            first_row = row_data[0]
            headers = []

            for cell in first_row.get("values", []):
                value = cell.get("formattedValue", "")
                headers.append(value)

            return headers

        except Exception as e:
            logger.warning(f"Failed to extract headers: {e}")
            return []

    async def _process_survey(self, sheet_data: Dict) -> List[Dict]:
        """
        Process survey response format.

        Args:
            sheet_data: Spreadsheet data

        Returns:
            List of feedback items
        """
        logger.debug("Processing as survey format")

        first_sheet = sheet_data["sheets"][0]
        headers = self._get_headers(first_sheet)

        # Find feedback column
        feedback_col_idx = self._find_feedback_column(headers)
        if feedback_col_idx is None:
            logger.warning("No feedback column found in survey")
            return []

        # Find customer column
        customer_col_idx = self._find_customer_column(headers)

        # Extract rows (skip header row)
        data = first_sheet.get("data", [])
        if not data:
            return []

        row_data = data[0].get("rowData", [])[1:]  # Skip header

        feedback_texts = []
        customers = []

        for row in row_data:
            values = row.get("values", [])

            # Get feedback text
            if len(values) > feedback_col_idx:
                feedback_text = values[feedback_col_idx].get("formattedValue", "")
                if feedback_text and len(feedback_text) > 10:  # Skip very short
                    feedback_texts.append({"text": feedback_text})

                    # Get customer if available
                    if customer_col_idx is not None and len(values) > customer_col_idx:
                        customer = values[customer_col_idx].get("formattedValue")
                        customers.append(customer)
                    else:
                        customers.append(None)

        if not feedback_texts:
            return []

        # Classify
        try:
            classifications = await self.classifier.classify_messages(feedback_texts)

            feedback_items = []
            for i, (text, classification) in enumerate(zip(feedback_texts, classifications)):
                if classification["classification"] == "feedback":
                    customer = customers[i] if i < len(customers) else None
                    feedback_items.append({
                        "text": text["text"],
                        "customer_extracted": customer or classification.get("customer_extracted"),
                        "confidence": classification["confidence"],
                        "source": "survey_response",
                    })

            return feedback_items

        except Exception as e:
            logger.error(f"Failed to classify survey responses: {e}")
            return []

    async def _process_feedback_table(self, sheet_data: Dict) -> List[Dict]:
        """
        Process feedback table format.

        Args:
            sheet_data: Spreadsheet data

        Returns:
            List of feedback items
        """
        logger.debug("Processing as feedback table format")

        first_sheet = sheet_data["sheets"][0]
        headers = self._get_headers(first_sheet)

        # Find columns
        feedback_col_idx = self._find_feedback_column(headers)
        customer_col_idx = self._find_customer_column(headers)

        if feedback_col_idx is None:
            logger.warning("No feedback column found in table")
            return []

        # Extract rows
        data = first_sheet.get("data", [])
        if not data:
            return []

        row_data = data[0].get("rowData", [])[1:]  # Skip header

        feedback_items = []

        for row in row_data:
            values = row.get("values", [])

            if len(values) > feedback_col_idx:
                feedback_text = values[feedback_col_idx].get("formattedValue", "")

                if feedback_text and len(feedback_text) > 10:
                    customer = None
                    if customer_col_idx is not None and len(values) > customer_col_idx:
                        customer = values[customer_col_idx].get("formattedValue")

                    # For tables, we assume all rows are feedback (not classified)
                    feedback_items.append({
                        "text": feedback_text,
                        "customer_extracted": customer,
                        "confidence": 0.9,  # High confidence for structured tables
                        "source": "feedback_table",
                    })

        return feedback_items

    async def _process_generic(self, sheet_data: Dict) -> List[Dict]:
        """
        Process generic sheet format.

        Args:
            sheet_data: Spreadsheet data

        Returns:
            List of feedback items
        """
        logger.debug("Processing as generic format")

        # For generic sheets, extract all text cells and classify
        all_cells = []

        for sheet in sheet_data.get("sheets", []):
            data = sheet.get("data", [])
            if not data:
                continue

            for row in data[0].get("rowData", []):
                for cell in row.get("values", []):
                    text = cell.get("formattedValue", "")
                    if text and len(text) > 20:  # Only substantial text
                        all_cells.append({"text": text})

        if not all_cells:
            return []

        # Limit to prevent excessive API calls
        all_cells = all_cells[:100]

        try:
            classifications = await self.classifier.classify_messages(all_cells)

            feedback_items = []
            for text, classification in zip(all_cells, classifications):
                if classification["classification"] == "feedback":
                    feedback_items.append({
                        "text": text["text"],
                        "customer_extracted": classification.get("customer_extracted"),
                        "confidence": classification["confidence"],
                        "source": "sheet_cell",
                    })

            return feedback_items

        except Exception as e:
            logger.error(f"Failed to classify generic sheet: {e}")
            return []

    def _find_feedback_column(self, headers: List[str]) -> Optional[int]:
        """Find the feedback column index."""
        feedback_keywords = ["feedback", "comment", "response", "text", "input", "description", "issue"]
        headers_lower = [h.lower() for h in headers]

        for keyword in feedback_keywords:
            for i, header in enumerate(headers_lower):
                if keyword in header:
                    logger.debug(f"Found feedback column: {headers[i]} (index {i})")
                    return i

        return None

    def _find_customer_column(self, headers: List[str]) -> Optional[int]:
        """Find the customer column index."""
        customer_keywords = ["customer", "company", "client", "organization", "account", "name"]
        headers_lower = [h.lower() for h in headers]

        for keyword in customer_keywords:
            for i, header in enumerate(headers_lower):
                if keyword in header and "email" not in header:  # Exclude email columns
                    logger.debug(f"Found customer column: {headers[i]} (index {i})")
                    return i

        return None
