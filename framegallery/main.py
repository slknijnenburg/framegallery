import asyncio
import json
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sse_starlette import EventSourceResponse, ServerSentEvent
from starlette.responses import Response

from framegallery import crud, models, schemas
from framegallery.config import settings
from framegallery.configuration.update_current_active_image_config_listener import (
    UpdateCurrentActiveImageConfigListener,
)
from framegallery.database import get_db
from framegallery.dependencies import get_config_repository, get_filter_repository, get_slideshow_instance
from framegallery.frame_connector.frame_connector import FrameConnector, api_version
from framegallery.frame_connector.status import SlideshowStatus, Status
from framegallery.importer2.importer import Importer
from framegallery.logging_config import setup_logging
from framegallery.migrations import run_migrations
from framegallery.repository.config_repository import ConfigKey, ConfigRepository
from framegallery.repository.filter_repository import FilterRepository
from framegallery.repository.image_repository import ImageRepository
from framegallery.routers import config_router, filters_router
from framegallery.routers.images import router as images_router
from framegallery.schemas import ConfigResponse, Filter, Image
from framegallery.slideshow.slideshow import Slideshow
from framegallery.sse.slideshow_signal_listener import SlideshowSignalSSEListener

logger = setup_logging(log_level=settings.log_level)

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


def _raise_migration_error() -> None:
    """Raise migration error."""
    msg = "Database migrations failed"
    raise RuntimeError(msg)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Run tasks on startup and shutdown."""
    logger.info("logger - Inside lifespan")

    # Run database migrations first
    logger.info("Running database migrations...")
    try:
        migration_success = run_migrations()
        if not migration_success:
            logger.error("Database migrations failed - application startup aborted")
            _raise_migration_error()
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.exception("Critical error during database migration")
        msg = f"Database migration failed: {e}"
        raise RuntimeError(msg) from e

    logger.info("Proceeding with application initialization after migrations...")

    # Initialize FrameConnector within lifespan
    frame_connector = FrameConnector(settings.tv_ip_address, settings.tv_port)
    app.state.frame_connector = frame_connector  # Store in app state

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
    app.state.update_active_image_in_config_listener = UpdateCurrentActiveImageConfigListener(config_repository)

    # Instantiate and store the new SSE signal listener
    app.state.slideshow_signal_sse_listener = SlideshowSignalSSEListener(slideshow_event_queue)

    yield


logger.info("logger - Before FastAPI launch")
app = FastAPI(lifespan=lifespan)
logger.info("logging - Before FastAPI launch")

# CORS configuration with security considerations
development_origins = [
    "http://localhost:3000",  # Vite dev server
    "http://127.0.0.1:3000",  # Vite dev server
    "http://localhost:5173",  # Alternative Vite port
    "http://127.0.0.1:5173",  # Alternative Vite port
    "http://localhost:7999",  # Backend server (for development)
    "http://127.0.0.1:7999",  # Backend server (for development)
]


def _get_cors_configuration() -> tuple[list[str], bool]:
    """Get CORS configuration from environment variables."""
    cors_origins_raw = os.getenv("CORS_ORIGINS", ",".join(development_origins))
    cors_origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]
    use_permissive_cors = os.getenv("CORS_ALLOW_ALL", "false").lower() == "true"
    return cors_origins, use_permissive_cors


# Use environment variable to control CORS policy
cors_origins, use_permissive_cors = _get_cors_configuration()

if use_permissive_cors:
    # Permissive CORS for development/testing (less secure)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,  # Must be False with wildcard origins
        allow_methods=["GET", "POST", "OPTIONS"],  # Limit methods
        allow_headers=["Content-Type", "Cache-Control"],  # Limit headers
    )
else:
    # Secure CORS with specific origins (recommended for production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Cache-Control"],
    )


def _validate_cors_origin(origin: str | None) -> str:
    """Validate CORS origin and return appropriate Access-Control-Allow-Origin value."""
    if not origin:
        return "*"

    # Get CORS configuration
    cors_origins, use_permissive_cors = _get_cors_configuration()

    if use_permissive_cors:
        return "*"

    # Check if origin is in allowed list
    if origin in cors_origins:
        return origin

    # For localhost development, be more permissive
    if "localhost" in origin or "127.0.0.1" in origin:
        return origin

    # Default to no access for unknown origins
    return "null"


# Conditionally set up templates directory based on what's available
ui_dist_path = Path("./ui/dist")
ui_dist_assets_path = Path("./ui/dist/assets")
ui_templates_path = Path("./ui/templates")

if ui_dist_path.exists():
    # Production mode - use built frontend
    templates = Jinja2Templates(directory="./ui/dist")
    logger.info("Using production templates from ./ui/dist")
# Development/test mode - fallback to templates directory or create empty
elif ui_templates_path.exists():
    templates = Jinja2Templates(directory="./ui/templates")
    logger.info("Using development templates from ./ui/templates")
else:
    # Create a minimal templates object for tests
    templates = None
    logger.warning("No templates directory found - template rendering disabled")

# Conditionally mount static files only if directories exist
if ui_dist_assets_path.exists():
    app.mount("/assets", StaticFiles(directory="./ui/dist/assets"), "assets")
    logger.info("Mounted /assets from ./ui/dist/assets")
else:
    logger.warning("./ui/dist/assets not found - /assets route not mounted")

# Always try to mount images directory (should exist or be created by the application)
if Path(settings.gallery_path).exists():
    app.mount("/images", StaticFiles(directory=settings.gallery_path), "images")
    logger.info("Mounted /images from %s", settings.gallery_path)
else:
    logger.warning("Gallery path %s not found - /images route not mounted", settings.gallery_path)


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
async def available_images(db: Annotated[Session, Depends(get_db)]) -> list[models.Image]:
    """Get a list of all available images."""
    images = crud.get_images(db)

    for image in images:
        image.thumbnail_path = image.thumbnail_path.replace(settings.gallery_path, "/images")

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
async def select_art(
    image_id: int,
    db: Annotated[Session, Depends(get_db)],
    slideshow: Annotated[Slideshow, Depends(get_slideshow_instance)],
) -> Image:
    """Set the active item."""
    image = crud.get_image_by_id(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail=f"Image with ID {image_id} not found")

    await slideshow.set_slideshow_active_image(image)

    return image


@app.get("/api/slideshow")
async def get_slideshow_status(db: Annotated[Session, Depends(get_db)]) -> SlideshowStatus:
    """Get the current slideshow status."""
    config_repo = ConfigRepository(db)
    slideshow_status = config_repo.get_or(ConfigKey.SLIDESHOW_ENABLED, default_value=True)
    return SlideshowStatus(enabled=slideshow_status.value == "true", interval=settings.slideshow_interval)


@app.post("/api/slideshow/enable")
async def enable_slideshow(db: Annotated[Session, Depends(get_db)]) -> dict:
    """Enable the slideshow."""
    config_repo = ConfigRepository(db)
    config_repo.set(ConfigKey.SLIDESHOW_ENABLED, value=True)

    return {}


@app.post("/api/slideshow/disable")
async def disable_slideshow(db: Annotated[Session, Depends(get_db)]) -> dict:
    """Disable the slideshow."""
    config_repo = ConfigRepository(db)
    config_repo.set(ConfigKey.SLIDESHOW_ENABLED, "false")
    return {}


@app.options("/api/slideshow/events")
async def slideshow_events_options(request: Request) -> JSONResponse:
    """Handle preflight requests for SSE endpoint."""
    # Use same origin validation as main CORS middleware
    origin = request.headers.get("origin")
    allowed_origin = _validate_cors_origin(origin)

    headers = {
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Cache-Control, Content-Type",
        "Access-Control-Max-Age": "86400",  # 24 hours
    }

    # Set origin header based on validation
    if allowed_origin != "null":
        headers["Access-Control-Allow-Origin"] = allowed_origin
        # Only allow credentials if not using wildcard origin
        if allowed_origin != "*":
            headers["Access-Control-Allow-Credentials"] = "true"

    return JSONResponse(content={}, headers=headers)


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
        except Exception:
            # Log other potential errors from the queue or SSE generation
            logger.exception("SSE: Error in event generator")
            # Depending on the error, you might want to raise or just stop generation
            raise  # Reraising to ensure the connection closes on unexpected errors

    # Add explicit CORS headers for Firefox compatibility with origin validation
    origin = request.headers.get("origin")
    allowed_origin = _validate_cors_origin(origin)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Cache-Control",
    }

    # Set origin header based on validation
    if allowed_origin != "null":
        headers["Access-Control-Allow-Origin"] = allowed_origin
        # Only allow credentials if not using wildcard origin
        if allowed_origin != "*":
            headers["Access-Control-Allow-Credentials"] = "true"

    return EventSourceResponse(event_generator(), ping=100, headers=headers)


@app.get("/api/settings")
async def get_settings(
    db: Annotated[Session, Depends(get_db)],
    filter_repository: Annotated[FilterRepository, Depends(get_filter_repository)],
) -> ConfigResponse:
    """Get the current settings."""
    config_repo = ConfigRepository(db)
    active_image_id = config_repo.get_or(ConfigKey.CURRENT_ACTIVE_IMAGE, default_value=None).value
    active_image = crud.get_image_by_id(db, int(active_image_id)) if active_image_id else None
    if active_image:
        active_image = Image.model_validate(active_image)

    active_filter = None
    active_filter_id = config_repo.get_or(ConfigKey.ACTIVE_FILTER, default_value=None).value
    if active_filter_id is not None:
        active_filter = filter_repository.get_filter(int(active_filter_id))
    if active_filter:
        active_filter = Filter.model_validate(active_filter)

    config = {
        "slideshow_enabled": config_repo.get_or(ConfigKey.SLIDESHOW_ENABLED, default_value=True).value,
        "slideshow_interval": settings.slideshow_interval,
        "current_active_image": active_image,
        "current_active_image_since": config_repo.get_or(
            ConfigKey.CURRENT_ACTIVE_IMAGE_SINCE, default_value=None
        ).value,
        "active_filter": active_filter,
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
async def react_app(
    req: Request,
    config_repo: Annotated[ConfigRepository, Depends(get_config_repository)],
    filter_repository: Annotated[FilterRepository, Depends(get_filter_repository)],
) -> Response:
    """Render the React app or return error if templates not available."""
    # If templates are not available, return API-only error
    if templates is None:
        return JSONResponse(status_code=503, content={"error": "Frontend not available - templates not found"})

    active_filter_id = config_repo.get_or(ConfigKey.ACTIVE_FILTER, default_value=None).value
    active_filter = filter_repository.get_filter(int(active_filter_id)) if active_filter_id else None

    config = {
        "slideshow_enabled": config_repo.get_or(ConfigKey.SLIDESHOW_ENABLED, default_value=True).value,
        "slideshow_interval": settings.slideshow_interval,
        "current_active_image": config_repo.get_or(ConfigKey.CURRENT_ACTIVE_IMAGE, default_value=None).value,
        "current_active_image_since": config_repo.get_or(
            ConfigKey.CURRENT_ACTIVE_IMAGE_SINCE, default_value=None
        ).value,
        "active_filter": active_filter,
    }

    return templates.TemplateResponse("index.html", {"request": req, "config": config})
