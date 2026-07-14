from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from framegallery.database import get_db
from framegallery.dependencies import get_library_manager
from framegallery.libraries.base import AlbumRef
from framegallery.main import app
from framegallery.models import Base, Library


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide an in-memory database seeded with the default local library."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            Library(
                library_id="local",
                name="Local Gallery",
                source_type="local",
                enabled=True,
                weight=1.0,
                config={"filter_id": None},
            )
        )
        session.commit()
        yield session


@pytest.fixture
def manager_mock() -> AsyncMock:
    """Return a mocked LibraryManager for the connection/album probe endpoints."""
    manager = AsyncMock()
    manager.test_connection.return_value = {"ok": True, "version": "1.140.0"}
    manager.list_albums_for.return_value = [AlbumRef(id="album-1", name="Trip", photo_count=5)]
    manager.library_status.return_value = [
        {"id": 1, "library_id": "local", "enabled": True, "count": 1465, "error": None},
    ]
    return manager


@pytest.fixture
def client(db_session: Session, manager_mock: AsyncMock) -> Generator[TestClient, None, None]:
    """Test client with DB and manager dependencies overridden."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_library_manager] = lambda: manager_mock
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_library_manager, None)


def test_list_libraries_returns_local(client: TestClient) -> None:
    """The seeded local library is listed and marked local without an API key."""
    response = client.get("/api/libraries")
    assert response.status_code == status.HTTP_200_OK
    libraries = response.json()
    assert len(libraries) == 1
    assert libraries[0]["is_local"] is True
    assert libraries[0]["has_api_key"] is False


def test_create_immich_library_does_not_leak_api_key(client: TestClient) -> None:
    """Creating an Immich library reports has_api_key but never returns the key."""
    response = client.post(
        "/api/libraries",
        json={
            "name": "My Immich",
            "source_type": "immich",
            "base_url": "http://immich.local",
            "api_key": "secret",
            "album_ids": ["album-1"],
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["has_api_key"] is True
    assert body["base_url"] == "http://immich.local"
    assert "api_key" not in body
    assert "secret" not in response.text


def test_local_library_cannot_be_deleted(client: TestClient) -> None:
    """Deleting the local library is rejected."""
    response = client.delete("/api/libraries/1")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_update_library_weight_and_enabled(client: TestClient) -> None:
    """Weight and enabled flags can be updated."""
    response = client.put("/api/libraries/1", json={"weight": 2.5, "enabled": False})
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["weight"] == 2.5  # noqa: PLR2004
    assert body["enabled"] is False


def test_test_connection_endpoint(client: TestClient, manager_mock: AsyncMock) -> None:
    """The test-connection endpoint proxies the manager result."""
    response = client.post(
        "/api/libraries/test-connection",
        json={"base_url": "http://immich.local", "api_key": "secret"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"ok": True, "version": "1.140.0", "error": None}
    manager_mock.test_connection.assert_awaited_once()


def test_albums_endpoint(client: TestClient) -> None:
    """The albums endpoint returns the probed album list."""
    response = client.post(
        "/api/libraries/albums",
        json={"base_url": "http://immich.local", "api_key": "secret"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [{"id": "album-1", "name": "Trip", "photo_count": 5}]


def test_stored_albums_uses_saved_key(client: TestClient, manager_mock: AsyncMock) -> None:
    """Listing albums by library id reuses the stored key without re-sending it."""
    saved = client.post(
        "/api/libraries",
        json={
            "name": "Immich",
            "source_type": "immich",
            "base_url": "http://immich.local",
            "api_key": "secret",
            "album_ids": [],
        },
    ).json()

    response = client.get(f"/api/libraries/{saved['id']}/albums")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [{"id": "album-1", "name": "Trip", "photo_count": 5}]
    # The manager was called with the stored credentials, not something from the request.
    manager_mock.list_albums_for.assert_awaited_with("http://immich.local", "secret")


def test_stored_albums_rejects_local_library(client: TestClient) -> None:
    """The stored-credential album endpoint is Immich-only."""
    response = client.get("/api/libraries/1/albums")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_status_endpoint(client: TestClient) -> None:
    """The status endpoint surfaces each library's live matching-photo count."""
    response = client.get("/api/libraries/status")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body == [{"id": 1, "library_id": "local", "enabled": True, "count": 1465, "error": None}]
