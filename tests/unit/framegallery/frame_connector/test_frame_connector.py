"""Unit tests for FrameConnector.list_files() method."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import websockets.exceptions

from framegallery.frame_connector.frame_connector import (
    FrameConnector,
    TvConnectionTimeoutError,
)


@pytest.fixture
def frame_connector():
    """Create a FrameConnector instance for testing."""
    with patch("framegallery.frame_connector.frame_connector.asyncio.create_task"):
        connector = FrameConnector("192.168.1.100", 8001)
        connector._tv = AsyncMock()
        connector._connected = True
        connector._tv_is_online = True
        return connector


@pytest.mark.asyncio
async def test_list_files_success(frame_connector):
    """Test successful retrieval of files from TV."""
    mock_tv_response = [
        {
            "content_id": "MY-F0001",
            "category_id": "MY-C0002",
            "title": "Sunset Photo",
            "format": "JPEG",
            "file_size": 2048576,
            "date": "2024-01-15",
            "thumbnail_available": True,
            "matte": "none",
        },
        {
            "content_id": "MY-F0002",
            "category_id": "MY-C0002",
            "title": "Beach Scene",
            "format": "PNG",
            "file_size": 3145728,
            "date": "2024-01-16",
            "thumbnail_available": True,
            "matte": "shadowbox_black",
        },
        {
            "content_id": "MY-F0003",
            "category_id": "MY-C0001",
            "title": "Art Store Image",
            "format": "JPEG",
            "file_size": 1048576,
            "date": "2024-01-10",
            "thumbnail_available": False,
            "matte": "modern_warm",
        },
    ]

    frame_connector._tv.available = AsyncMock(return_value=mock_tv_response)

    # Test with default category (MY-C0002)
    result = await frame_connector.list_files()

    assert result is not None
    assert len(result) == 2  # Should only return MY-C0002 files
    assert result[0]["content_id"] == "MY-F0001"
    assert result[0]["file_name"] == "Sunset Photo"
    assert result[0]["file_type"] == "JPEG"
    assert result[1]["content_id"] == "MY-F0002"

    frame_connector._tv.available.assert_called_once()


@pytest.mark.asyncio
async def test_list_files_with_specific_category(frame_connector):
    """Test retrieval of files for a specific category."""
    mock_tv_response = [
        {
            "content_id": "MY-F0001",
            "category_id": "MY-C0002",
            "title": "User Photo",
            "format": "JPEG",
        },
        {
            "content_id": "MY-F0003",
            "category_id": "MY-C0001",
            "title": "Art Store Image",
            "format": "PNG",
        },
    ]

    frame_connector._tv.available = AsyncMock(return_value=mock_tv_response)

    # Request MY-C0001 category
    result = await frame_connector.list_files("MY-C0001")

    assert result is not None
    assert len(result) == 1
    assert result[0]["content_id"] == "MY-F0003"
    assert result[0]["category_id"] == "MY-C0001"


@pytest.mark.asyncio
async def test_list_files_no_category_filter(frame_connector):
    """Test retrieval of all files when category is None."""
    mock_tv_response = [
        {
            "content_id": "MY-F0001",
            "category_id": "MY-C0002",
            "title": "Photo 1",
        },
        {
            "content_id": "MY-F0002",
            "category_id": "MY-C0001",
            "title": "Photo 2",
        },
    ]

    frame_connector._tv.available = AsyncMock(return_value=mock_tv_response)

    result = await frame_connector.list_files(category=None)

    assert result is not None
    assert len(result) == 2  # Should return all files


@pytest.mark.asyncio
async def test_list_files_tv_not_connected(frame_connector):
    """Test behavior when TV is not connected."""
    frame_connector._connected = False

    result = await frame_connector.list_files()

    assert result is None
    frame_connector._tv.available.assert_not_called()


@pytest.mark.asyncio
async def test_list_files_tv_offline(frame_connector):
    """Test behavior when TV is offline."""
    frame_connector._tv_is_online = False

    result = await frame_connector.list_files()

    assert result is None
    frame_connector._tv.available.assert_not_called()


@pytest.mark.asyncio
async def test_list_files_empty_response(frame_connector):
    """Test handling of empty response from TV."""
    frame_connector._tv.available = AsyncMock(return_value=[])

    result = await frame_connector.list_files()

    assert result == []


@pytest.mark.asyncio
async def test_list_files_none_response(frame_connector):
    """Test handling of None response from TV."""
    frame_connector._tv.available = AsyncMock(return_value=None)

    result = await frame_connector.list_files()

    assert result == []


@pytest.mark.asyncio
async def test_list_files_connection_closed_error(frame_connector):
    """Test handling of connection closed error."""
    frame_connector._tv.available = AsyncMock(
        side_effect=websockets.exceptions.ConnectionClosedError(None, None)
    )
    frame_connector.close = AsyncMock()

    result = await frame_connector.list_files()

    assert result is None
    frame_connector.close.assert_called_once()


@pytest.mark.asyncio
async def test_list_files_timeout_error(frame_connector):
    """Test handling of timeout error."""
    frame_connector._tv.available = AsyncMock(side_effect=TimeoutError())

    with pytest.raises(TvConnectionTimeoutError):
        await frame_connector.list_files()


@pytest.mark.asyncio
async def test_list_files_generic_exception(frame_connector):
    """Test handling of generic exceptions."""
    frame_connector._tv.available = AsyncMock(side_effect=Exception("Unknown error"))

    result = await frame_connector.list_files()

    assert result is None


@pytest.mark.asyncio
async def test_list_files_field_mapping(frame_connector):
    """Test that fields are properly mapped from different possible names."""
    mock_tv_response = [
        {
            "content_id": "MY-F0001",
            "category_id": "MY-C0002",
            "file_name": "photo.jpg",  # Has file_name
            "file_type": "JPEG",       # Has file_type
            "extra_field": "extra_value",
        },
        {
            "content_id": "MY-F0002",
            "category_id": "MY-C0002",
            "title": "Another Photo",   # Has title instead of file_name
            "format": "PNG",            # Has format instead of file_type
            "another_field": "another_value",
        },
    ]

    frame_connector._tv.available = AsyncMock(return_value=mock_tv_response)

    result = await frame_connector.list_files()

    assert result[0]["file_name"] == "photo.jpg"  # Uses file_name directly
    assert result[0]["file_type"] == "JPEG"       # Uses file_type directly
    assert result[0]["extra_field"] == "extra_value"  # Additional field preserved

    assert result[1]["file_name"] == "Another Photo"  # Falls back to title
    assert result[1]["file_type"] == "PNG"            # Falls back to format
    assert result[1]["another_field"] == "another_value"  # Additional field preserved