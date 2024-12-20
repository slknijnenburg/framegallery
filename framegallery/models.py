from sqlalchemy import Boolean, Column, Integer, String

from .database import Base

"""
Representation of an Art item on the Samsung television
"""
class ArtItem(Base):
    __tablename__ = "art_items"
    content_id = Column(String, primary_key=True)
    local_filename = Column(String)
    category_id = Column(String)
    slideshow = Column(Boolean)
    matte_id = Column(String)
    portrait_matte_id = Column(String)
    width = Column(Integer)
    height = Column(Integer)
    aspect_width = Column(Integer)
    aspect_height = Column(Integer)
    image_date = Column(String)
    content_type = Column(String)
    thumbnail_filename = Column(String)
    thumbnail_filetype = Column(String)
    thumbnail_data = Column(String)

#art_contents: List[ArtContent] = [
#    {"content_id": "MY_F0003", "category_id": "MY-C0002", "slideshow": False, "matte_id": "none", "portrait_matte_id": "shadowbox_black", "width": 1920, "height": 1080, "image_date": "2024:10:02 12:08:25", "content_type": "mobile"},
#    {"content_id": "MY_F0002", "category_id": "MY-C0002", "slideshow": False, "matte_id": "shadowbox_polar", "portrait_matte_id": "shadowbox_polar", "width": 1920, "height": 1280, "image_date": "2024:10:02 11:58:36", "content_type": "mobile"}
#]

class Image(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String, index=True)
    filepath = Column(String, index=True)
    filetype = Column(String)
    thumbnail_path = Column(String)
    width = Column(Integer)
    height = Column(Integer)
    aspect_width = Column(Integer)
    aspect_height = Column(Integer)
