#!/usr/bin/env python3
"""
Maintenance script to update keywords for all existing images in the database.

This script reads EXIF/XMP metadata from all images in the database and updates
their keywords field. It overwrites existing keywords as the EXIF data is
considered the source of truth.

Usage:
    python update_keywords.py
    # OR with uv:
    uv run python update_keywords.py
"""

import sys
from pathlib import Path

from framegallery import database, models
from framegallery.config import settings
from framegallery.importer2.importer import Importer
from framegallery.logging_config import setup_logging

logger = setup_logging(log_level=settings.log_level)


def update_all_keywords() -> None:
    """Update keywords for all images in the database."""
    db = database.SessionLocal()

    try:
        # Get all images from database
        images = db.query(models.Image).all()
        total_images = len(images)

        if total_images == 0:
            logger.info("No images found in database")
            return

        logger.info("Found %d images to process", total_images)

        updated_count = 0
        skipped_count = 0
        error_count = 0

        for i, image in enumerate(images, 1):
            logger.info("Processing image %d/%d: %s", i, total_images, image.filename)

            # Check if file exists
            if not Path(image.filepath).exists():
                logger.warning("Image file not found: %s", image.filepath)
                skipped_count += 1
                continue

            try:
                # Read keywords using the same function as importer
                keywords = Importer.read_exif_keywords(image.filepath)

                # Update the image record
                old_keywords = image.keywords
                image.keywords = keywords if keywords else None

                # Log the change
                if old_keywords != image.keywords:
                    logger.info("Updated keywords for %s: %s -> %s", image.filename, old_keywords, image.keywords)
                    updated_count += 1
                else:
                    logger.debug("No keyword changes for %s", image.filename)

            except Exception:
                logger.exception("Error processing image %s", image.filepath)
                error_count += 1
                continue

        # Commit all changes
        db.commit()

        logger.info(
            "Keyword update complete: %d updated, %d skipped, %d errors out of %d total images",
            updated_count,
            skipped_count,
            error_count,
            total_images,
        )

    except Exception:
        logger.exception("Fatal error during keyword update")
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    """Execute the keyword update process."""
    try:
        logger.info("Starting keyword update for all images")
        update_all_keywords()
        logger.info("Keyword update completed successfully")
    except (KeyboardInterrupt, SystemExit):
        logger.info("Keyword update interrupted by user")
        sys.exit(1)
    except Exception:
        logger.exception("Keyword update failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
