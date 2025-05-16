import json
from typing import Any

from sqlalchemy import true
from sqlalchemy.sql.elements import ColumnElement

from .image_filter import (
    AndFilter,
    AspectRatioHeightFilter,
    AspectRatioWidthFilter,
    DirectoryFilter,
    FilenameFilter,
    ImageFilter,
    OrFilter,
)


class InvalidRuleError(Exception):
    """Raised when a rule is missing required keys or is otherwise invalid."""

    def __init__(self, message: str = "Invalid rule: missing required keys") -> None:
        super().__init__(message)

    @classmethod
    def missing_rules_key(cls) -> "InvalidRuleError":
        """Return an InvalidRuleError for missing 'rules' key in a query group."""
        return cls("Invalid query group: missing 'rules' key")

class UnsupportedFieldError(Exception):
    """Raised when an unsupported field is encountered in a rule."""

    def __init__(self, field: str) -> None:
        message = f"Unsupported field: {field}"
        super().__init__(message)

class UnsupportedCombinatorError(Exception):
    """Raised when an unsupported combinator is encountered in a group."""

    def __init__(self, combinator: str) -> None:
        message = f"Unsupported combinator: {combinator}"
        super().__init__(message)

class EmptyGroupError(Exception):
    """Raised when a query group contains no rules."""

    def __init__(self, message: str = "Query group contains no rules") -> None:
        super().__init__(message)


class QueryBuilder:
    """Converts react-querybuilder JSON queries into SQLAlchemy expressions."""

    def __init__(self, query_json: str) -> None:
        """
        Initialize the query builder with a JSON string from react-querybuilder.

        Args:
            query_json: JSON string containing a react-querybuilder query

        """
        self._query_dict = json.loads(query_json)

    def build(self) -> ColumnElement[bool]:
        """
        Convert the query into a SQLAlchemy expression.

        Returns:
            A SQLAlchemy binary expression that can be used in a filter

        """
        return self._process_group(self._query_dict)

    def _process_group(self, group: dict[str, Any]) -> ColumnElement[bool]:
        """
        Process a query group and convert it to a SQLAlchemy expression.

        Args:
            group: Dictionary containing a react-querybuilder group

        Returns:
            A SQLAlchemy binary expression

        """
        if "rules" not in group:
            raise InvalidRuleError.missing_rules_key()

        rules: list[dict[str, Any]] = group["rules"]
        if not rules:
            return true()  # Return true() if the group has no rules

        filters: list[ImageFilter] = []
        for rule in rules:
            if self._is_group(rule):
                filters.append(self._wrap_expression(self._process_group(rule)))
            else:
                filters.append(self._process_rule(rule))

        combinator = group.get("combinator", "and").lower()
        if combinator == "and":
            return AndFilter(filters).get_expression()
        if combinator == "or":
            return OrFilter(filters).get_expression()
        raise UnsupportedCombinatorError(combinator)

    def _process_rule(self, rule: dict[str, Any]) -> ImageFilter:
        """
        Convert a single rule into an ImageFilter.

        Args:
            rule: Dictionary containing a react-querybuilder rule

        Returns:
            An ImageFilter instance

        """
        if not all(key in rule for key in ["field", "operator", "value"]):
            raise InvalidRuleError

        field = rule["field"]
        value = rule["value"]

        # Map fields to appropriate filters
        operator = rule["operator"]
        if field == "filename":
            return FilenameFilter(value, operator)
        if field == "directory":
            return DirectoryFilter(value, operator)
        if field == "aspect_ratio_width":
            return AspectRatioWidthFilter(float(value))
        if field == "aspect_ratio_height":
            return AspectRatioHeightFilter(float(value))
        raise UnsupportedFieldError(field)

    @staticmethod
    def _is_group(rule: dict[str, Any]) -> bool:
        """
        Check if a rule is actually a nested group.

        Args:
            rule: Dictionary that might be a group

        Returns:
            True if the rule is a group, False otherwise

        """
        return "rules" in rule

    @staticmethod
    def _wrap_expression(expression: ColumnElement[bool]) -> ImageFilter:
        """
        Wrap a SQLAlchemy expression in an ImageFilter.

        Args:
            expression: SQLAlchemy expression to wrap

        Returns:
            An ImageFilter that returns the given expression

        """
        class WrappedFilter(ImageFilter):
            def get_expression(self) -> ColumnElement[bool]:
                return expression

        return WrappedFilter()
