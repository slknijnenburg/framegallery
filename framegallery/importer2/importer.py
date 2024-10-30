import asyncio
import logging
import os
from typing import Optional, Tuple

from PIL import Image
from sqlalchemy.orm import Session

import framegallery.aspect_ratio
import framegallery.crud as crud
import framegallery.database as database
import framegallery.models as models
from framegallery.config import settings


class Importer:
    def __init__(self, image_path: str):
        # Validate that image_path is a full path
        if not os.path.isabs(image_path):
            raise ValueError('image_path must be an absolute path')

        self.image_path = image_path

    def get_imagelist_on_disk(self):
        files = sorted([os.path.join(root, f) for root, dirs, files in os.walk(self.image_path) for f in files if f.endswith('.jpg') or f.endswith('.png')])

        # Remove image_folder from the paths.
        # files = [f.replace(self.image_path + '/', './') for f in files]

        logging.info('Found {} images in folder {}'.format(len(files), self.image_path))
        logging.info('Images: {}'.format(files))

        return files

    def check_if_local_image_exists_in_db(self, image_path: str, db: Session) -> Optional[models.ArtItem]:
        return crud.get_image_by_path(db, filepath=image_path)

    """
    Get image dimensions using PIL
    """
    def get_image_dimensions(self, image_path: str) -> Tuple[int, int]:
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                return width, height
        except Exception as e:
            logging.error('Error reading image dimensions: {}, {}'.format(image_path, e))



    """
    read image file, return file binary data and file type
    """
    def read_file(self, filename: str):
        try:
            with open(filename, 'rb') as f:
                file_data = f.read()
            file_type = self.get_file_type(filename)
            return file_data, file_type
        except Exception as e:
            logging.error('Error reading file: {}, {}'.format(filename, e))
        return None, None

    '''
    Try to figure out what kind of image file is, starting with the extension
    '''
    @staticmethod
    def get_file_type(filename):
        try:
            file_type = os.path.splitext(filename)[1][1:].lower()
            file_type = file_type.lower() if file_type else None
            return file_type
        except Exception as e:
            logging.error('Error reading file: {}, {}'.format(filename, e))
        return None


    async def synchronize_files(self, db: Session):
        # First, let's read all files currently on disk and ensure they are present in the DB/
        image_list = self.get_imagelist_on_disk()

        processed_images = []

        for image in image_list:
            image_exists = self.check_if_local_image_exists_in_db(image, db)
            if image_exists:
                logging.info('Image {} already exists in the database'.format(image))
                processed_images.append(image_exists)
                continue

            width, height = self.get_image_dimensions(image)
            aspect_ratio = framegallery.aspect_ratio.get_aspect_ratio(width, height)
            img = models.Image(
                filepath=image,
                filename=os.path.basename(image),
                filetype=self.get_file_type(image),
                width=width,
                height=height,
                aspect_width=aspect_ratio[0],
                aspect_height=aspect_ratio[1]
            )
            db.add(img)
            db.commit()
            processed_images.append(img)
            logging.info('Added image {} to the database'.format(img.id))

        logging.info('Processed {} images'.format(len(processed_images)))

        # Delete all Images that have not been processed
        delete_count = crud.delete_images_not_in_processed_items_list(db, [i.filepath for i in processed_images])
        logging.info('Deleted {} images from the database'.format(delete_count))


    async def main(self):
        models.Base.metadata.create_all(bind=database.engine)
        db = database.SessionLocal()
        await self.synchronize_files(db)


if __name__ == '__main__':
    try:
        importer = Importer(settings.gallery_path)
        logging.basicConfig(level=logging.INFO)  # or logging.DEBUG to see messages
        asyncio.run(importer.main())
    except (KeyboardInterrupt, SystemExit):
        exit(1)