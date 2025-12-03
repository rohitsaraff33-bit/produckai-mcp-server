"""Google Drive integration tools - folder browsing, sync, and configuration."""

from typing import Any, Dict, List, Optional

from produckai_mcp.ai import CustomerMatcher, FeedbackClassifier
from produckai_mcp.api.client import ProduckAIClient
from produckai_mcp.integrations import GoogleDriveClient, OAuthHandler
from produckai_mcp.processors import (
    GoogleDocsProcessor,
    GoogleSheetsProcessor,
    PDFProcessor,
)
from produckai_mcp.state.database import Database
from produckai_mcp.state.sync_state import SyncStateManager
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)

# Supported MIME types
SUPPORTED_MIME_TYPES = {
    "application/vnd.google-apps.document": "Google Doc",
    "application/vnd.google-apps.spreadsheet": "Google Sheet",
    "application/pdf": "PDF",
}


async def setup_google_drive_integration(
    client_id: str,
    client_secret: str,
) -> Dict[str, Any]:
    """
    Set up Google Drive OAuth integration.

    Starts an OAuth flow that opens your browser to authorize ProduckAI
    to access your Google Drive. A local web server runs temporarily on
    port 8765 to handle the OAuth callback.

    Required Google OAuth setup:
    1. Create project at https://console.cloud.google.com
    2. Enable Drive, Docs, and Sheets APIs
    3. Create OAuth credentials (Desktop app type)
    4. Add authorized redirect URI: http://localhost:8765/callback

    Args:
        client_id: Google OAuth Client ID
        client_secret: Google OAuth Client Secret

    Returns:
        Dict with status, user info, and granted scopes
    """
    try:
        logger.info("Starting Google Drive OAuth flow")

        oauth_handler = OAuthHandler("gdrive")
        result = await oauth_handler.start_google_drive_oauth_flow(
            client_id=client_id,
            client_secret=client_secret,
        )

        return {
            "status": "success",
            "message": f"✅ Google Drive integration configured successfully!\n\n"
                      f"**Account**: {result['user_email']}\n"
                      f"**Name**: {result['user_name']}\n"
                      f"**Scopes**: {len(result['scopes'])} permissions granted\n\n"
                      f"You can now use `browse_drive_folders` to explore your Drive.",
        }

    except Exception as e:
        logger.error(f"Google Drive OAuth failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"❌ Failed to set up Google Drive integration\n\n"
                      f"**Error**: {str(e)}\n\n"
                      f"**Troubleshooting**:\n"
                      f"- Verify Client ID and Secret are correct\n"
                      f"- Ensure redirect URI is http://localhost:8765/callback\n"
                      f"- Check that Drive API is enabled in Google Cloud Console",
        }


async def browse_drive_folders(
    folder_id: Optional[str] = None,
    show_statistics: bool = True,
) -> Dict[str, Any]:
    """
    Browse Google Drive folders with statistics.

    Lists folders in your Drive and shows useful statistics like file counts,
    supported formats, and last modified times. Helps you identify which
    folders contain feedback documents.

    Args:
        folder_id: Parent folder ID to browse (None for root)
        show_statistics: Include folder statistics

    Returns:
        Dict with folder list and statistics
    """
    try:
        # Get token
        access_token = OAuthHandler.get_google_drive_token()
        if not access_token:
            return {
                "status": "error",
                "message": "❌ Not authenticated with Google Drive\n\n"
                          "Run `setup_google_drive_integration` first.",
            }

        # Create client
        refresh_token = OAuthHandler.get_google_drive_refresh_token()
        gdrive_client = GoogleDriveClient(access_token, refresh_token)

        # List folders
        folders = gdrive_client.list_folders(
            parent_folder_id=folder_id,
            include_shared=True,
        )

        if not folders:
            return {
                "status": "success",
                "message": "📁 No folders found\n\n"
                          "Either this folder is empty or you don't have access.",
            }

        # Build response
        lines = [f"📁 **Found {len(folders)} folders**\n"]

        for folder in folders[:20]:  # Limit to 20 for readability
            folder_name = folder.get("name", "Untitled")
            folder_id_str = folder.get("id")
            modified_time = folder.get("modifiedTime", "Unknown")

            lines.append(f"\n**{folder_name}**")
            lines.append(f"  ID: `{folder_id_str}`")
            lines.append(f"  Modified: {modified_time}")

            # Add statistics if requested
            if show_statistics:
                stats = gdrive_client.get_folder_statistics(folder_id_str)

                if "error" not in stats:
                    total_files = stats.get("total_files", 0)
                    supported = stats.get("supported_formats", 0)

                    lines.append(f"  Files: {total_files} total, {supported} supported formats")

                    # Show file type breakdown
                    type_breakdown = stats.get("type_breakdown", {})
                    doc_count = type_breakdown.get("application/vnd.google-apps.document", 0)
                    sheet_count = type_breakdown.get("application/vnd.google-apps.spreadsheet", 0)
                    pdf_count = type_breakdown.get("application/pdf", 0)

                    if doc_count + sheet_count + pdf_count > 0:
                        lines.append(f"  Types: {doc_count} Docs, {sheet_count} Sheets, {pdf_count} PDFs")

        if len(folders) > 20:
            lines.append(f"\n... and {len(folders) - 20} more folders")

        return {
            "status": "success",
            "message": "\n".join(lines),
            "folders": folders,  # Full data for programmatic use
        }

    except Exception as e:
        logger.error(f"Failed to browse folders: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"❌ Failed to browse folders\n\n**Error**: {str(e)}",
        }


async def sync_drive_folders(
    api_client: ProduckAIClient,
    database: Database,
    sync_state: SyncStateManager,
    folder_ids: List[str],
    file_types: Optional[List[str]] = None,
    force_full_sync: bool = False,
) -> Dict[str, Any]:
    """
    Sync folders and extract feedback using AI.

    This is the main tool for Google Drive integration. It processes
    documents from specified folders, extracts feedback using AI, and
    stores it in ProduckAI backend.

    Supports:
    - Google Docs (with comments)
    - Google Sheets (auto-detects format)
    - PDFs (text extraction)
    - Delta sync (only new/modified files)
    - Customer attribution

    Args:
        api_client: ProduckAI API client
        database: Database instance
        sync_state: Sync state manager
        folder_ids: List of folder IDs to sync
        file_types: Optional MIME types to filter (None for all supported)
        force_full_sync: Force full sync instead of delta

    Returns:
        Dict with sync summary and statistics
    """
    try:
        logger.info(f"Starting Google Drive sync for {len(folder_ids)} folders")

        # Get token
        access_token = OAuthHandler.get_google_drive_token()
        if not access_token:
            return {
                "status": "error",
                "message": "❌ Not authenticated with Google Drive\n\n"
                          "Run `setup_google_drive_integration` first.",
            }

        # Create client
        refresh_token = OAuthHandler.get_google_drive_refresh_token()
        gdrive_client = GoogleDriveClient(access_token, refresh_token)

        # Initialize AI components
        classifier = FeedbackClassifier()
        customer_matcher = CustomerMatcher(database)

        # Initialize processors
        processors = {
            "application/vnd.google-apps.document": GoogleDocsProcessor(gdrive_client, classifier),
            "application/vnd.google-apps.spreadsheet": GoogleSheetsProcessor(gdrive_client, classifier),
            "application/pdf": PDFProcessor(gdrive_client, classifier),
        }

        # Filter processors by file_types if specified
        if file_types:
            processors = {k: v for k, v in processors.items() if k in file_types}

        # Process each folder
        total_files_processed = 0
        total_feedback_extracted = 0
        folder_results = []

        for folder_id in folder_ids:
            logger.info(f"Processing folder: {folder_id}")

            try:
                # Check sync state
                state = sync_state.get_sync_state("gdrive", folder_id)
                last_sync_timestamp = state.get("last_sync_timestamp") if state else None

                # Determine if full sync or delta
                should_full_sync = force_full_sync or sync_state.should_full_sync("gdrive", folder_id)

                if should_full_sync:
                    logger.info("Performing full sync (30 days)")
                    # Full sync - get files from last 30 days
                    from datetime import datetime, timedelta
                    thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat() + "Z"
                    modified_after = thirty_days_ago
                else:
                    logger.info(f"Performing delta sync since {last_sync_timestamp}")
                    modified_after = last_sync_timestamp

                # List files to process
                files = gdrive_client.list_files_in_folder(
                    folder_id=folder_id,
                    file_types=list(processors.keys()) if processors else None,
                    modified_after=modified_after,
                )

                if not files:
                    logger.info(f"No files to process in folder {folder_id}")
                    folder_results.append({
                        "folder_id": folder_id,
                        "files_processed": 0,
                        "feedback_extracted": 0,
                        "status": "no_new_files",
                    })
                    continue

                logger.info(f"Found {len(files)} files to process")

                # Process each file
                folder_feedback_count = 0
                files_processed = 0

                for file_data in files:
                    file_id = file_data["id"]
                    file_name = file_data["name"]
                    mime_type = file_data["mimeType"]

                    logger.debug(f"Processing: {file_name} ({mime_type})")

                    # Get appropriate processor
                    processor = processors.get(mime_type)
                    if not processor:
                        logger.debug(f"No processor for {mime_type}, skipping")
                        continue

                    try:
                        # Process document
                        result = await processor.process(file_data)

                        if "error" in result:
                            logger.warning(f"Error processing {file_name}: {result['error']}")
                            continue

                        feedback_items = result.get("feedback_items", [])

                        # Store feedback
                        for item in feedback_items:
                            # Try customer matching
                            customer_name = item.get("customer_extracted")

                            if not customer_name:
                                # Try pattern matching
                                customer_name = customer_matcher.match_customer(item["text"])

                            # Upload feedback via CSV (backend doesn't support direct POST)
                            try:
                                import csv
                                import tempfile
                                from datetime import datetime

                                with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
                                    writer = csv.DictWriter(f, fieldnames=['feedback', 'customer', 'date'])
                                    writer.writeheader()
                                    writer.writerow({
                                        'feedback': item["text"],
                                        'customer': customer_name or "Unknown",
                                        'source': "gdrive",
                                        'date': datetime.now().strftime('%Y-%m-%d')
                                    })
                                    temp_path = Path(f.name)

                                try:
                                    upload_result = await api_client.upload_csv(temp_path, template_type="standard")
                                    if upload_result.feedback_count > 0:
                                        folder_feedback_count += upload_result.feedback_count
                                finally:
                                    if temp_path.exists():
                                        temp_path.unlink()

                            except Exception as e:
                                logger.error(f"Failed to store feedback: {e}")
                                continue

                        files_processed += 1

                    except Exception as e:
                        logger.error(f"Failed to process file {file_name}: {e}")
                        continue

                # Update sync state
                latest_modified = max([f.get("modifiedTime", "") for f in files], default=None)

                sync_state.update_sync_state(
                    integration="gdrive",
                    resource_id=folder_id,
                    last_timestamp=latest_modified,
                    new_items=folder_feedback_count,
                    status="success",
                )

                total_files_processed += files_processed
                total_feedback_extracted += folder_feedback_count

                folder_results.append({
                    "folder_id": folder_id,
                    "files_processed": files_processed,
                    "feedback_extracted": folder_feedback_count,
                    "status": "success",
                })

            except Exception as e:
                logger.error(f"Failed to process folder {folder_id}: {e}")
                folder_results.append({
                    "folder_id": folder_id,
                    "status": "error",
                    "error": str(e),
                })
                continue

        # Build summary message
        lines = [
            f"🔄 **Google Drive Sync Complete**\n",
            f"**Folders synced**: {len(folder_ids)}",
            f"**Files processed**: {total_files_processed}",
            f"**Feedback extracted**: {total_feedback_extracted}\n",
        ]

        for result in folder_results:
            if result["status"] == "success":
                lines.append(
                    f"✅ `{result['folder_id'][:20]}...`: "
                    f"{result['files_processed']} files, {result['feedback_extracted']} feedback"
                )
            elif result["status"] == "error":
                lines.append(f"❌ `{result['folder_id'][:20]}...`: {result.get('error', 'Unknown error')}")
            else:
                lines.append(f"ℹ️ `{result['folder_id'][:20]}...`: No new files")

        return {
            "status": "success",
            "message": "\n".join(lines),
            "summary": {
                "folders_synced": len(folder_ids),
                "files_processed": total_files_processed,
                "feedback_extracted": total_feedback_extracted,
            },
        }

    except Exception as e:
        logger.error(f"Drive sync failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"❌ Failed to sync Google Drive folders\n\n**Error**: {str(e)}",
        }


async def get_drive_sync_status(
    sync_state: SyncStateManager,
) -> Dict[str, Any]:
    """
    Get Google Drive sync status and history.

    Shows sync history for all folders, including last sync times,
    item counts, and any errors. Helps monitor sync health.

    Args:
        sync_state: Sync state manager

    Returns:
        Dict with sync status for all folders
    """
    try:
        # Get all Google Drive sync states
        all_states = sync_state.get_all_sync_states("gdrive")

        if not all_states:
            return {
                "status": "success",
                "message": "📊 **No Google Drive syncs yet**\n\n"
                          "Use `sync_drive_folders` to start syncing.",
            }

        lines = [f"📊 **Google Drive Sync Status** ({len(all_states)} folders)\n"]

        # Sort by last sync time
        all_states.sort(key=lambda x: x.get("last_sync_time", ""), reverse=True)

        for state in all_states:
            folder_id = state["resource_id"]
            last_sync = state.get("last_sync_time", "Never")
            total_items = state.get("total_items_synced", 0)
            last_run_items = state.get("last_sync_new_items", 0)
            status = state.get("last_sync_status", "unknown")

            status_emoji = "✅" if status == "success" else "❌"

            lines.append(f"{status_emoji} **Folder** `{folder_id[:20]}...`")
            lines.append(f"  Last sync: {last_sync}")
            lines.append(f"  Total synced: {total_items} items")
            lines.append(f"  Last run: {last_run_items} new items")

            if status != "success":
                error_msg = state.get("last_sync_error", "Unknown error")
                lines.append(f"  Error: {error_msg}")

            lines.append("")  # Blank line

        return {
            "status": "success",
            "message": "\n".join(lines),
            "states": all_states,  # Full data for programmatic use
        }

    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        return {
            "status": "error",
            "message": f"❌ Failed to get sync status\n\n**Error**: {str(e)}",
        }


async def preview_drive_folder(
    folder_id: str,
) -> Dict[str, Any]:
    """
    Preview folder contents before syncing (dry run).

    Shows what files would be processed without actually processing them.
    Provides estimates for processing time and AI costs.

    Args:
        folder_id: Folder ID to preview

    Returns:
        Dict with preview information
    """
    try:
        # Get token
        access_token = OAuthHandler.get_google_drive_token()
        if not access_token:
            return {
                "status": "error",
                "message": "❌ Not authenticated with Google Drive\n\n"
                          "Run `setup_google_drive_integration` first.",
            }

        # Create client
        refresh_token = OAuthHandler.get_google_drive_refresh_token()
        gdrive_client = GoogleDriveClient(access_token, refresh_token)

        # List files
        files = gdrive_client.list_files_in_folder(
            folder_id=folder_id,
            file_types=list(SUPPORTED_MIME_TYPES.keys()),
        )

        if not files:
            return {
                "status": "success",
                "message": "📋 **No supported files in folder**\n\n"
                          "This folder doesn't contain any Docs, Sheets, or PDFs.",
            }

        # Analyze files
        type_counts = {}
        total_size = 0

        for file in files:
            mime_type = file.get("mimeType")
            type_name = SUPPORTED_MIME_TYPES.get(mime_type, "Other")
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

            if "size" in file:
                total_size += int(file["size"])

        # Estimate processing
        total_files = len(files)
        estimated_time = total_files * 8  # ~8 seconds per file average
        estimated_cost = total_files * 0.05  # ~$0.05 per file for AI

        lines = [
            f"📋 **Folder Preview**\n",
            f"**Folder ID**: `{folder_id}`",
            f"**Total files**: {total_files}",
            f"**Total size**: {total_size / 1024 / 1024:.1f} MB\n",
            f"**File types**:",
        ]

        for type_name, count in type_counts.items():
            lines.append(f"  • {type_name}: {count} files")

        lines.extend([
            f"\n**Estimates**:",
            f"  • Processing time: ~{estimated_time // 60} minutes",
            f"  • AI cost: ~${estimated_cost:.2f}",
            f"  • Expected feedback: ~{total_files * 3}-{total_files * 5} items\n",
            f"💡 Run `sync_drive_folders` with this folder ID to process.",
        ])

        return {
            "status": "success",
            "message": "\n".join(lines),
            "preview": {
                "total_files": total_files,
                "type_counts": type_counts,
                "estimated_time_seconds": estimated_time,
                "estimated_cost_usd": estimated_cost,
            },
        }

    except Exception as e:
        logger.error(f"Failed to preview folder: {e}")
        return {
            "status": "error",
            "message": f"❌ Failed to preview folder\n\n**Error**: {str(e)}",
        }


async def configure_drive_processing(
    database: Database,
    action: str,
    setting: Optional[str] = None,
    value: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Configure Google Drive processing settings.

    Manage settings like comment processing, file type filters,
    and size limits.

    Args:
        database: Database instance
        action: Action to perform (get, set, list)
        setting: Setting name (for get/set actions)
        value: Setting value (for set action)

    Returns:
        Dict with configuration result
    """
    try:
        if action == "list":
            # List all settings
            # Note: For now, return hardcoded defaults
            # In future, store in database
            settings = {
                "process_comments": "true",
                "process_pdfs": "true",
                "max_file_size_mb": "100",
                "chunk_size": "1000",
            }

            lines = [
                "⚙️ **Google Drive Processing Settings**\n",
                "**Current settings**:",
            ]

            for key, val in settings.items():
                lines.append(f"  • `{key}`: {val}")

            return {
                "status": "success",
                "message": "\n".join(lines),
                "settings": settings,
            }

        elif action == "get":
            if not setting:
                return {
                    "status": "error",
                    "message": "❌ Setting name required for 'get' action",
                }

            # Return default for now
            defaults = {
                "process_comments": "true",
                "process_pdfs": "true",
                "max_file_size_mb": "100",
                "chunk_size": "1000",
            }

            value = defaults.get(setting, "unknown")

            return {
                "status": "success",
                "message": f"⚙️ `{setting}` = {value}",
                "setting": setting,
                "value": value,
            }

        elif action == "set":
            if not setting or value is None:
                return {
                    "status": "error",
                    "message": "❌ Both setting name and value required for 'set' action",
                }

            # For now, just acknowledge (not persisted)
            return {
                "status": "success",
                "message": f"⚙️ Setting `{setting}` = {value}\n\n"
                          "Note: Settings currently not persisted. Will be saved in database in future update.",
                "setting": setting,
                "value": value,
            }

        else:
            return {
                "status": "error",
                "message": f"❌ Unknown action: {action}\n\n"
                          "Valid actions: list, get, set",
            }

    except Exception as e:
        logger.error(f"Failed to configure settings: {e}")
        return {
            "status": "error",
            "message": f"❌ Failed to configure settings\n\n**Error**: {str(e)}",
        }
