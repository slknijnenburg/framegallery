from framegallery.repository.filters.image_filter import (AndFilter, DirectoryFilter, FilenameFilter, OrFilter,
    AspectRatioWidthFilter, AspectRatioHeightFilter)


def test_directory_filter():
    dir_filter = DirectoryFilter('2024-Album')
    binary_operator = dir_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert compiled_expression == "images.filepath LIKE '%2024-Album%'"

def test_file_filter():
    # Filter all first images from albums...
    file_filter = FilenameFilter('_001.jpg')
    binary_operator = file_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert compiled_expression == "images.filename LIKE '%_001.jpg%'"

def test_and_filter():
    file_filter = FilenameFilter('_001.jpg')
    dir_filter = DirectoryFilter('2024-Album')
    and_filter = AndFilter([file_filter, dir_filter])
    binary_operator = and_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert compiled_expression == "images.filename LIKE '%_001.jpg%' AND images.filepath LIKE '%2024-Album%'"

def test_or_filter():
    file_filter = FilenameFilter('_001.jpg')
    dir_filter = DirectoryFilter('2024-Album')
    and_filter = AndFilter([file_filter, dir_filter])
    binary_operator = and_filter.get_expression()

    compiled_expression = str(binary_operator.compile(compile_kwargs={"literal_binds": True}))

    # Assert the components of the SQL expression
    assert compiled_expression == "images.filename LIKE '%_001.jpg%' AND images.filepath LIKE '%2024-Album%'"

def test_combine_and_and_or_filters():
    file_filter = FilenameFilter('_001.jpg')
    dir_filter = DirectoryFilter('2024-Kenya')
    and_filter = AndFilter([file_filter, dir_filter])

    file_filter = FilenameFilter('_002.jpg')
    dir_filter = DirectoryFilter('2024-CostaRica')
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