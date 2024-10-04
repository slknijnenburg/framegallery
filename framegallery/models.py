from sqlalchemy import Boolean, Column, Integer, String

from .database import Base

class ArtItem(Base):
    __tablename__ = "art_items"
    content_id = Column(String, primary_key=True)
    category_id = Column(String)
    slideshow = Column(Boolean)
    matte_id = Column(String)
    portrait_matte_id = Column(String)
    width = Column(Integer)
    height = Column(Integer)
    image_date = Column(String)
    content_type = Column(String)
    thumbnail = Column(String)

#art_contents: List[ArtContent] = [
#    {"content_id": "MY_F0003", "category_id": "MY-C0002", "slideshow": False, "matte_id": "none", "portrait_matte_id": "shadowbox_black", "width": 1920, "height": 1080, "image_date": "2024:10:02 12:08:25", "content_type": "mobile"},
#    {"content_id": "MY_F0002", "category_id": "MY-C0002", "slideshow": False, "matte_id": "shadowbox_polar", "portrait_matte_id": "shadowbox_polar", "width": 1920, "height": 1280, "image_date": "2024:10:02 11:58:36", "content_type": "mobile"}
#]