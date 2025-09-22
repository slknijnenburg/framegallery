import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from framegallery.repository.config_repository import ConfigKey, ConfigRepository

if TYPE_CHECKING:
    from framegallery.frame_connector.frame_connector import FrameConnector

logger = logging.getLogger("framegallery")


class TvCleanupService:
    """Service for automatically cleaning up old TV files to prevent memory buildup."""

    def __init__(self, frame_connector: "FrameConnector", config_repository: ConfigRepository) -> None:
        self._frame_connector = frame_connector
        self._config_repository = config_repository
        self._cleanup_interval = 3600  # 1 hour in seconds
        self._files_to_keep = 3  # Keep the 3 most recent files

    async def run_periodic_cleanup(self) -> None:
        """Run the cleanup service periodically while checking if it's enabled."""
        logger.info("TV auto-cleanup service started")

        while True:
            try:
                # Check if auto-cleanup is enabled
                cleanup_enabled = self._is_cleanup_enabled()

                if cleanup_enabled:
                    logger.info("Auto-cleanup is enabled, running TV file cleanup")
                    await self._cleanup_old_tv_files()
                else:
                    logger.debug("Auto-cleanup is disabled, skipping cleanup")

                # Wait for the next cleanup cycle
                await asyncio.sleep(self._cleanup_interval)

            except Exception:
                logger.exception("Error in TV auto-cleanup service, will retry in next cycle")
                await asyncio.sleep(self._cleanup_interval)

    def _is_cleanup_enabled(self) -> bool:
        """Check if auto-cleanup is enabled in the configuration."""
        try:
            config = self._config_repository.get_or(ConfigKey.AUTO_CLEANUP_ENABLED, default_value=False)
            return config.value == "true" if isinstance(config.value, str) else bool(config.value)
        except Exception:
            logger.exception("Error checking auto-cleanup configuration, defaulting to disabled")
            return False

    async def _cleanup_old_tv_files(self) -> None:
        """Clean up old TV files, keeping only the most recent ones."""
        try:
            # Get all files from the TV (user content category)
            tv_files = await self._frame_connector.list_files(category="MY-C0002")

            if tv_files is None:
                logger.warning("TV not connected, skipping cleanup")
                return

            if not tv_files:
                logger.info("No files found on TV, nothing to cleanup")
                return

            logger.info("Found %d files on TV for cleanup evaluation", len(tv_files))

            # Sort files by date (most recent first)
            sorted_files = self._sort_files_by_date(tv_files)

            # Determine which files to delete (all except the most recent N)
            files_to_delete = sorted_files[self._files_to_keep :]

            if not files_to_delete:
                logger.info(
                    "Only %d files found, all within keep limit of %d, no cleanup needed",
                    len(sorted_files),
                    self._files_to_keep,
                )
                return

            logger.info(
                "Will delete %d old files, keeping %d most recent files",
                len(files_to_delete),
                min(len(sorted_files), self._files_to_keep),
            )

            # Extract content IDs for deletion
            content_ids_to_delete = [file_info["content_id"] for file_info in files_to_delete]

            # Delete old files using the multi-delete functionality
            deletion_results = await self._frame_connector.delete_files(content_ids_to_delete)

            if deletion_results is None:
                logger.error("TV became unavailable during cleanup")
                return

            # Log cleanup results
            deleted_count = sum(1 for success in deletion_results.values() if success)
            failed_count = len(deletion_results) - deleted_count

            logger.info("Auto-cleanup completed: %d files deleted, %d failed", deleted_count, failed_count)

            if failed_count > 0:
                failed_files = [content_id for content_id, success in deletion_results.items() if not success]
                logger.warning("Failed to delete %d files: %s", failed_count, failed_files)

        except Exception:
            logger.exception("Error during TV file cleanup")

    def _sort_files_by_date(self, tv_files: list[dict]) -> list[dict]:
        """Sort TV files by date, most recent first."""

        def parse_tv_date(date_string: str | None) -> datetime:
            """Parse Samsung TV date format: '2025:09:08 17:58:00'."""
            if not date_string:
                # Use naive datetime for consistency (TV dates don't include timezone)
                return datetime.min  # noqa: DTZ901

            try:
                # Convert Samsung TV format to standard format
                normalized_date = date_string.replace(":", "-", 2)  # Only replace first 2 colons
                # Use naive datetime for consistency with Samsung TV format
                return datetime.strptime(normalized_date, "%Y-%m-%d %H:%M:%S")  # noqa: DTZ007
            except (ValueError, TypeError):
                logger.warning("Could not parse date '%s', treating as oldest", date_string)
                return datetime.min  # noqa: DTZ901

        # Sort by date, most recent first
        return sorted(tv_files, key=lambda f: parse_tv_date(f.get("date")), reverse=True)

    async def cleanup_now(self) -> dict[str, int]:
        """
        Run cleanup immediately (for manual triggers).

        Returns:
            Dictionary with deleted_count and failed_count

        """
        logger.info("Manual TV cleanup triggered")

        try:
            await self._cleanup_old_tv_files()
        except Exception as e:
            logger.exception("Error during manual cleanup")
            return {"status": "error", "message": str(e)}
        else:
            return {"status": "completed"}
