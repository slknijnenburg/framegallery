from sqlalchemy import JSON, Boolean, Float, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""


class Image(Base):
    """Class for images."""

    __tablename__ = "images"
    __table_args__ = (
        Index("ix_images_filename", "filename"),
        Index("ix_images_filepath", "filepath"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String)
    filepath: Mapped[str] = mapped_column(String)
    filetype: Mapped[str] = mapped_column(String)
    thumbnail_path: Mapped[str] = mapped_column(String, nullable=True)
    width: Mapped[int] = mapped_column(Integer, nullable=True)
    height: Mapped[int] = mapped_column(Integer, nullable=True)
    aspect_width: Mapped[int] = mapped_column(Integer, nullable=True)
    aspect_height: Mapped[int] = mapped_column(Integer, nullable=True)
    crop_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    crop_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    crop_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    crop_height: Mapped[float | None] = mapped_column(Float, nullable=True)
    keywords: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    def get_crop_info(self) -> dict | None:
        """Get the crop info for the image."""
        if (
            self.crop_x is not None
            and self.crop_y is not None
            and self.crop_width is not None
            and self.crop_height is not None
        ):
            return {
                "x": self.crop_x,
                "y": self.crop_y,
                "width": self.crop_width,
                "height": self.crop_height,
            }
        return None


class Config(Base):
    """Configuration settings."""

    __tablename__ = "config"
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String, index=True)
    value: Mapped[str] = mapped_column(String, nullable=True)


class Filter(Base):
    """Class for image filters."""

    __tablename__ = "filters"
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, index=True)
    query: Mapped[str] = mapped_column(String, nullable=True)


class Library(Base):
    """A configured photo source (the local gallery or an external service like Immich)."""

    __tablename__ = "libraries"
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    # Stable string identifier used in composite photo ids, e.g. "local" or "immich-1".
    library_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    source_type: Mapped[str] = mapped_column(String)  # "local" | "immich"
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # Relative selection weight; the effective probability is weight * matching_photo_count.
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    # Per-source configuration. local: {"filter_id": int|null};
    # immich: {"base_url": str, "api_key": str, "album_ids": [str, ...]}.
    config: Mapped[dict] = mapped_column(JSON, default=dict)
