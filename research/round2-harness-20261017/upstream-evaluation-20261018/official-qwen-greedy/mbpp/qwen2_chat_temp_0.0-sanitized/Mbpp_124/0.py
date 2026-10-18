import cmath
def angle_complex(real, imag):
    """
    Calculate the angle of a complex number.
    
    Args:
    real (float): The real part of the complex number.
    imag (float): The imaginary part of the complex number.
    
    Returns:
    float: The angle of the complex number in radians.
    """
    # Convert the complex number to polar coordinates
    polar_coordinates = cmath.polar(complex(real, imag))
    # Return the angle
    return polar_coordinates[1]