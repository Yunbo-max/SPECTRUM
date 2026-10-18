import math

def volume_cone(radius, height):
    """
    Calculate the volume of a cone.
    
    Args:
    radius (float): The radius of the base of the cone.
    height (float): The height of the cone.
    
    Returns:
    float: The volume of the cone.
    """
    volume = (1/3) * math.pi * radius**2 * height
    return volume