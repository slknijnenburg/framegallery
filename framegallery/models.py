from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy.orm import mapped_column


class Base(DeclarativeBase):
    pass


class Image(Base):
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


class Config(Base):
    __tablename__ = "config"
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String, index=True)
    value: Mapped[str] = mapped_column(String, nullable=True)


class Filter(Base):
    __tablename__ = "filters"
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, index=True)
    query: Mapped[str] = mapped_column(String, nullable=True)
