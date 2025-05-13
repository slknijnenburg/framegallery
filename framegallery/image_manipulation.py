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

def crop_image_data(file_data: bytes, crop_info: dict, image_format: str) -> bytes:
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
        save_format = image_format.lstrip(".").upper()
        if save_format == "JPG":
            save_format = "JPEG"
        supported_formats = ["JPEG", "PNG", "GIF", "BMP", "TIFF"]
        if save_format not in supported_formats:
            logger.warning("Unsupported save format '%s', defaulting to JPEG.", save_format)
            save_format = "JPEG"

        cropped_img.save(buffer, format=save_format)
        return buffer.getvalue()
    except Exception:
        logger.exception("Error cropping image data")
        return file_data

def read_file_data(image: Image) -> tuple[bytes, str]:
    """Read image file, optionally crop it, and return file binary data and file type."""
    image_path = image.filepath
    try:
        with Path(image_path).open("rb") as f:
            file_data = f.read()
            file_type = get_file_type(image_path)

            if not file_type:
                logger.warning("Could not determine file type for %s, skipping crop.", image_path)
                return file_data, "image/jpeg"

            # Construct crop_info from Image object
            crop_info = None
            if image.crop_width is not None and image.crop_height is not None and \
               image.crop_x is not None and image.crop_y is not None:
                crop_info = {
                    "x": image.crop_x,
                    "y": image.crop_y,
                    "width": image.crop_width,
                    "height": image.crop_height,
                }

            if crop_info:
                logger.info("Applying crop %s to %s", crop_info, image_path)
                file_data = crop_image_data(file_data, crop_info, file_type)

            return file_data, file_type
    except FileNotFoundError:
        logger.exception("File not found: %s", image_path)
        raise
    except Exception:
        logger.exception("Error reading or processing file: %s", image_path)
        raise
