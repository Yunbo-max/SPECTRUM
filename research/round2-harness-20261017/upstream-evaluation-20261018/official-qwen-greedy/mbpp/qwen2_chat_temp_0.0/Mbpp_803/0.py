import math

def is_perfect_square(n):
    """
    Check whether the given number is a perfect square or not.
    
    Args:
    n (int): The number to check.
    
    Returns:
    bool: True if n is a perfect square, False otherwise.
    """
    if n < 0:
        return False
    root = math.isqrt(n)
    return root * root == n