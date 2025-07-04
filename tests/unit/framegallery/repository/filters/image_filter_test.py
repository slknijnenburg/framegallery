import pytest

from framegallery.repository.filters.image_filter import (
    AndFilter,
    AspectRatioHeightFilter,
    AspectRatioWidthFilter,
    DirectoryFilter,
    FilenameFilter,
    OrFilter,
)


def test_directory_filter() -> None:
    """Test DirectoryFilter SQL expression."""
    dir_filter = DirectoryFilter("2024-Album", "contains")
    binary_operator = dir_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert compiled_expression == "images.filepath LIKE '%2024-Album%'"

def test_file_filter() -> None:
    """Test FilenameFilter SQL expression."""
    # Filter all first images from albums...
    file_filter = FilenameFilter("_001.jpg", "contains")
    binary_operator = file_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert compiled_expression == "images.filename LIKE '%_001.jpg%'"

def test_and_filter() -> None:
    """Test AndFilter SQL expression."""
    file_filter = FilenameFilter("_001.jpg", "contains")
    dir_filter = DirectoryFilter("2024-Album", "contains")
    and_filter = AndFilter([file_filter, dir_filter])
    binary_operator = and_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert compiled_expression == (
        "images.filename LIKE '%_001.jpg%' AND images.filepath LIKE '%2024-Album%'"
    )

def test_or_filter() -> None:
    """Test OrFilter SQL expression."""
    file_filter = FilenameFilter("_001.jpg", "contains")
    dir_filter = DirectoryFilter("2024-Album", "contains")
    or_filter = OrFilter([file_filter, dir_filter])
    binary_operator = or_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert compiled_expression == (
        "images.filename LIKE '%_001.jpg%' OR images.filepath LIKE '%2024-Album%'"
    )

@pytest.mark.parametrize(
    ("filter_class", "operator", "value", "expected_sql"), [
        (DirectoryFilter, "=", "foo", "images.filepath = 'foo'"),
        (DirectoryFilter, "!=", "foo", "images.filepath != 'foo'"),
        (DirectoryFilter, "contains", "foo", "images.filepath LIKE '%foo%'"),
        (DirectoryFilter, "beginsWith", "foo", "images.filepath LIKE 'foo%'"),
        (DirectoryFilter, "endsWith", "foo", "images.filepath LIKE '%foo'"),
        (DirectoryFilter, "doesNotContain", "foo", "images.filepath NOT LIKE '%foo%'"),
        (DirectoryFilter, "doesNotBeginWith", "foo", "images.filepath NOT LIKE 'foo%'"),
        (DirectoryFilter, "doesNotEndWith", "foo", "images.filepath NOT LIKE '%foo'"),
        (DirectoryFilter, "null", None, "images.filepath IS NULL"),
        (DirectoryFilter, "notNull", None, "images.filepath IS NOT NULL"),
        (DirectoryFilter, "in", ["foo","bar"], "images.filepath IN ('foo', 'bar')"),
        (DirectoryFilter, "notIn", ["foo","bar"], "(images.filepath NOT IN ('foo', 'bar'))"),

        (FilenameFilter, "=", "foo.jpg", "images.filename = 'foo.jpg'"),
        (FilenameFilter, "!=", "foo.jpg", "images.filename != 'foo.jpg'"),
        (FilenameFilter, "contains", "foo.jpg", "images.filename LIKE '%foo.jpg%'"),
        (FilenameFilter, "beginsWith", "foo", "images.filename LIKE 'foo%'"),
        (FilenameFilter, "endsWith", "jpg", "images.filename LIKE '%jpg'"),
        (FilenameFilter, "doesNotContain", "foo", "images.filename NOT LIKE '%foo%'"),
        (FilenameFilter, "doesNotBeginWith", "foo", "images.filename NOT LIKE 'foo%'"),
        (FilenameFilter, "doesNotEndWith", "jpg", "images.filename NOT LIKE '%jpg'"),
        (FilenameFilter, "null", None, "images.filename IS NULL"),
        (FilenameFilter, "notNull", None, "images.filename IS NOT NULL"),
        (FilenameFilter, "in", ["foo","bar"], "images.filename IN ('foo', 'bar')"),
        (FilenameFilter, "notIn", ["foo","bar"], "(images.filename NOT IN ('foo', 'bar'))"),
    ]
)
def test_filter_operators(
    filter_class: type,
    operator: str,
    value: object,
    expected_sql: str,
) -> None:
    """Test filter SQL operators for DirectoryFilter and FilenameFilter."""
    # Instantiate the filter with value and operator
    filter_instance = filter_class(value, operator)
    # Get the SQLAlchemy expression
    expr = filter_instance.get_expression()
    # Compile to SQL string
    compiled = str(expr.compile(compile_kwargs={"literal_binds": True}))
    # Assert SQL matches expected
    assert compiled == expected_sql

def test_combine_and_and_or_filters() -> None:
    """Test combining AndFilter and OrFilter."""
    file_filter = FilenameFilter("_001.jpg", "contains")
    dir_filter = DirectoryFilter("2024-Kenya", "contains")
    and_filter = AndFilter([file_filter, dir_filter])

    file_filter = FilenameFilter("_002.jpg", "contains")
    dir_filter = DirectoryFilter("2024-CostaRica", "contains")
    and_filter_2 = AndFilter([file_filter, dir_filter])

    or_filter = OrFilter([and_filter, and_filter_2])
    binary_operator = or_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert (
        compiled_expression
        == "images.filename LIKE '%_001.jpg%' AND images.filepath LIKE '%2024-Kenya%' "
        "OR images.filename LIKE '%_002.jpg%' AND images.filepath LIKE '%2024-CostaRica%'"
    )


def test_aspect_ratio_width_filter() -> None:
    """Test AspectRatioWidthFilter SQL expression."""
    width_filter = AspectRatioWidthFilter(16.0)
    binary_operator = width_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert compiled_expression == "images.aspect_width = 16.0"


def test_aspect_ratio_height_filter() -> None:
    """Test AspectRatioHeightFilter SQL expression."""
    height_filter = AspectRatioHeightFilter(9.0)
    binary_operator = height_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert compiled_expression == "images.aspect_height = 9.0"


def test_combine_aspect_ratio_filters() -> None:
    """Test combining aspect ratio filters."""
    width_filter = AspectRatioWidthFilter(16.0)
    height_filter = AspectRatioHeightFilter(9.0)
    and_filter = AndFilter([width_filter, height_filter])
    binary_operator = and_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert compiled_expression == "images.aspect_width = 16.0 AND images.aspect_height = 9.0"
