def parabola_directrix(a, b, c):
    """
    Calculate the directrix of a parabola given its coefficients a, b, and c.
    
    Args:
    a (float): The coefficient of x^2.
    b (float): The coefficient of x.
    c (float): The constant term.
    
    Returns:
    float: The directrix of the parabola.
    """
    # Calculate the discriminant
    discriminant = b**2 - 4*a*c
    
    # Calculate the directrix
    if discriminant < 0:
        # If the discriminant is negative, the parabola opens upwards
        directrix = -c / (2*a)
    else:
        # If the discriminant is non-negative, the parabola opens downwards
        directrix = -c / (2*a) - b / (2*a)
    
    return directrix