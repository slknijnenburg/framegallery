import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import framegallery.crud as crud
import framegallery.models as models
import framegallery.schemas as schemas
from framegallery.config import settings
from framegallery.database import engine, get_db
from framegallery.frame_connector.status import SlideshowStatus, Status
from framegallery.frame_connector.frame_connector import api_version
from framegallery.importer2.importer import Importer
from framegallery.slideshow.slideshow import Slideshow, get_slideshow

models.Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.DEBUG)  # or logging.DEBUG to see messages


current_active_art: Optional[schemas.ActiveArt] = None

# Background task to run the filesystem sync
async def run_importer_periodically(db: Session):
    importer = Importer(settings.gallery_path, db)
    while True:
        logging.info("Running importer")
        await importer.synchronize_files()
        await asyncio.sleep(settings.filesystem_refresh_interval)

async def update_slideshow_periodically(slideshow: Slideshow):
    while True:
        logging.info("Updating slideshow")
        await slideshow.update_slideshow()
        await asyncio.sleep(120)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create a database session and run the importer periodically
    db = next(get_db())
    asyncio.create_task(run_importer_periodically(db))

    slideshow = next(get_slideshow(db))
    asyncio.create_task(update_slideshow_periodically(slideshow))

    yield

app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:3000",  # React dev server
    "http://127.0.0.1:3000",  # React dev server
    "http://localhost:7999",  # ASGI server
    "http://127.0.0.1:7999",  # ASGI server
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Sets the templates directory to the `build` folder from `npm run build`
# this is where you'll find the index.html file.
templates = Jinja2Templates(directory="./ui/build")

# Mounts the `static` folder within the `build` folder to the `/static` route.
app.mount('/static', StaticFiles(directory="./ui/build/static"), 'static')
app.mount('/images', StaticFiles(directory=settings.gallery_path), 'images')

@app.get("/api/status")
async def status(request: Request) -> Status:
    # Stub the response for now
    return Status(tv_on=True, art_mode_supported=True, art_mode_active=True, api_version=api_version)


# @app.patch("/api/available-art/{content_id}")
# async def update_art_item(request: Request, content_id: str, art_item_update: schemas.ArtItemUpdate, db: Session = Depends(get_db)) -> schemas.ArtItem:
#     stored_art_item = crud.get_art_item(db, content_id)
#     if not stored_art_item:
#         raise HTTPException(status_code=404, detail=f"Art item {content_id} not found")
#
#     input_art_item = art_item_update.model_dump(exclude_unset=True)
#     for field, value in input_art_item.items():
#         setattr(stored_art_item, field, value)
#     db.commit()
#
#     # Now we have updated the matte in the local DB, let's update it on the TV as well
#     await tv.change_matte(content_id, stored_art_item.matte_id)
#
#     # In order to reload the image on the screen, we need to re-activate the image.
#     await tv.select_image(content_id, "MY-C0002")
#
#     return stored_art_item

#
# @app.get("/api/active-art")
# async def active_art() -> schemas.ActiveArt:
#     active_art_details_response = await tv.get_current()
#     active_art_details = schemas.ActiveArt(**active_art_details_response)
#
#     current_active_art = active_art_details
#
#     return active_art_details

@app.get("/api/available-images")
async def available_images(request: Request, db: Session = Depends(get_db)):
    images = crud.get_images(db)

    for image in images:
        image.thumbnail_path = image.thumbnail_path.replace(settings.gallery_path, '/images')
    
    return images

# """
# Sets the active item
# """
# @app.post("/api/active-art/{id}")
# async def select_art(request: Request, id: int, db: Session = Depends(get_db), slideshow: Slideshow = Depends(get_slideshow)):
#     image = crud.get_image_by_id(db, id)
#     if not image:
#         raise HTTPException(status_code=404, detail=f"Image with ID {id} not found")
#
#     await slideshow.set_slideshow_active_image(image)
#
#     # Update current_active_art
#     await active_art()
#
#     return image

#
# @app.get("/api/available-art/refresh", status_code=200)
# async def refresh_available_art(request: Request, db: Session = Depends(get_db)):
#     counts = {
#         "items_on_tv": 0,
#         "existed_in_db_already": 0,
#         "deleted_from_db": 0,
#     }
#     processed_items = []
#
#     artlist = await tv.available('MY-C0002')
#     for art in artlist:
#         counts["items_on_tv"] += 1
#         # Check if the art item already exists in the database
#         art_item = crud.get_art_item(db, content_id=art['content_id'])
#         if art_item:
#             processed_items.append(art['content_id'])
#             counts["existed_in_db_already"] += 1
#             continue
#
#         art_item = crud.create_art_item(db, art_item=schemas.ArtItem(**art))
#         art_item_dict = schemas.ArtItem.model_validate(art_item).model_dump_json()
#         logging.info('Art item: {}'.format(art_item_dict))
#
#         ## Add thumbnail for this new item
#         try:
#             thumb = b''
#             if int(api_version.replace('.', '')) < 4000:  # check api version number, and use correct api call
#                 thumbs = await tv.get_thumbnail(art_item.content_id,
#                                                 True)  # old api, gets thumbs in same format as new api
#             else:
#                 thumbs = await tv.get_thumbnail_list(art_item.content_id)  # list of content_id's or single content_id
#             if thumbs:  # dictionary of content_id (with file type extension) and binary data, e.g. "{'MY_F0003.jpg': b'...'}"
#                 thumb = list(thumbs.values())[0]
#                 content_id = list(thumbs.keys())[0]
#                 art_item.thumbnail_data = base64.b64encode(thumb)
#                 art_item.thumbnail_filename = content_id
#                 art_item.thumbnail_filetype = os.path.splitext(content_id)[1][1:]
#
#                 db.flush([art_item])
#                 db.commit()
#                 processed_items.append(art_item.content_id)
#             logging.info('got thumbnail for {} binary data length: {}'.format(art_item.content_id, len(thumb)))
#         except asyncio.exceptions.IncompleteReadError as e:
#             logging.error('FAILED to get thumbnail for {}: {}'.format(art_item.content_id, e))
#
#     counts["deleted_from_db"] = crud.delete_items_not_in_list(db, processed_items)
#
#     return counts

@app.get("/api/slideshow")
async def get_slideshow_status(request: Request) -> SlideshowStatus:
    # response = await tv.get_slideshow_status()

    # slideshow_status = SlideshowStatus(**response)

    # return slideshow_status
    return SlideshowStatus(
        value="off",
        category_id="MY-C0002",
        sub_category_id="",
        type="shuffleslideshow",
        current_content_id="",
        content_list=[]
    )
#
# @app.post("/api/slideshow/enable")
# async def enable_slideshow(request: Request):
#     response = await tv.set_slideshow_status(duration=3)
#
#     return response
#
#
# @app.post("/api/slideshow/disable")
# async def enable_slideshow(request: Request):
#     response = await tv.set_slideshow_status(type="shuffleslideshow", category=2, duration=0)
#
#     return response


# Defines a route handler for `/*` essentially.
# NOTE: this needs to be the last route defined b/c it's a catch all route
@app.get("/{rest_of_path:path}")
async def react_app(req: Request, rest_of_path: str):
    return templates.TemplateResponse('index.html', {'request': req})
