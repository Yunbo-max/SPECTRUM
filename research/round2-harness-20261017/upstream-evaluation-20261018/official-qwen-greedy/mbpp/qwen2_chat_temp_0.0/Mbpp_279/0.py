def is_num_decagonal(n):
    """
    Calculate the nth decagonal number.
    
    Args:
    n (int): The position of the decagonal number to calculate.
    
    Returns:
    int: The nth decagonal number.
    """
    return 5 * n * (n - 1) // 2