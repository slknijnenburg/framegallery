from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from samsungtvws.async_art import SamsungTVAsyncArt
from typing import Optional
from pydantic import BaseModel
import logging

from sqlalchemy.orm import Session
from starlette.responses import Response
from starlette.status import HTTP_204_NO_CONTENT

from . import crud, models, schemas
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.INFO)  # or logging.DEBUG to see messages
ip = "192.168.2.76"

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.middleware("http")
async def bootstrap_tv(request: Request, call_next):
    tv = SamsungTVAsyncArt(host=ip, port=8002)
    await tv.start_listening()
    request.state.tv = tv

    response = await call_next(request)
    return response


# Sets the templates directory to the `build` folder from `npm run build`
# this is where you'll find the index.html file.
templates = Jinja2Templates(directory="./ui/build")

# Mounts the `static` folder within the `build` folder to the `/static` route.
app.mount('/static', StaticFiles(directory="./ui/build/static"), 'static')

class Status(BaseModel):
    tv_on: bool
    art_mode_supported: Optional[bool] = None
    art_mode_active: Optional[bool] = None
    api_version: Optional[str] = None

@app.get("/api/status")
async def status(request: Request) -> Status:
    tv = request.state.tv

    # is art mode supported
    tv_on = await tv.on()
    if not tv_on:
        return Status(tv_on=False)

    supported = await tv.supported()
    if not supported:
        return Status(tv_on=True, art_mode_supported=False)

    art_mode_active = await tv.get_artmode()
    api_version = await tv.get_api_version()

    return Status(tv_on=True, art_mode_supported=supported, art_mode_active=art_mode_active, api_version=api_version)


@app.get("/api/available-art")
async def available_art(request: Request, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    art_items = crud.get_art_items(db, skip=skip, limit=limit)

    return art_items


@app.get("/api/available-art/refresh", status_code=200)
async def refresh_available_art(request: Request, db: Session = Depends(get_db)):
    tv = request.state.tv
    artlist = await tv.available('MY-C0002')
    for art in artlist:
        # Check if the art item already exists in the database
        art_in_db = crud.get_art_item(db, content_id=art['content_id'])
        if art_in_db:
            continue

        art_item = crud.create_art_item(db, art_item=schemas.ArtItem(**art))
        logging.info('Art item: {}'.format(art_item))

    return Response(status_code=HTTP_204_NO_CONTENT)


# Defines a route handler for `/*` essentially.
# NOTE: this needs to be the last route defined b/c it's a catch all route
@app.get("/{rest_of_path:path}")
async def react_app(req: Request, rest_of_path: str):
    return templates.TemplateResponse('index.html', { 'request': req })