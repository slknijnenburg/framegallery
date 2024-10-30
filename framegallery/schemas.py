from typing import Optional

from pydantic import BaseModel

class ArtItem(BaseModel):
    content_id: str
    local_filename: Optional[str] = None
    category_id: Optional[str] = None
    slideshow: Optional[bool] = False
    matte_id: str
    portrait_matte_id: str
    width: int
    height: int
    aspect_width: int
    aspect_height: int
    image_date: Optional[str] = None
    content_type: Optional[str] = None
    thumbnail_filename: Optional[str] = None
    thumbnail_filetype: Optional[str] = None
    thumbnail_data: Optional[str] = None

    class Config:
        from_attributes = True


class ArtItemUpdate(BaseModel):
    matte_id: Optional[str] = None
    portrait_matte_id: Optional[str] = None

    class Config:
        from_attributes = True

class ActiveArt(BaseModel):
    content_id: str
    matte_id: str
    portrait_matte_id: str
    category_id: str