from pydantic import BaseModel, ConfigDict, Field


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
    keywords: list[str] | None = None


class Filter(BaseModel):
    """Pydantic model for image filters."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    query: str


class ActivePhoto(BaseModel):
    """Pydantic model for the currently active photo, from any library."""

    library_id: str
    external_id: str
    composite_id: str
    source_type: str
    is_local: bool
    bytes_url: str
    filename: str | None = None
    width: int | None = None
    height: int | None = None
    aspect_width: int | None = None
    aspect_height: int | None = None
    keywords: list[str] | None = None


class ConfigResponse(BaseModel):
    """Pydantic model for the response of the /config endpoint."""

    slideshow_enabled: bool
    slideshow_interval: int
    current_active_photo: ActivePhoto | None
    current_active_image_since: str | None
    active_filter: Filter | None
    auto_cleanup_enabled: bool


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


class CropData(BaseModel):
    """Pydantic model for crop input data."""

    x: float = Field(..., ge=0, le=100, description="The x coordinate of the crop area as a percentage.")
    y: float = Field(..., ge=0, le=100, description="The y coordinate of the crop area as a percentage.")
    width: float = Field(..., gt=0, le=100, description="The width of the crop area as a percentage.")
    height: float = Field(..., gt=0, le=100, description="The height of the crop area as a percentage.")


class AlbumSummary(BaseModel):
    """Pydantic model for an album offered by an external library."""

    id: str
    name: str
    photo_count: int | None = None


class LibrarySummary(BaseModel):
    """API-facing view of a configured library. Never exposes the stored API key."""

    id: int
    library_id: str
    name: str
    source_type: str
    enabled: bool
    weight: float
    is_local: bool
    has_api_key: bool
    base_url: str | None = None
    album_ids: list[str] = Field(default_factory=list)
    filter_id: int | None = None


class LibraryStatus(BaseModel):
    """Live health/count of a library, for surfacing problems in the UI."""

    id: int
    library_id: str
    enabled: bool
    count: int | None = None
    error: str | None = None


class LibraryCreate(BaseModel):
    """Payload for creating an external (Immich) library."""

    name: str
    source_type: str = "immich"
    base_url: str
    api_key: str
    album_ids: list[str] = Field(default_factory=list)
    enabled: bool = True
    weight: float = 1.0


class LibraryUpdate(BaseModel):
    """Payload for updating a library. Fields left unset are unchanged."""

    name: str | None = None
    enabled: bool | None = None
    weight: float | None = None
    base_url: str | None = None
    # Only sent when the user wants to change the key; omitted keeps the stored one.
    api_key: str | None = None
    album_ids: list[str] | None = None
    filter_id: int | None = None


class ImmichConnectionRequest(BaseModel):
    """Payload for testing an Immich connection or listing its albums."""

    base_url: str
    api_key: str


class ConnectionTestResult(BaseModel):
    """Result of probing an Immich server."""

    ok: bool
    version: str | None = None
    error: str | None = None


class TvFileResponse(BaseModel):
    """Pydantic model for TV file information."""

    content_id: str = Field(..., description="Unique identifier from TV")
    file_name: str = Field(..., description="Display name of the file")
    file_type: str = Field(..., description="File format (JPEG, PNG, etc.)")
    file_size: int | None = Field(None, description="File size in bytes")
    width: int | None = Field(None, description="Image width in pixels")
    height: int | None = Field(None, description="Image height in pixels")
    date: str | None = Field(None, description="Upload/creation date")
    category_id: str = Field(..., description="TV category identifier")
    thumbnail_available: bool | None = Field(None, description="Whether thumbnail exists")
    matte: str | None = Field(None, description="Applied matte style")
