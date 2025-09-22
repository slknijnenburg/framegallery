from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from framegallery.dependencies import get_frame_connector
from framegallery.frame_connector.frame_connector import FrameConnector, TvConnectionTimeoutError
from framegallery.main import app

# Test constants
EXPECTED_FILES_COUNT = 2
TEST_FILE_SIZE_2MB = 2048576
TEST_FILE_SIZE_1KB = 1024


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_frame_connector() -> FrameConnector:
    """Create a mock FrameConnector."""
    mock_connector = MagicMock(spec=FrameConnector)
    mock_connector.list_files = AsyncMock()
    return mock_connector


@pytest.fixture(autouse=True)
def override_get_frame_connector(mock_frame_connector: FrameConnector) -> Generator[None, None, None]:
    """Replace the actual get_frame_connector with one that returns our mock."""

    def _override_get_frame_connector() -> FrameConnector:
        return mock_frame_connector

    app.dependency_overrides[get_frame_connector] = _override_get_frame_connector
    yield  # Allow tests to run
    # Clean up the override after tests
    app.dependency_overrides.pop(get_frame_connector, None)


@pytest.mark.asyncio
async def test_list_tv_files_success(client: TestClient, mock_frame_connector: FrameConnector) -> None:
    """Test successfully listing TV files."""
    # Mock TV response data
    mock_tv_files = [
        {
            "content_id": "MY-F0001",
            "file_name": "Sunset Photo",
            "file_type": "JPEG",
            "file_size": TEST_FILE_SIZE_2MB,
            "date": "2024-01-15",
            "category_id": "MY-C0002",
            "thumbnail_available": True,
            "matte": "none",
        },
        {
            "content_id": "MY-F0002",
            "file_name": "Beach Scene",
            "file_type": "PNG",
            "file_size": 3145728,
            "date": "2024-01-16",
            "category_id": "MY-C0002",
            "thumbnail_available": True,
            "matte": "shadowbox_black",
        },
    ]

    mock_frame_connector.list_files.return_value = mock_tv_files

    response = client.get("/api/tv/files")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()

    # Verify response structure
    assert isinstance(response_data, list)
    assert len(response_data) == EXPECTED_FILES_COUNT

    # Verify first file
    first_file = response_data[0]
    assert first_file["content_id"] == "MY-F0001"
    assert first_file["file_name"] == "Sunset Photo"
    assert first_file["file_type"] == "JPEG"
    assert first_file["file_size"] == TEST_FILE_SIZE_2MB
    assert first_file["date"] == "2024-01-15"
    assert first_file["category_id"] == "MY-C0002"
    assert first_file["thumbnail_available"] is True
    assert first_file["matte"] == "none"

    # Verify second file
    second_file = response_data[1]
    assert second_file["content_id"] == "MY-F0002"
    assert second_file["file_name"] == "Beach Scene"
    assert second_file["file_type"] == "PNG"

    # Verify the mock was called with default category
    mock_frame_connector.list_files.assert_called_once_with(category="MY-C0002")


@pytest.mark.asyncio
async def test_list_tv_files_with_custom_category(client: TestClient, mock_frame_connector: FrameConnector) -> None:
    """Test listing TV files with a custom category."""
    mock_tv_files = [
        {
            "content_id": "MY-F0003",
            "file_name": "Art Store Image",
            "file_type": "JPEG",
            "category_id": "MY-C0001",
        }
    ]

    mock_frame_connector.list_files.return_value = mock_tv_files

    response = client.get("/api/tv/files?category=MY-C0001")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()

    assert len(response_data) == 1
    assert response_data[0]["content_id"] == "MY-F0003"
    assert response_data[0]["category_id"] == "MY-C0001"

    # Verify the mock was called with custom category
    mock_frame_connector.list_files.assert_called_once_with(category="MY-C0001")


@pytest.mark.asyncio
async def test_list_tv_files_empty_result(client: TestClient, mock_frame_connector: FrameConnector) -> None:
    """Test listing TV files when no files are available."""
    mock_frame_connector.list_files.return_value = []

    response = client.get("/api/tv/files")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()

    assert isinstance(response_data, list)
    assert len(response_data) == 0

    mock_frame_connector.list_files.assert_called_once_with(category="MY-C0002")


@pytest.mark.asyncio
async def test_list_tv_files_tv_unavailable(client: TestClient, mock_frame_connector: FrameConnector) -> None:
    """Test listing TV files when TV is unavailable."""
    # When TV is unavailable, list_files returns None
    mock_frame_connector.list_files.return_value = None

    response = client.get("/api/tv/files")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    response_data = response.json()

    assert response_data["detail"] == "TV is not connected or unavailable"

    mock_frame_connector.list_files.assert_called_once_with(category="MY-C0002")


@pytest.mark.asyncio
async def test_list_tv_files_timeout_error(client: TestClient, mock_frame_connector: FrameConnector) -> None:
    """Test listing TV files when TV connection times out."""
    mock_frame_connector.list_files.side_effect = TvConnectionTimeoutError("Timeout")

    response = client.get("/api/tv/files")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    response_data = response.json()

    assert response_data["detail"] == "TV connection timeout"

    mock_frame_connector.list_files.assert_called_once_with(category="MY-C0002")


@pytest.mark.asyncio
async def test_list_tv_files_unexpected_error(client: TestClient, mock_frame_connector: FrameConnector) -> None:
    """Test listing TV files when an unexpected error occurs."""
    mock_frame_connector.list_files.side_effect = Exception("Unexpected error")

    response = client.get("/api/tv/files")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    response_data = response.json()

    assert response_data["detail"] == "Internal server error while retrieving TV files"

    mock_frame_connector.list_files.assert_called_once_with(category="MY-C0002")


@pytest.mark.asyncio
async def test_list_tv_files_missing_fields(client: TestClient, mock_frame_connector: FrameConnector) -> None:
    """Test listing TV files with missing optional fields."""
    # Mock response with minimal required fields and some missing optional fields
    mock_tv_files = [
        {
            "content_id": "MY-F0001",
            # Missing file_name (should default to "Unknown")
            # Missing file_type (should default to "Unknown")
            # Missing optional fields like file_size, date, etc.
        }
    ]

    mock_frame_connector.list_files.return_value = mock_tv_files

    response = client.get("/api/tv/files")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()

    assert len(response_data) == 1
    first_file = response_data[0]

    # Required fields
    assert first_file["content_id"] == "MY-F0001"
    assert first_file["category_id"] == "MY-C0002"  # Should default to query parameter

    # Fields with defaults
    assert first_file["file_name"] == "Unknown"
    assert first_file["file_type"] == "Unknown"

    # Optional fields should be None
    assert first_file["file_size"] is None
    assert first_file["date"] is None
    assert first_file["thumbnail_available"] is None
    assert first_file["matte"] is None


@pytest.mark.asyncio
async def test_list_tv_files_field_mapping(client: TestClient, mock_frame_connector: FrameConnector) -> None:
    """Test that fields are properly mapped from TV response to API response."""
    mock_tv_files = [
        {
            "content_id": "MY-F0001",
            "file_name": "Test Photo",
            "file_type": "JPEG",
            "file_size": TEST_FILE_SIZE_1KB,
            "date": "2024-01-01",
            "category_id": "MY-C0002",
            "thumbnail_available": False,
            "matte": "modern_warm",
            "extra_field": "should_be_ignored",  # Extra field should not cause issues
        }
    ]

    mock_frame_connector.list_files.return_value = mock_tv_files

    response = client.get("/api/tv/files")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()

    assert len(response_data) == 1
    file_data = response_data[0]

    # Verify all expected fields are present and correctly mapped
    expected_fields = {
        "content_id",
        "file_name",
        "file_type",
        "file_size",
        "width",
        "height",
        "date",
        "category_id",
        "thumbnail_available",
        "matte",
    }

    assert set(file_data.keys()) == expected_fields

    # Verify values are correctly mapped
    assert file_data["content_id"] == "MY-F0001"
    assert file_data["file_name"] == "Test Photo"
    assert file_data["file_type"] == "JPEG"
    assert file_data["file_size"] == TEST_FILE_SIZE_1KB
    assert file_data["date"] == "2024-01-01"
    assert file_data["category_id"] == "MY-C0002"
    assert file_data["thumbnail_available"] is False
    assert file_data["matte"] == "modern_warm"

    # Extra field should not appear in response
    assert "extra_field" not in file_data
