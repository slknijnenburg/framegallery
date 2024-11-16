from abc import ABC, abstractmethod
from typing import List

from sqlalchemy import BinaryExpression, and_, or_

from framegallery.models import Image

class ImageFilter(ABC):
    @abstractmethod
    def get_expression(self) -> BinaryExpression:
        pass


class DirectoryFilter(ImageFilter):
    """
    Filter images by (part of) a directory name
    """
    def __init__(self, directory: str):
        self._directory = directory

    def get_expression(self) -> BinaryExpression:
        return Image.filepath.like(f'%{self._directory}%')


class FilenameFilter(ImageFilter):
    """
    Filter images by (part of) a filename
    """
    def __init__(self, filename: str):
        self._filename = filename

    def get_expression(self) -> BinaryExpression:
        return Image.filename.like(f'%{self._filename}%')


class AndFilter(ImageFilter):
    """
    Filter images by multiple filters, combined with AND
    """
    def __init__(self, filters: List[ImageFilter]):
        self._filters = filters

    def get_expression(self) -> BinaryExpression:
        return self._and_filters(self._filters)

    @staticmethod
    def _and_filters(filters: List[ImageFilter]) -> BinaryExpression:
        if len(filters) == 0:
            raise ValueError('No filters provided')

        if len(filters) == 1:
            return filters[0].get_expression()

        return and_(*[image_filter.get_expression() for image_filter in filters])


class OrFilter(ImageFilter):
    """
    Filter images by multiple filters, combined with OR
    """
    def __init__(self, filters: List[ImageFilter]):
        self._filters = filters

    def get_expression(self) -> BinaryExpression:
        return self._and_filters(self._filters)

    @staticmethod
    def _and_filters(filters: List[ImageFilter]) -> BinaryExpression:
        if len(filters) == 0:
            raise ValueError('No filters provided')

        if len(filters) == 1:
            return filters[0].get_expression()

        return or_(*[image_filter.get_expression() for image_filter in filters])

