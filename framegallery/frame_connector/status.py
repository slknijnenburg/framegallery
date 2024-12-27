from typing import Optional

from pydantic import BaseModel

class Status(BaseModel):
    tv_on: bool
    art_mode_supported: Optional[bool] = None
    art_mode_active: Optional[bool] = None
    api_version: Optional[str] = None


class SlideshowStatus(BaseModel):
    enabled: bool
    interval: int