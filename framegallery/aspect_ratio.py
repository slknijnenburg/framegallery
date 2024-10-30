import math

def get_aspect_ratio(width: int, height: int) -> tuple[int, int]:
    gcd = math.gcd(width, height)
    aspect_width = width // gcd
    aspect_height = height // gcd
    return aspect_width, aspect_height

# Example usage:
# width = 1920
# height = 1080
# print(get_aspect_ratio(width, height))  # Output: (16, 9)