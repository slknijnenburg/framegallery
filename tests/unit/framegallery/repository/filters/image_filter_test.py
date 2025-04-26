from framegallery.repository.filters.image_filter import (
    AndFilter,
    AspectRatioHeightFilter,
    AspectRatioWidthFilter,
    DirectoryFilter,
    FilenameFilter,
    OrFilter,
)


def test_directory_filter():
    dir_filter = DirectoryFilter("2024-Album", "contains")
    binary_operator = dir_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert compiled_expression == "images.filepath LIKE '%2024-Album%'"

def test_file_filter():
    # Filter all first images from albums...
    file_filter = FilenameFilter("_001.jpg", "contains")
    binary_operator = file_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert compiled_expression == "images.filename LIKE '%_001.jpg%'"

def test_and_filter():
    file_filter = FilenameFilter("_001.jpg", "contains")
    dir_filter = DirectoryFilter("2024-Album", "contains")
    and_filter = AndFilter([file_filter, dir_filter])
    binary_operator = and_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert compiled_expression == "images.filename LIKE '%_001.jpg%' AND images.filepath LIKE '%2024-Album%'"

def test_or_filter():
    file_filter = FilenameFilter("_001.jpg", "contains")
    dir_filter = DirectoryFilter("2024-Album", "contains")
    and_filter = AndFilter([file_filter, dir_filter])
    binary_operator = and_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert compiled_expression == "images.filename LIKE '%_001.jpg%' AND images.filepath LIKE '%2024-Album%'"

import pytest


@pytest.mark.parametrize("FilterClass,field,operator,value,expected_sql", [
    (DirectoryFilter, "filepath", "=", "foo", "images.filepath = 'foo'"),
    (DirectoryFilter, "filepath", "!=", "foo", "images.filepath != 'foo'"),
    (DirectoryFilter, "filepath", "contains", "foo", "images.filepath LIKE '%foo%'"),
    (DirectoryFilter, "filepath", "beginsWith", "foo", "images.filepath LIKE 'foo%'"),
    (DirectoryFilter, "filepath", "endsWith", "foo", "images.filepath LIKE '%foo'"),
    (DirectoryFilter, "filepath", "doesNotContain", "foo", "images.filepath NOT LIKE '%foo%'") ,
    (DirectoryFilter, "filepath", "doesNotBeginWith", "foo", "images.filepath NOT LIKE 'foo%'") ,
    (DirectoryFilter, "filepath", "doesNotEndWith", "foo", "images.filepath NOT LIKE '%foo'") ,
    (DirectoryFilter, "filepath", "null", None, "images.filepath IS NULL"),
    (DirectoryFilter, "filepath", "notNull", None, "images.filepath IS NOT NULL"),
    (DirectoryFilter, "filepath", "in", ["foo","bar"], "images.filepath IN ('foo', 'bar')"),
    (DirectoryFilter, "filepath", "notIn", ["foo","bar"], "(images.filepath NOT IN ('foo', 'bar'))"),

    (FilenameFilter, "filename", "=", "foo.jpg", "images.filename = 'foo.jpg'"),
    (FilenameFilter, "filename", "!=", "foo.jpg", "images.filename != 'foo.jpg'"),
    (FilenameFilter, "filename", "contains", "foo.jpg", "images.filename LIKE '%foo.jpg%'"),
    (FilenameFilter, "filename", "beginsWith", "foo", "images.filename LIKE 'foo%'"),
    (FilenameFilter, "filename", "endsWith", "jpg", "images.filename LIKE '%jpg'"),
    (FilenameFilter, "filename", "doesNotContain", "foo", "images.filename NOT LIKE '%foo%'") ,
    (FilenameFilter, "filename", "doesNotBeginWith", "foo", "images.filename NOT LIKE 'foo%'") ,
    (FilenameFilter, "filename", "doesNotEndWith", "jpg", "images.filename NOT LIKE '%jpg'") ,
    (FilenameFilter, "filename", "null", None, "images.filename IS NULL"),
    (FilenameFilter, "filename", "notNull", None, "images.filename IS NOT NULL"),
    (FilenameFilter, "filename", "in", ["foo","bar"], "images.filename IN ('foo', 'bar')"),
    (FilenameFilter, "filename", "notIn", ["foo","bar"], "(images.filename NOT IN ('foo', 'bar'))"),
])
def test_filter_operators(FilterClass, field, operator, value, expected_sql):
    # Handle None for value
    if value is None:
        filter_instance = FilterClass(value, operator)
    else:
        filter_instance = FilterClass(value, operator)
    expr = filter_instance.get_expression()
    compiled = str(expr.compile(compile_kwargs={"literal_binds": True}))
    # Normalize parentheses for NOT IN and similar cases
    if compiled.startswith("(") and compiled.endswith(")"):
        compiled = compiled[1:-1]
    if expected_sql.startswith("(") and expected_sql.endswith(")"):
        expected_sql = expected_sql[1:-1]
    assert compiled == expected_sql

def test_combine_and_and_or_filters():
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
    assert compiled_expression == "images.filename LIKE '%_001.jpg%' AND images.filepath LIKE '%2024-Kenya%' OR images.filename LIKE '%_002.jpg%' AND images.filepath LIKE '%2024-CostaRica%'"


def test_aspect_ratio_width_filter():
    width_filter = AspectRatioWidthFilter(16.0)
    binary_operator = width_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert compiled_expression == "images.aspect_width = 16.0"


def test_aspect_ratio_height_filter():
    height_filter = AspectRatioHeightFilter(9.0)
    binary_operator = height_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert compiled_expression == "images.aspect_height = 9.0"


def test_combine_aspect_ratio_filters():
    width_filter = AspectRatioWidthFilter(16.0)
    height_filter = AspectRatioHeightFilter(9.0)
    and_filter = AndFilter([width_filter, height_filter])
    binary_operator = and_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert compiled_expression == "images.aspect_width = 16.0 AND images.aspect_height = 9.0"
