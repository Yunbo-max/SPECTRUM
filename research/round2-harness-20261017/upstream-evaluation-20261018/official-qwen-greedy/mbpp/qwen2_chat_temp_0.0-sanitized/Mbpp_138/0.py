def is_Sum_Of_Powers_Of_Two(n):
    """
    Check whether the given number can be represented as sum of non-zero powers of 2 or not.
    
    Args:
    n (int): The number to check.
    
    Returns:
    bool: True if the number can be represented as sum of non-zero powers of 2, False otherwise.
    """
    # Check if the number is a power of 2
    if n & (n - 1) == 0:
        return True
    return False