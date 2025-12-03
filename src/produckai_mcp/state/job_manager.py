"""Job management for long-running operations."""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from produckai_mcp.state.database import Database
from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


class JobManager:
    """Manages long-running background jobs."""

    def __init__(self, database: Database):
        """
        Initialize job manager.

        Args:
            database: Database instance
        """
        self.db = database
        self.active_jobs: Dict[str, asyncio.Task] = {}

    def create_job(
        self,
        integration: str,
        operation: str,
        total_items: Optional[int] = None,
    ) -> str:
        """
        Create a new job record.

        Args:
            integration: Integration name
            operation: Operation name (sync, upload, cluster)
            total_items: Total items to process (if known)

        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())

        self.db.execute_write(
            """
            INSERT INTO sync_jobs (
                id, integration, operation, status,
                total_items, started_at
            ) VALUES (?, ?, ?, 'pending', ?, CURRENT_TIMESTAMP)
            """,
            (job_id, integration, operation, total_items),
        )

        logger.info(f"Created job {job_id} for {integration}:{operation}")
        return job_id

    def start_job(
        self,
        job_id: str,
        job_func: Callable,
    ) -> None:
        """
        Start executing a job.

        Args:
            job_id: Job ID
            job_func: Async function to execute
        """
        # Update status to running
        self.db.execute_write(
            """
            UPDATE sync_jobs
            SET status = 'running', started_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (job_id,),
        )

        # Start async task
        task = asyncio.create_task(self._run_job(job_id, job_func))
        self.active_jobs[job_id] = task

        logger.info(f"Started job {job_id}")

    async def _run_job(self, job_id: str, job_func: Callable) -> None:
        """
        Execute job and handle completion/errors.

        Args:
            job_id: Job ID
            job_func: Job function to execute
        """
        try:
            # Execute job with progress callback
            result = await job_func(
                progress_callback=lambda p, i: self.update_progress(job_id, p, i)
            )

            # Mark as completed
            self.complete_job(job_id, "completed", result)

        except Exception as e:
            logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)
            self.complete_job(job_id, "failed", None, str(e))

        finally:
            # Remove from active jobs
            self.active_jobs.pop(job_id, None)

    def update_progress(
        self,
        job_id: str,
        progress: float,
        processed_items: Optional[int] = None,
    ) -> None:
        """
        Update job progress.

        Args:
            job_id: Job ID
            progress: Progress percentage (0.0 to 1.0)
            processed_items: Number of items processed so far
        """
        params = [progress]
        query = "UPDATE sync_jobs SET progress = ?"

        if processed_items is not None:
            query += ", processed_items = ?"
            params.append(processed_items)

        query += " WHERE id = ?"
        params.append(job_id)

        self.db.execute_write(query, tuple(params))

    def complete_job(
        self,
        job_id: str,
        status: str,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Mark job as completed or failed.

        Args:
            job_id: Job ID
            status: Final status (completed, failed)
            result: Job result (will be serialized to JSON)
            error: Error message if failed
        """
        result_json = json.dumps(result) if result else None

        self.db.execute_write(
            """
            UPDATE sync_jobs
            SET status = ?, result = ?, error = ?,
                completed_at = CURRENT_TIMESTAMP,
                progress = 1.0
            WHERE id = ?
            """,
            (status, result_json, error, job_id),
        )

        logger.info(f"Job {job_id} {status}")

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current job status.

        Args:
            job_id: Job ID

        Returns:
            Job status dictionary or None if not found
        """
        job = self.db.execute_one(
            "SELECT * FROM sync_jobs WHERE id = ?",
            (job_id,),
        )

        if job and job["result"]:
            # Parse JSON result
            job = dict(job)
            try:
                job["result"] = json.loads(job["result"])
            except json.JSONDecodeError:
                pass

        return job

    def get_active_jobs(self) -> list[Dict[str, Any]]:
        """
        Get all active (running or pending) jobs.

        Returns:
            List of job dictionaries
        """
        return self.db.execute(
            """
            SELECT * FROM sync_jobs
            WHERE status IN ('pending', 'running')
            ORDER BY created_at DESC
            """
        )

    def get_recent_jobs(self, limit: int = 10) -> list[Dict[str, Any]]:
        """
        Get recent jobs.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of job dictionaries
        """
        return self.db.execute(
            """
            SELECT * FROM sync_jobs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.

        Args:
            job_id: Job ID

        Returns:
            True if job was cancelled
        """
        task = self.active_jobs.get(job_id)
        if task:
            task.cancel()
            self.complete_job(job_id, "cancelled", error="Cancelled by user")
            return True

        return False

    def cleanup_old_jobs(self, days: int = 7) -> int:
        """
        Clean up old completed jobs.

        Args:
            days: Delete jobs older than this many days

        Returns:
            Number of jobs deleted
        """
        return self.db.execute_write(
            """
            DELETE FROM sync_jobs
            WHERE status IN ('completed', 'failed', 'cancelled')
            AND created_at < datetime('now', '-' || ? || ' days')
            """,
            (days,),
        )
