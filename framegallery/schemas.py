from pydantic import BaseModel

class ArtItem(BaseModel):
    content_id: str
    category_id: str
    slideshow: bool
    matte_id: str
    portrait_matte_id: str
    width: int
    height: int
    image_date: str
    content_type: str

    class Config:
        from_attributes = True