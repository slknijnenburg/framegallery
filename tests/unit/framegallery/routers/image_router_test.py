from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from framegallery.database import get_db

# Assuming your main FastAPI app instance is named 'app' in 'framegallery.main'
from framegallery.main import app
from framegallery.models import Image


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_db_session() -> MagicMock:
    """Create a mock database session."""
    db = MagicMock(spec=Session)
    # Mock the get method used in the endpoint
    db.get = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    return db


@pytest.fixture(autouse=True)
def override_get_db(mock_db_session: MagicMock) -> Generator[None, None, None]:
    """Replace the actual get_db with one that returns our mock session."""

    def _override_get_db() -> Generator[MagicMock, None, None]:
        try:
            yield mock_db_session
        finally:
            pass  # No cleanup needed for mock

    app.dependency_overrides[get_db] = _override_get_db
    yield  # Allow tests to run
    # Clean up the override after tests
    app.dependency_overrides.pop(get_db, None)


def test_crop_image_success(client: TestClient, mock_db_session: MagicMock) -> None:
    """Test successfully cropping an image."""
    image_id = 1
    # Corrected payload to be within 0-100
    crop_payload = {"x": 10.0, "y": 20.0, "width": 80.0, "height": 75.5}

    # Mock the image object that db.get should return
    mock_image = Image(id=image_id, filename="test.jpg", filepath="/path/test.jpg", filetype="image/jpeg")
    mock_db_session.get.return_value = mock_image

    response = client.post(f"/api/images/{image_id}/crop", json=crop_payload)

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["message"] == f"Crop data saved for image {image_id}"
    assert response_data["data"] == crop_payload

    # Verify database interactions
    mock_db_session.get.assert_called_once_with(Image, image_id)
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(mock_image)

    # Verify the image object was updated (before commit)
    assert mock_image.crop_x == crop_payload["x"]
    assert mock_image.crop_y == crop_payload["y"]
    assert mock_image.crop_width == crop_payload["width"]
    assert mock_image.crop_height == crop_payload["height"]


def test_crop_image_not_found(client: TestClient, mock_db_session: MagicMock) -> None:
    """Test cropping an image that does not exist."""
    image_id = 999
    # Corrected payload to be within 0-100
    crop_payload = {"x": 10, "y": 20, "width": 90, "height": 80}

    # Configure the mock session to return None when getting the image
    mock_db_session.get.return_value = None

    response = client.post(f"/api/images/{image_id}/crop", json=crop_payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Image not found"}

    # Verify database interactions
    mock_db_session.get.assert_called_once_with(Image, image_id)
    mock_db_session.commit.assert_not_called()
    mock_db_session.refresh.assert_not_called()


def test_crop_image_invalid_data(client: TestClient, mock_db_session: MagicMock) -> None:
    """Test cropping an image with invalid data."""
    image_id = 1
    # Missing 'height' field
    invalid_payload = {"x": 10, "y": 20, "width": 100}

    # Mock the image object (though it shouldn't be reached due to validation)
    mock_image = Image(id=image_id, filename="test.jpg", filepath="/path/test.jpg", filetype="image/jpeg")
    mock_db_session.get.return_value = mock_image

    response = client.post(f"/api/images/{image_id}/crop", json=invalid_payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    # Optionally, assert specific details about the validation error
    response_data = response.json()
    assert "detail" in response_data
    assert isinstance(response_data["detail"], list)
    assert any(err["loc"] == ["body", "height"] and err["type"] == "missing" for err in response_data["detail"])

    # Verify database was not called unnecessarily
    mock_db_session.get.assert_not_called()
    mock_db_session.commit.assert_not_called()
    mock_db_session.refresh.assert_not_called()
