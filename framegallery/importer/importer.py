import asyncio
import base64
import logging
import os
from typing import Optional

from samsungtvws.async_art import SamsungTVAsyncArt
from sqlalchemy.orm import Session

import framegallery.crud as crud
import framegallery.models as models
import framegallery.database as database

api_version = "4.3.4.0"

def get_imagelist_on_disk(image_folder: str):
    files = sorted([os.path.join(root, f) for root, dirs, files in os.walk(image_folder) for f in files if f.endswith('.jpg') or f.endswith('.png')])

    # Remove image_folder from the paths.
    files = [f.replace(image_folder + '/', './') for f in files]

    logging.info('Found {} images in folder {}'.format(len(files), image_folder))
    logging.info('Images: {}'.format(files))

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
    data = await tv.upload(file_data, file_type=file_type, timeout=60)
    content_id = data['content_id']
    logging.info('Received content_id: {}'.format(content_id))

    content_id_without_extension = os.path.splitext(content_id)[0]    #remove file extension if any (eg .jpg)
    logging.info('uploaded {} to tv as {}'.format(full_path, content_id_without_extension))

    # Now the upload has complete, we can add the image to the database
    art_item = models.ArtItem(
        content_id=content_id_without_extension,
        local_filename=image_path,
        matte_id=data['matte_id'],
        portrait_matte_id=data['portrait_matte_id'],
        width=data['width'],
        height=data['height'],
    )
    crud.persist_art_item(db, art_item)
    logging.info('Persisted {} to database'.format(content_id_without_extension))

    ## Add thumbnail for this new item
    try:
        thumb = b''
        if int(api_version.replace('.', '')) < 4000:  # check api version number, and use correct api call
            thumbs = await tv.get_thumbnail(art_item.content_id,
                                            True)  # old api, gets thumbs in same format as new api
        else:
            thumbs = await tv.get_thumbnail_list(art_item.content_id)  # list of content_id's or single content_id
        if thumbs:  # dictionary of content_id (with file type extension) and binary data, e.g. "{'MY_F0003.jpg': b'...'}"
            thumb = list(thumbs.values())[0]
            content_id = list(thumbs.keys())[0]
            art_item.thumbnail_data = base64.b64encode(thumb)
            art_item.thumbnail_filename = content_id
            art_item.thumbnail_filetype = os.path.splitext(content_id)[1][1:]

            db.flush([art_item])
            db.commit()
        logging.info('got thumbnail for {} binary data length: {}'.format(art_item.content_id, len(thumb)))
    except asyncio.exceptions.IncompleteReadError as e:
        logging.error('FAILED to get thumbnail for {}: {}'.format(art_item.content_id, e))

"""
read image file, return file binary data and file type
"""
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