import asyncio
import logging
import os
from typing import Optional, Tuple


from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS, IFD
from pillow_heif import register_heif_opener  # HEIF support

from sqlalchemy.orm import Session

import framegallery.aspect_ratio
import framegallery.crud as crud
import framegallery.database as database
import framegallery.models as models
from framegallery.config import settings

register_heif_opener()  # HEIF support

"""
Imports all images from the gallery folder to the SQLite database.
Generates thumbnails on the fly for display in the UI.
Calculates aspect ratio of the image.
"""
class Importer:
    def __init__(self, image_path: str, db: Session):
        self.image_path = image_path
        self._db = db

    def get_imagelist_on_disk(self):
        files = sorted([os.path.join(root, f) for root, dirs, files in os.walk(self.image_path) for f in files if (f.endswith('.jpg') or f.endswith('.png')) and not f.endswith('.thumbnail.jpg')])

        logging.info('Found {} images in folder {}'.format(len(files), self.image_path))

        return files

    def check_if_local_image_exists_in_db(self, image_path: str) -> Optional[models.ArtItem]:
        return crud.get_image_by_path(self._db, filepath=image_path)

    """
    Get image dimensions using PIL
    """
    @staticmethod
    def get_image_dimensions(img: Image) -> Tuple[int, int]:
        try:
            width, height = img.size
            return width, height
        except Exception as e:
            logging.error('Error reading image dimensions: {}'.format(e))



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
    def get_file_type(filename: str):
        try:
            file_type = os.path.splitext(filename)[1][1:].lower()
            file_type = file_type.lower() if file_type else None
            return file_type
        except Exception as e:
            logging.error('Error reading file: {}, {}'.format(filename, e))
        return None

    @staticmethod
    def print_exif(img: Image):
        exif = img.getexif()

        print('>>>>>>>>>>>>>>>>>>', 'Base tags', '<<<<<<<<<<<<<<<<<<<<')
        for k, v in exif.items():
            tag = TAGS.get(k, k)
            print(tag, v)

        for ifd_id in IFD:
            print('>>>>>>>>>', ifd_id.name, '<<<<<<<<<<')
            try:
                ifd = exif.get_ifd(ifd_id)

                if ifd_id == IFD.GPSInfo:
                    resolve = GPSTAGS
                else:
                    resolve = TAGS

                for k, v in ifd.items():
                    tag = resolve.get(k, k)
                    print(tag, v)
            except KeyError:
                pass

    async def synchronize_files(self):
        # First, let's read all files currently on disk and ensure they are present in the DB/
        image_list = self.get_imagelist_on_disk()

        processed_images = []

        for image in image_list:
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
                filename=os.path.basename(image),
                filetype=self.get_file_type(image),
                width=width,
                height=height,
                aspect_width=aspect_ratio[0],
                aspect_height=aspect_ratio[1],
                thumbnail_path=thumbnail_path
            )
            self._db.add(img)
            self._db.commit()
            processed_images.append(img)
            logging.info('Added image {} to the database'.format(img.id))

        logging.info('Processed {} images'.format(len(processed_images)))

        # Delete all Images that have not been processed
        delete_count = crud.delete_images_not_in_processed_items_list(self._db, [i.filepath for i in processed_images])
        logging.info('Deleted {} images from the database'.format(delete_count))


    @staticmethod
    def resize_image(pil_image: Image, image_path: str) -> str:
        thumbnail = pil_image.copy()
        thumbnail.thumbnail((200, 200))
        thumbnail_path = image_path.replace('.jpg', '.thumbnail.jpg')
        thumbnail.save(thumbnail_path)

        return thumbnail_path


    async def main(self):
        await self.synchronize_files()


if __name__ == '__main__':
    try:
        models.Base.metadata.create_all(bind=database.engine)
        db = database.SessionLocal()

        importer = Importer(settings.gallery_path, db)
        logging.basicConfig(level=logging.INFO)  # or logging.DEBUG to see messages
        asyncio.run(importer.main())
    except (KeyboardInterrupt, SystemExit):
        exit(1)