import cmath

def convert(complex_num):
    """
    Convert a complex number to polar coordinates.
    
    Args:
    complex_num (complex): The complex number to convert.
    
    Returns:
    tuple: A tuple containing the magnitude and phase angle of the complex number.
    """
    magnitude, angle = cmath.polar(complex_num)
    return magnitude, angle