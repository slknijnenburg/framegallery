import io
import logging
from pathlib import Path

from PIL import Image as PILImage

from framegallery.models import Image

# It's good practice to get a logger specific to this module
logger = logging.getLogger(__name__)

def get_file_type(image_path: str) -> str | None:
    """Try to figure out what kind of image file is, starting with the extension."""
    try:
        file_type = Path(image_path).suffix
        return file_type.lower() if file_type else None
    except Exception:
        logger.exception("Error determining file type for: %s", image_path)
        raise

def crop_image_data(file_data: bytes, crop_info: dict) -> bytes:
    """Crop image data based on percentage crop info."""
    try:
        img = PILImage.open(io.BytesIO(file_data))
        img_width, img_height = img.size

        # Calculate pixel coordinates from percentages
        x_pct = crop_info.get("x", 0)
        y_pct = crop_info.get("y", 0)
        width_pct = crop_info.get("width", 100)
        height_pct = crop_info.get("height", 100)

        left = int(img_width * x_pct / 100)
        top = int(img_height * y_pct / 100)
        right = left + int(img_width * width_pct / 100)
        bottom = top + int(img_height * height_pct / 100)

        # Ensure crop box is within image bounds and valid
        left = max(0, left)
        top = max(0, top)
        right = min(img_width, right)
        bottom = min(img_height, bottom)

        if left >= right or top >= bottom:
            logger.warning("Calculated invalid crop box for image, returning original image.")
            return file_data

        logger.info(
            "Cropping image: original=(%sx%s), box=(%s,%s,%s,%s)",
            img_width, img_height, left, top, right, bottom
        )
        cropped_img = img.crop((left, top, right, bottom))

        # Save cropped image back to bytes
        buffer = io.BytesIO()
        cropped_img.save(buffer, format="JPEG")
        return buffer.getvalue()
    except Exception:
        logger.exception("Error cropping image data")
        return file_data

def read_file_data(image: Image) -> tuple[bytes, str]:
    """Read image file data, crop if necessary, and return bytes and file type."""
    image_path_str = image.filepath
    if not image_path_str:
        # Handle case where filepath might be None or empty on the Image object
        err_msg = f"Image filepath is not set for image ID {image.id}."
        logger.error(err_msg)
        raise FileNotFoundError(err_msg)

    image_path = Path(image_path_str)

    if not image_path.exists():
        logger.error("Image file not found at path: %s for image ID %s", image_path_str, image.id)
        # EM102 & TRY003: Assign formatted string to variable first
        error_message = f"Image file not found at {image_path_str}"
        raise FileNotFoundError(error_message)

    crop_info = None
    if (
        image.crop_x is not None
        and image.crop_y is not None
        and image.crop_width is not None
        and image.crop_height is not None
    ):
        crop_info = {
            "x": image.crop_x,
            "y": image.crop_y,
            "width": image.crop_width,
            "height": image.crop_height,
        }
        logger.info("Crop info found for image %s: %s", image.id, crop_info)

    with image_path.open("rb") as f:
        file_data = f.read()

    file_type_suffix = image_path.suffix.lower()

    if crop_info:
        try:
            logger.info("Attempting to crop image %s (type: %s)", image.id, file_type_suffix)
            file_data = crop_image_data(file_data, crop_info)
            file_type_suffix = ".jpeg"
            logger.info("Successfully cropped image %s, new type: %s", image.id, file_type_suffix)
        except Exception:
            logger.exception(
                "Failed to crop image %s. Returning original image.", image.id
            )
            with image_path.open("rb") as f:
                file_data = f.read()
            file_type_suffix = image_path.suffix.lower()

    return file_data, file_type_suffix
