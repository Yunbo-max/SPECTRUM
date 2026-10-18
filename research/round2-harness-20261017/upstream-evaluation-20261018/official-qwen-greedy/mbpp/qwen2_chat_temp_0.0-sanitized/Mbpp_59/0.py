def is_octagonal(n):
    """
    Calculate the nth octagonal number.
    
    Args:
    n (int): The position in the sequence of octagonal numbers.
    
    Returns:
    int: The nth octagonal number.
    """
    # Formula to calculate the nth octagonal number
    return 3 * n * n - 2 * n