import math

def lateralsurface_cylinder(radius, height):
    """
    Calculate the lateral surface area of a cylinder.
    
    Parameters:
    radius (float): The radius of the cylinder.
    height (float): The height of the cylinder.
    
    Returns:
    float: The lateral surface area of the cylinder.
    """
    lateral_surface = 2 * math.pi * radius * height
    return lateral_surface