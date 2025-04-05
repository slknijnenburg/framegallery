from abc import ABC, abstractmethod

from sqlalchemy import BinaryExpression, and_, or_

from framegallery.models import Image


class ImageFilter(ABC):
    """Base class for image filters."""

    @abstractmethod
    def get_expression(self) -> BinaryExpression:
        """Return a SQL expression that filters images."""


class DirectoryFilter(ImageFilter):
    """Filter images by (part of) a directory name."""

    def __init__(self, directory: str) -> None:
        self._directory = directory

    def get_expression(self) -> BinaryExpression:
        """Return a SQL expression that filters images by directory name."""
        return Image.filepath.like(f"%{self._directory}%")


class FilenameFilter(ImageFilter):
    """Filter images by (part of) a filename."""

    def __init__(self, filename: str) -> None:
        self._filename = filename

    def get_expression(self) -> BinaryExpression:
        """Return a SQL expression that filters images by filename."""
        return Image.filename.like(f"%{self._filename}%")


class AspectRatioWidthFilter(ImageFilter):
    """Filter images by aspect ratio width."""

    def __init__(self, aspect_ratio_width: float) -> None:
        self._aspect_ratio_width = aspect_ratio_width

    def get_expression(self) -> BinaryExpression:
        """Return a SQL expression that filters images by aspect ratio width."""
        return Image.aspect_width == self._aspect_ratio_width



class AspectRatioHeightFilter(ImageFilter):
    """Filter images by aspect ratio height."""

    def __init__(self, aspect_ratio_height: float) -> None:
        self._aspect_ratio_height = aspect_ratio_height

    def get_expression(self) -> BinaryExpression:
        """Return a SQL expression that filters images by aspect ratio height."""
        return Image.aspect_height == self._aspect_ratio_height


class AndFilter(ImageFilter):
    """Filter images by multiple filters, combined with AND."""

    def __init__(self, filters: list[ImageFilter]) -> None:
        self._filters = filters

    def get_expression(self) -> BinaryExpression:
        """Return a SQL expression that filters images by multiple filters, combined with AND."""
        return self._and_filters(self._filters)

    @staticmethod
    def _and_filters(filters: list[ImageFilter]) -> BinaryExpression:
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

    def get_expression(self) -> BinaryExpression:
        """Return a SQL expression that filters images by multiple filters, combined with OR."""
        return self._or_filters(self._filters)

    @staticmethod
    def _or_filters(filters: list[ImageFilter]) -> BinaryExpression:
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
