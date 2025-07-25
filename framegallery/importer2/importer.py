import asyncio
import os
import sys
from pathlib import Path

from PIL import Image
from PIL.ExifTags import GPSTAGS, IFD, TAGS
from pillow_heif import register_heif_opener  # HEIF support
from sqlalchemy.orm import Session

import framegallery.aspect_ratio
from framegallery import crud, database, models
from framegallery.config import settings
from framegallery.logging_config import setup_logging

logger = setup_logging(log_level=settings.log_level)
register_heif_opener()  # HEIF support


class Importer:
    """
    Imports all images from the gallery folder to the SQLite database.
    Generates thumbnails on the fly for display in the UI.
    Calculates aspect ratio of the image.
    """

    def __init__(self, image_path: str, db: Session) -> None:
        self.image_path = image_path
        self._db = db

    def get_imagelist_on_disk(self) -> list[Path]:
        """Get a list of all images on disk."""
        files = sorted(
            [
                Path(root) / f
                for root, dirs, files in os.walk(self.image_path)
                for f in files
                if (f.endswith((".jpg", ".png"))) and not f.endswith(".thumbnail.jpg")
            ]
        )

        logger.info("Found %d images in folder %s", len(files), self.image_path)

        return files

    def check_if_local_image_exists_in_db(self, image_path: str) -> models.Image | None:
        """Check if an image exists in the database by its file path."""
        return crud.get_image_by_path(self._db, filepath=image_path)

    @staticmethod
    def get_image_dimensions(img: Image) -> tuple[int, int]:
        """Get the dimensions of an image using PIL."""
        try:
            width, height = img.size
        except Exception:
            logger.exception("Error reading image dimensions")
            return 0, 0
        return width, height

    def read_file(self, filename: str) -> tuple[bytes, str] | tuple[None, None]:
        """Read a file from disk and return the file data and type."""
        try:
            with Path(filename).open("rb") as f:
                file_data = f.read()
                file_type = self.get_file_type(filename)
                return file_data, file_type
        except Exception:
            logger.exception("Error reading file: %s", filename)
        return None, None

    @staticmethod
    def get_file_type(filename: str) -> str | None:
        """Try to figure out what kind of image file is, starting with the extension."""
        try:
            file_type = Path(filename).suffix.lower()
            return file_type.lower() if file_type else None
        except Exception:
            logger.exception("Error reading file: %s.", filename)
        return None

    @staticmethod
    def print_exif(img: Image) -> None:
        """Print EXIF data from an image."""
        exif = img.getexif()

        logger.debug(">>>>>>>>>>>>>>>>>> EXIF Base tags <<<<<<<<<<<<<<<<<<<<")
        for k, v in exif.items():
            tag = TAGS.get(k, k)
            logger.debug("%s: %s", tag, v)

        for ifd_id in IFD:
            logger.debug(">>>>>>>>> %s <<<<<<<<<<", ifd_id.name)
            try:
                ifd = exif.get_ifd(ifd_id)

                resolve = GPSTAGS if ifd_id == IFD.GPSInfo else TAGS

                for k, v in ifd.items():
                    tag = resolve.get(k, k)
                    logger.debug("%s: %s", tag, v)
            except KeyError:
                pass

    async def synchronize_files(self) -> None:
        """Read all files from disk and synchronize them with the database."""
        # First, let's read all files currently on disk and ensure they are present in the DB/
        image_list = self.get_imagelist_on_disk()

        processed_images = []

        for image_path in image_list:
            image = str(image_path)
            image_exists = self.check_if_local_image_exists_in_db(image)
            if image_exists:
                processed_images.append(image_exists)
                continue

            pil_image = Image.open(image)
            width, height = self.get_image_dimensions(pil_image)
            aspect_ratio = framegallery.aspect_ratio.get_aspect_ratio(width, height)
            self.print_exif(pil_image)
            # Create thumbnail image for display in browser
            thumbnail_path = self.resize_image(pil_image, image)

            img = models.Image(
                filepath=image,
                filename=Path(image).name,
                filetype=self.get_file_type(image),
                width=width,
                height=height,
                aspect_width=aspect_ratio[0],
                aspect_height=aspect_ratio[1],
                thumbnail_path=thumbnail_path,
            )
            self._db.add(img)
            self._db.commit()
            processed_images.append(img)
            logger.debug("Added image %s to the database", img.id)

        logger.debug("Processed %d images", len(processed_images))

        # Delete all Images that have not been processed
        delete_count = crud.delete_images_not_in_processed_items_list(self._db, [i.filepath for i in processed_images])
        logger.debug("Deleted %d images from the database", delete_count)

    @staticmethod
    def resize_image(pil_image: Image, image_path: str) -> str:
        """Resize an image to a thumbnail and save it to disk. Return the thumbnail path."""
        thumbnail_path = image_path.replace(".jpg", ".thumbnail.jpg")
        if Path(thumbnail_path).exists():
            logger.debug("Thumbnail already exists for %s", image_path)
            return thumbnail_path

        thumbnail = pil_image.copy()
        thumbnail.thumbnail((200, 200))
        thumbnail.save(thumbnail_path)

        return thumbnail_path

    async def main(self) -> None:
        """Start the importer."""
        await self.synchronize_files()


if __name__ == "__main__":
    try:
        # Database migrations are now handled centrally in main.py
        db = database.SessionLocal()

        importer = Importer(settings.gallery_path, db)
        logger.info("Starting importer")
        asyncio.run(importer.main())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(1)
