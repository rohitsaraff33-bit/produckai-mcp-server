"""Google Drive client wrapper for ProduckAI MCP Server."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import io

from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleDriveClient:
    """Wrapper around Google Drive, Docs, and Sheets APIs."""

    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        """
        Initialize Google Drive client.

        Args:
            access_token: Google OAuth access token
            refresh_token: Optional refresh token for token renewal
        """
        # Create credentials
        self.credentials = Credentials(token=access_token)
        if refresh_token:
            self.credentials.refresh_token = refresh_token

        # Initialize API services
        try:
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            self.docs_service = build('docs', 'v1', credentials=self.credentials)
            self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
            logger.info("Google Drive API services initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google API services: {e}")
            raise

    def list_folders(
        self,
        parent_folder_id: Optional[str] = None,
        include_shared: bool = True,
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List folders with metadata.

        Args:
            parent_folder_id: Parent folder ID (None for root)
            include_shared: Include shared drives
            max_results: Maximum folders to return

        Returns:
            List of folder dictionaries
        """
        try:
            query_parts = ["mimeType='application/vnd.google-apps.folder'"]

            if parent_folder_id:
                query_parts.append(f"'{parent_folder_id}' in parents")

            if not include_shared:
                query_parts.append("'me' in owners")

            query = " and ".join(query_parts)

            results = self.drive_service.files().list(
                q=query,
                pageSize=max_results,
                fields="files(id, name, parents, createdTime, modifiedTime, owners, shared, webViewLink)",
                orderBy="modifiedTime desc",
            ).execute()

            folders = results.get('files', [])
            logger.info(f"Listed {len(folders)} folders")
            return folders

        except HttpError as e:
            logger.error(f"Failed to list folders: {e}")
            return []

    def get_folder_statistics(self, folder_id: str) -> Dict[str, Any]:
        """
        Get folder statistics.

        Args:
            folder_id: Folder ID

        Returns:
            Statistics dictionary
        """
        try:
            # Query all files in folder
            query = f"'{folder_id}' in parents and trashed=false"

            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, mimeType, size, modifiedTime)",
                pageSize=1000,
            ).execute()

            files = results.get('files', [])

            # Count by type
            type_counts = {}
            total_size = 0
            latest_modified = None

            for file in files:
                mime_type = file.get('mimeType', 'unknown')
                type_counts[mime_type] = type_counts.get(mime_type, 0) + 1

                # Size (if available)
                if 'size' in file:
                    total_size += int(file['size'])

                # Latest modified
                modified_time = file.get('modifiedTime')
                if modified_time:
                    if not latest_modified or modified_time > latest_modified:
                        latest_modified = modified_time

            # Categorize
            supported_formats = sum([
                type_counts.get('application/vnd.google-apps.document', 0),
                type_counts.get('application/vnd.google-apps.spreadsheet', 0),
                type_counts.get('application/pdf', 0),
            ])

            return {
                "total_files": len(files),
                "supported_formats": supported_formats,
                "type_breakdown": type_counts,
                "total_size_bytes": total_size,
                "last_modified": latest_modified,
            }

        except HttpError as e:
            logger.error(f"Failed to get folder statistics: {e}")
            return {"error": str(e)}

    def list_files_in_folder(
        self,
        folder_id: str,
        file_types: Optional[List[str]] = None,
        modified_after: Optional[str] = None,
        max_results: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        List files in folder with filtering.

        Args:
            folder_id: Folder ID
            file_types: MIME types to include (None for all)
            modified_after: ISO timestamp to filter by
            max_results: Maximum files to return

        Returns:
            List of file dictionaries
        """
        try:
            query_parts = [f"'{folder_id}' in parents", "trashed=false"]

            # Filter by file types
            if file_types:
                type_queries = [f"mimeType='{t}'" for t in file_types]
                query_parts.append(f"({' or '.join(type_queries)})")

            # Filter by modified time
            if modified_after:
                query_parts.append(f"modifiedTime > '{modified_after}'")

            query = " and ".join(query_parts)

            files = []
            page_token = None

            while True:
                results = self.drive_service.files().list(
                    q=query,
                    pageSize=min(max_results - len(files), 100),
                    pageToken=page_token,
                    fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, owners, permissions, webViewLink)",
                    orderBy="modifiedTime desc",
                ).execute()

                files.extend(results.get('files', []))
                page_token = results.get('nextPageToken')

                if not page_token or len(files) >= max_results:
                    break

            logger.info(f"Listed {len(files)} files from folder {folder_id}")
            return files

        except HttpError as e:
            logger.error(f"Failed to list files: {e}")
            return []

    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Get file metadata.

        Args:
            file_id: File ID

        Returns:
            File metadata dictionary
        """
        try:
            file = self.drive_service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, createdTime, modifiedTime, owners, permissions, parents, webViewLink, description",
            ).execute()

            logger.debug(f"Retrieved metadata for file: {file.get('name')}")
            return file

        except HttpError as e:
            logger.error(f"Failed to get file metadata: {e}")
            return {}

    def export_google_doc(self, file_id: str) -> Dict[str, Any]:
        """
        Export Google Doc with structure.

        Args:
            file_id: Document ID

        Returns:
            Document content with structure
        """
        try:
            document = self.docs_service.documents().get(documentId=file_id).execute()
            logger.debug(f"Exported Google Doc: {document.get('title')}")
            return document

        except HttpError as e:
            logger.error(f"Failed to export Google Doc: {e}")
            return {}

    def get_google_sheet_data(self, file_id: str) -> Dict[str, Any]:
        """
        Get Google Sheet data.

        Args:
            file_id: Spreadsheet ID

        Returns:
            Spreadsheet data
        """
        try:
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=file_id,
                includeGridData=True,
            ).execute()

            logger.debug(f"Retrieved Google Sheet: {spreadsheet.get('properties', {}).get('title')}")
            return spreadsheet

        except HttpError as e:
            logger.error(f"Failed to get Google Sheet: {e}")
            return {}

    def get_file_comments(self, file_id: str) -> List[Dict[str, Any]]:
        """
        Get comments on a file.

        Args:
            file_id: File ID

        Returns:
            List of comment dictionaries
        """
        try:
            results = self.drive_service.comments().list(
                fileId=file_id,
                fields="comments(id, content, author, createdTime, quotedFileContent, replies)",
            ).execute()

            comments = results.get('comments', [])
            logger.debug(f"Retrieved {len(comments)} comments for file {file_id}")
            return comments

        except HttpError as e:
            logger.error(f"Failed to get comments: {e}")
            return []

    def download_file(self, file_id: str) -> bytes:
        """
        Download file content (for PDFs, etc.).

        Args:
            file_id: File ID

        Returns:
            File content as bytes
        """
        try:
            request = self.drive_service.files().get_media(fileId=file_id)
            file_data = io.BytesIO()
            downloader = MediaIoBaseDownload(file_data, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(f"Download progress: {int(status.progress() * 100)}%")

            logger.info(f"Downloaded file {file_id}")
            return file_data.getvalue()

        except HttpError as e:
            logger.error(f"Failed to download file: {e}")
            return b''

    def get_start_page_token(self) -> str:
        """
        Get current page token for delta sync.

        Returns:
            Page token string
        """
        try:
            response = self.drive_service.changes().getStartPageToken().execute()
            token = response.get('startPageToken')
            logger.debug(f"Got start page token: {token}")
            return token

        except HttpError as e:
            logger.error(f"Failed to get start page token: {e}")
            return ""

    def get_changes_since_token(
        self,
        start_page_token: str,
        folder_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get changes since last sync (delta sync).

        Args:
            start_page_token: Token from last sync
            folder_id: Optional folder to filter changes

        Returns:
            Dictionary with changes and new token
        """
        try:
            changes = []
            page_token = start_page_token

            while page_token:
                response = self.drive_service.changes().list(
                    pageToken=page_token,
                    spaces='drive',
                    fields='nextPageToken, newStartPageToken, changes(fileId, file(id, name, mimeType, parents, trashed, modifiedTime))',
                ).execute()

                for change in response.get('changes', []):
                    file = change.get('file', {})

                    # Filter by folder if specified
                    if folder_id:
                        parents = file.get('parents', [])
                        if folder_id not in parents:
                            continue

                    # Skip trashed files
                    if file.get('trashed'):
                        continue

                    changes.append({
                        "file_id": change.get('fileId'),
                        "file_name": file.get('name'),
                        "mime_type": file.get('mimeType'),
                        "modified_time": file.get('modifiedTime'),
                        "change_type": self._detect_change_type(file),
                    })

                page_token = response.get('nextPageToken')

                # Break if we have new start token (end of changes)
                if response.get('newStartPageToken'):
                    page_token = None

            new_token = response.get('newStartPageToken', start_page_token)

            logger.info(f"Found {len(changes)} changes since last sync")

            return {
                "changes": changes,
                "new_start_page_token": new_token,
            }

        except HttpError as e:
            logger.error(f"Failed to get changes: {e}")
            return {"changes": [], "new_start_page_token": start_page_token}

    def _detect_change_type(self, file: Dict[str, Any]) -> str:
        """Detect type of change (added, modified, etc.)."""
        # Simple heuristic based on creation vs modification time
        created_time = file.get('createdTime', '')
        modified_time = file.get('modifiedTime', '')

        if created_time == modified_time:
            return "added"
        else:
            return "modified"

    def search_files(
        self,
        query: str,
        file_types: Optional[List[str]] = None,
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search files by name or content.

        Args:
            query: Search query
            file_types: MIME types to filter
            max_results: Maximum results

        Returns:
            List of matching files
        """
        try:
            query_parts = [f"fullText contains '{query}'", "trashed=false"]

            if file_types:
                type_queries = [f"mimeType='{t}'" for t in file_types]
                query_parts.append(f"({' or '.join(type_queries)})")

            search_query = " and ".join(query_parts)

            results = self.drive_service.files().list(
                q=search_query,
                pageSize=max_results,
                fields="files(id, name, mimeType, modifiedTime, webViewLink)",
                orderBy="modifiedTime desc",
            ).execute()

            files = results.get('files', [])
            logger.info(f"Search found {len(files)} files for query: {query}")
            return files

        except HttpError as e:
            logger.error(f"Search failed: {e}")
            return []
