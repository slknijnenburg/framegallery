from fastapi import APIRouter, HTTPException, status, Path, Body
from pydantic import BaseModel, Field

from framegallery.schemas import CropData

router = APIRouter()


@router.post("/api/images/{image_id}/crop", status_code=status.HTTP_200_OK)
async def crop_image(
    image_id: int = Path(..., title="The ID of the image to crop", ge=1),
    crop_data: CropData = Body(...)
):
    """Recieve crop data for a specific image."""
    # For now, we'll just print the received data and return it.
    # Database interaction will be added later.
    print(f"Received crop data for image ID {image_id}: {crop_data.model_dump_json(indent=2)}")
    return {"message": f"Crop data received for image {image_id}", "data": crop_data}
