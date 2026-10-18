import math
def next_Perfect_Square(n):
    """
    Find the next perfect square greater than the given number.
    
    Args:
    n (int): The number to find the next perfect square for.
    
    Returns:
    int: The next perfect square greater than n.
    """
    # Calculate the square root of n
    root = math.sqrt(n)
    # Find the next integer greater than the square root
    next_root = math.ceil(root)
    # Return the square of the next integer
    return next_root ** 2