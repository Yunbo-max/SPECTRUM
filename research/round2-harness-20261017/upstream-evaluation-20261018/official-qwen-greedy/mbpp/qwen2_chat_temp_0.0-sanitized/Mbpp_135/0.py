def hexagonal_num(n):
    """
    Calculate the nth hexagonal number.
    
    Args:
    n (int): The position of the hexagonal number in the sequence.
    
    Returns:
    int: The nth hexagonal number.
    """
    return 3 * n * (n - 1) + 1