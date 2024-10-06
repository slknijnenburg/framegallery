import asyncio
import base64
import os

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from samsungtvws.async_art import SamsungTVAsyncArt
from typing import Optional
from pydantic import BaseModel
import logging

from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware

from . import crud, models, schemas
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.INFO)  # or logging.DEBUG to see messages
ip = "192.168.2.76"
api_version = "4.3.4.0"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", # React dev server
        "http://localhost:7999", # ASGI server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    counts = {
        "items_on_tv": 0,
        "existed_in_db_already": 0,
        "deleted_from_db": 0,
    }
    processed_items = []

    artlist = await tv.available('MY-C0002')
    for art in artlist:
        counts["items_on_tv"] += 1
        # Check if the art item already exists in the database
        art_item = crud.get_art_item(db, content_id=art['content_id'])
        if art_item:
            processed_items.append(art['content_id'])
            counts["existed_in_db_already"] += 1
            continue

        art_item = crud.create_art_item(db, art_item=schemas.ArtItem(**art))
        art_item_dict = schemas.ArtItem.model_validate(art_item).model_dump_json()
        logging.info('Art item: {}'.format(art_item_dict))

        ## Add thumbnail for this new item
        try:
            thumb = b''
            if int(api_version.replace('.', '')) < 4000:  # check api version number, and use correct api call
                thumbs = await tv.get_thumbnail(art_item.content_id, True)  # old api, gets thumbs in same format as new api
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
                processed_items.append(art_item.content_id)
            logging.info('got thumbnail for {} binary data length: {}'.format(art_item.content_id, len(thumb)))
        except asyncio.exceptions.IncompleteReadError as e:
            logging.error('FAILED to get thumbnail for {}: {}'.format(art_item.content_id, e))

    counts["deleted_from_db"] = crud.delete_items_not_in_list(db, processed_items)

    return counts


# Defines a route handler for `/*` essentially.
# NOTE: this needs to be the last route defined b/c it's a catch all route
@app.get("/{rest_of_path:path}")
async def react_app(req: Request, rest_of_path: str):
    return templates.TemplateResponse('index.html', { 'request': req })