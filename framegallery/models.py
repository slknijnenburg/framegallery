from pydantic import BaseModel

class ArtContent(BaseModel):
    content_id: str
    category_id: str
    slideshow: bool
    matte_id: str
    portrait_matte_id: str
    width: int
    height: int
    image_date: str
    content_type: str

#art_contents: List[ArtContent] = [
#    {"content_id": "MY_F0003", "category_id": "MY-C0002", "slideshow": False, "matte_id": "none", "portrait_matte_id": "shadowbox_black", "width": 1920, "height": 1080, "image_date": "2024:10:02 12:08:25", "content_type": "mobile"},
#    {"content_id": "MY_F0002", "category_id": "MY-C0002", "slideshow": False, "matte_id": "shadowbox_polar", "portrait_matte_id": "shadowbox_polar", "width": 1920, "height": 1280, "image_date": "2024:10:02 11:58:36", "content_type": "mobile"}
#]