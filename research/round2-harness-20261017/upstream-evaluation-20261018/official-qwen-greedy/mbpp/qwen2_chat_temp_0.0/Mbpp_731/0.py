import math

def lateralsurface_cone(r, h):
    """
    Calculate the lateral surface area of a cone given the radius r and height h.
    
    Parameters:
    r (float): The radius of the base of the cone.
    h (float): The height of the cone.
    
    Returns:
    float: The lateral surface area of the cone.
    """
    lateral_surface = math.pi * r * h
    return lateral_surface