from abc import ABC, abstractmethod

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.sql.elements import ColumnElement

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
        """Return a SQLAlchemy expression that filters images by directory."""
        op = self._operator
        value = self._value
        if op in (
            "=",
            "!=",
            "contains",
            "beginsWith",
            "endsWith",
            "doesNotContain",
            "doesNotBeginWith",
            "doesNotEndWith",
            "null",
            "notNull",
            "in",
            "notIn",
        ):
            mapping = {
                "=": lambda: Image.filepath == value,
                "!=": lambda: Image.filepath != value,
                "contains": lambda: Image.filepath.like(f"%{value}%"),
                "beginsWith": lambda: Image.filepath.like(f"{value}%"),
                "endsWith": lambda: Image.filepath.like(f"%{value}"),
                "doesNotContain": lambda: ~Image.filepath.like(f"%{value}%"),
                "doesNotBeginWith": lambda: ~Image.filepath.like(f"{value}%"),
                "doesNotEndWith": lambda: ~Image.filepath.like(f"%{value}"),
                "null": lambda: Image.filepath.is_(None),
                "notNull": lambda: Image.filepath.is_not(None),
                "in": lambda: Image.filepath.in_(value if isinstance(value, list) else [value]),
                "notIn": lambda: ~Image.filepath.in_(value if isinstance(value, list) else [value]),
            }
            return mapping[op]()
        msg = f"Unsupported operator for DirectoryFilter: {op}"
        raise ValueError(msg)


class FilenameFilter(ImageFilter):
    """Filter images by filename with various operators."""

    def __init__(self, value: str, operator: str) -> None:
        self._value = value
        self._operator = operator

    def get_expression(self) -> ColumnElement[bool]:
        """Return a SQLAlchemy expression that filters images by filename."""
        op = self._operator
        value = self._value
        if op in (
            "=",
            "!=",
            "contains",
            "beginsWith",
            "endsWith",
            "doesNotContain",
            "doesNotBeginWith",
            "doesNotEndWith",
            "null",
            "notNull",
            "in",
            "notIn",
        ):
            mapping = {
                "=": lambda: Image.filename == value,
                "!=": lambda: Image.filename != value,
                "contains": lambda: Image.filename.like(f"%{value}%"),
                "beginsWith": lambda: Image.filename.like(f"{value}%"),
                "endsWith": lambda: Image.filename.like(f"%{value}"),
                "doesNotContain": lambda: ~Image.filename.like(f"%{value}%"),
                "doesNotBeginWith": lambda: ~Image.filename.like(f"{value}%"),
                "doesNotEndWith": lambda: ~Image.filename.like(f"%{value}"),
                "null": lambda: Image.filename.is_(None),
                "notNull": lambda: Image.filename.is_not(None),
                "in": lambda: Image.filename.in_(value if isinstance(value, list) else [value]),
                "notIn": lambda: ~Image.filename.in_(value if isinstance(value, list) else [value]),
            }
            return mapping[op]()
        msg = f"Unsupported operator for FilenameFilter: {op}"
        raise ValueError(msg)


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


class KeywordFilter(ImageFilter):
    """Filter images by keywords with various operators."""

    SUPPORTED_OPERATORS = (
        "=",
        "!=",
        "contains",
        "beginsWith",
        "endsWith",
        "doesNotContain",
        "doesNotBeginWith",
        "doesNotEndWith",
        "null",
        "notNull",
        "in",
        "notIn",
    )

    def __init__(self, value: str | list[str], operator: str) -> None:
        self._value = value
        self._operator = operator

    def get_expression(self) -> ColumnElement[bool]:
        """Return a SQLAlchemy expression that filters images by keywords."""
        op = self._operator
        value = self._value

        if op in self.SUPPORTED_OPERATORS:
            # Handle null checks for keywords column
            if op == "null":
                return Image.keywords.is_(None)
            if op == "notNull":
                return Image.keywords.is_not(None)

            # For array-based operations, we need to check if any keyword in the array matches
            # Using JSON functions to search within the keywords array
            json_each_table = func.json_each(Image.keywords).table_valued("value")

            mapping = {
                "=": lambda: exists(select(json_each_table.c.value).where(json_each_table.c.value == value)),
                "!=": lambda: ~exists(select(json_each_table.c.value).where(json_each_table.c.value == value)),
                "contains": lambda: exists(
                    select(json_each_table.c.value).where(json_each_table.c.value.like(func.concat("%", value, "%")))
                ),
                "beginsWith": lambda: exists(
                    select(json_each_table.c.value).where(json_each_table.c.value.like(func.concat(value, "%")))
                ),
                "endsWith": lambda: exists(
                    select(json_each_table.c.value).where(json_each_table.c.value.like(func.concat("%", value)))
                ),
                "doesNotContain": lambda: ~exists(
                    select(json_each_table.c.value).where(json_each_table.c.value.like(func.concat("%", value, "%")))
                ),
                "doesNotBeginWith": lambda: ~exists(
                    select(json_each_table.c.value).where(json_each_table.c.value.like(func.concat(value, "%")))
                ),
                "doesNotEndWith": lambda: ~exists(
                    select(json_each_table.c.value).where(json_each_table.c.value.like(func.concat("%", value)))
                ),
                "in": lambda: exists(
                    select(json_each_table.c.value).where(
                        json_each_table.c.value.in_(value if isinstance(value, list) else [value])
                    )
                ),
                "notIn": lambda: ~exists(
                    select(json_each_table.c.value).where(
                        json_each_table.c.value.in_(value if isinstance(value, list) else [value])
                    )
                ),
            }
            return mapping[op]()
        msg = f"Unsupported operator for KeywordFilter: {op}"
        raise ValueError(msg)


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
    def _or_filters(filters: list[ImageFilter]) -> ColumnElement[bool]:
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
