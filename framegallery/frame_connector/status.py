from pydantic import BaseModel


class Status(BaseModel):
    """Pydantic model for the status of the Frame TV."""

    tv_on: bool
    art_mode_supported: bool | None = None
    art_mode_active: bool | None = None
    api_version: str | None = None


class SlideshowStatus(BaseModel):
    """Pydantic model for the slideshow status."""

    enabled: bool
    interval: int
