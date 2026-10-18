def centered_hexagonal_number(n):
    """
    Calculate the nth centered hexagonal number.
    
    Args:
    n (int): The position of the centered hexagonal number to calculate.
    
    Returns:
    int: The nth centered hexagonal number.
    """
    return 3 * n * (n - 1) + 1