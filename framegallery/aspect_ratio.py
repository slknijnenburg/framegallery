import math


def get_aspect_ratio(width: int, height: int) -> tuple[int, int]:
    """Calculate the aspect ratio of an image."""
    gcd = math.gcd(width, height)
    aspect_width = width // gcd
    aspect_height = height // gcd
    return aspect_width, aspect_height
