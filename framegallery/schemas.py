from typing import Optional

from pydantic import BaseModel

class ArtItem(BaseModel):
    content_id: str
    local_filename: Optional[str] = None
    category_id: str
    slideshow: bool
    matte_id: str
    portrait_matte_id: str
    width: int
    height: int
    image_date: str
    content_type: str
    thumbnail_filename: Optional[str] = None
    thumbnail_filetype: Optional[str] = None
    thumbnail_data: Optional[str] = None

    class Config:
        from_attributes = True