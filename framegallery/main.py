import asyncio
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sse_starlette import EventSourceResponse, ServerSentEvent
import json

from framegallery import crud, models, schemas
from framegallery.config import settings
from framegallery.configuration.update_current_active_image_config_listener import (
    UpdateCurrentActiveImageConfigListener,
)
from framegallery.database import engine, get_db
from framegallery.dependencies import get_config_repository, get_filter_repository, get_slideshow_instance
from framegallery.frame_connector.frame_connector import FrameConnector, api_version
from framegallery.frame_connector.status import SlideshowStatus, Status
from framegallery.importer2.importer import Importer
from framegallery.logging_config import setup_logging
from framegallery.repository.config_repository import ConfigKey, ConfigRepository
from framegallery.repository.filter_repository import FilterRepository
from framegallery.repository.image_repository import ImageRepository
from framegallery.routers import config_router, filters_router
from framegallery.routers.images import router as images_router
from framegallery.schemas import ConfigResponse, Filter, Image
from framegallery.slideshow.slideshow import Slideshow
from framegallery.sse.slideshow_signal_listener import SlideshowSignalSSEListener

logger = setup_logging(log_level=settings.log_level)

models.Base.metadata.create_all(bind=engine)

background_tasks = set()

# Background task to run the filesystem sync
async def run_importer_periodically(db: Session) -> None:
    """Run the importer periodically to synchronize the filesystem with the database."""
    logger.info("Inside run_importer_periodically")

    importer = Importer(settings.gallery_path, db)
    while True:
        logger.info("Running importer now")
        await importer.synchronize_files()
        await asyncio.sleep(settings.filesystem_refresh_interval)


async def update_slideshow_periodically(slideshow: Slideshow) -> None:
    """Update the slideshow periodically."""
    while True:
        logger.debug("Updating slideshow")
        await slideshow.update_slideshow()
        await asyncio.sleep(settings.slideshow_interval)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    """Run tasks on startup and shutdown."""
    logger.info("logger - Inside lifespan")

    # Initialize FrameConnector within lifespan
    frame_connector = FrameConnector(settings.tv_ip_address, settings.tv_port)
    app.state.frame_connector = frame_connector # Store in app state

    # Call startup logic for the connector
    await frame_connector.get_active_item_details()

    # Create a database session and run the importer periodically
    db = next(get_db())
    logger.info("Scheduling the filesystem importer task")
    image_importer = asyncio.create_task(run_importer_periodically(db))
    background_tasks.add(image_importer)
    image_importer.add_done_callback(background_tasks.discard)

    image_repository = ImageRepository(db)
    config_repository = ConfigRepository(db)
    filter_repository = FilterRepository(db)
    slideshow = get_slideshow_instance(image_repository, config_repository, filter_repository)
    logger.info("Scheduling the slideshow updater")
    slideshow_updater = asyncio.create_task(update_slideshow_periodically(slideshow))
    background_tasks.add(slideshow_updater)
    slideshow_updater.add_done_callback(background_tasks.discard)

    # Create an event queue for slideshow updates
    slideshow_event_queue = asyncio.Queue()
    app.state.slideshow_event_queue = slideshow_event_queue

    config_repository = ConfigRepository(db)
    # Store the listener in the app state so that it doesn't get garbage collected
    app.state.update_active_image_in_config_listener = UpdateCurrentActiveImageConfigListener(
        config_repository
    )

    # Instantiate and store the new SSE signal listener
    app.state.slideshow_signal_sse_listener = SlideshowSignalSSEListener(slideshow_event_queue)

    yield


logger.info("logger - Before FastAPI launch")
logger.info("logging - Before FastAPI launch")
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
    config_repo.set(ConfigKey.SLIDESHOW_ENABLED, "false")
    return {}


@app.get("/api/slideshow/events")
async def slideshow_events(request: Request) -> EventSourceResponse:
    """SSE endpoint for slideshow updates."""
    queue: asyncio.Queue = request.app.state.slideshow_event_queue

    async def event_generator() -> AsyncGenerator[ServerSentEvent, None]:
        try:
            while True:
                # Wait for an event from the queue
                event_data = await queue.get()
                logger.debug("SSE: Sending event: %s", event_data)
                yield ServerSentEvent(data=json.dumps(event_data), event=event_data.get("event", "message"))
                queue.task_done()
        except asyncio.CancelledError:
            # Handle client disconnection
            logger.info("SSE: Client disconnected")
            # It's important to reraise CancelledError or ensure the generator stops
            raise
        except Exception as e:
            # Log other potential errors from the queue or SSE generation
            logger.error("SSE: Error in event generator: %s", e, exc_info=True)
            # Depending on the error, you might want to raise or just stop generation
            raise # Reraising to ensure the connection closes on unexpected errors

    return EventSourceResponse(event_generator())


@app.get("/api/settings")
async def get_settings(
    db: Annotated[Session, Depends(get_db)],
    filter_repository: Annotated[FilterRepository, Depends(get_filter_repository)]
    ) -> ConfigResponse:
    """Get the current settings."""
    config_repo = ConfigRepository(db)
    active_image_id = config_repo.get_or(ConfigKey.CURRENT_ACTIVE_IMAGE, default_value=None).value
    active_image = crud.get_image_by_id(db, int(active_image_id))
    if active_image:
        active_image = Image.model_validate(active_image)

    active_filter = None
    active_filter_id = config_repo.get_or(
            ConfigKey.ACTIVE_FILTER, default_value=None
        ).value
    if active_filter_id is not None:
        active_filter = filter_repository.get_filter(int(active_filter_id))
    if active_filter:
        active_filter = Filter.model_validate(active_filter)

    config = {
        "slideshow_enabled": config_repo.get_or(ConfigKey.SLIDESHOW_ENABLED, default_value=True).value,
        "slideshow_interval": settings.slideshow_interval,
        "current_active_image": active_image,
        "current_active_image_since":
            config_repo.get_or(ConfigKey.CURRENT_ACTIVE_IMAGE_SINCE, default_value=None).value,
        "active_filter": active_filter
    }

    return ConfigResponse(**config)


@app.post("/api/images/next")
async def next_image(slideshow: Annotated[Slideshow, Depends(get_slideshow_instance)]) -> Image:
    """Advance to the next image in the slideshow."""
    return await slideshow.update_slideshow()


# Include routers for modular API endpoints
app.include_router(filters_router)
app.include_router(config_router)
app.include_router(images_router)

# Defines a route handler for `/*` essentially.
# NOTE: this needs to be the last route defined b/c it's a catch all route
@app.get("/{rest_of_path:path}", response_model=None)
async def react_app(req: Request,
                    config_repo: Annotated[ConfigRepository, Depends(get_config_repository)],
                    filter_repository: Annotated[FilterRepository, Depends(get_filter_repository)]
                    ) -> templates.TemplateResponse:
    """Render the React app."""
    active_filter_id = config_repo.get_or(
            ConfigKey.ACTIVE_FILTER, default_value=None
        ).value
    active_filter = filter_repository.get_filter(int(active_filter_id))

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
        "active_filter": active_filter
    }

    return templates.TemplateResponse("index.html", {"request": req, "config": config})
