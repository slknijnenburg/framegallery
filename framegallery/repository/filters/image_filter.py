from abc import ABC, abstractmethod

from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy import and_, or_

from framegallery.models import Image


class ImageFilter(ABC):
    """Base class for image filters."""

    @abstractmethod
    def get_expression(self) -> ColumnElement[bool]:
        """Return a SQLAlchemy expression that filters images."""


class DirectoryFilter(ImageFilter):
    """Filter images by directory name with various operators."""

    def __init__(self, value: str, operator: str) -> None:
        self._value = value
        self._operator = operator

    def get_expression(self) -> ColumnElement[bool]:
        op = self._operator
        if op == '=':
            return Image.filepath == self._value
        elif op == '!=':
            return Image.filepath != self._value
        elif op == 'contains':
            return Image.filepath.like(f"%{self._value}%")
        elif op == 'beginsWith':
            return Image.filepath.like(f"{self._value}%")
        elif op == 'endsWith':
            return Image.filepath.like(f"%{self._value}")
        elif op == 'doesNotContain':
            return ~Image.filepath.like(f"%{self._value}%")
        elif op == 'doesNotBeginWith':
            return ~Image.filepath.like(f"{self._value}%")
        elif op == 'doesNotEndWith':
            return ~Image.filepath.like(f"%{self._value}")
        elif op == 'null':
            return Image.filepath.is_(None)
        elif op == 'notNull':
            return Image.filepath.is_not(None)
        elif op == 'in':
            return Image.filepath.in_(self._value if isinstance(self._value, list) else [self._value])
        elif op == 'notIn':
            return ~Image.filepath.in_(self._value if isinstance(self._value, list) else [self._value])
        else:
            raise ValueError(f"Unsupported operator for DirectoryFilter: {op}")


class FilenameFilter(ImageFilter):
    """Filter images by filename with various operators."""

    def __init__(self, value: str, operator: str) -> None:
        self._value = value
        self._operator = operator

    def get_expression(self) -> ColumnElement[bool]:
        op = self._operator
        if op == '=':
            return Image.filename == self._value
        elif op == '!=':
            return Image.filename != self._value
        elif op == 'contains':
            return Image.filename.like(f"%{self._value}%")
        elif op == 'beginsWith':
            return Image.filename.like(f"{self._value}%")
        elif op == 'endsWith':
            return Image.filename.like(f"%{self._value}")
        elif op == 'doesNotContain':
            return ~Image.filename.like(f"%{self._value}%")
        elif op == 'doesNotBeginWith':
            return ~Image.filename.like(f"{self._value}%")
        elif op == 'doesNotEndWith':
            return ~Image.filename.like(f"%{self._value}")
        elif op == 'null':
            return Image.filename.is_(None)
        elif op == 'notNull':
            return Image.filename.is_not(None)
        elif op == 'in':
            return Image.filename.in_(  self._value if isinstance(self._value, list) else [self._value])
        elif op == 'notIn':
            return ~Image.filename.in_(self._value if isinstance(self._value, list) else [self._value])
        else:
            raise ValueError(f"Unsupported operator for FilenameFilter: {op}")



class AspectRatioWidthFilter(ImageFilter):
    """Filter images by aspect ratio width."""

    def __init__(self, aspect_ratio_width: float) -> None:
        self._aspect_ratio_width = aspect_ratio_width

    def get_expression(self) -> ColumnElement[bool]:
        """Return a SQLAlchemy expression that filters images by aspect ratio width."""
        return Image.aspect_width == self._aspect_ratio_width



class AspectRatioHeightFilter(ImageFilter):
    """Filter images by aspect ratio height."""

    def __init__(self, aspect_ratio_height: float) -> None:
        self._aspect_ratio_height = aspect_ratio_height

    def get_expression(self) -> ColumnElement[bool]:
        """Return a SQLAlchemy expression that filters images by aspect ratio height."""
        return Image.aspect_height == self._aspect_ratio_height


class AndFilter(ImageFilter):
    """Filter images by multiple filters, combined with AND."""

    def __init__(self, filters: list[ImageFilter]) -> None:
        self._filters = filters

    def get_expression(self) -> ColumnElement[bool]:
        """Return a SQLAlchemy expression that filters images by multiple filters, combined with AND."""
        return self._and_filters(self._filters)

    @staticmethod
    def _and_filters(filters: list[ImageFilter]) -> ColumnElement[bool]:
        """Return a SQL expression that filters images by multiple filters, combined with AND."""
        if len(filters) == 0:
            raise NoFiltersError

        if len(filters) == 1:
            return filters[0].get_expression()

        return and_(*[image_filter.get_expression() for image_filter in filters])


class OrFilter(ImageFilter):
    """Filter images by multiple filters, combined with OR."""

    def __init__(self, filters: list[ImageFilter]) -> None:
        self._filters = filters

    def get_expression(self) -> ColumnElement[bool]:
        """Return a SQLAlchemy expression that filters images by multiple filters, combined with OR."""
        return self._or_filters(self._filters)

    @staticmethod
    def _or_filters(filters: list[ImageFilter]) ->  ColumnElement[bool]:
        """Return a SQL expression that filters images by multiple filters, combined with OR."""
        if len(filters) == 0:
            raise NoFiltersError

        if len(filters) == 1:
            return filters[0].get_expression()

        return or_(*[image_filter.get_expression() for image_filter in filters])

class NoFiltersError(ValueError):
    """Raised when there are no filters provided."""

    def __init__(self) -> None:
        super().__init__("No filters provided")
