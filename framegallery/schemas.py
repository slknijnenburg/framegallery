from pydantic import BaseModel, ConfigDict


class ActiveArt(BaseModel):
    """Pydantic model for the active image in the slideshow."""

    content_id: str
    matte_id: str
    portrait_matte_id: str
    category_id: str


class Image(BaseModel):
    """Pydantic model for images."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    filepath: str
    filetype: str
    thumbnail_path: str
    width: int
    height: int
    aspect_width: int
    aspect_height: int


class Filter(BaseModel):
    """Pydantic model for image filters."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    query: str


class ConfigResponse(BaseModel):
    """Pydantic model for the response of the /config endpoint."""

    slideshow_enabled: bool
    slideshow_interval: int
    current_active_image: Image | None
    current_active_image_since: str | None
    active_filter: Filter | None


class FilterCreate(BaseModel):
    """Pydantic model for image filters."""

    name: str
    query: str


class ConfigValue(BaseModel):
    """Pydantic model for config values."""

    value: str | None


class FilterUpdate(BaseModel):
    """Pydantic model for updating image filters."""

    name: str
    query: str
