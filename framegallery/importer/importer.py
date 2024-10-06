import asyncio
import logging
import os
from typing import Optional

from samsungtvws.async_art import SamsungTVAsyncArt
from sqlalchemy.orm import Session
from framegallery import crud, database, models

def get_imagelist_on_disk(image_folder: str):
    files = [os.path.join(root, f) for root, dirs, files in os.walk(image_folder) for f in files if f.endswith('.jpg') or f.endswith('.png')]

    # Remove image_folder from the paths.
    files = [f.replace(image_folder + '/', './') for f in files]

    return files

def check_if_local_image_exists_in_db(image_path: str, db: Session) -> Optional[models.ArtItem]:
    return crud.get_image_by_path(db, image_path=image_path)


async def upload_new_image_to_tv(db: Session, tv: SamsungTVAsyncArt, image_path: str):
    full_path = "../images/" + image_path
    logging.info('Uploading new image: ' + str(full_path))

    # Check that file really exists
    if not os.path.isfile(full_path):
        logging.error('File does not exist: ' + str(full_path))
        return

    file_data, file_type = read_file(full_path)

    logging.info('Going to upload {} with file_type {}'.format(full_path, file_type))
    content_id = await tv.upload(file_data, file_type=file_type)
    logging.info('Received content_id: {}'.format(content_id))

    content_id_without_extension = os.path.splitext(content_id)[0]    #remove file extension if any (eg .jpg)
    logging.info('uploaded {} to tv as {}'.format(full_path, content_id_without_extension))

    # Now the upload has complete, we can add the image to the database
    art_item = models.ArtItem(content_id=content_id_without_extension, local_filename=image_path)
    crud.persist_art_item(db, art_item)
    logging.info('Persisted {} to database'.format(content_id_without_extension))

'''
read image file, return file binary data and file type
'''
def read_file(filename: str):
    try:
        with open(filename, 'rb') as f:
            file_data = f.read()
        file_type = get_file_type(filename)
        return file_data, file_type
    except Exception as e:
        logging.error('Error reading file: {}, {}'.format(filename, e))
    return None, None

'''
Try to figure out what kind of image file is, starting with the extension
'''
def get_file_type(filename):
    try:
        file_type = os.path.splitext(filename)[1][1:].lower()
        file_type = file_type.lower() if file_type else None
        return file_type
    except Exception as e:
        logging.error('Error reading file: {}, {}'.format(filename, e))
    return None

async def synchronize_files(tv: SamsungTVAsyncArt, db: Session):
    image_folder = '../images'
    image_list = get_imagelist_on_disk(image_folder)

    for image in image_list:
        image_exists = check_if_local_image_exists_in_db(image, db)
        if image_exists:
            continue

        # Image does not exist yet, so let's upload it
        await upload_new_image_to_tv(db=db, tv=tv, image_path=image)

async def main():
    models.Base.metadata.create_all(bind=database.engine)
    db = database.SessionLocal()
    tv = SamsungTVAsyncArt(host="192.168.2.76", port=8002, timeout=60)
    await tv.start_listening()
    await synchronize_files(tv, db)


if __name__ == '__main__':
    try:
        logging.basicConfig(level=logging.DEBUG)  # or logging.DEBUG to see messages
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        exit(1)