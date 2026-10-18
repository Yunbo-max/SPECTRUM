def next_power_of_2(n):
    """
    Find the smallest power of 2 greater than or equal to n.
    
    Args:
    n (int): The number to find the next power of 2 for.
    
    Returns:
    int: The smallest power of 2 greater than or equal to n.
    """
    if n == 0:
        return 1
    power = 1
    while power < n:
        power *= 2
    return power