import cmath

def polar_rect(r, theta):
    """
    Convert polar coordinates (r, theta) to rectangular coordinates (x, y).
    
    Parameters:
    r (float): The radius in polar coordinates.
    theta (float): The angle in radians in polar coordinates.
    
    Returns:
    tuple: A tuple containing the rectangular coordinates (x, y).
    """
    x = r * cmath.cos(theta)
    y = r * cmath.sin(theta)
    return (x, y)