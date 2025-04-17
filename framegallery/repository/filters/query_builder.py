import json
from typing import Any, Dict, List, Union

from sqlalchemy import BinaryExpression

from framegallery.repository.filters.image_filter import (
    AndFilter,
    AspectRatioHeightFilter,
    AspectRatioWidthFilter,
    DirectoryFilter,
    FilenameFilter,
    ImageFilter,
    OrFilter,
)


class QueryBuilder:
    """Converts react-querybuilder JSON queries into SQLAlchemy expressions."""

    def __init__(self, query_json: str) -> None:
        """Initialize the query builder with a JSON string from react-querybuilder.
        
        Args:
            query_json: JSON string containing a react-querybuilder query
        """
        self._query_dict = json.loads(query_json)

    def build(self) -> BinaryExpression:
        """Convert the query into a SQLAlchemy expression.
        
        Returns:
            A SQLAlchemy binary expression that can be used in a filter
        """
        return self._process_group(self._query_dict)

    def _process_group(self, group: Dict[str, Any]) -> BinaryExpression:
        """Process a query group and convert it to a SQLAlchemy expression.
        
        Args:
            group: Dictionary containing a react-querybuilder group
            
        Returns:
            A SQLAlchemy binary expression
        """
        if "rules" not in group:
            raise ValueError("Invalid query group: missing 'rules' key")

        rules: List[Dict[str, Any]] = group["rules"]
        if not rules:
            raise ValueError("Query group contains no rules")

        filters: List[ImageFilter] = []
        for rule in rules:
            if self._is_group(rule):
                filters.append(self._wrap_expression(self._process_group(rule)))
            else:
                filters.append(self._process_rule(rule))

        combinator = group.get("combinator", "and").lower()
        if combinator == "and":
            return AndFilter(filters).get_expression()
        elif combinator == "or":
            return OrFilter(filters).get_expression()
        else:
            raise ValueError(f"Unsupported combinator: {combinator}")

    def _process_rule(self, rule: Dict[str, Any]) -> ImageFilter:
        """Convert a single rule into an ImageFilter.
        
        Args:
            rule: Dictionary containing a react-querybuilder rule
            
        Returns:
            An ImageFilter instance
        """
        if not all(key in rule for key in ["field", "operator", "value"]):
            raise ValueError("Invalid rule: missing required keys")

        field = rule["field"]
        value = rule["value"]

        # Map fields to appropriate filters
        if field == "filename":
            return FilenameFilter(str(value))
        elif field == "directory":
            return DirectoryFilter(str(value))
        elif field == "aspect_ratio_width":
            return AspectRatioWidthFilter(float(value))
        elif field == "aspect_ratio_height":
            return AspectRatioHeightFilter(float(value))
        else:
            raise ValueError(f"Unsupported field: {field}")

    @staticmethod
    def _is_group(rule: Dict[str, Any]) -> bool:
        """Check if a rule is actually a nested group.
        
        Args:
            rule: Dictionary that might be a group
            
        Returns:
            True if the rule is a group, False otherwise
        """
        return "rules" in rule

    @staticmethod
    def _wrap_expression(expression: BinaryExpression) -> ImageFilter:
        """Wrap a SQLAlchemy expression in an ImageFilter.
        
        Args:
            expression: SQLAlchemy expression to wrap
            
        Returns:
            An ImageFilter that returns the given expression
        """
        class WrappedFilter(ImageFilter):
            def get_expression(self) -> BinaryExpression:
                return expression

        return WrappedFilter()
