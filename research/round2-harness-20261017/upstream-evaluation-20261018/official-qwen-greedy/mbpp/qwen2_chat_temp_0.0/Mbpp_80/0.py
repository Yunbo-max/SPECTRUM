def tetrahedral_number(n):
    """
    Calculate the nth tetrahedral number.
    
    Args:
    n (int): The position in the tetrahedral sequence.
    
    Returns:
    int: The nth tetrahedral number.
    """
    return n * (n + 1) * (n + 2) // 6