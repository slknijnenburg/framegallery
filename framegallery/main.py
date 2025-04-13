import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from framegallery import crud, models, schemas
from framegallery.config import settings
from framegallery.configuration.update_current_active_image_config_listener import (
    UpdateCurrentActiveImageConfigListener,
)
from framegallery.database import engine, get_db
from framegallery.dependencies import get_config_repository, get_slideshow_instance
from framegallery.frame_connector.frame_connector import FrameConnector, api_version
from framegallery.frame_connector.status import SlideshowStatus, Status
from framegallery.importer2.importer import Importer
from framegallery.repository.config_repository import ConfigKey, ConfigRepository
from framegallery.repository.image_repository import ImageRepository
from framegallery.routers import config_router, filters_router
from framegallery.schemas import ConfigResponse, Image
from framegallery.slideshow.slideshow import Slideshow

models.Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.getLevelName(settings.log_level))

# Create Frame TV Connector
frame_connector = FrameConnector(settings.tv_ip_address, settings.tv_port)

background_tasks = set()

# Background task to run the filesystem sync
async def run_importer_periodically(db: Session) -> None:
    """Run the importer periodically to synchronize the filesystem with the database."""
    importer = Importer(settings.gallery_path, db)
    while True:
        logging.debug("Running importer")
        await importer.synchronize_files()
        await asyncio.sleep(settings.filesystem_refresh_interval)


async def update_slideshow_periodically(slideshow: Slideshow) -> None:
    """Update the slideshow periodically."""
    while True:
        logging.debug("Updating slideshow")
        await slideshow.update_slideshow()
        await asyncio.sleep(settings.slideshow_interval)


@asynccontextmanager
async def lifespan() -> AsyncGenerator[None, any]:
    """Run tasks on startup and shutdown."""
    await frame_connector.get_active_item_details()

    # Create a database session and run the importer periodically
    db = next(get_db())
    image_importer = asyncio.create_task(run_importer_periodically(db))
    background_tasks.add(image_importer)
    image_importer.add_done_callback(background_tasks.discard)

    image_repository = ImageRepository(db)
    slideshow = get_slideshow_instance(image_repository)
    slideshow_updater = asyncio.create_task(update_slideshow_periodically(slideshow))
    background_tasks.add(slideshow_updater)
    slideshow_updater.add_done_callback(background_tasks.discard)

    config_repository = ConfigRepository(db)
    UpdateCurrentActiveImageConfigListener(config_repository)

    yield


app = FastAPI()

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
# Uncomment this when running from npm dev: templates = Jinja2Templates(directory="./ui/templates")

# Mounts the `static` folder within the `build` folder to the `/static` route.
app.mount("/static", StaticFiles(directory="./ui/build/static"), "static")
app.mount("/images", StaticFiles(directory=settings.gallery_path), "images")


@app.get("/api/status")
async def status() -> Status:
    """Return the application state. Stubbed for now."""
    return Status(
        tv_on=True,
        art_mode_supported=True,
        art_mode_active=True,
        api_version=api_version,
    )


@app.get("/api/available-images", response_model=list[schemas.Image])
async def available_images(db: Annotated[Session,  Depends(get_db)]) -> list[models.Image]:
    """Get a list of all available images."""
    images = crud.get_images(db)

    for image in images:
        image.thumbnail_path = image.thumbnail_path.replace(
            settings.gallery_path, "/images"
        )

    return images


"""
Retrieves a list of (nested) folders in the gallery path, that can be used for filtering in the UI.
"""
@app.get("/api/albums")
async def get_albums() -> dict:
    """Get a directory tree of gallery albums."""
    def build_tree(path: str) -> dict:
        """Build a directory tree of gallery albums."""
        tree = {"id": "/", "name": "/", "label": "/", "children": []}
        for root, dirs, _ in os.walk(path):
            folder = root.replace(path, "").strip(os.sep)
            subtree = tree["children"]
            if folder:
                for part in Path(folder).parts:
                    found = next((item for item in subtree if item["id"] == part), None)
                    if not found:
                        found = {
                            "id": part,
                            "name": part,
                            "label": part,
                            "children": [],
                        }
                        subtree.append(found)
                    subtree = found["children"]
            for directory in dirs:
                subtree.append(
                    {
                        "id": directory,
                        "name": directory,
                        "label": directory,
                        "children": [],
                    }
                )

        return tree

    return build_tree(settings.gallery_path)

@app.post("/api/active-art/{image_id}")
async def select_art(image_id: int, db: Annotated[Session, Depends(get_db)],
                     slideshow: Annotated[Slideshow, Depends(get_slideshow_instance)]) -> Image:
    """Set the active item."""
    image = crud.get_image_by_id(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail=f"Image with ID {image_id} not found")

    await slideshow.set_slideshow_active_image(image)

    return image


@app.get("/api/slideshow")
async def get_slideshow_status(db: Annotated[Session,  Depends(get_db)]) -> SlideshowStatus:
    """Get the current slideshow status."""
    config_repo = ConfigRepository(db)
    slideshow_status = config_repo.get_or(ConfigKey.SLIDESHOW_ENABLED, default_value=True)
    return SlideshowStatus(
        enabled=slideshow_status.value == "true", interval=settings.slideshow_interval
    )


@app.post("/api/slideshow/enable")
async def enable_slideshow(db: Annotated[Session,  Depends(get_db)]) -> dict:
    """Enable the slideshow."""
    config_repo = ConfigRepository(db)
    config_repo.set(ConfigKey.SLIDESHOW_ENABLED, value=True)

    return {}


@app.post("/api/slideshow/disable")
async def disable_slideshow(db: Annotated[Session,  Depends(get_db)]) -> dict:
    """Disable the slideshow."""
    config_repo = ConfigRepository(db)
    config_repo.set(ConfigKey.SLIDESHOW_ENABLED, value=False)

    return {}


@app.get("/api/settings")
async def get_settings(db: Annotated[Session, Depends(get_db)]) -> ConfigResponse:
    """Get the current settings."""
    config_repo = ConfigRepository(db)
    active_image_id = config_repo.get_or(ConfigKey.CURRENT_ACTIVE_IMAGE, default_value=None).value
    active_image = crud.get_image_by_id(db, int(active_image_id))
    config = {
        "slideshow_enabled": config_repo.get_or(ConfigKey.SLIDESHOW_ENABLED, default_value=True).value,
        "slideshow_interval": settings.slideshow_interval,
        "current_active_image": Image.model_validate(active_image),
        "current_active_image_since":
            config_repo.get_or(ConfigKey.CURRENT_ACTIVE_IMAGE_SINCE, default_value=None).value,
    }

    return ConfigResponse(**config)


@app.post("/api/images/next")
async def next_image(slideshow: Annotated[Slideshow, Depends(get_slideshow_instance)]) -> Image:
    """Advance to the next image in the slideshow."""
    new_image = await slideshow.update_slideshow()
    return new_image


# Include routers for modular API endpoints
app.include_router(filters_router)
app.include_router(config_router)

# Defines a route handler for `/*` essentially.
# NOTE: this needs to be the last route defined b/c it's a catch all route
@app.get("/{rest_of_path:path}", response_model=None)
async def react_app(req: Request,
                    config_repo: Annotated[ConfigRepository, Depends(get_config_repository)]
                    ) -> templates.TemplateResponse:
    """Render the React app."""
    config = {
        "slideshow_enabled": config_repo.get_or(
            ConfigKey.SLIDESHOW_ENABLED, default_value=True
        ).value,
        "slideshow_interval": settings.slideshow_interval,
        "current_active_image": config_repo.get_or(
            ConfigKey.CURRENT_ACTIVE_IMAGE, default_value=None
        ).value,
        "current_active_image_since": config_repo.get_or(
            ConfigKey.CURRENT_ACTIVE_IMAGE_SINCE, default_value=None
        ).value,
    }

    return templates.TemplateResponse("index.html", {"request": req, "config": config})
