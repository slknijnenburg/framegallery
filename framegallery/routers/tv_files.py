from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from framegallery.dependencies import get_frame_connector
from framegallery.frame_connector.frame_connector import FrameConnector, TvConnectionTimeoutError
from framegallery.logging_config import setup_logging
from framegallery.schemas import TvFileResponse

router = APIRouter()
logger = setup_logging()


class DeleteFilesRequest(BaseModel):
    """Request model for deleting multiple TV files."""

    content_ids: list[str]


class DeleteFilesResponse(BaseModel):
    """Response model for multi-file deletion."""

    deleted_count: int
    failed_count: int
    results: dict[str, bool]


def _raise_tv_unavailable() -> None:
    """Raise HTTP exception for TV unavailable."""
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="TV is not connected or unavailable")


def _raise_file_not_found(content_id: str) -> None:
    """Raise HTTP exception for file not found."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"File with content_id '{content_id}' not found or could not be deleted",
    )


@router.get("/api/tv/files", status_code=status.HTTP_200_OK)
async def list_tv_files(
    frame_connector: Annotated[FrameConnector, Depends(get_frame_connector)],
    category: str = "MY-C0002",
) -> list[TvFileResponse]:
    """
    List all files available on the Samsung Frame TV.

    Args:
        frame_connector: Injected FrameConnector instance
        category: The image folder/category on the TV (default: "MY-C0002" for user content)

    Returns:
        List of TV files with metadata

    Raises:
        HTTPException: 503 if TV is unavailable, 500 for other errors

    """
    try:
        logger.info("Fetching TV files for category: %s", category)

        # Call the FrameConnector's list_files method
        tv_files = await frame_connector.list_files(category=category)

        if tv_files is None:
            logger.warning("TV is not connected or files could not be retrieved")
            _raise_tv_unavailable()
        else:
            # Transform the raw TV response to our schema format
            response_files = []
            for file_data in tv_files:
                # Map the TV response fields to our schema
                # The list_files method already normalizes field names
                tv_file = TvFileResponse(
                    content_id=file_data.get("content_id", ""),
                    file_name=file_data.get("file_name", "Unknown"),
                    file_type=file_data.get("file_type", "Unknown"),
                    file_size=file_data.get("file_size"),
                    width=file_data.get("width"),
                    height=file_data.get("height"),
                    date=file_data.get("date"),
                    category_id=file_data.get("category_id", category),
                    thumbnail_available=file_data.get("thumbnail_available"),
                    matte=file_data.get("matte"),
                )
                response_files.append(tv_file)

            logger.info("Successfully retrieved %d files from TV", len(response_files))
            return response_files

    except TvConnectionTimeoutError as e:
        logger.exception("TV connection timeout while listing files")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="TV connection timeout") from e
    except HTTPException:
        # Re-raise HTTPExceptions (like our TV unavailable exception) without logging
        raise
    except Exception as e:
        logger.exception("Unexpected error while listing TV files")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error while retrieving TV files"
        ) from e


@router.delete("/api/tv/files/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tv_file(
    content_id: str,
    frame_connector: Annotated[FrameConnector, Depends(get_frame_connector)],
) -> None:
    """
    Delete a file from the Samsung Frame TV.

    Args:
        content_id: The content ID of the file to delete
        frame_connector: Injected FrameConnector instance

    Raises:
        HTTPException: 503 if TV is unavailable, 404 if file not found, 500 for other errors

    """
    try:
        logger.info("Deleting TV file with content_id: %s", content_id)

        # Use the multi-delete functionality for consistency
        results = await frame_connector.delete_files([content_id])

        if results is None:
            logger.warning("TV is not connected or file could not be deleted")
            _raise_tv_unavailable()
        elif not results.get(content_id, False):
            logger.warning("File with content_id %s not found or could not be deleted", content_id)
            _raise_file_not_found(content_id)
        else:
            logger.info("Successfully deleted file with content_id: %s", content_id)

    except TvConnectionTimeoutError as e:
        logger.exception("TV connection timeout while deleting file")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="TV connection timeout") from e
    except HTTPException:
        # Re-raise HTTPExceptions (like our TV unavailable exception) without logging
        raise
    except Exception as e:
        logger.exception("Unexpected error while deleting TV file")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error while deleting TV file"
        ) from e


@router.post("/api/tv/files/delete", status_code=status.HTTP_200_OK)
async def delete_tv_files(
    request: DeleteFilesRequest,
    frame_connector: Annotated[FrameConnector, Depends(get_frame_connector)],
) -> DeleteFilesResponse:
    """
    Delete multiple files from the Samsung Frame TV.

    Args:
        request: Request containing list of content IDs to delete
        frame_connector: Injected FrameConnector instance

    Returns:
        DeleteFilesResponse with deletion results

    Raises:
        HTTPException: 503 if TV is unavailable, 400 for invalid request, 500 for other errors

    """
    if not request.content_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No content IDs provided for deletion")

    try:
        logger.info("Deleting %d TV files: %s", len(request.content_ids), request.content_ids)

        # Call the FrameConnector's delete_files method
        results = await frame_connector.delete_files(request.content_ids)

        if results is None:
            logger.warning("TV is not connected or files could not be deleted")
            _raise_tv_unavailable()
        else:
            # Count successful and failed deletions
            deleted_count = sum(1 for success in results.values() if success)
            failed_count = len(results) - deleted_count

            logger.info("Multi-file deletion completed: %d deleted, %d failed", deleted_count, failed_count)

            return DeleteFilesResponse(deleted_count=deleted_count, failed_count=failed_count, results=results)

    except TvConnectionTimeoutError as e:
        logger.exception("TV connection timeout while deleting files")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="TV connection timeout") from e
    except HTTPException:
        # Re-raise HTTPExceptions (like our TV unavailable exception) without logging
        raise
    except Exception as e:
        logger.exception("Unexpected error while deleting TV files")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error while deleting TV files"
        ) from e
