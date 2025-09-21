from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from framegallery.dependencies import get_frame_connector
from framegallery.frame_connector.frame_connector import FrameConnector, TvConnectionTimeoutError
from framegallery.logging_config import setup_logging
from framegallery.schemas import TvFileResponse

router = APIRouter()
logger = setup_logging()


def _raise_tv_unavailable() -> None:
    """Raise HTTP exception for TV unavailable."""
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="TV is not connected or unavailable")


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
