from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from framegallery.database import get_db
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
