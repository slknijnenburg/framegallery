"""Unit tests for keyword extraction functionality."""

from pathlib import Path

import pytest

from framegallery.importer2.importer import Importer


class TestKeywordExtraction:
    """Test class for XMP keyword extraction functionality."""

    def test_read_exif_keywords_with_test_image(self) -> None:
        """Test keyword extraction from test image with known XMP metadata."""
        # Path to the test image with known keywords
        test_image_path = Path(__file__).parent.parent.parent.parent / "unit" / "test_image.jpg"

        # Ensure test image exists
        assert test_image_path.exists(), f"Test image not found at {test_image_path}"

        # Extract keywords using the Importer method
        keywords = Importer.read_exif_keywords(str(test_image_path))

        # Assert the expected keywords are extracted
        expected_keywords = ["Kenia2019", "Kenia2019Selectie1", "Kenia2019Selectie2"]
        assert keywords == expected_keywords
        assert len(keywords) == len(expected_keywords)
        assert all(isinstance(keyword, str) for keyword in keywords)

    def test_read_exif_keywords_with_nonexistent_file(self) -> None:
        """Test keyword extraction with a non-existent file."""
        nonexistent_path = "/path/to/nonexistent/image.jpg"

        # Should return empty list for non-existent files
        keywords = Importer.read_exif_keywords(nonexistent_path)

        assert keywords == []
        assert isinstance(keywords, list)

    def test_read_exif_keywords_return_type(self) -> None:
        """Test that keyword extraction always returns a list."""
        # Test with non-existent file
        keywords = Importer.read_exif_keywords("/nonexistent/file.jpg")
        assert isinstance(keywords, list)

        # Test with existing test image
        test_image_path = Path(__file__).parent.parent.parent.parent / "unit" / "test_image.jpg"
        if test_image_path.exists():
            keywords = Importer.read_exif_keywords(str(test_image_path))
            assert isinstance(keywords, list)

    def test_read_exif_keywords_handles_invalid_path(self) -> None:
        """Test keyword extraction with invalid file paths."""
        invalid_paths = [
            "",  # Empty string
            "/dev/null",  # Not an image file
            "/var",  # Directory, not a file
        ]

        for invalid_path in invalid_paths:
            keywords = Importer.read_exif_keywords(invalid_path)
            assert keywords == []
            assert isinstance(keywords, list)

    def test_read_exif_keywords_keywords_are_strings(self) -> None:
        """Test that extracted keywords are always strings."""
        test_image_path = Path(__file__).parent.parent.parent.parent / "unit" / "test_image.jpg"

        if test_image_path.exists():
            keywords = Importer.read_exif_keywords(str(test_image_path))

            # All keywords should be strings
            for keyword in keywords:
                assert isinstance(keyword, str)
                assert len(keyword.strip()) > 0  # No empty or whitespace-only keywords

    def test_read_exif_keywords_no_duplicates(self) -> None:
        """Test that extracted keywords contain no duplicates."""
        test_image_path = Path(__file__).parent.parent.parent.parent / "unit" / "test_image.jpg"

        if test_image_path.exists():
            keywords = Importer.read_exif_keywords(str(test_image_path))

            # Check for duplicates
            assert len(keywords) == len(set(keywords)), "Keywords should not contain duplicates"

    @pytest.mark.parametrize("file_extension", [".jpg", ".jpeg", ".JPG", ".JPEG"])
    def test_read_exif_keywords_handles_different_extensions(self, file_extension: str) -> None:
        """Test that the function handles different file extensions gracefully."""
        # This test ensures the function doesn't crash with different extensions
        # Even if the file doesn't exist, it should return an empty list
        fake_path = f"/nonexistent/image{file_extension}"
        keywords = Importer.read_exif_keywords(fake_path)

        assert isinstance(keywords, list)
        assert keywords == []
