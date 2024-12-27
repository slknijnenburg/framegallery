import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import framegallery.crud as crud
import framegallery.models as models
from framegallery.repository.image_repository import ImageRepository
from framegallery.repository.config_repository import ConfigRepository
from framegallery.frame_connector.frame_connector import FrameConnector
from framegallery.config import settings
from framegallery.database import engine, get_db
from framegallery.frame_connector.status import SlideshowStatus, Status
from framegallery.frame_connector.frame_connector import api_version
from framegallery.importer2.importer import Importer
from framegallery.slideshow.slideshow import Slideshow, get_slideshow

models.Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.getLevelName(settings.log_level))

# Create Frame TV Connector
frame_connector = FrameConnector(settings.tv_ip_address, settings.tv_port)

# Background task to run the filesystem sync
async def run_importer_periodically(db: Session):
    importer = Importer(settings.gallery_path, db)
    while True:
        logging.debug("Running importer")
        await importer.synchronize_files()
        await asyncio.sleep(settings.filesystem_refresh_interval)

async def update_slideshow_periodically(slideshow: Slideshow):
    while True:
        logging.debug("Updating slideshow")
        await slideshow.update_slideshow()
        await asyncio.sleep(settings.slideshow_interval)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await frame_connector.get_active_item_details()

    # Create a database session and run the importer periodically
    db = next(get_db())
    asyncio.create_task(run_importer_periodically(db))

    image_repository = ImageRepository(db)
    slideshow = next(get_slideshow(image_repository))
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
# templates = Jinja2Templates(directory="./ui/templates")

# Mounts the `static` folder within the `build` folder to the `/static` route.
app.mount('/static', StaticFiles(directory="./ui/build/static"), 'static')
app.mount('/images', StaticFiles(directory=settings.gallery_path), 'images')

@app.get("/api/status")
async def status(request: Request) -> Status:
    # Stub the response for now
    return Status(tv_on=True, art_mode_supported=True, art_mode_active=True, api_version=api_version)


@app.get("/api/available-images")
async def available_images(request: Request, db: Session = Depends(get_db)):
    images = crud.get_images(db)

    for image in images:
        image.thumbnail_path = image.thumbnail_path.replace(settings.gallery_path, '/images')

    return images


"""
Retrieves a list of (nested) folders in the gallery path, that can be used for filtering in the UI.
"""
@app.get("/api/albums")
async def get_albums(request: Request):
    def build_tree(path: str) -> Dict:
        tree = {"id": "/", "name": "/", "label": "/", "children": []}
        for root, dirs, _ in os.walk(path):
            folder = root.replace(path, '').strip(os.sep)
            subtree = tree["children"]
            if folder:
                for part in folder.split(os.sep):
                    found = next((item for item in subtree if item["id"] == part), None)
                    if not found:
                        found = {"id": part, "name": part, "label": part, "children": []}
                        subtree.append(found)
                    subtree = found["children"]
            for directory in dirs:
                subtree.append({"id": directory, "name": directory, "label": directory, "children": []})

        return tree

    return build_tree(settings.gallery_path)


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


@app.get("/api/slideshow")
async def get_slideshow_status(request: Request, db: Session = Depends(get_db)) -> SlideshowStatus:
    config_repo = ConfigRepository(db)
    slideshow_status = config_repo.get_or("slideshow_enabled", True)
    return SlideshowStatus(enabled=slideshow_status.value=="true", interval=settings.slideshow_interval)

@app.post("/api/slideshow/enable")
async def enable_slideshow(request: Request, db: Session = Depends(get_db)):
    config_repo = ConfigRepository(db)
    config_repo.set("slideshow_enabled", True)

    return {}


@app.post("/api/slideshow/disable")
async def enable_slideshow(request: Request, db: Session = Depends(get_db)):
    config_repo = ConfigRepository(db)
    config_repo.set("slideshow_enabled", False)

    return {}


# Defines a route handler for `/*` essentially.
# NOTE: this needs to be the last route defined b/c it's a catch all route
@app.get("/{rest_of_path:path}")
async def react_app(req: Request, rest_of_path: str, db: Session = Depends(get_db)):
    config_repo = ConfigRepository(db)
    config = {
        "slideshow_enabled": config_repo.get_or("slideshow_enabled", True).value,
    }

    return templates.TemplateResponse('index.html', {'request': req, 'config': config})
