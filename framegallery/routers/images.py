from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from framegallery.database import get_db
from framegallery.image_manipulation import read_file_data
from framegallery.logging_config import setup_logging
from framegallery.models import Image
from framegallery.schemas import CropData

router = APIRouter()
logger = setup_logging()

@router.post("/api/images/{image_id}/crop", status_code=status.HTTP_200_OK)
async def crop_image(
    image_id: int,
    crop_data: CropData,
    db: Annotated[Session, Depends(get_db)]
) -> dict:
    """Receive crop data for a specific image and save it to the database."""
    # Fetch the image from the database
    db_image = db.get(Image, image_id)
    if not db_image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    # Update the crop attributes
    db_image.crop_x = crop_data.x
    db_image.crop_y = crop_data.y
    db_image.crop_width = crop_data.width
    db_image.crop_height = crop_data.height

    # Commit the changes
    db.commit()
    db.refresh(db_image)

    logger.info(
        "Saved crop data for image ID %s: %s",
        image_id,
        crop_data.model_dump_json(indent=2)
    )
    return {"message": f"Crop data saved for image {image_id}", "data": crop_data}

@router.get("/api/images/{image_id}/cropped")
async def get_cropped_image(
    image_id: int,
    db: Annotated[Session, Depends(get_db)]
) -> Response:
    """Retrieve an image, cropped according to its stored details."""
    db_image = db.get(Image, image_id)
    if not db_image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    try:
        image_bytes, file_type_suffix = read_file_data(db_image)
    except FileNotFoundError as fnf_error:
        logger.exception("File not found for image ID %s at path %s", image_id, db_image.filepath)
        detail_message = "Image file not found on server"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail_message
        ) from fnf_error
    except Exception as e:
        logger.exception("Error reading or cropping image ID %s", image_id)
        detail_message_generic = "Error processing image"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail_message_generic
        ) from e

    # Determine media type based on file suffix
    media_type = "application/octet-stream" # Default
    if file_type_suffix:
        s = file_type_suffix.lower()
        if s in {".jpeg", ".jpg"}:
            media_type = "image/jpeg"
        elif s == ".png":
            media_type = "image/png"
        elif s == ".gif":
            media_type = "image/gif"
        elif s == ".bmp":
            media_type = "image/bmp"
        elif s in {".tiff", ".tif"}:
            media_type = "image/tiff"
        # Add more types as needed

    logger.info("Serving cropped image ID %s, type: %s", image_id, media_type)
    return Response(content=image_bytes, media_type=media_type)
