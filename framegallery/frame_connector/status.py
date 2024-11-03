from typing import Optional

from pydantic import BaseModel

class Status(BaseModel):
    tv_on: bool
    art_mode_supported: Optional[bool] = None
    art_mode_active: Optional[bool] = None
    api_version: Optional[str] = None


class SlideshowStatus(BaseModel):
    value: str
    category_id: str
    sub_category_id: str
    current_content_id: str
    type: str
    content_list: str | list[str]