from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from samsungtvws.async_art import SamsungTVAsyncArt
from samsungtvws import exceptions
from typing import Optional
from pydantic import BaseModel
import logging

logging.basicConfig(level=logging.INFO)  # or logging.DEBUG to see messages
ip = "192.168.2.76"

app = FastAPI()


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
async def status() -> Status:
    tv = SamsungTVAsyncArt(host=ip, port=8002)
    await tv.start_listening()

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

# Defines a route handler for `/*` essentially.
# NOTE: this needs to be the last route defined b/c it's a catch all route
@app.get("/{rest_of_path:path}")
async def react_app(req: Request, rest_of_path: str):
    return templates.TemplateResponse('index.html', { 'request': req })