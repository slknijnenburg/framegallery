from sqlalchemy import select
from sqlalchemy.orm import Session

from framegallery.models import Library


class LibraryRepository:
    """Manages the configured photo libraries in the database."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_all(self, *, enabled_only: bool = False) -> list[Library]:
        """Get all libraries, optionally only the enabled ones."""
        stmt = select(Library).order_by(Library.id)
        if enabled_only:
            stmt = stmt.where(Library.enabled.is_(True))
        result = self._db.execute(stmt).scalars().all()
        return list(result)

    def get(self, library_pk: int) -> Library | None:
        """Get a library by its primary key."""
        return self._db.get(Library, library_pk)

    def get_by_library_id(self, library_id: str) -> Library | None:
        """Get a library by its stable string ``library_id``."""
        stmt = select(Library).where(Library.library_id == library_id)
        return self._db.execute(stmt).scalar_one_or_none()

    def save(self, library: Library) -> Library:
        """Persist a new or modified library instance and return the refreshed row."""
        self._db.add(library)
        self._db.commit()
        self._db.refresh(library)
        return library

    def delete(self, library_pk: int) -> None:
        """Delete a library by its primary key."""
        library = self._db.get(Library, library_pk)
        if library is not None:
            self._db.delete(library)
            self._db.commit()
