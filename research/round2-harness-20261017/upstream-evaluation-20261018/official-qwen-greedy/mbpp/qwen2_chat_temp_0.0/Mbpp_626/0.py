import math

def triangle_area(radius):
    if radius < 0:
        return None
    # The formula for the area of a triangle inscribed in a semicircle is (1/2) * r^2 * sin(180 degrees)
    area = (1/2) * radius**2 * math.sin(math.radians(180))
    return area