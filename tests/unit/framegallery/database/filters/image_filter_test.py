from framegallery.repository.filters.image_filter import AndFilter, DirectoryFilter, FilenameFilter, ImageFilter, \
    OrFilter
from framegallery.models import Image


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