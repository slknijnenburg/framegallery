from typing import Optional

from pydantic import BaseModel

class ActiveArt(BaseModel):
    content_id: str
    matte_id: str
    portrait_matte_id: str
    category_id: str

class Image(BaseModel):
    id: int
    filename: str
    filepath: str
    filetype: str
    thumbnail_path: str
    width: int
    height: int
    aspect_width: int
    aspect_height: int

class ConfigResponse(BaseModel):
    slideshow_enabled: bool
    slideshow_interval: int
    current_active_image: str|None
    current_active_image_since: str|None